from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from constants import (
    COLOR_BG_DARK, COLOR_BG_LIGHT, COLOR_ACCENT, COLOR_SEPARATOR,
    COLOR_TEXT_PRIMARY, FONT_FAMILY, FONT_SIZE_SMALL,
    STICKY_PALETTE,
)
from theme import theme as _theme

# ── 莫蘭迪調色盤（20 色）────────────────────────────────────────────────────

PALETTE = [
    "#f5f1eb",  # 米白（明亮模式形狀預設底色）
    "#ffffff",  # 純白
    "#bf8888",  # 霧玫瑰紅
    "#c4966e",  # 赭陶
    "#c4b070",  # 沙金
    "#a8bc78",  # 橄欖黃綠
    "#7eae80",  # 鼠尾草綠
    "#6eaaa0",  # 海沫綠
    "#70a4bc",  # 霧藍
    "#7888c4",  # 長春花藍
    "#9480c0",  # 暗紫
    "#b87ec4",  # 蘭花紫
    "#c47eb0",  # 莫蘭迪紫紅
    "#c4789a",  # 玫瑰粉
    "#b8a890",  # 亞麻米
    "#a8b0a8",  # 鼠灰綠
    "#94a4b8",  # 鋼藍灰
    "#b4acbc",  # 薰衣草灰
    "#d4c4b8",  # 暖奶白
    "#24283b",  # 深底色（保留）
]

# Bug 3 修正：label 顏色從 #565f89 → #a9b1d6，大小從 8px → 10px
_LABEL_STYLE = (
    f"color:#a9b1d6; font-family:'{FONT_FAMILY}';"
    f"font-size:{FONT_SIZE_SMALL + 1}px;"
)


# ── 單色色票 ──────────────────────────────────────────────────────────────────

class _Swatch(QPushButton):
    def __init__(self, hex_color: str, size: int = 20, parent=None):
        super().__init__(parent)
        self._hex  = hex_color
        self._ring = False
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(hex_color)
        self._refresh()

    def _refresh(self):
        sep = _theme.get("separator", "#3b4261")
        ac  = _theme.get("accent_hover", "#7dcfff")
        border = f"2px solid {ac}" if self._ring else f"1px solid {sep}"
        self.setStyleSheet(f"""
            QPushButton {{
                background: {self._hex};
                border: {border};
                border-radius: 3px;
            }}
            QPushButton:hover {{ border: 2px solid #7aa2f7; }}
        """)

    def set_active(self, yes: bool):
        self._ring = yes
        self._refresh()

    @property
    def hex_color(self) -> str:
        return self._hex


# ── 顏色列（標籤 + 色票）────────────────────────────────────────────────────

class _ColorRow(QWidget):
    color_picked = pyqtSignal(QColor)

    def __init__(self, label: str, palette: list | None = None,
                 swatch_size: int = 20, parent=None):
        super().__init__(parent)
        if palette is None:
            palette = PALETTE
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        lbl = QLabel(label)
        lbl.setFixedWidth(32)
        lbl.setStyleSheet(_LABEL_STYLE)
        layout.addWidget(lbl)

        self._swatches: list[_Swatch] = []
        for hex_c in palette:
            sw = _Swatch(hex_c, swatch_size, self)
            sw.clicked.connect(lambda _, c=hex_c: self.color_picked.emit(QColor(c)))
            layout.addWidget(sw)
            self._swatches.append(sw)

    def mark_active(self, color: QColor):
        target = color.name().lower()
        for sw in self._swatches:
            sw.set_active(sw.hex_color.lower() == target)


# ── 字型大小列（便利貼用）────────────────────────────────────────────────────

