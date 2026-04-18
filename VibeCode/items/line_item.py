import uuid
import math
from PyQt6.QtWidgets import QGraphicsItem
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor,
    QPainterPath, QPainterPathStroker, QPolygonF,
)
from constants import LINE_DEFAULT_COLOR, LINE_SELECTED_COLOR, LINE_WIDTH, LINE_ARROW_SIZE

ENDPOINT_RADIUS  = 5
EP_HIT_RADIUS    = 12
MIDPOINT_RADIUS  = 4      # 繪製半徑（黃點）
MP_HIT_RADIUS    = 10     # 命中偵測半徑


def _anchor_nudge(item, anchor: QPointF, step: float):
    """
    回傳錨點往形狀外延伸 step 像素的點。
    左右錨點 → 水平延伸；上下錨點 → 垂直延伸。
    沒有連接物件時回傳 None。
    """
    if item is None:
        return None
    rect = item.sceneBoundingRect()
    cx   = rect.center().x()
    cy   = rect.center().y()
    px   = anchor.x()
    py   = anchor.y()
    dx   = px - cx
    dy   = py - cy
    if abs(dx) >= abs(dy):          # 左側或右側錨點
        return QPointF(px + (step if dx >= 0 else -step), py)
    else:                           # 頂部或底部錨點
        return QPointF(px, py + (step if dy >= 0 else -step))


