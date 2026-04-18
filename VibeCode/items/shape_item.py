import uuid
import math
from PyQt6.QtWidgets import QGraphicsObject, QGraphicsItem, QGraphicsTextItem
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor,
    QPainterPath, QPainterPathStroker, QPolygonF, QFont, QTextCursor, QTextCharFormat
)

from constants import (
    ShapeType,
    SHAPE_DEFAULT_W, SHAPE_DEFAULT_H, SHAPE_MIN_W, SHAPE_MIN_H,
    BOX_BODY_BG, BOX_HEADER_BG, BOX_BORDER_COLOR, BOX_SELECTED_BORDER,
    BOX_BORDER_WIDTH, BOX_HEADER_H, BOX_CORNER_RADIUS,
    BOX_HEADER_TEXT, BOX_BODY_TEXT, BOX_HEADER_FONT_SIZE, BOX_BODY_FONT_SIZE,
    CANVAS_GRID_STEP, FONT_FAMILY
)
from theme import theme as _theme

H_TL,H_T,H_TR,H_R,H_BR,H_B,H_BL,H_L = range(8)
HS = 4

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


class _EditText(QGraphicsTextItem):
    """行內可編輯文字，掛在 ShapeItem 下。"""

    def __init__(self, text, color, size, parent):
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
        self.document().contentsChanged.connect(self._on_contents_changed)
        scene = self.scene()
        if scene and hasattr(scene, 'text_editing_started'):
            scene.text_editing_started.emit(self)

    def _on_contents_changed(self):
        p = self.parentItem()
        if p and hasattr(p, '_layout_text'):
            p._layout_text()

    def stop_edit(self):
        try:
            self.document().contentsChanged.disconnect(self._on_contents_changed)
        except Exception:
            pass
        cur = self.textCursor()
        cur.clearSelection()
        self.setTextCursor(cur)
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
        super().focusOutEvent(e)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.stop_edit()
        else:
            super().keyPressEvent(e)

    @property
    def plain_text(self): return self.toPlainText()


