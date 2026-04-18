import uuid
from PyQt6.QtWidgets import QGraphicsObject, QGraphicsItem, QGraphicsTextItem
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont,
    QPainterPath, QTextCursor, QTextCharFormat,
)

from constants import (
    STICKY_DEFAULT_W, STICKY_DEFAULT_H, STICKY_MIN_W, STICKY_MIN_H,
    STICKY_DEFAULT_BG, STICKY_DEFAULT_TEXT, STICKY_FONT_SIZE, STICKY_CORNER_RADIUS,
    CANVAS_GRID_STEP, FONT_FAMILY, BOX_SELECTED_BORDER,
)

# ── Handle 索引（與 ShapeItem 相同規範）──────────────────────────────────────
H_TL, H_T, H_TR, H_R, H_BR, H_B, H_BL, H_L = range(8)
HS = 4   # handle 半尺寸

HANDLE_CURSORS = {
    H_TL: Qt.CursorShape.SizeFDiagCursor,
    H_TR: Qt.CursorShape.SizeBDiagCursor,
    H_BR: Qt.CursorShape.SizeFDiagCursor,
    H_BL: Qt.CursorShape.SizeBDiagCursor,
    H_T:  Qt.CursorShape.SizeVerCursor,
    H_B:  Qt.CursorShape.SizeVerCursor,
    H_L:  Qt.CursorShape.SizeHorCursor,
    H_R:  Qt.CursorShape.SizeHorCursor,
}


# ── 行內可編輯文字（私有）────────────────────────────────────────────────────

class _StickyText(QGraphicsTextItem):
    """便利貼行內文字，掛在 StickyNoteItem 下。"""

    def __init__(self, text: str, color: str, size: int, parent):
        super().__init__(text, parent)
        self.setDefaultTextColor(QColor(color))
        self.setFont(QFont(FONT_FAMILY, size))
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.setFlag(self.GraphicsItemFlag.ItemIsSelectable, False)

    def start_edit(self):
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
        self.setAcceptedMouseButtons(Qt.MouseButton.AllButtons)
        self.setFocus()
        cur = self.textCursor()
        cur.select(QTextCursor.SelectionType.Document)
        self.setTextCursor(cur)
        scene = self.scene()
        if scene and hasattr(scene, 'text_editing_started'):
            scene.text_editing_started.emit(self)

    def stop_edit(self):
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.clearFocus()
        scene = self.scene()
        if scene and hasattr(scene, 'text_editing_stopped'):
            scene.text_editing_stopped.emit()

    def apply_char_format(self, fmt: QTextCharFormat):
        cur = self.textCursor()
        if not cur.hasSelection():
            return
        cur.mergeCharFormat(fmt)
        self.setTextCursor(cur)

    def focusOutEvent(self, e):
        # 不在此自動 stop_edit，由 canvas_view 統一控制
        super().focusOutEvent(e)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.stop_edit()
        else:
            super().keyPressEvent(e)

    @property
    def plain_text(self) -> str:
        return self.toPlainText()


# ── StickyNoteItem ────────────────────────────────────────────────────────────