class LineItem(QGraphicsItem):
    """
    正交折線連接線（含方向箭頭）。
    連接 ShapeItem / StickyNoteItem，Shape 移動時自動重新路由。
    端點位置由滑鼠點擊決定，shape 移動時以 offset 追蹤，不強制吸附到邊緣中心。
    """

    def __init__(self, start: QPointF, end: QPointF,
                 start_item=None, end_item=None):
        super().__init__()
        self._id         = str(uuid.uuid4())
        self._start      = QPointF(start)
        self._end        = QPointF(end)
        self._start_item = start_item
        self._end_item   = end_item
        self._color      = QColor(LINE_DEFAULT_COLOR)
        self._width      = LINE_WIDTH
        self._waypoints: list = [QPointF(start), QPointF(end)]
        self._start_offset: QPointF | None = None
        self._end_offset:   QPointF | None = None

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setZValue(-1)

    # ── 幾何 ───────────────────────────────────────────────────────────────────

    def boundingRect(self) -> QRectF:
        if not self._waypoints:
            return QRectF()
        pad = LINE_ARROW_SIZE + EP_HIT_RADIUS + 4
        xs = [p.x() for p in self._waypoints]
        ys = [p.y() for p in self._waypoints]
        return QRectF(min(xs)-pad, min(ys)-pad,
                      max(xs)-min(xs)+pad*2, max(ys)-min(ys)+pad*2)

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        if not self._waypoints:
            return path
        path.moveTo(self._waypoints[0])
        for pt in self._waypoints[1:]:
            path.lineTo(pt)
        s = QPainterPathStroker()
        s.setWidth(14)
        return s.createStroke(path)

    # ── 繪製 ───────────────────────────────────────────────────────────────────

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if len(self._waypoints) < 2:
            return

        sel   = self.isSelected()
        color = QColor(LINE_SELECTED_COLOR if sel else self._color)
        w     = self._width + (0.8 if sel else 0)

        p_tip = self._waypoints[-1]
        dx = dy = length = 0.0
        for i in range(len(self._waypoints)-2, -1, -1):
            p_prev = self._waypoints[i]
            dx = p_tip.x() - p_prev.x()
            dy = p_tip.y() - p_prev.y()
            length = math.sqrt(dx*dx + dy*dy)
            if length > 0.5:
                break
        if length < 0.5:
            return

        ux, uy   = dx/length, dy/length
        px, py   = -uy, ux
        arrow_sz = LINE_ARROW_SIZE
        half     = arrow_sz * 0.40
        base     = QPointF(p_tip.x()-ux*arrow_sz*0.85,
                           p_tip.y()-uy*arrow_sz*0.85)

        pen = QPen(color, w, Qt.PenStyle.SolidLine,
                   Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        pts = self._waypoints
        for i in range(len(pts)-1):
            p1 = pts[i]
            p2 = pts[i+1] if i < len(pts)-2 else base
            painter.drawLine(p1, p2)

        left  = QPointF(p_tip.x()-ux*arrow_sz+px*half,
                        p_tip.y()-uy*arrow_sz+py*half)
        right = QPointF(p_tip.x()-ux*arrow_sz-px*half,
                        p_tip.y()-uy*arrow_sz-py*half)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color))
        painter.drawPolygon(QPolygonF([p_tip, left, right]))

        if sel:
            # 端點（藍白）
            painter.setPen(QPen(color, 1.5))
            painter.setBrush(QBrush(QColor(LINE_DEFAULT_COLOR)))
            r = ENDPOINT_RADIUS
            painter.drawEllipse(pts[0], r, r)
            painter.drawEllipse(p_tip,  r, r)

            # 中點控制點（黃點）
            if len(pts) >= 2:
                painter.setPen(QPen(QColor("#f7c948"), 1.5))
                painter.setBrush(QBrush(QColor("#f7c948")))
                mr = MIDPOINT_RADIUS
                for i in range(len(pts) - 1):
                    mx = (pts[i].x() + pts[i + 1].x()) / 2
                    my = (pts[i].y() + pts[i + 1].y()) / 2
                    painter.drawEllipse(QPointF(mx, my), mr, mr)

    # ── 端點偵測 ──────────────────────────────────────────────────────────────

    def endpoint_hit(self, scene_pos: QPointF) -> str | None:
        if not self.isSelected():
            return None
        r2 = EP_HIT_RADIUS ** 2
        s  = self._waypoints[0]  if self._waypoints else self._start
        e  = self._waypoints[-1] if self._waypoints else self._end

        def d2(a, b):
            return (a.x()-b.x())**2 + (a.y()-b.y())**2

        if d2(scene_pos, s) <= r2: return "start"
        if d2(scene_pos, e) <= r2: return "end"
        return None

    # ── 中點偵測 ──────────────────────────────────────────────────────────────

    def midpoint_hit(self, scene_pos: QPointF) -> int | None:
        """回傳被點到的線段索引（0-based），None 表示未命中。"""
        if not self.isSelected() or len(self._waypoints) < 2:
            return None
        r2 = MP_HIT_RADIUS ** 2
        for i in range(len(self._waypoints) - 1):
            p1 = self._waypoints[i]
            p2 = self._waypoints[i + 1]
            mx = (p1.x() + p2.x()) / 2
            my = (p1.y() + p2.y()) / 2
            dx = scene_pos.x() - mx
            dy = scene_pos.y() - my
            if dx * dx + dy * dy <= r2:
                return i
        return None

    # ── 端點拖曳 ──────────────────────────────────────────────────────────────

    def drag_endpoint(self, end: str, pos: QPointF):
        self.prepareGeometryChange()
        if end == "start": self._start = QPointF(pos)
        else:              self._end   = QPointF(pos)
        self._waypoints = [QPointF(self._start), QPointF(self._end)]
        self.update()

    def set_start_connection(self, pos: QPointF, item=None):
        if self._start_item:
            self._start_item.remove_connection(self)
        self._start_item = item
        self._start      = QPointF(pos)
        if self._start_item:
            self._start_item.add_connection(self)
            self._start_offset = pos - self._start_item.scenePos()
        else:
            self._start_offset = None
        self.update_path()

    def set_end_connection(self, pos: QPointF, item=None):
        if self._end_item:
            self._end_item.remove_connection(self)
        self._end_item = item
        self._end      = QPointF(pos)
        if self._end_item:
            self._end_item.add_connection(self)
            self._end_offset = pos - self._end_item.scenePos()
        else:
            self._end_offset = None
        self.update_path()

    # ── 路由更新 ───────────────────────────────────────────────────────────────

    def update_path(self):
        self.prepareGeometryChange()
        if self._start_item and self._start_offset is not None:
            self._start = self._start_item.scenePos() + self._start_offset
        if self._end_item and self._end_offset is not None:
            self._end = self._end_item.scenePos() + self._end_offset

        obstacles = self._get_obstacles()
        from routing.orthogonal_router import route
        from constants import CANVAS_GRID_STEP

        # 計算「外推點」：從錨點往外一格，強迫路由器以垂直方向進出形狀
        nudge  = CANVAS_GRID_STEP * 2
        ns     = _anchor_nudge(self._start_item, self._start, nudge)
        ne     = _anchor_nudge(self._end_item,   self._end,   nudge)

        raw = route(
            ns if ns else self._start,
            ne if ne else self._end,
            obstacles, CANVAS_GRID_STEP
        )

        # 把實際錨點接回兩端
        if ns:
            raw = [self._start] + raw
        if ne:
            raw = raw + [self._end]

        self._waypoints = raw
        self.update()

    def _get_obstacles(self) -> list:
        scene = self.scene()
        if scene is None:
            return []
        from items.shape_item import ShapeItem
        try:
            from items.sticky_note_item import StickyNoteItem
            obstacle_types = (ShapeItem, StickyNoteItem)
        except ImportError:
            obstacle_types = (ShapeItem,)
        return [
            item.sceneBoundingRect()
            for item in scene.items()
            if isinstance(item, obstacle_types)
            and item is not self._start_item
            and item is not self._end_item
        ]

    # ── 連接登記 ──────────────────────────────────────────────────────────────

    def register_connections(self):
        if self._start_item:
            self._start_item.add_connection(self)
            self._start_offset = self._start - self._start_item.scenePos()
        if self._end_item:
            self._end_item.add_connection(self)
            self._end_offset = self._end - self._end_item.scenePos()
        self.update_path()

    def unregister_connections(self):
        if self._start_item: self._start_item.remove_connection(self)
        if self._end_item:   self._end_item.remove_connection(self)

    # ── Setters ───────────────────────────────────────────────────────────────

    @property
    def line_color(self): return self._color
    @property
    def line_width(self): return self._width

    def set_line_color(self, c):
        self._color = QColor(c) if not isinstance(c, QColor) else c
        self.update()

    def set_line_width(self, w): self._width = w; self.update()

    # ── 序列化 ────────────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "type":     "line",
            "id":       self._id,
            "x1": self._start.x(), "y1": self._start.y(),
            "x2": self._end.x(),   "y2": self._end.y(),
            "color":    self._color.name(),
            "width":    self._width,
            "start_id": getattr(self._start_item, '_id', None),
            "end_id":   getattr(self._end_item,   '_id', None),
            "waypoints": [[p.x(), p.y()] for p in self._waypoints],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "LineItem":
        item = cls(QPointF(d["x1"], d["y1"]), QPointF(d["x2"], d["y2"]))
        item.set_line_color(QColor(d.get("color", LINE_DEFAULT_COLOR)))
        item.set_line_width(d.get("width", LINE_WIDTH))
        # Restore saved waypoints (will be re-routed on shape move)
        pts = d.get("waypoints")
        if pts and len(pts) >= 2:
            item._waypoints = [QPointF(x, y) for x, y in pts]
        return item