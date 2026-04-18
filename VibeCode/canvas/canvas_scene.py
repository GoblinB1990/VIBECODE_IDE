"""
canvas_scene.py

CanvasScene — QGraphicsScene 子類。
- Undo Stack（30 步）
- Smart Guide 對齊輔助線（pool 預分配）
- itemChange → add/remove 連線管理
- text_editing_started / text_editing_stopped → TextStyleToolbar
"""
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsLineItem
from PyQt6.QtCore import pyqtSignal, QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPen, QBrush, QUndoStack, QUndoCommand

from constants import (
    CANVAS_BG, CANVAS_GRID_COLOR, CANVAS_GRID_STEP,
    GUIDE_COLOR, GUIDE_SNAP_RADIUS, GUIDE_MAX_POOL,
)
from theme import theme as _theme

UNDO_LIMIT = 30

# 深/淺主題下 Shape 的預設底色與邊框色（用於切換時自動更新）
_DARK_BG     = "#24283b"
_DARK_BORDER = "#7aa2f7"
_LIGHT_BG    = "#f5f1eb"
_LIGHT_BORDER = "#4a6fa5"


# ── 連線輔助 ──────────────────────────────────────────────────────────────────

def _line_register(item):
    from items.line_item import LineItem
    if isinstance(item, LineItem):
        item.register_connections()
        item.update_path()

def _line_unregister(item):
    from items.line_item import LineItem
    if isinstance(item, LineItem):
        item.unregister_connections()


# ── Undo Commands ─────────────────────────────────────────────────────────────

class _AddItemCmd(QUndoCommand):
    def __init__(self, scene: "CanvasScene", item, label: str = "Add"):
        super().__init__(str(label))
        self._scene = scene
        self._item  = item

    def redo(self):
        self._scene.addItem(self._item)
        _line_register(self._item)

    def undo(self):
        _line_unregister(self._item)
        self._scene.removeItem(self._item)


class _RemoveItemsCmd(QUndoCommand):
    def __init__(self, scene: "CanvasScene", items: list):
        super().__init__("Delete")
        self._scene = scene
        self._items = list(items)

    def redo(self):
        for item in self._items:
            _line_unregister(item)
            self._scene.removeItem(item)

    def undo(self):
        for item in self._items:
            self._scene.addItem(item)
            _line_register(item)


class _MoveItemCmd(QUndoCommand):
    def __init__(self, scene: "CanvasScene", item, old_pos, new_pos):
        super().__init__("Move")
        self._scene   = scene
        self._item    = item
        self._old_pos = old_pos
        self._new_pos = new_pos

    def redo(self):
        self._item.setPos(self._new_pos)

    def undo(self):
        self._item.setPos(self._old_pos)


class _ResizeItemCmd(QUndoCommand):
    def __init__(self, scene, item,
                 old_pos, old_w: float, old_h: float,
                 new_pos, new_w: float, new_h: float):
        super().__init__("Resize")
        self._scene = scene
        self._item  = item
        self._old   = (old_pos, old_w, old_h)
        self._new   = (new_pos, new_w, new_h)

    def _apply(self, pos, w, h):
        self._item.prepareGeometryChange()
        self._item._width  = w
        self._item._height = h
        self._item.setPos(pos)
        if hasattr(self._item, '_layout_text'):
            self._item._layout_text()
        if hasattr(self._item, '_notify_connections'):
            self._item._notify_connections()
        self._item.update()

    def redo(self):
        self._apply(*self._new)

    def undo(self):
        self._apply(*self._old)


class _WaypointMoveCmd(QUndoCommand):
    def __init__(self, scene, line_item, seg_idx: int,
                 old_pts: list, new_pts: list):
        super().__init__("Move Connector")
        self._scene   = scene
        self._item    = line_item
        self._seg_idx = seg_idx
        # 儲存拖曳後的完整 waypoints（redo 用）
        self._new_full = [QPointF(p) for p in line_item._waypoints]
        # 建立拖曳前的完整 waypoints（undo 用）：把被移動的兩點換回去
        self._old_full = [QPointF(p) for p in line_item._waypoints]
        idx = seg_idx
        if 0 <= idx < len(self._old_full) - 1:
            self._old_full[idx]     = QPointF(old_pts[0])
            self._old_full[idx + 1] = QPointF(old_pts[1])

    def redo(self):
        self._item._waypoints = [QPointF(p) for p in self._new_full]
        self._item.update()

    def undo(self):
        self._item._waypoints = [QPointF(p) for p in self._old_full]
        self._item.update()


