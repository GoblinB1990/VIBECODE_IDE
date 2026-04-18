import uuid
import base64
from PyQt6.QtWidgets import QGraphicsItem
from PyQt6.QtGui import QPainter, QPen, QColor, QPixmap, QCursor
from PyQt6.QtCore import Qt, QRectF, QPointF, QByteArray, QBuffer, QIODeviceBase


HANDLE_SIZE = 8
HANDLES = ['tl', 'tr', 'bl', 'br']


class ImageItem(QGraphicsItem):
    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self._id     = str(uuid.uuid4())
        self._pixmap = pixmap
        self._width  = float(pixmap.width())
        self._height = float(pixmap.height())

        self._drag_handle     = None
        self._drag_start_pos  = None
        self._drag_start_rect = None

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)

    # ── 幾何 ──────────────────────────────────────────────────────────────────

    def boundingRect(self) -> QRectF:
        pad = HANDLE_SIZE / 2
        return QRectF(-pad, -pad, self._width + pad * 2, self._height + pad * 2)

    def _handle_rect(self, handle: str) -> QRectF:
        s = HANDLE_SIZE
        w, h = self._width, self._height
        centers = {
            'tl': QPointF(0, 0),
            'tr': QPointF(w, 0),
            'bl': QPointF(0, h),
            'br': QPointF(w, h),
        }
        c = centers[handle]
        return QRectF(c.x() - s / 2, c.y() - s / 2, s, s)

    def _handle_at(self, pos: QPointF):
        if not self.isSelected():
            return None
        for h in HANDLES:
            if self._handle_rect(h).contains(pos):
                return h
        return None

    # ── 繪製 ──────────────────────────────────────────────────────────────────

    def paint(self, painter: QPainter, option, widget=None):
        painter.drawPixmap(0, 0, int(self._width), int(self._height), self._pixmap)

        if self.isSelected():
            pen = QPen(QColor('#4A9EFF'), 1.5, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawRect(QRectF(0, 0, self._width, self._height))

            painter.setPen(QPen(QColor('#4A9EFF'), 1))
            painter.setBrush(QColor('white'))
            for h in HANDLES:
                painter.drawRect(self._handle_rect(h))

    # ── 滑鼠事件 ──────────────────────────────────────────────────────────────

    def hoverMoveEvent(self, event):
        h = self._handle_at(event.pos())
        cursors = {
            'tl': Qt.CursorShape.SizeFDiagCursor,
            'br': Qt.CursorShape.SizeFDiagCursor,
            'tr': Qt.CursorShape.SizeBDiagCursor,
            'bl': Qt.CursorShape.SizeBDiagCursor,
        }
        if h:
            self.setCursor(QCursor(cursors[h]))
        else:
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            h = self._handle_at(event.pos())
            if h:
                self._drag_handle     = h
                self._drag_start_pos  = event.scenePos()
                self._drag_start_rect = (
                    self._width, self._height,
                    self.pos().x(), self.pos().y()
                )
                event.accept()
                return
        self._drag_handle = None
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_handle:
            delta = event.scenePos() - self._drag_start_pos
            ow, oh, ox, oy = self._drag_start_rect
            dx, dy = delta.x(), delta.y()
            h = self._drag_handle

            if h == 'br':
                nw = max(20, ow + dx)
                nh = max(20, oh + dy)
                self.prepareGeometryChange()
                self._width, self._height = nw, nh

            elif h == 'tl':
                nw = max(20, ow - dx)
                nh = max(20, oh - dy)
                self.prepareGeometryChange()
                self._width, self._height = nw, nh
                self.setPos(ox + ow - nw, oy + oh - nh)

            elif h == 'tr':
                nw = max(20, ow + dx)
                nh = max(20, oh - dy)
                self.prepareGeometryChange()
                self._width, self._height = nw, nh
                self.setPos(ox, oy + oh - nh)

            elif h == 'bl':
                nw = max(20, ow - dx)
                nh = max(20, oh + dy)
                self.prepareGeometryChange()
                self._width, self._height = nw, nh
                self.setPos(ox + ow - nw, oy)

            self.update()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_handle = None
        super().mouseReleaseEvent(event)

    # ── 序列化 ────────────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        ba  = QByteArray()
        buf = QBuffer(ba)
        buf.open(QIODeviceBase.OpenModeFlag.WriteOnly)
        self._pixmap.save(buf, "PNG")
        buf.close()
        img_b64 = base64.b64encode(bytes(ba)).decode("ascii")

        return {
            "type":   "image",
            "id":     self._id,
            "x":      self.pos().x(),
            "y":      self.pos().y(),
            "width":  self._width,
            "height": self._height,
            "img":    img_b64,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ImageItem":
        raw    = base64.b64decode(d["img"])
        pixmap = QPixmap()
        pixmap.loadFromData(QByteArray(raw))
        item         = cls(pixmap)
        item._width  = d["width"]
        item._height = d["height"]
        item.setPos(d["x"], d["y"])
        if d.get("id"):
            item._id = d["id"]
        return item