class ShapeItem(QGraphicsObject):
    """7 種流程圖形狀：resize、inline 編輯、Grid Snap、Smart Guide、連線錨點。"""

    def __init__(self, shape_type: ShapeType,
                 width=SHAPE_DEFAULT_W, height=SHAPE_DEFAULT_H, parent=None):
        super().__init__(parent)
        self._id         = str(uuid.uuid4())
        self._shape_type = shape_type
        self._width      = float(width)
        self._height     = float(height)
        self._connections = []

        # 顏色預設由 theme 決定，切換深/淺模式後新建的形狀會使用正確色
        self._border_color = QColor(_theme.get("box_border",  BOX_BORDER_COLOR))
        self._bg_color     = QColor(_theme.get("box_body_bg", BOX_BODY_BG))
        self._border_width = BOX_BORDER_WIDTH
        self._font_size    = BOX_BODY_FONT_SIZE

        body_color  = _theme.get("box_body_text",   BOX_BODY_TEXT)
        title_color = _theme.get("box_header_text",  BOX_HEADER_TEXT)
        self._body  = _EditText("雙擊編輯", body_color, BOX_BODY_FONT_SIZE, self)
        self._title = None
        if shape_type == ShapeType.RECT_DESCRIBE:
            self._title = _EditText("主題", title_color, BOX_HEADER_FONT_SIZE, self)

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
        w, h, pad = self._width, self._height, 10

        if self._shape_type == ShapeType.RECT_DESCRIBE:
            if self._title:
                self._title.setTextWidth(w - pad*2)
                ty = max((BOX_HEADER_H - self._title.boundingRect().height()) / 2, 4)
                self._title.setPos(pad, ty)
            self._body.setTextWidth(w - pad*2)
            self._body.setPos(pad, BOX_HEADER_H + pad)
        elif self._shape_type == ShapeType.DIAMOND:
            inner = min(w, h) * 0.5
            self._body.setTextWidth(inner)
            bh = self._body.boundingRect().height()
            self._body.setPos((w - inner)/2, (h - bh)/2)
        elif self._shape_type == ShapeType.CYLINDER:
            eh = min(h * 0.28, 32)
            self._body.setTextWidth(w - pad*2)
            self._body.setPos(pad, eh + pad)
        elif self._shape_type == ShapeType.PARALLELOGRAM:
            off = h * 0.25
            self._body.setTextWidth(w - off*2 - pad)
            self._body.setPos(off + pad/2, pad)
        elif self._shape_type == ShapeType.DOCUMENT:
            wave_h = max(h * 0.12, 8)
            self._body.setTextWidth(w - pad*2)
            bh = self._body.boundingRect().height()
            self._body.setPos(pad, ((h - wave_h) - bh)/2)
        elif self._shape_type == ShapeType.MANUAL_INPUT:
            slope = h * 0.20
            self._body.setTextWidth(w - pad*2)
            bh = self._body.boundingRect().height()
            self._body.setPos(pad, slope + (h - slope - bh)/2)
        elif self._shape_type == ShapeType.HEXAGON:
            notch = w * 0.25 * 0.25
            self._body.setTextWidth(w - notch*4 - pad)
            bh = self._body.boundingRect().height()
            self._body.setPos(notch*2 + pad/2, (h - bh)/2)
        elif self._shape_type == ShapeType.DELAY:
            radius = h / 2
            flat_w = max(w - radius, 4)
            self._body.setTextWidth(flat_w - pad)
            bh = self._body.boundingRect().height()
            self._body.setPos(pad, (h - bh)/2)
        else:
            self._body.setTextWidth(w - pad*2)
            bh = self._body.boundingRect().height()
            self._body.setPos(pad, (h - bh)/2)

    # ── QGraphicsItem 必實作 ───────────────────────────────────────────────────

    def boundingRect(self):
        p = HS + 2
        return QRectF(-p, -p, self._width + p*2, self._height + p*2)

    def shape(self):
        p = QPainterPath()
        p.addRect(QRectF(0, 0, self._width, self._height))
        return p

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        sel  = self.isSelected()
        bc   = QColor(BOX_SELECTED_BORDER) if sel else self._border_color
        pen  = QPen(bc, self._border_width)
        rect = QRectF(0, 0, self._width, self._height)
        painter.setPen(pen)
        painter.setBrush(QBrush(self._bg_color))

        draw = {
            ShapeType.OVAL:          self._draw_oval,
            ShapeType.RECT:          self._draw_rect,
            ShapeType.DIAMOND:       self._draw_diamond,
            ShapeType.PARALLELOGRAM: self._draw_parallelogram,
            ShapeType.CYLINDER:      self._draw_cylinder,
            ShapeType.PREDEFINED:    self._draw_predefined,
            ShapeType.RECT_DESCRIBE: self._draw_rect_desc,
            ShapeType.DOCUMENT:      self._draw_document,
            ShapeType.MANUAL_INPUT:  self._draw_manual_input,
            ShapeType.HEXAGON:       self._draw_hexagon,
            ShapeType.DELAY:         self._draw_delay,
        }
        draw[self._shape_type](painter, rect)

        if sel:
            self._draw_handles(painter)

    # ── 各形狀繪製 ─────────────────────────────────────────────────────────────

    def _draw_oval(self, p, r):         p.drawEllipse(r)
    def _draw_rect(self, p, r):         p.drawRect(r)

    def _draw_document(self, p, r):
        """Document：矩形加波浪底邊。"""
        wave_h = max(r.height() * 0.12, 8)
        body = QRectF(r.left(), r.top(), r.width(), r.height() - wave_h)
        path = QPainterPath()
        path.addRect(body)
        # 波浪從左下到右下
        x0, y0 = r.left(), body.bottom()
        w = r.width()
        path.moveTo(x0, y0)
        path.cubicTo(
            x0 + w * 0.25, y0 + wave_h * 1.8,
            x0 + w * 0.50, y0 - wave_h * 0.8,
            x0 + w * 0.75, y0 + wave_h * 1.8,
        )
        path.cubicTo(
            x0 + w * 0.875, y0 + wave_h * 2.4,
            x0 + w,         y0 + wave_h,
            x0 + w,         y0,
        )
        path.closeSubpath()
        p.drawPath(path)

    def _draw_manual_input(self, p, r):
        """Manual Input：左高右低斜切頂邊的四邊形。"""
        slope = r.height() * 0.20
        p.drawPolygon(QPolygonF([
            QPointF(r.left(),  r.top() + slope),
            QPointF(r.right(), r.top()),
            QPointF(r.right(), r.bottom()),
            QPointF(r.left(),  r.bottom()),
        ]))

    def _draw_hexagon(self, p, r):
        """Hexagon（Preparation）：水平六邊形。"""
        cx, cy = r.center().x(), r.center().y()
        hw = r.width() / 2
        hh = r.height() / 2
        notch = hw * 0.25
        p.drawPolygon(QPolygonF([
            QPointF(r.left() + notch, r.top()),
            QPointF(r.right() - notch, r.top()),
            QPointF(r.right(), cy),
            QPointF(r.right() - notch, r.bottom()),
            QPointF(r.left() + notch, r.bottom()),
            QPointF(r.left(), cy),
        ]))

    def _draw_delay(self, p, r):
        """Delay（D 形）：左側直邊 + 右側半圓。"""
        radius = r.height() / 2
        flat_w = max(r.width() - radius, 4)
        path = QPainterPath()
        path.moveTo(r.left(), r.top())
        path.lineTo(r.left() + flat_w, r.top())
        path.arcTo(QRectF(r.left() + flat_w - radius, r.top(), radius * 2, r.height()),
                   90, -180)
        path.lineTo(r.left(), r.bottom())
        path.closeSubpath()
        p.drawPath(path)

    def _draw_diamond(self, p, r):
        cx, cy = r.center().x(), r.center().y()
        p.drawPolygon(QPolygonF([
            QPointF(cx, r.top()), QPointF(r.right(), cy),
            QPointF(cx, r.bottom()), QPointF(r.left(), cy)
        ]))

    def _draw_parallelogram(self, p, r):
        off = r.height() * 0.25
        p.drawPolygon(QPolygonF([
            QPointF(r.left()+off, r.top()), QPointF(r.right(), r.top()),
            QPointF(r.right()-off, r.bottom()), QPointF(r.left(), r.bottom())
        ]))

    def _draw_cylinder(self, p, r):
        eh = min(r.height() * 0.28, 32)
        p.drawRect(QRectF(r.left(), r.top()+eh/2, r.width(), r.height()-eh/2))
        p.drawEllipse(QRectF(r.left(), r.top(), r.width(), eh))
        p.drawArc(QRectF(r.left(), r.bottom()-eh, r.width(), eh), 0, -180*16)

    def _draw_predefined(self, p, r):
        m = 8
        p.drawRect(r)
        p.drawLine(QPointF(r.left()+m,  r.top()), QPointF(r.left()+m,  r.bottom()))
        p.drawLine(QPointF(r.right()-m, r.top()), QPointF(r.right()-m, r.bottom()))

    def _draw_rect_desc(self, p, r):
        rv = BOX_CORNER_RADIUS
        p.drawRoundedRect(r, rv, rv)
        p.save()
        clip = QPainterPath()
        clip.addRoundedRect(r, rv, rv)
        p.setClipPath(clip)
        hdr_color = _theme.get("box_header_bg", BOX_HEADER_BG)
        p.fillRect(QRectF(r.left(), r.top(), r.width(), BOX_HEADER_H), QColor(hdr_color))
        p.restore()
        p.drawLine(QPointF(r.left(), r.top()+BOX_HEADER_H),
                   QPointF(r.right(), r.top()+BOX_HEADER_H))

    # ── Handles ───────────────────────────────────────────────────────────────

    def _handle_rects(self):
        w, h = self._width, self._height
        sz   = HS * 2
        return [
            QRectF(-HS,   -HS,   sz, sz), QRectF(w/2-HS, -HS,   sz, sz),
            QRectF(w-HS,  -HS,   sz, sz), QRectF(w-HS,  h/2-HS, sz, sz),
            QRectF(w-HS,  h-HS,  sz, sz), QRectF(w/2-HS, h-HS,  sz, sz),
            QRectF(-HS,   h-HS,  sz, sz), QRectF(-HS,   h/2-HS, sz, sz),
        ]

    def _handle_at(self, pos):
        for i, r in enumerate(self._handle_rects()):
            if r.contains(pos): return i
        return -1

    def _draw_handles(self, p):
        p.setPen(QPen(QColor(BOX_SELECTED_BORDER), 1))
        p.setBrush(QBrush(QColor(BOX_BODY_BG)))
        for r in self._handle_rects(): p.drawRect(r)

    # ── Mouse Events ──────────────────────────────────────────────────────────

    def mousePressEvent(self, e):
        if self.isSelected() and e.button() == Qt.MouseButton.LeftButton:
            h = self._handle_at(e.pos())
            if h >= 0:
                self._resizing = True; self._rh = h
                self._rm = self.mapToScene(e.pos())
                self._rp = self.pos()
                self._rw = self._width; self._rh_size = self._height
                e.accept(); return
        self._drag_start_pos = self.pos()   # ← 記錄移動起點
        self._resizing = False
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._resizing:
            sp = self.mapToScene(e.pos())
            self._apply_resize(sp.x()-self._rm.x(), sp.y()-self._rm.y())
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
        if (self._shape_type == ShapeType.RECT_DESCRIBE
                and self._title and e.pos().y() < BOX_HEADER_H):
            self._title.start_edit()
        else:
            self._body.start_edit()
        e.accept()

    def hoverMoveEvent(self, e):
        if self.isSelected():
            h = self._handle_at(e.pos())
            if h >= 0: self.setCursor(HANDLE_CURSORS[h]); return
        self.setCursor(Qt.CursorShape.SizeAllCursor)

    def hoverLeaveEvent(self, e): self.unsetCursor()

    # ── Resize ────────────────────────────────────────────────────────────────

    def _apply_resize(self, dx, dy):
        h = self._rh
        sw, sh = self._rw, self._rh_size
        ox, oy = self._rp.x(), self._rp.y()
        nx, ny, nw, nh = ox, oy, sw, sh

        if h in (H_TR,H_R,H_BR):  nw = sw+dx
        if h in (H_BL,H_B,H_BR):  nh = sh+dy
        if h in (H_TL,H_L,H_BL):  nx = ox+dx; nw = sw-dx
        if h in (H_TL,H_T,H_TR):  ny = oy+dy; nh = sh-dy

        if nw < SHAPE_MIN_W:
            nw = SHAPE_MIN_W
            if h in (H_TL,H_L,H_BL): nx = ox+sw-SHAPE_MIN_W
        if nh < SHAPE_MIN_H:
            nh = SHAPE_MIN_H
            if h in (H_TL,H_T,H_TR): ny = oy+sh-SHAPE_MIN_H

        self.prepareGeometryChange()
        self._width = nw; self._height = nh
        self.setPos(nx, ny)
        self._layout_text()
        self._notify_connections()

    # ── Item Change（Smart Guide 整合）────────────────────────────────────────

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            if self._resizing:
                s = CANVAS_GRID_STEP
                return QPointF(round(value.x()/s)*s, round(value.y()/s)*s)
            scene = self.scene()
            if scene and hasattr(scene, 'snap_to_guides_or_grid'):
                return scene.snap_to_guides_or_grid(self, value)
            s = CANVAS_GRID_STEP
            return QPointF(round(value.x()/s)*s, round(value.y()/s)*s)
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self._notify_connections()
        return super().itemChange(change, value)

    def _notify_connections(self):
        for line in self._connections: line.update_path()

    # ── 連線 ──────────────────────────────────────────────────────────────────

    def add_connection(self, line):
        if line not in self._connections: self._connections.append(line)

    def remove_connection(self, line):
        if line in self._connections: self._connections.remove(line)

    def get_anchor_points(self) -> list:
        """
        回傳連線磁吸用的 4 個基本錨點（上、右、下、左中點）。
        只用四個基本方向，確保箭頭永遠垂直進入形狀邊緣，不會斜切。
        """
        w, h   = self._width, self._height
        cx, cy = w/2, h/2
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
            key=lambda p: (p.x()-from_scene.x())**2 + (p.y()-from_scene.y())**2
        )

    # ── Mermaid ───────────────────────────────────────────────────────────────

    def mermaid_node(self, node_id: str) -> str:
        body  = self._body.plain_text.replace('"', "'")
        title = self._title.plain_text if self._title else ""
        return {
            ShapeType.OVAL:          f'{node_id}(["{body}"])',
            ShapeType.RECT:          f'{node_id}["{body}"]',
            ShapeType.DIAMOND:       f'{node_id}{{"{body}"}}',
            ShapeType.PARALLELOGRAM: f'{node_id}[/"{body}"/]',
            ShapeType.CYLINDER:      f'{node_id}[("{body}")]',
            ShapeType.PREDEFINED:    f'{node_id}[["{body}"]]',
            ShapeType.RECT_DESCRIBE: f'{node_id}["**{title}**\n{body}"]',
            ShapeType.DOCUMENT:      f'{node_id}["{body}"]',
            ShapeType.MANUAL_INPUT:  f'{node_id}["{body}"]',
            ShapeType.HEXAGON:       f'{node_id}["{body}"]',
            ShapeType.DELAY:         f'{node_id}["{body}"]',
        }.get(self._shape_type, f'{node_id}["{body}"]')

    # ── 序列化 ────────────────────────────────────────────────────────────────

    def to_dict(self):
        d = {
            "type": "shape", "id": self._id,
            "shape_type": self._shape_type.name,
            "x": self.pos().x(), "y": self.pos().y(),
            "w": self._width,    "h": self._height,
            "body":      self._body.plain_text,
            "body_html": self._body.toHtml(),
            "border_color": self._border_color.name(),
            "bg_color":     self._bg_color.name(),
            "border_width": self._border_width,
            "font_size":    self._font_size,
        }
        if self._title:
            d["title"]      = self._title.plain_text
            d["title_html"] = self._title.toHtml()
        return d

    @classmethod
    def from_dict(cls, d):
        item = cls(ShapeType[d["shape_type"]], d["w"], d["h"])
        item.setPos(d["x"], d["y"])
        body_html = d.get("body_html")
        if body_html:
            item._body.setHtml(body_html)
        else:
            item._body.setPlainText(d.get("body", ""))
        if item._title:
            title_html = d.get("title_html")
            if title_html:
                item._title.setHtml(title_html)
            else:
                item._title.setPlainText(d.get("title", ""))
        item._border_color = QColor(d.get("border_color", BOX_BORDER_COLOR))
        item._bg_color     = QColor(d.get("bg_color",     BOX_BODY_BG))
        item._border_width = d.get("border_width", BOX_BORDER_WIDTH)
        item._font_size    = d.get("font_size",    BOX_BODY_FONT_SIZE)
        item._layout_text()
        return item

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def shape_type(self):   return self._shape_type
    @property
    def border_color(self): return self._border_color
    @property
    def bg_color(self):     return self._bg_color
    @property
    def border_width(self): return self._border_width
    @property
    def font_size(self):    return self._font_size

    def set_border_color(self, c):
        self._border_color = QColor(c) if not isinstance(c, QColor) else c
        self.update()

    def set_bg_color(self, c):
        self._bg_color = QColor(c) if not isinstance(c, QColor) else c
        self.update()

    def set_border_width(self, w):
        self._border_width = w
        self.update()

    def set_font_size(self, s):
        self._font_size = s
        self.update()
