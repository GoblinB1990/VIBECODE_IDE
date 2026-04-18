# 檔案位置：ui/text_style_toolbar.py

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QFrame
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextCharFormat, QFont, QColor, QTextBlockFormat

from constants import (
    TEXT_STYLE_SIZES, TEXT_STYLE_COLORS,
    COLOR_BG_DARK, COLOR_SEPARATOR, COLOR_ACCENT,
    COLOR_TEXT_PRIMARY, FONT_FAMILY, FONT_SIZE_SMALL,
)
from theme import theme as _theme

_TOOLBAR_H = 34   # 固定高度，讓第一次定位就能算對


class TextStyleToolbar(QWidget):
    """
    文字格式工具列 — 浮動覆蓋層（掛在 CanvasView 上，貼近底部）。
    - WA_ShowWithoutActivating：顯示時不搶焦點
    - 所有按鈕 NoFocus：點擊時不搶走 text item 的焦點
    - 格式只作用於「目前游標選取的文字」，無選取則不動作
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TextStyleToolbar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFixedHeight(_TOOLBAR_H)
        self.setStyleSheet(f"""
            #TextStyleToolbar {{
                background: {_theme.get('bg_dark')};
                border: 1px solid {_theme.get('separator')};
                border-radius: 6px;
            }}
        """)
        self._current = None
        self._build_ui()
        self.hide()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(3)

        self._btn_bold   = self._fmt_btn("B",  "粗體",  style="bold")
        self._btn_italic = self._fmt_btn("I",  "斜體",  style="italic")
        self._btn_strike = self._fmt_btn("S\u0336", "刪除線", style="strike")
        layout.addWidget(self._btn_bold)
        layout.addWidget(self._btn_italic)
        layout.addWidget(self._btn_strike)

        layout.addWidget(_VSep())

        self._btn_al = self._align_btn("L", "靠左",  Qt.AlignmentFlag.AlignLeft)
        self._btn_ac = self._align_btn("C", "置中",  Qt.AlignmentFlag.AlignHCenter)
        self._btn_ar = self._align_btn("R", "靠右",  Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._btn_al)
        layout.addWidget(self._btn_ac)
        layout.addWidget(self._btn_ar)

        layout.addWidget(_VSep())

        for sz in TEXT_STYLE_SIZES:
            btn = QPushButton(str(sz))
            btn.setFixedSize(26, 22)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setStyleSheet(self._small_btn_css())
            btn.clicked.connect(lambda _, s=sz: self._apply_size(s))
            layout.addWidget(btn)

        layout.addWidget(_VSep())

        for hex_c in TEXT_STYLE_COLORS:
            sw = _ColorDot(hex_c)
            sw.clicked.connect(lambda _, c=hex_c: self._apply_color(c))
            layout.addWidget(sw)

    def _fmt_btn(self, label, tip, style):
        btn = QPushButton(label)
        btn.setFixedSize(26, 22)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setToolTip(tip)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        f = QFont(FONT_FAMILY, FONT_SIZE_SMALL)
        if style == "bold":   f.setBold(True)
        if style == "italic": f.setItalic(True)
        btn.setFont(f)
        btn.setStyleSheet(self._small_btn_css())
        if   style == "bold":   btn.clicked.connect(self._toggle_bold)
        elif style == "italic": btn.clicked.connect(self._toggle_italic)
        elif style == "strike": btn.clicked.connect(self._toggle_strike)
        return btn

    def _align_btn(self, label, tip, alignment):
        btn = QPushButton(label)
        btn.setFixedSize(26, 22)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setToolTip(tip)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn.setStyleSheet(self._small_btn_css())
        btn.clicked.connect(lambda _, a=alignment: self._apply_alignment(a))
        return btn

    def _small_btn_css(self):
        sep = _theme.get("separator")
        txt = _theme.get("text_primary")
        ac  = _theme.get("accent")
        return f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {sep};
                border-radius: 3px;
                color: {txt};
                font-family: '{FONT_FAMILY}';
                font-size: {FONT_SIZE_SMALL}px;
                padding: 0;
            }}
            QPushButton:hover {{
                background: {ac}33;
                border: 1px solid {ac};
                color: {ac};
            }}
        """

    # ── 浮動定位 ──────────────────────────────────────────────────────────────

    def show_for(self, text_item):
        self._current = text_item
        self.show()          # 先 show，Qt 才能計算真實尺寸
        self.adjustSize()    # 強制計算 sizeHint
        self._position_toolbar()
        self.raise_()

    def hide_toolbar(self):
        self._current = None
        self.hide()

    def apply_theme(self):
        """切換主題後更新文字工具列背景及按鈕顏色。"""
        self.setStyleSheet(f"""
            #TextStyleToolbar {{
                background: {_theme.get('bg_dark')};
                border: 1px solid {_theme.get('separator')};
                border-radius: 6px;
            }}
        """)
        new_css = self._small_btn_css()
        for btn in self.findChildren(QPushButton):
            if isinstance(btn, _ColorDot):
                btn.apply_theme()
            else:
                btn.setStyleSheet(new_css)
        for sep in self.findChildren(QFrame):
            if sep.frameShape() == QFrame.Shape.VLine:
                sep.setStyleSheet(f"background:{_theme.get('separator')}; border:none;")
        self.update()

    def reposition(self):
        if self.isVisible():
            self._position_toolbar()

    def _position_toolbar(self):
        """置中顯示在父元件底部，距底部 12px。"""
        p = self.parent()
        if p is None:
            return
        w = self.width() if self.width() > 0 else self.sizeHint().width()
        h = self.height() if self.height() > 0 else _TOOLBAR_H
        x = max(10, (p.width() - w) // 2)
        y = p.height() - h - 12   # 貼底部
        self.move(x, y)

    # ── 格式套用 ──────────────────────────────────────────────────────────────

    def _toggle_bold(self):
        if not self._current: return
        cur = self._current.textCursor()
        if not cur.hasSelection(): return
        fmt = QTextCharFormat()
        is_bold = cur.charFormat().fontWeight() >= QFont.Weight.Bold
        fmt.setFontWeight(QFont.Weight.Normal if is_bold else QFont.Weight.Bold)
        cur.mergeCharFormat(fmt)
        self._current.setTextCursor(cur)

    def _toggle_italic(self):
        if not self._current: return
        cur = self._current.textCursor()
        if not cur.hasSelection(): return
        fmt = QTextCharFormat()
        fmt.setFontItalic(not cur.charFormat().fontItalic())
        cur.mergeCharFormat(fmt)
        self._current.setTextCursor(cur)

    def _toggle_strike(self):
        if not self._current: return
        cur = self._current.textCursor()
        if not cur.hasSelection(): return
        fmt = QTextCharFormat()
        fmt.setFontStrikeOut(not cur.charFormat().fontStrikeOut())
        cur.mergeCharFormat(fmt)
        self._current.setTextCursor(cur)

    def _apply_size(self, size):
        if not self._current: return
        cur = self._current.textCursor()
        if not cur.hasSelection(): return
        fmt = QTextCharFormat()
        fmt.setFontPointSize(float(size))
        cur.mergeCharFormat(fmt)
        self._current.setTextCursor(cur)

    def _apply_color(self, hex_c):
        if not self._current: return
        cur = self._current.textCursor()
        if not cur.hasSelection(): return
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(hex_c))
        cur.mergeCharFormat(fmt)
        self._current.setTextCursor(cur)

    def _apply_alignment(self, alignment):
        if not self._current: return
        cur = self._current.textCursor()
        fmt = QTextBlockFormat()
        fmt.setAlignment(alignment)
        cur.mergeBlockFormat(fmt)
        self._current.setTextCursor(cur)


# ── 垂直分隔線 ─────────────────────────────────────────────────────────────────

class _VSep(QFrame):
    """工具列垂直分隔線。"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.VLine)
        self.setFixedWidth(1)
        self.setFixedHeight(18)
        from theme import theme as _t
        self.setStyleSheet(f"background: {_t.get('separator', '#3b4261')}; border: none;")


# ── 顏色圓點 ───────────────────────────────────────────────────────────────────

class _ColorDot(QPushButton):
    """文字顏色選擇圓點，帶可見邊框以在淺色模式下顯示白色點。"""
    def __init__(self, hex_color: str, parent=None):
        super().__init__(parent)
        self._hex = hex_color
        self.setFixedSize(20, 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setToolTip(hex_color)
        self._refresh()

    def _refresh(self):
        from theme import theme as _t
        border_color = _t.get("separator", "#3b4261")
        self.setStyleSheet(f"""
            QPushButton {{
                background: {self._hex};
                border: 1.5px solid {border_color};
                border-radius: 10px;
                padding: 0;
            }}
            QPushButton:hover {{
                border: 2px solid {_t.get("accent", "#7aa2f7")};
            }}
        """)

    def apply_theme(self):
        self._refresh()