class StickyNoteItem(QGraphicsObject):
    """
    便利貼 Item：
    - 可移動、Resize（8 handles）、Grid Snap、Smart Guide
    - 雙擊行內編輯
    - 9 個連線錨點（可接 LineItem）
    - ColorPopup 控制底色 / 字色 / 字型大小
    - to_dict / from_dict 序列化
    """

    def __init__(self, width: float = STICKY_DEFAULT_W,
                 height: float = STICKY_DEFAULT_H, parent=None):
        super().__init__(parent)
        self._id      = str(uuid.uuid4())
        self._width   = float(width)
        self._height  = float(height)
        self._bg_color   = QColor(STICKY_DEFAULT_BG)
        self._text_color = QColor(STICKY_DEFAULT_TEXT)
        self._font_size  = STICKY_FONT_SIZE
        self._connections: list = []

        # 行內文字
        self._body = _StickyText("便利貼", STICKY_DEFAULT_TEXT, STICKY_FONT_SIZE, self)

        # Resize 狀態
        self._resizing  = False
        self._rh        = -1
        self._rm        = QPointF()
        self._rp        = QPointF()
        self._rw        = 0.0
        self._rh_size   = 0.0

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable    |
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self._layout_text()

    # ── 文字排版 ───────────────────────────────────────────────────────────────

    def _layout_text(self):
        pad = 10
        self._body.setTextWidth(self._width - pad * 2)
        self._body.setPos(pad, pad)

    # ── QGraphicsItem 必實作 ───────────────────────────────────────────────────

    def boundingRect(self) -> QRectF:
        p = HS + 2
        return QRectF(-p, -p, self._width + p * 2, self._height + p * 2)

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        path.addRoundedRect(
            QRectF(0, 0, self._width, self._height),
            STICKY_CORNER_RADIUS, STICKY_CORNER_RADIUS
        )
        return path

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        sel  = self.isSelected()
        rect = QRectF(0, 0, self._width, self._height)

        # 主體
        border_col = QColor(BOX_SELECTED_BORDER) if sel else self._bg_color.darker(125)
        painter.setPen(QPen(border_col, 1.5))
        painter.setBrush(QBrush(self._bg_color))
        painter.drawRoundedRect(rect, STICKY_CORNER_RADIUS, STICKY_CORNER_RADIUS)

        # 折角（右上）
        fold = 14
        fold_path = QPainterPath()
        fold_path.moveTo(self._width - fold, 0)
        fold_path.lineTo(self._width,        0)
        fold_path.lineTo(self._width,        fold)
        fold_path.closeSubpath()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self._bg_color.darker(140)))
        painter.drawPath(fold_path)

        # 折角分隔線
        painter.setPen(QPen(self._bg_color.darker(160), 1))
        painter.drawLine(
            QPointF(self._width - fold, 0),
            QPointF(self._width - fold, fold)
        )
        painter.drawLine(
            QPointF(self._width - fold, fold),
            QPointF(self._width,        fold)
        )

        if sel:
            self._draw_handles(painter)

    # ── Handles ───────────────────────────────────────────────────────────────

    def _handle_rects(self) -> list[QRectF]:
        w, h = self._width, self._height
        sz   = HS * 2
        return [
            QRectF(-HS,    -HS,    sz, sz), QRectF(w/2-HS, -HS,    sz, sz),
            QRectF(w-HS,   -HS,    sz, sz), QRectF(w-HS,   h/2-HS, sz, sz),
            QRectF(w-HS,   h-HS,   sz, sz), QRectF(w/2-HS, h-HS,   sz, sz),
            QRectF(-HS,    h-HS,   sz, sz), QRectF(-HS,    h/2-HS, sz, sz),
        ]

    def _handle_at(self, pos: QPointF) -> int:
        for i, r in enumerate(self._handle_rects()):
            if r.contains(pos):
                return i
        return -1

    def _draw_handles(self, painter: QPainter):
        painter.setPen(QPen(QColor(BOX_SELECTED_BORDER), 1))
        painter.setBrush(QBrush(self._bg_color))
        for r in self._handle_rects():
            painter.drawRect(r)

    # ── Mouse Events ──────────────────────────────────────────────────────────

    def mousePressEvent(self, e):
        if self.isSelected() and e.button() == Qt.MouseButton.LeftButton:
            h = self._handle_at(e.pos())
            if h >= 0:
                self._resizing = True
                self._rh       = h
                self._rm       = self.mapToScene(e.pos())
                self._rp       = self.pos()
                self._rw       = self._width
                self._rh_size  = self._height
                e.accept()
                return
        self._drag_start_pos = self.pos()   # ← 記錄移動起點
        self._resizing = False
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._resizing:
            sp = self.mapToScene(e.pos())
            self._apply_resize(sp.x() - self._rm.x(), sp.y() - self._rm.y())
            e.accept()
        else:
            super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        scene = self.scene()
        if self._resizing:
            self._resizing = False
            if scene and hasattr(scene, 'push_resize_cmd'):
                scene.push_resize_cmd(
                    self,
                    self._rp,   self._rw,    self._rh_size,
                    self.pos(), self._width, self._height,
                )
            if scene and hasattr(scene, 'clear_guides'):
                scene.clear_guides()
            e.accept()
        else:
            super().mouseReleaseEvent(e)
            if scene and hasattr(scene, 'push_move_cmd'):
                start = getattr(self, '_drag_start_pos', None)
                if start is not None and start != self.pos():
                    scene.push_move_cmd(self, start, self.pos())

    def mouseDoubleClickEvent(self, e):
        self._body.start_edit()
        e.accept()

    def hoverMoveEvent(self, e):
        if self.isSelected():
            h = self._handle_at(e.pos())
            if h >= 0:
                self.setCursor(HANDLE_CURSORS[h])
                return
        self.setCursor(Qt.CursorShape.SizeAllCursor)

    def hoverLeaveEvent(self, e):
        self.unsetCursor()

    # ── Resize ────────────────────────────────────────────────────────────────

    def _apply_resize(self, dx: float, dy: float):
        h   = self._rh
        sw, sh = self._rw, self._rh_size
        ox, oy = self._rp.x(), self._rp.y()
        nx, ny, nw, nh = ox, oy, sw, sh

        if h in (H_TR, H_R,  H_BR): nw = sw + dx
        if h in (H_BL, H_B,  H_BR): nh = sh + dy
        if h in (H_TL, H_L,  H_BL): nx = ox + dx; nw = sw - dx
        if h in (H_TL, H_T,  H_TR): ny = oy + dy; nh = sh - dy

        if nw < STICKY_MIN_W:
            nw = STICKY_MIN_W
            if h in (H_TL, H_L, H_BL): nx = ox + sw - STICKY_MIN_W
        if nh < STICKY_MIN_H:
            nh = STICKY_MIN_H
            if h in (H_TL, H_T, H_TR): ny = oy + sh - STICKY_MIN_H

        self.prepareGeometryChange()
        self._width  = nw
        self._height = nh
        self.setPos(nx, ny)
        self._layout_text()
        self._notify_connections()

    # ── Item Change ───────────────────────────────────────────────────────────

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            if self._resizing:
                s = CANVAS_GRID_STEP
                return QPointF(round(value.x() / s) * s, round(value.y() / s) * s)
            scene = self.scene()
            if scene and hasattr(scene, 'snap_to_guides_or_grid'):
                return scene.snap_to_guides_or_grid(self, value)
            s = CANVAS_GRID_STEP
            return QPointF(round(value.x() / s) * s, round(value.y() / s) * s)
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self._notify_connections()
        return super().itemChange(change, value)

    def _notify_connections(self):
        for line in self._connections:
            line.update_path()

    # ── 連線錨點（9 個，供 LineItem / ToolController 使用）──────────────────

    def get_anchor_points(self) -> list[QPointF]:
        """4 個基本錨點：上右下左中點，確保箭頭垂直進入形狀。"""
        w, h   = self._width, self._height
        cx, cy = w / 2, h / 2
        local  = [
            QPointF(cx, 0),    # 上中
            QPointF(w,  cy),   # 右中
            QPointF(cx, h),    # 下中
            QPointF(0,  cy),   # 左中
        ]
        return [self.mapToScene(p) for p in local]

    def get_connection_point(self, from_scene: QPointF) -> QPointF:
        return min(
            self.get_anchor_points(),
            key=lambda p: (p.x() - from_scene.x()) ** 2 + (p.y() - from_scene.y()) ** 2
        )

    def add_connection(self, line):
        if line not in self._connections:
            self._connections.append(line)

    def remove_connection(self, line):
        if line in self._connections:
            self._connections.remove(line)

    # ── 屬性（供 ColorPopup 用）──────────────────────────────────────────────

    @property
    def bg_color(self)   -> QColor: return self._bg_color
    @property
    def text_color(self) -> QColor: return self._text_color
    @property
    def font_size(self)  -> int:    return self._font_size

    def set_bg_color(self, c):
        self._bg_color = QColor(c)
        self.update()

    def set_text_color(self, c):
        self._text_color = QColor(c)
        self._body.setDefaultTextColor(self._text_color)
        self._body.update()

    def set_font_size(self, s: int):
        self._font_size = s
        self._body.setFont(QFont(FONT_FAMILY, s))
        self._layout_text()
        self.update()

    # ── 序列化 ────────────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "type":       "sticky",
            "id":         self._id,
            "x":          self.pos().x(),
            "y":          self.pos().y(),
            "w":          self._width,
            "h":          self._height,
            "bg_color":   self._bg_color.name(),
            "text_color": self._text_color.name(),
            "font_size":  self._font_size,
            "text":       self._body.plain_text,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "StickyNoteItem":
        item = cls(d.get("w", STICKY_DEFAULT_W), d.get("h", STICKY_DEFAULT_H))
        item.setPos(d.get("x", 0), d.get("y", 0))
        item._bg_color   = QColor(d.get("bg_color",   STICKY_DEFAULT_BG))
        item._text_color = QColor(d.get("text_color", STICKY_DEFAULT_TEXT))
        item._font_size  = d.get("font_size", STICKY_FONT_SIZE)
        item._body.setPlainText(d.get("text", ""))
        item._body.setDefaultTextColor(item._text_color)
