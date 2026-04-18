# 檔案位置：canvas/canvas_view.py

from PyQt6.QtWidgets import QGraphicsView
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QWheelEvent, QMouseEvent, QKeyEvent

from constants import CANVAS_BG, ToolMode
from theme import theme as _theme


class CanvasView(QGraphicsView):

    ZOOM_FACTOR = 1.15
    ZOOM_MIN    = 0.1
    ZOOM_MAX    = 5.0

    def __init__(self, scene, tool_controller, parent=None):
        super().__init__(scene, parent)
        self._tool_ctrl    = tool_controller
        self._zoom_level   = 1.0
        self._panning      = False
        self._pan_start    = QPoint()
        self._space_held   = False
        self._text_toolbar = None
        self._editing_item = None   # ★ 直接追蹤正在編輯的物件
        self._setup_view()
        scene.text_editing_started.connect(self._on_text_editing_started)
        scene.text_editing_stopped.connect(self._on_text_editing_stopped)

    def _setup_view(self):
        from PyQt6.QtWidgets import QGraphicsView as GV
        self.setRenderHint(self.renderHints().Antialiasing)
        self.setDragMode(GV.DragMode.RubberBandDrag)
        self.setTransformationAnchor(GV.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(GV.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet(f"background: {CANVAS_BG}; border: none;")

    def apply_theme(self):
        """切換主題後更新 canvas view 背景色。"""
        self.setStyleSheet(f"background: {_theme.get('canvas_bg')}; border: none;")
        self.viewport().update()

    def set_text_toolbar(self, toolbar):
        self._text_toolbar = toolbar

    def _on_text_editing_started(self, item):
        self._editing_item = item          # ★ 記住正在編輯的物件
        if self._text_toolbar:
            self._text_toolbar.show_for(item)

    def _on_text_editing_stopped(self):
        self._editing_item = None
        if self._text_toolbar:
            self._text_toolbar.hide_toolbar()

    def _exit_text_editing(self):
        """
        直接呼叫 stop_edit()，不依賴 Qt focus 機制，保證一定結束編輯。
        ★ 先清 cursor selection，再 stop_edit，防止反白視覺殘留。
        """
        if self._editing_item is not None:
            item = self._editing_item
            self._editing_item = None   # 先清，避免訊號循環
            # ★ 直接清除 QTextCursor 選取，解決反白殘留問題
            try:
                cur = item.textCursor()
                cur.clearSelection()
                item.setTextCursor(cur)
            except Exception:
                pass
            item.stop_edit()
            self.scene().clearSelection()

    def _click_is_on_editing_item(self, scene_pos) -> bool:
        """點擊是否在目前編輯物件的範圍內（讓 text item 內部點擊繼續正常）。"""
        if self._editing_item is None:
            return False
        # editing_item 可能是子 item（_EditText, _StickyText），取 top-level
        top = self._editing_item
        while top.parentItem() is not None:
            top = top.parentItem()
        return top.sceneBoundingRect().contains(scene_pos)

    # ── 事件 ──────────────────────────────────────────────────────────────────

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = self.ZOOM_FACTOR if event.angleDelta().y() > 0 else 1 / self.ZOOM_FACTOR
            new_z  = self._zoom_level * factor
            if self.ZOOM_MIN <= new_z <= self.ZOOM_MAX:
                self._zoom_level = new_z
                self.scale(factor, factor)
        else:
            super().wheelEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            if self._editing_item is not None:          # ← 加這個判斷
               super().keyPressEvent(event)
               return
            self._space_held = True
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        elif event.key() == Qt.Key.Key_Delete:
            # 編輯中不要觸發刪除物件
            if self._editing_item is None:
                focused = self.scene().focusItem()
                if focused is not None:
                    # 有 focus 的 item（如 TableItem）自己處理 Delete
                    self.scene().sendEvent(focused, event)
                else:
                    self.scene().delete_selected()
        elif event.key() == Qt.Key.Key_Escape:
            if self._editing_item is not None:
                self._exit_text_editing()
            else:
                self._tool_ctrl._cancel_preview()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self._space_held = False
            self._panning    = False
            self.unsetCursor()
        else:
            super().keyReleaseEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.MiddleButton or (
            self._space_held and event.button() == Qt.MouseButton.LeftButton
        ):
            self._exit_text_editing()
            self._panning   = True
            self._pan_start = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return

        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.pos())

            # ★ 核心修正：任何點擊，只要不在正在編輯的物件上，就結束編輯
            if not self._click_is_on_editing_item(scene_pos):
                self._exit_text_editing()

            if self._tool_ctrl.current_mode == ToolMode.SELECT:
                items_at_pos = self.scene().items(scene_pos)
                selectable_items = [
                    i for i in items_at_pos
                    if hasattr(i, 'flags') and
                    i.flags() & i.GraphicsItemFlag.ItemIsSelectable
                ]
                if not selectable_items:
                    self._panning   = True
                    self._pan_start = event.pos()
                    self.setCursor(Qt.CursorShape.ClosedHandCursor)
                    return

        mode     = self._tool_ctrl.current_mode
        consumed = self._tool_ctrl.on_mouse_press(event, self.mapToScene(event.pos()))

        if mode == ToolMode.SELECT and not consumed:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._panning:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            return

        self._tool_ctrl.on_mouse_move(event, self.mapToScene(event.pos()))

        if (self._tool_ctrl.current_mode == ToolMode.SELECT
                and not self._tool_ctrl.is_ep_dragging
                and not self._tool_ctrl.is_wp_dragging):
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._panning and event.button() in (
            Qt.MouseButton.MiddleButton, Qt.MouseButton.LeftButton
        ):
            self._panning = False
            if self._space_held:
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                self.unsetCursor()
            return

        was_ep_drag = self._tool_ctrl.is_ep_dragging
        was_wp_drag = self._tool_ctrl.is_wp_dragging
        self._tool_ctrl.on_mouse_release(event, self.mapToScene(event.pos()))

        if (self._tool_ctrl.current_mode == ToolMode.SELECT
                and not was_ep_drag and not was_wp_drag):
            super().mouseReleaseEvent(event)

        if hasattr(self.scene(), 'clear_guides'):
            self.scene().clear_guides()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        self._tool_ctrl.on_double_click(event, self.mapToScene(event.pos()))
        super().mouseDoubleClickEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._text_toolbar:
            self._text_toolbar.reposition()