class _SizeRow(QWidget):
    size_picked = pyqtSignal(int)

    SIZES = [10, 12, 14, 16, 18]

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        lbl = QLabel("大小")
        lbl.setFixedWidth(32)
        lbl.setStyleSheet(_LABEL_STYLE)
        layout.addWidget(lbl)

        for sz in self.SIZES:
            btn = QPushButton(str(sz))
            btn.setFixedSize(26, 20)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {COLOR_BG_LIGHT};
                    border: 1px solid {COLOR_SEPARATOR};
                    border-radius: 3px;
                    color: #a9b1d6;
                    font-family: '{FONT_FAMILY}';
                    font-size: {FONT_SIZE_SMALL}px;
                }}
                QPushButton:hover {{
                    background: {COLOR_ACCENT}33;
                    border: 1px solid {COLOR_ACCENT};
                    color: {COLOR_ACCENT};
                }}
            """)
            btn.clicked.connect(lambda _, s=sz: self.size_picked.emit(s))
            layout.addWidget(btn)


# ── 主浮動顏色選單 ────────────────────────────────────────────────────────────

class ColorPopup(QWidget):
    """
    浮動顏色選單，掛在 CanvasView 上方置中顯示。
    根據選取物件類型切換 Shape / Line / StickyNote / 混合 模式。
    """

    border_color_picked    = pyqtSignal(QColor)
    fill_color_picked      = pyqtSignal(QColor)
    line_color_picked      = pyqtSignal(QColor)
    sticky_bg_picked       = pyqtSignal(QColor)
    sticky_text_picked     = pyqtSignal(QColor)
    sticky_size_picked     = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ColorPopup")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            #ColorPopup {{
                background: {COLOR_BG_DARK};
                border: 1px solid {COLOR_SEPARATOR};
                border-radius: 8px;
            }}
        """)
        self._build_ui()
        self.hide()

    def _build_ui(self):
        self._main_layout = QHBoxLayout(self)
        self._main_layout.setContentsMargins(10, 7, 10, 7)
        self._main_layout.setSpacing(8)

        # ── Shape 區域 ────────────────────────────────────────────────────────
        self._shape_widget = QWidget()
        sv = QVBoxLayout(self._shape_widget)
        sv.setContentsMargins(0, 0, 0, 0)
        sv.setSpacing(4)
        self._row_border = _ColorRow("邊框")
        self._row_fill   = _ColorRow("填色")
        self._row_border.color_picked.connect(self.border_color_picked)
        self._row_fill.color_picked.connect(self.fill_color_picked)
        sv.addWidget(self._row_border)
        sv.addWidget(self._row_fill)
        self._main_layout.addWidget(self._shape_widget)

        # ── 分隔 ──────────────────────────────────────────────────────────────
        self._sep = _Sep()
        self._main_layout.addWidget(self._sep)

        # ── Line 區域 ─────────────────────────────────────────────────────────
        self._line_widget = QWidget()
        lv = QVBoxLayout(self._line_widget)
        lv.setContentsMargins(0, 0, 0, 0)
        self._row_line = _ColorRow("線色")
        self._row_line.color_picked.connect(self.line_color_picked)
        lv.addWidget(self._row_line)
        self._main_layout.addWidget(self._line_widget)

        # ── StickyNote 區域 ───────────────────────────────────────────────────
        self._sticky_widget = QWidget()
        sticky_v = QVBoxLayout(self._sticky_widget)
        sticky_v.setContentsMargins(0, 0, 0, 0)
        sticky_v.setSpacing(4)
        self._row_sticky_bg   = _ColorRow("底色", STICKY_PALETTE, swatch_size=22)
        self._row_sticky_text = _ColorRow("字色", PALETTE, swatch_size=18)
        self._row_sticky_size = _SizeRow()
        self._row_sticky_bg.color_picked.connect(self.sticky_bg_picked)
        self._row_sticky_text.color_picked.connect(self.sticky_text_picked)
        self._row_sticky_size.size_picked.connect(self.sticky_size_picked)
        sticky_v.addWidget(self._row_sticky_bg)
        sticky_v.addWidget(self._row_sticky_text)
        sticky_v.addWidget(self._row_sticky_size)
        self._main_layout.addWidget(self._sticky_widget)

    # ── 顯示切換 ──────────────────────────────────────────────────────────────

    def _show_only(self, shape=False, line=False, sep=False, sticky=False):
        self._shape_widget.setVisible(shape)
        self._sep.setVisible(sep)
        self._line_widget.setVisible(line)
        self._sticky_widget.setVisible(sticky)
        self.adjustSize()
        self.show()
        self._center_in_parent()

    def show_for_shapes(self, shapes: list):
        if shapes:
            self._row_border.mark_active(shapes[0].border_color)
            self._row_fill.mark_active(shapes[0].bg_color)
        self._show_only(shape=True)

    def show_for_lines(self, lines: list):
        if lines:
            self._row_line.mark_active(lines[0].line_color)
        self._show_only(line=True)

    def show_for_mixed(self, shapes: list, lines: list):
        if shapes:
            self._row_border.mark_active(shapes[0].border_color)
            self._row_fill.mark_active(shapes[0].bg_color)
        if lines:
            self._row_line.mark_active(lines[0].line_color)
        self._show_only(shape=True, sep=True, line=True)

    def show_for_sticky(self, notes: list):
        if notes:
            self._row_sticky_bg.mark_active(notes[0].bg_color)
            self._row_sticky_text.mark_active(notes[0].text_color)
        self._show_only(sticky=True)

    def reposition(self):
        if self.isVisible():
            self._center_in_parent()

    def _center_in_parent(self):
        p = self.parent()
        if p is None:
            return
        x = max(10, (p.width() - self.width()) // 2)
        self.move(x, 12)

    def apply_theme(self):
        """切換主題後更新 popup 容器背景及標籤顏色。"""
        self.setStyleSheet(f"""
            #ColorPopup {{
                background: {_theme.get('bg_dark')};
                border: 1px solid {_theme.get('separator')};
                border-radius: 8px;
            }}
        """)
        lbl_color = _theme.get("text_primary")
        for lbl in self.findChildren(QLabel):
            lbl.setStyleSheet(f"color:{lbl_color};")
        for sw in self.findChildren(_Swatch):
            sw._refresh()
        for btn in self.findChildren(QPushButton):
            if isinstance(btn, _Swatch):
                continue
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {_theme.get('bg_light')};
                    border: 1px solid {_theme.get('separator')};
                    border-radius: 3px;
                    color: {_theme.get('text_primary')};
                    font-family: '{FONT_FAMILY}';
                    font-size: {FONT_SIZE_SMALL}px;
                }}
                QPushButton:hover {{
                    background: {_theme.get('accent')}33;
                    border: 1px solid {_theme.get('accent')};
                    color: {_theme.get('accent')};
                }}
            """)


# ── 分隔線 ─────────────────────────────────────────────────────────────────

class _Sep(QFrame):
    """直線分隔（豎直）。"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.VLine)
        self.setLineWidth(1)
        self.setStyleSheet(f"background:{_theme.get('separator')}; border:none;")
