"""
file_picker.py

FILE 按鈕彈出的選單（仿 ShapePicker 風格）。
包含 New / Open / Save 三個選項。
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QSize
from PyQt6.QtGui import QPainter, QPixmap, QIcon, QPen, QColor, QPolygonF
from PyQt6.QtCore import QPointF

from constants import (
    PICKER_BG, COLOR_ACCENT, COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED,
    COLOR_SEPARATOR, FONT_FAMILY, FONT_SIZE_SMALL
)
from theme import theme as _theme


# ── Icon 繪製 ─────────────────────────────────────────────────────────────────

def _make_icon(draw_fn, size=20) -> QIcon:
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    draw_fn(p, size)
    p.end()
    return QIcon(px)


def _draw_new(p, s):
    """空白文件 + 中央 + 號。"""
    fold = 4
    p.setPen(QPen(QColor(_theme.get("text_primary")), 1.4))
    p.setBrush(Qt.BrushStyle.NoBrush)
    pts = QPolygonF([
        QPointF(2, 1),
        QPointF(s - 2 - fold, 1),
        QPointF(s - 2, 1 + fold),
        QPointF(s - 2, s - 1),
        QPointF(2, s - 1),
    ])
    p.drawPolygon(pts)
    p.drawLine(QPointF(s - 2 - fold, 1),      QPointF(s - 2 - fold, 1 + fold))
    p.drawLine(QPointF(s - 2 - fold, 1 + fold), QPointF(s - 2, 1 + fold))
    # + 號
    cx  = s / 2
    cy  = s * 0.64
    seg = 3.5
    p.drawLine(QPointF(cx - seg, cy), QPointF(cx + seg, cy))
    p.drawLine(QPointF(cx, cy - seg), QPointF(cx, cy + seg))


def _draw_open(p, s):
    """開啟資料夾圖示。"""
    p.setPen(QPen(QColor(_theme.get("text_primary")), 1.4))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(2, 7, s - 4, s - 10)
    p.drawLine(2, 7, 7, 3)
    p.drawLine(7, 3, 13, 3)
    p.drawLine(13, 3, 13, 7)


def _draw_save(p, s):
    """磁碟片圖示。"""
    p.setPen(QPen(QColor(_theme.get("text_primary")), 1.4))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(2, 2, s - 4, s - 4)
    p.drawRect(6, 2, 8, 5)
    p.drawRect(5, 13, s - 10, s - 16)


# ── FilePicker ─────────────────────────────────────────────────────────────────

class FilePicker(QWidget):
    """
    FILE 按鈕彈出的浮動選單。
    Signals:
        new_clicked()  — 使用者選擇「新建」
        open_clicked() — 使用者選擇「開啟」
        save_clicked() — 使用者選擇「儲存」
    """
    new_clicked  = pyqtSignal()
    open_clicked = pyqtSignal()
    save_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(f"""
            FilePicker {{
                background: {PICKER_BG};
                border: 1px solid {COLOR_SEPARATOR};
                border-radius: 8px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(2)

        self._add_item("New",  "新建空白圖樣",  _draw_new,  self.new_clicked)
        self._add_item("Open", "開啟 .vbc 檔案", _draw_open, self.open_clicked)
        self._add_item("Save", "儲存目前檔案",   _draw_save, self.save_clicked)

    def _add_item(self, label: str, tip: str, draw_fn, signal: pyqtSignal):
        btn = QPushButton()
        btn.setFixedHeight(32)
        btn.setIcon(_make_icon(draw_fn))
        btn.setIconSize(QSize(18, 18))
        btn.setText("  " + label)
        btn.setToolTip(tip)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 5px;
                color: {COLOR_TEXT_PRIMARY};
                font-family: '{FONT_FAMILY}';
                font-size: {FONT_SIZE_SMALL + 1}px;
                text-align: left;
                padding: 0 8px;
            }}
            QPushButton:hover {{
                background: {COLOR_ACCENT}22;
                color: {COLOR_ACCENT};
            }}
        """)
        # 用 lambda 捕獲 signal，避免閉包問題
        btn.clicked.connect(lambda _checked=False, s=signal: (self.hide(), s.emit()))
        self.layout().addWidget(btn)

    def show_near(self, global_pos: QPoint):
        self.adjustSize()
        self.move(global_pos)
        self.show()
