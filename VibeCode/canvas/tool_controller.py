from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtWidgets import QGraphicsView, QGraphicsEllipseItem
from PyQt6.QtGui import QPen, QBrush, QColor

from constants import (
    ToolMode, ShapeType, CANVAS_GRID_STEP,
    LINE_CURSOR_MOVE, COLOR_ACCENT
)

_SNAP_RADIUS = 50   # px：游標距錨點多近時磁吸


class ToolController:
    """
    Tool Mode 狀態機：分派滑鼠事件給對應的放置邏輯。
    回傳值約定：on_mouse_press() 回傳 bool，True 表示事件已消費。
    """

    def __init__(self, scene, view):
        self._scene      = scene
        self._view       = view
        self._mode       = ToolMode.SELECT
        self._shape_type = ShapeType.RECT
        self._table_rows = 3    # ADD_TABLE 尺寸（由 Toolbar 設定）
        self._table_cols = 3

        self.on_shape_placed = None   # callable(ToolMode) | None

        # 連線工具狀態
        self._line_start      = None
        self._line_start_item = None
        self._preview_line    = None

        # 磁吸指示器
        self._snap_indicator: QGraphicsEllipseItem | None = None

        # 端點拖曳狀態
        self._ep_line  = None
        self._ep_end   = None
        self._ep_shape = None
        self._ep_pos   = None

        # 中點線段平移狀態
        self._wp_line     = None   # LineItem
        self._wp_seg_idx  = None   # 線段索引
        self._wp_start    = None   # 拖曳起始 scene_pos
        self._wp_orig_pts = None   # [p1, p2] 原始兩端座標

    # ── 公開 API ───────────────────────────────────────────────────────────────

    @property
    def current_mode(self) -> ToolMode:
        return self._mode

    @property
    def is_ep_dragging(self) -> bool:
        return self._ep_line is not None

    @property
    def is_wp_dragging(self) -> bool:
        return self._wp_line is not None and self._wp_seg_idx is not None

    def set_mode(self, mode: ToolMode):
        self._mode = mode
        self._cancel_preview()
        self._hide_snap()
        if mode == ToolMode.SELECT:
            self._view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        else:
            self._view.setDragMode(QGraphicsView.DragMode.NoDrag)

    def set_shape_type(self, shape_type: ShapeType):
        self._shape_type = shape_type

    def set_table_size(self, rows: int, cols: int):
        """由 Toolbar table_size_changed 訊號呼叫。"""
        self._table_rows = rows
        self._table_cols = cols

    # ── 事件入口 ───────────────────────────────────────────────────────────────

    def on_mouse_press(self, event, scene_pos: QPointF) -> bool:
        if event.button() != Qt.MouseButton.LeftButton:
            return False

        if self._mode == ToolMode.SELECT:
            return self._try_ep_drag_start(scene_pos)
        if self._mode == ToolMode.ADD_TEXT:
            self._place_text(scene_pos)
        elif self._mode == ToolMode.ADD_SHAPE:
            self._place_shape(scene_pos)
        elif self._mode == ToolMode.ADD_LINE:
            self._handle_line_press(scene_pos)
        elif self._mode == ToolMode.ADD_NOTE:
            self._place_note(scene_pos)
        elif self._mode == ToolMode.ADD_IMAGE:
            self._place_image(scene_pos)
        elif self._mode == ToolMode.ADD_TABLE:
            self._place_table(scene_pos)
        return False

    def on_mouse_move(self, event, scene_pos: QPointF):
        if self._mode == ToolMode.ADD_LINE:
            self._line_move(scene_pos)
        elif self._mode == ToolMode.SELECT:
            if self._ep_line:
                self._ep_drag_move(scene_pos)
            elif self._wp_line:
                self._wp_drag_move(scene_pos)

    def on_mouse_release(self, event, scene_pos: QPointF):
        if self._mode == ToolMode.SELECT:
            if self._ep_line:
                self._ep_drag_finish()
            elif self._wp_line:
                self._wp_drag_finish()

    def on_double_click(self, event, scene_pos: QPointF):
        pass

    # ── ADD_TEXT ──────────────────────────────────────────────────────────────

    def _place_text(self, pos: QPointF):
        from items.text_item import TextItem
        item = TextItem()
        item.setPos(self._snap(pos))
        self._scene.add_item_undoable(item)
        self._scene.clearSelection()
        item.setSelected(True)

        self.set_mode(ToolMode.SELECT)
        if self.on_shape_placed:
            self.on_shape_placed(ToolMode.SELECT)

        item.start_edit()

    # ── ADD_SHAPE ─────────────────────────────────────────────────────────────

    def _place_shape(self, pos: QPointF):
        from items.shape_item import ShapeItem
        item = ShapeItem(self._shape_type)
        item.setPos(self._snap(pos))
        self._scene.add_item_undoable(item)
        self._scene.clearSelection()
        item.setSelected(True)
        self.set_mode(ToolMode.SELECT)
        if self.on_shape_placed:
            self.on_shape_placed(ToolMode.SELECT)

    # ── ADD_NOTE ──────────────────────────────────────────────────────────────

    def _place_note(self, pos: QPointF):
        from items.sticky_note_item import StickyNoteItem
        item = StickyNoteItem()
        item.setPos(self._snap(pos))
        self._scene.add_item_undoable(item)
        self._scene.clearSelection()
        item.setSelected(True)
        self.set_mode(ToolMode.SELECT)
        if self.on_shape_placed:
            self.on_shape_placed(ToolMode.SELECT)

    # ── ADD_IMAGE ─────────────────────────────────────────────────────────────

    def _place_image(self, pos: QPointF):
        from PyQt6.QtWidgets import QFileDialog
        from PyQt6.QtGui import QPixmap
        from PyQt6.QtCore import Qt as _Qt
        from items.image_item import ImageItem

        path, _ = QFileDialog.getOpenFileName(
            None, '選擇圖片', '',
            'Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp)'
        )

        # 無論取消或完成都切回 Select
        self.set_mode(ToolMode.SELECT)
        if self.on_shape_placed:
            self.on_shape_placed(ToolMode.SELECT)

        if not path:
            return

        pixmap = QPixmap(path)
        if pixmap.isNull():
            return

        # 初始最大寬度 400px，等比縮放
        if pixmap.width() > 400:
            pixmap = pixmap.scaledToWidth(
                400, _Qt.TransformationMode.SmoothTransformation
            )

        item = ImageItem(pixmap)
        item.setPos(pos - QPointF(pixmap.width() / 2, pixmap.height() / 2))
        self._scene.add_item_undoable(item)
        self._scene.clearSelection()
        item.setSelected(True)

    # ── ADD_TABLE ─────────────────────────────────────────────────────────────

    def _place_table(self, pos: QPointF):
        from items.table_item import TableItem
        item = TableItem(self._table_rows, self._table_cols)
        item.setPos(self._snap(pos))
        self._scene.add_item_undoable(item)
        self._scene.clearSelection()
        item.setSelected(True)
        self.set_mode(ToolMode.SELECT)
        if self.on_shape_placed:
            self.on_shape_placed(ToolMode.SELECT)

    # ── ADD_LINE ──────────────────────────────────────────────────────────────

    def _handle_line_press(self, scene_pos: QPointF):
        shape, anchor = self._nearest_anchor(scene_pos)
        pos = anchor if anchor else self._snap(scene_pos)

        if self._line_start is None:
            self._line_start_item = shape
            self._line_start      = pos
            self._start_preview(pos)
        else:
            self._finish_line(pos, shape)

    def _line_move(self, scene_pos: QPointF):
        if not self._preview_line:
            return
        shape, anchor = self._nearest_anchor(scene_pos)
        snap_pos = anchor if anchor else scene_pos
        from PyQt6.QtCore import QLineF
        old = self._preview_line.line()
        self._preview_line.setLine(QLineF(old.p1(), snap_pos))
        if anchor:
            self._show_snap(anchor)
        else:
            self._hide_snap()

    def _start_preview(self, start: QPointF):
        from PyQt6.QtWidgets import QGraphicsLineItem
        from PyQt6.QtCore import QLineF
        pen = QPen(QColor(LINE_CURSOR_MOVE), 1.5)
        pen.setStyle(Qt.PenStyle.DashLine)
        self._preview_line = QGraphicsLineItem(QLineF(start, start))
        self._preview_line.setPen(pen)
        self._preview_line.setZValue(9999)
        self._scene.addItem(self._preview_line)

    def _finish_line(self, end_pos: QPointF, end_item=None):
        start      = self._line_start
        start_item = self._line_start_item
        self._cancel_preview()

        from items.line_item import LineItem
        item = LineItem(start, end_pos, start_item, end_item)
        self._scene.add_item_undoable(item)
        self._scene.clearSelection()
        item.setSelected(True)
        self.set_mode(ToolMode.SELECT)
        if self.on_shape_placed:
            self.on_shape_placed(ToolMode.SELECT)

    def _cancel_preview(self):
        if self._preview_line:
            self._scene.removeItem(self._preview_line)
            self._preview_line    = None
        self._line_start      = None
        self._line_start_item = None

    # ── SELECT：端點拖曳 ──────────────────────────────────────────────────────

    def _try_ep_drag_start(self, scene_pos: QPointF) -> bool:
        from items.line_item import LineItem
        for item in self._scene.selectedItems():
            if not isinstance(item, LineItem):
                continue
            # 優先偵測端點
            end = item.endpoint_hit(scene_pos)
            if end:
                self._ep_line = item
                self._ep_end  = end
                return True
            # 再偵測中點黃點（線段平移）
            seg_idx = item.midpoint_hit(scene_pos)
            if seg_idx is not None:
                self._wp_line     = item
                self._wp_seg_idx  = seg_idx
                self._wp_start    = QPointF(scene_pos)
                self._wp_orig_pts = [
                    QPointF(item._waypoints[seg_idx]),
                    QPointF(item._waypoints[seg_idx + 1]),
                ]
                return True
        return False

    def _ep_drag_move(self, scene_pos: QPointF):
        shape, anchor = self._nearest_anchor(scene_pos)
        pos = anchor if anchor else scene_pos
        self._ep_shape = shape
        self._ep_pos   = pos
        self._ep_line.drag_endpoint(self._ep_end, pos)
        if anchor: self._show_snap(anchor)
        else:      self._hide_snap()

    def _ep_drag_finish(self):
        self._hide_snap()
        line  = self._ep_line
        end   = self._ep_end
        pos   = self._ep_pos or (line._start if end == "start" else line._end)
        shape = self._ep_shape

        if end == "start": line.set_start_connection(pos, shape)
        else:              line.set_end_connection(pos, shape)

        self._ep_line  = None
        self._ep_end   = None
        self._ep_shape = None
        self._ep_pos   = None

    # ── 中點線段平移 ─────────────────────────────────────────────────────────

    def _wp_drag_move(self, scene_pos: QPointF):
        dx = scene_pos.x() - self._wp_start.x()
        dy = scene_pos.y() - self._wp_start.y()
        p1 = self._wp_orig_pts[0]
        p2 = self._wp_orig_pts[1]
        # 判斷水平段（Y差小）或垂直段（X差小）
        is_horiz = abs(p2.y() - p1.y()) <= abs(p2.x() - p1.x())
        line = self._wp_line
        idx  = self._wp_seg_idx
        line.prepareGeometryChange()
        if is_horiz:
            line._waypoints[idx]     = QPointF(p1.x(), p1.y() + dy)
            line._waypoints[idx + 1] = QPointF(p2.x(), p2.y() + dy)
        else:
            line._waypoints[idx]     = QPointF(p1.x() + dx, p1.y())
            line._waypoints[idx + 1] = QPointF(p2.x() + dx, p2.y())
        line.update()

    def _wp_drag_finish(self):
        line = self._wp_line
        idx  = self._wp_seg_idx
        if line and idx is not None and self._wp_orig_pts:
            new_pts = [
                QPointF(line._waypoints[idx]),
                QPointF(line._waypoints[idx + 1]),
            ]
            old_pts = self._wp_orig_pts
            if old_pts[0] != new_pts[0] or old_pts[1] != new_pts[1]:
                scene = line.scene()
                if scene and hasattr(scene, 'push_waypoint_cmd'):
                    scene.push_waypoint_cmd(line, idx, old_pts, new_pts)
        self._wp_line     = None
        self._wp_seg_idx  = None
        self._wp_start    = None
        self._wp_orig_pts = None

    # ── 磁吸：最近錨點 ────────────────────────────────────────────────────────

    def _nearest_anchor(self, scene_pos: QPointF, radius: int = _SNAP_RADIUS):
        from items.shape_item import ShapeItem
        try:
            from items.sticky_note_item import StickyNoteItem
            anchor_types = (ShapeItem, StickyNoteItem)
        except ImportError:
            anchor_types = (ShapeItem,)

        best_d2    = radius ** 2
        best_shape = None
        best_pt    = None

        for item in self._scene.items():
            if not isinstance(item, anchor_types):
                continue
            for pt in item.get_anchor_points():
                d2 = (pt.x()-scene_pos.x())**2 + (pt.y()-scene_pos.y())**2
                if d2 < best_d2:
                    best_d2    = d2
                    best_shape = item
                    best_pt    = pt

        return best_shape, best_pt

    # ── 磁吸指示器 ────────────────────────────────────────────────────────────

    def _show_snap(self, pos: QPointF):
        if self._snap_indicator is None:
            r   = 7
            ind = QGraphicsEllipseItem(-r, -r, r*2, r*2)
            ind.setPen(QPen(QColor("#9ece6a"), 2.2))
            ind.setBrush(QBrush(QColor("#9ece6a44")))
            ind.setZValue(10000)
            self._scene.addItem(ind)
            self._snap_indicator = ind
        self._snap_indicator.setPos(pos)
        self._snap_indicator.setVisible(True)

    def _hide_snap(self):
        if self._snap_indicator:
            self._snap_indicator.setVisible(False)

    def _snap(self, pos: QPointF) -> QPointF:
        s = CANVAS_GRID_STEP
        return QPointF(round(pos.x()/s)*s, round(pos.y()/s)*s)