import uuid
from PyQt6.QtWidgets import QGraphicsItem
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QPen, QColor

from constants import (
    TEXT_DEFAULT_COLOR, TEXT_DEFAULT_SIZE, TEXT_SELECTED_BORDER,
    CANVAS_GRID_STEP
)
from items.editable_text import EditableText


class TextItem(EditableText):
    """獨立文字：可移動、可選取、雙擊編輯、Grid Snap / Smart Guide，選取時虛線邊框。"""

    def __init__(self, text: str = "文字", parent=None):
        super().__init__(text, TEXT_DEFAULT_COLOR, TEXT_DEFAULT_SIZE, parent)
        self._id = str(uuid.uuid4())
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable    |
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setTextWidth(200)

    def paint(self, painter: QPainter, option, widget=None):
        super().paint(painter, option, widget)
        if self.isSelected():
            pen = QPen(QColor(TEXT_SELECTED_BORDER), 1)
            pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self.boundingRect().adjusted(1, 1, -1, -1))

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            scene = self.scene()
            if scene and hasattr(scene, 'snap_to_guides_or_grid'):
                return scene.snap_to_guides_or_grid(self, value)
            s = CANVAS_GRID_STEP
            return QPointF(round(value.x()/s)*s, round(value.y()/s)*s)
        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        self._drag_start_pos = self.pos()   # ← 記錄移動起點
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        scene = self.scene()
        if scene and hasattr(scene, 'push_move_cmd'):
            start = getattr(self, '_drag_start_pos', None)
            if start is not None and start != self.pos():
                scene.push_move_cmd(self, start, self.pos())

    def mouseDoubleClickEvent(self, event):
        self.start_edit()
        event.accept()

    def to_dict(self) -> dict:
        return {
            "type": "text", "id": self._id,
            "x": self.pos().x(), "y": self.pos().y(),
            "text": self.plain_text,
            "html": self.toHtml(),          # ← 存 HTML 保留格式
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TextItem":
        item = cls(d.get("text", ""))
        item.setPos(d["x"], d["y"])
        html = d.get("html")
        if html:
            item.setHtml(html)              # ← 有 HTML 就還原格式
        return item