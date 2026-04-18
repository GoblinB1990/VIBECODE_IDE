"""
table_picker.py

TABLE 按鈕彈出的尺寸選擇器。
使用者將滑鼠移過格子選擇 M×N，點擊確認。
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen

from constants import (
    PICKER_BG, COLOR_ACCENT, COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED,
    COLOR_SEPARATOR, FONT_FAMILY, FONT_SIZE_SMALL
)

# 每個格子的像素大小（比畫布網格 20px 稍小）
CELL_PX  = 15
MAX_COLS = 16
MAX_ROWS = 12


# ── 內部格子繪製元件 ──────────────────────────────────────────────────────────

class _GridWidget(QWidget):
    hover_changed = pyqtSignal(int, int)   # col, row (1-based, 0=none)
    cell_clicked  = pyqtSignal(int, int)   # col, row (1-based)

    def __init__(self, cols: int, rows: int, cell_px: int, parent=None):
        super().__init__(parent)
        self._cols    = cols
        self._rows    = rows
        self._cell    = cell_px
        self._hover_c = 0
        self._hover_r = 0
        self.setMouseTracking(True)
        w = cols * (cell_px + 1) + 1
        h = rows * (cell_px + 1) + 1
        self.setFixedSize(w, h)

    def mouseMoveEvent(self, event):
        pos = event.position()
        c = min(int(pos.x() / (self._cell + 1)) + 1, self._cols)
        r = min(int(pos.y() / (self._cell + 1)) + 1, self._rows)
        c = max(c, 1)
        r = max(r, 1)
        if c != self._hover_c or r != self._hover_r:
            self._hover_c = c
            self._hover_r = r
            self.hover_changed.emit(c, r)
            self.update()

    def leaveEvent(self, event):
        self._hover_c = 0
        self._hover_r = 0
        self.hover_changed.emit(0, 0)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._hover_c > 0:
            self.cell_clicked.emit(self._hover_c, self._hover_r)

    def paintEvent(self, event):
        p = QPainter(self)
        cs = self._cell
        accent_color = QColor(COLOR_ACCENT)
        hl_fill      = QColor(COLOR_ACCENT)
        hl_fill.setAlpha(0x44)
        bg_fill      = QColor("#24283b")
        sep_color    = QColor(COLOR_SEPARATOR)

        for r in range(self._rows):
            for c in range(self._cols):
                x = c * (cs + 1) + 1
                y = r * (cs + 1) + 1
                highlighted = (c + 1) <= self._hover_c and (r + 1) <= self._hover_r
                if highlighted:
                    p.fillRect(x, y, cs, cs, hl_fill)
                    p.setPen(QPen(accent_color, 1))
                else:
                    p.fillRect(x, y, cs, cs, bg_fill)
                    p.setPen(QPen(sep_color, 1))
                p.drawRect(x, y, cs, cs)
        p.end()


# ── TablePicker ───────────────────────────────────────────────────────────────

class TablePicker(QWidget):
    """
    彈出式表格尺寸選擇器。
    Signals:
        table_selected(rows, cols) — 使用者確認選擇後發出
    """
    table_selected = pyqtSignal(int, int)  # rows, cols

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(f"""
            TablePicker {{
                background: {PICKER_BG};
                border: 1px solid {COLOR_SEPARATOR};
                border-radius: 8px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        title = QLabel("Insert Table")
        title.setStyleSheet(
            f"color:{COLOR_TEXT_MUTED}; font-family:'{FONT_FAMILY}';"
            f"font-size:{FONT_SIZE_SMALL}px; font-weight:600;"
        )
        layout.addWidget(title)

        self._grid = _GridWidget(MAX_COLS, MAX_ROWS, CELL_PX)
        self._grid.hover_changed.connect(self._on_hover)
        self._grid.cell_clicked.connect(self._on_click)
        layout.addWidget(self._grid)

        self._label = QLabel("Move cursor to select size")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet(
            f"color:{COLOR_TEXT_PRIMARY}; font-family:'{FONT_FAMILY}';"
            f"font-size:{FONT_SIZE_SMALL + 1}px; font-weight:600;"
        )
        layout.addWidget(self._label)

    def _on_hover(self, col: int, row: int):
        if col > 0 and row > 0:
            self._label.setText(f"{col} × {row}  Table")
        else:
            self._label.setText("Move cursor to select size")

    def _on_click(self, col: int, row: int):
        if col > 0 and row > 0:
            self.hide()
            self.table_selected.emit(row, col)

    def show_near(self, global_pos: QPoint):
        self.adjustSize()
        self.move(global_pos)
        self.show()