# ── CanvasScene ───────────────────────────────────────────────────────────────

class CanvasScene(QGraphicsScene):
    """
    Scene — Undo Stack（30步）、Smart Guide、連線管理。
    Signals:
      text_editing_started(item)   — TextItem / StickyText 進入編輯
      text_editing_stopped()       — 編輯結束
      selection_changed_signal(shapes, lines, sticky)
    """

    text_editing_started  = pyqtSignal(object)
    text_editing_stopped  = pyqtSignal()
    selection_changed_signal = pyqtSignal(list, list, list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(-5000, -5000, 10000, 10000)
        self.setBackgroundBrush(QBrush(QColor(_theme.get("canvas_bg", CANVAS_BG))))
        self._undo_stack = QUndoStack(self)
        self._undo_stack.setUndoLimit(UNDO_LIMIT)
        self.selectionChanged.connect(self._on_selection_changed)
        self._guide_pool:    list[QGraphicsLineItem] = []
        self._active_guides: list[QGraphicsLineItem] = []
        self._init_guide_pool()

    # ── Guide pool ────────────────────────────────────────────────────────────

    def _init_guide_pool(self):
        pen = QPen(QColor(_theme.get("guide_color", GUIDE_COLOR)))
        pen.setStyle(Qt.PenStyle.DashLine)
        pen.setWidth(1)
        for _ in range(GUIDE_MAX_POOL):
            line = QGraphicsLineItem()
            line.setPen(pen)
            line.setZValue(1000)
            line.setVisible(False)
            line.setFlag(line.GraphicsItemFlag.ItemIsSelectable, False)
            line.setFlag(line.GraphicsItemFlag.ItemIsMovable,    False)
            self.addItem(line)
            self._guide_pool.append(line)

    # ── Undo stack property ───────────────────────────────────────────────────

    @property
    def undo_stack(self) -> QUndoStack:
        return self._undo_stack

    # ── Undo-able operations ──────────────────────────────────────────────────

    def add_item_undoable(self, item, label: str = "Add"):
        self._undo_stack.push(_AddItemCmd(self, item, label))

    def push_move_cmd(self, item, old_pos, new_pos):
        self._undo_stack.push(_MoveItemCmd(self, item, old_pos, new_pos))

    def push_resize_cmd(self, item, old_pos, old_w, old_h, new_pos, new_w, new_h):
        self._undo_stack.push(
            _ResizeItemCmd(self, item, old_pos, old_w, old_h, new_pos, new_w, new_h))

    def push_waypoint_cmd(self, line_item, seg_idx, old_pts, new_pts):
        self._undo_stack.push(
            _WaypointMoveCmd(self, line_item, seg_idx, old_pts, new_pts))

    # ── Delete ────────────────────────────────────────────────────────────────

    def delete_selected(self):
        selected = [
            i for i in self.selectedItems()
            if i not in self._guide_pool and i.parentItem() is None
        ]
        if not selected:
            return
        self._undo_stack.push(_RemoveItemsCmd(self, selected))

    # ── Theme ─────────────────────────────────────────────────────────────────

    def apply_theme(self):
        """切換主題：更新畫布背景、輔助線、以及所有使用預設色的 Shape。"""
        self.setBackgroundBrush(QBrush(QColor(_theme.get("canvas_bg", CANVAS_BG))))

        guide_pen = QPen(QColor(_theme.get("guide_color", GUIDE_COLOR)))
        guide_pen.setStyle(Qt.PenStyle.DashLine)
        guide_pen.setWidth(1)
        for line in self._guide_pool:
            line.setPen(guide_pen)

        # 把還在用「上一個主題預設色」的 Shape 改成新主題預設色
        from items.shape_item import ShapeItem
        if _theme.is_dark:
            # 切換到深色 → old 預設是淺色
            old_bg, old_border = _LIGHT_BG, _LIGHT_BORDER
        else:
            # 切換到淺色 → old 預設是深色
            old_bg, old_border = _DARK_BG, _DARK_BORDER

        new_bg     = _theme.get("box_body_bg")
        new_border = _theme.get("box_border")

        for item in self.items():
            if isinstance(item, ShapeItem):
                if item._bg_color.name().lower() == old_bg.lower():
                    item.set_bg_color(QColor(new_bg))
                if item._border_color.name().lower() == old_border.lower():
                    item.set_border_color(QColor(new_border))
                item.update()

        self.update()

    # ── Grid background ───────────────────────────────────────────────────────

    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        pen = QPen(QColor(_theme.get("canvas_grid", CANVAS_GRID_COLOR)))
        pen.setWidth(1)
        painter.setPen(pen)
        step   = CANVAS_GRID_STEP
        left   = int(rect.left())   - (int(rect.left())   % step)
        top    = int(rect.top())    - (int(rect.top())    % step)
        right  = int(rect.right())  + step
        bottom = int(rect.bottom()) + step
        for x in range(left, right, step):
            painter.drawLine(x, int(rect.top()),  x, int(rect.bottom()))
        for y in range(top,  bottom, step):
            painter.drawLine(int(rect.left()), y, int(rect.right()), y)

    # ── Selection ─────────────────────────────────────────────────────────────

    def _on_selection_changed(self):
        from items.shape_item       import ShapeItem
        from items.line_item        import LineItem
        from items.sticky_note_item import StickyNoteItem
        shapes, lines, sticky = [], [], []
        for item in self.selectedItems():
            if item in self._guide_pool:
                continue
            if isinstance(item, ShapeItem):
                shapes.append(item)
            elif isinstance(item, LineItem):
                lines.append(item)
            elif isinstance(item, StickyNoteItem):
                sticky.append(item)
        self.selection_changed_signal.emit(shapes, lines, sticky)

    # ── Smart Guide snap ──────────────────────────────────────────────────────

    def snap_to_guides_or_grid(self, moving_item, new_pos: QPointF) -> QPointF:
        from items.shape_item       import ShapeItem
        from items.sticky_note_item import StickyNoteItem

        self.clear_guides()
        rect = moving_item.boundingRect()
        mx, my = new_pos.x(), new_pos.y()
        mw, mh = rect.width(), rect.height()

        m_xs = [mx, mx + mw / 2, mx + mw]
        m_ys = [my, my + mh / 2, my + mh]

        snap_r  = GUIDE_SNAP_RADIUS
        best_dx = snap_r + 1
        best_dy = snap_r + 1
        snap_x  = None
        snap_y  = None
        guide_xs: list[float] = []
        guide_ys: list[float] = []
        seen:     set         = set()

        for item in self.items():
            if item is moving_item:
                continue
            if item in self._guide_pool:
                continue
            if not isinstance(item, (ShapeItem, StickyNoteItem)):
                continue
            if item.parentItem() is not None:
                continue
            ir = item.boundingRect()
            ip = item.pos()
            i_xs = [ip.x(), ip.x() + ir.width() / 2, ip.x() + ir.width()]
            i_ys = [ip.y(), ip.y() + ir.height() / 2, ip.y() + ir.height()]

            for sx in m_xs:
                for tx in i_xs:
                    d = abs(sx - tx)
                    if d < best_dx:
                        best_dx = d
                        snap_x  = tx - (sx - mx)
                        if tx not in seen:
                            guide_xs.append(tx)
                            seen.add(tx)

            for sy in m_ys:
                for ty in i_ys:
                    d = abs(sy - ty)
                    if d < best_dy:
                        best_dy = d
                        snap_y  = ty - (sy - my)
                        if ty not in seen:
                            guide_ys.append(ty)
                            seen.add(ty)

        if snap_x is not None and best_dx <= snap_r:
            mx = snap_x
            for gx in guide_xs:
                self._show_v_guide(gx)

        if snap_y is not None and best_dy <= snap_r:
            my = snap_y
            for gy in guide_ys:
                self._show_h_guide(gy)

        step = CANVAS_GRID_STEP
        if snap_x is None or best_dx > snap_r:
            mx = round(mx / step) * step
        if snap_y is None or best_dy > snap_r:
            my = round(my / step) * step

        return QPointF(mx, my)

    def _show_v_guide(self, x: float):
        r = self.sceneRect()
        for line in self._guide_pool:
            if not line.isVisible():
                line.setLine(x, r.top(), x, r.bottom())
                line.setVisible(True)
                self._active_guides.append(line)
                return

    def _show_h_guide(self, y: float):
        r = self.sceneRect()
        for line in self._guide_pool:
            if not line.isVisible():
                line.setLine(r.left(), y, r.right(), y)
                line.setVisible(True)
                self._active_guides.append(line)
                return

    def clear_guides(self):
        for line in self._active_guides:
            line.setVisible(False)
        self._active_guides.clear()
