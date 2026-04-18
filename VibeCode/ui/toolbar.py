from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QFrame
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QPointF, QRectF
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QPixmap, QIcon, QFont, QPolygonF

from constants import (
    ToolMode, ShapeType,
    TOOLBAR_WIDTH, TOOLBAR_BTN_SIZE, TOOLBAR_BTN_ICON_SZ,
    COLOR_BG_DARK, COLOR_ACCENT, COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED,
    COLOR_SEPARATOR, FONT_FAMILY, FONT_SIZE_SMALL
)
from theme import theme as _theme


# ── Icon 繪製 ──────────────────────────────────────────────────────────────────

def _make_icon(draw_fn, size=24) -> QIcon:
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    draw_fn(p, size)
    p.end()
    return QIcon(px)


def _icon_select(p, s):
    c = _theme.get("text_primary")
    p.setPen(QPen(QColor(c), 1.5))
    p.setBrush(QBrush(QColor(c)))
    arrow = QPolygonF([QPointF(5,3),QPointF(5,18),QPointF(9,14),
                       QPointF(12,20),QPointF(14,19),QPointF(11,13),QPointF(16,13)])
    p.drawPolygon(arrow)


def _icon_text(p, s):
    p.setPen(QPen(QColor(_theme.get("text_primary")), 1.5))
    f = QFont(FONT_FAMILY, 14, QFont.Weight.Bold)
    p.setFont(f)
    p.drawText(4, s - 4, "T")


def _icon_shape(p, s):
    p.setPen(QPen(QColor(_theme.get("accent")), 1.8))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(3, 3, s-6, s-6, 4, 4)
    p.drawLine(3, 9, s-3, 9)


def _icon_line(p, s):
    p.setPen(QPen(QColor(_theme.get("accent")), 1.8))
    p.drawLine(3, s-3, s-3, 3)
    p.setBrush(QBrush(QColor(_theme.get("accent"))))
    p.drawPolygon(QPolygonF([QPointF(s-3,3), QPointF(s-9,4), QPointF(s-4,9)]))


def _icon_note(p, s):
    """便利貼 icon：帶折角的方形 + 橫線。"""
    fold = 6
    p.setPen(QPen(QColor(_theme.get("accent")), 1.6))
    p.setBrush(Qt.BrushStyle.NoBrush)
    pts = QPolygonF([
        QPointF(3,       3),
        QPointF(s-3-fold, 3),
        QPointF(s-3,     3+fold),
        QPointF(s-3,     s-3),
        QPointF(3,       s-3),
    ])
    p.drawPolygon(pts)
    p.drawLine(QPointF(s-3-fold, 3), QPointF(s-3-fold, 3+fold))
    p.drawLine(QPointF(s-3-fold, 3+fold), QPointF(s-3, 3+fold))
    p.setPen(QPen(QColor(_theme.get("accent")), 1))
    for y in [10, 14, 18]:
        if y < s - 4:
            p.drawLine(QPointF(6, float(y)), QPointF(float(s-7), float(y)))


def _icon_table(p, s):
    """Table icon：3×3 格子。"""
    rows, cols = 3, 3
    x0, y0 = 3, 5
    w = s - 6
    h = s - 10
    cw = w / cols
    rh = h / rows
    p.setPen(QPen(QColor(_theme.get("accent")), 1.5))
    p.setBrush(Qt.BrushStyle.NoBrush)
    # 外框
    p.drawRect(QRectF(x0, y0, w, h))
    # 垂直線
    for i in range(1, cols):
        x = x0 + i * cw
        p.drawLine(QPointF(x, y0), QPointF(x, y0 + h))
    # 水平線（第一條加粗，代表表頭）
    for i in range(1, rows):
        y = y0 + i * rh
        pen_w = 1.8 if i == 1 else 1.0
        p.setPen(QPen(QColor(_theme.get("accent")), pen_w))
        p.drawLine(QPointF(x0, y), QPointF(x0 + w, y))


def _icon_image(p, s):
    """圖片 icon：方框 + 山形 + 太陽。"""
    p.setPen(QPen(QColor(_theme.get("accent")), 1.8))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(3, 3, s-6, s-6, 3, 3)
    pts = QPolygonF([
        QPointF(3,    s-6),
        QPointF(9,    s-13),
        QPointF(14,   s-9),
        QPointF(17,   s-13),
        QPointF(s-3,  s-6),
    ])
    p.drawPolyline(pts)
    p.drawEllipse(QPointF(7, 9), 3, 3)


def _icon_screenshot(p, s):
    p.setPen(QPen(QColor(_theme.get("text_primary")), 1.5))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(2, 5, s-4, s-8, 3, 3)
    p.drawEllipse(s//2-4, s//2-2, 8, 8)
    p.drawRect(8, 3, 8, 4)


def _icon_ai(p, s):
    """AI icon：簡單人頭（圓圈頭部 + 肩膀半弧）。"""
    cx      = s / 2
    head_r  = s * 0.17
    head_cy = s * 0.36
    p.setPen(QPen(QColor(_theme.get("text_primary")), 1.5))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QPointF(cx, head_cy), head_r, head_r)
    shoulder_top = head_cy + head_r + 2
    rect = QRectF(3, shoulder_top, s - 6, s - shoulder_top - 1)
    p.drawArc(rect, 0, 180 * 16)


def _icon_settings(p, s):
    """Settings icon：純輪廓齒輪（無填色）。"""
    import math
    cx, cy = s / 2, s / 2
    r_out, r_mid, r_in = s/2 - 2, s/2 - 5, s/2 - 9
    teeth = 6
    pts = []
    for i in range(teeth * 2):
        angle = math.radians(i * (360 / (teeth * 2)) - 90)
        r = r_out if i % 2 == 0 else r_mid
        pts.append(QPointF(cx + r * math.cos(angle), cy + r * math.sin(angle)))
    p.setPen(QPen(QColor(_theme.get("text_primary")), 1.5))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPolygon(QPolygonF(pts))
    p.drawEllipse(QPointF(cx, cy), r_in, r_in)


def _icon_file(p, s):
    """File icon：帶折角的文件（通用檔案管理）。"""
    fold = 5
    p.setPen(QPen(QColor(_theme.get("text_primary")), 1.5))
    p.setBrush(Qt.BrushStyle.NoBrush)
    pts = QPolygonF([
        QPointF(4,       3),
        QPointF(s-4-fold, 3),
        QPointF(s-4,     3+fold),
        QPointF(s-4,     s-3),
        QPointF(4,       s-3),
    ])
    p.drawPolygon(pts)
    p.drawLine(QPointF(s-4-fold, 3),        QPointF(s-4-fold, 3+fold))
    p.drawLine(QPointF(s-4-fold, 3+fold),   QPointF(s-4, 3+fold))
    # 文件內橫線
    p.setPen(QPen(QColor(_theme.get("text_primary")), 1.0))
    for y in [10, 14, 18]:
        if y < s - 5:
            p.drawLine(QPointF(7, float(y)), QPointF(float(s-7), float(y)))


def _icon_open(p, s):
    p.setPen(QPen(QColor(_theme.get("text_primary")), 1.5))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(2, 7, s-4, s-10)
    p.drawLine(2,7,7,3); p.drawLine(7,3,13,3); p.drawLine(13,3,13,7)


def _icon_save(p, s):
    p.setPen(QPen(QColor(_theme.get("text_primary")), 1.5))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(3, 3, s-6, s-6)
    p.drawRect(7, 3, 10, 6)
    p.drawRect(6, 14, s-12, s-16)


# ── ToolButton ────────────────────────────────────────────────────────────────

class ToolButton(QPushButton):
    def __init__(self, label, draw_fn, tooltip="", checkable=True,
                 label_en=None, tooltip_en=None):
        super().__init__()
        self.setFixedSize(TOOLBAR_BTN_SIZE, TOOLBAR_BTN_SIZE + 14)
        self.setCheckable(checkable)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._draw_fn  = draw_fn
        self._icon     = _make_icon(draw_fn, TOOLBAR_BTN_ICON_SZ)
        self._label_zh = label
        self._label_en = label_en if label_en is not None else label
        self._tip_zh   = tooltip
        self._tip_en   = tooltip_en if tooltip_en is not None else tooltip
        self._locked   = False
        self._refresh_lang()
        self._apply_style(False)

    def _refresh_lang(self):
        from ui.i18n import tr
        self._label = tr(self._label_zh, self._label_en)
        self.setToolTip(tr(self._tip_zh, self._tip_en))
        self.update()

    def rebuild_icon(self):
        """主題切換後重新繪製 icon（以新主題色彩）。"""
        self._icon = _make_icon(self._draw_fn, TOOLBAR_BTN_ICON_SZ)
        self.update()

    def _apply_style(self, checked):
        if self._locked:
            return   # 鎖定狀態由 set_locked() 管理，不覆蓋
        ac   = _theme.get("accent")
        txt  = _theme.get("text_primary")
        bg   = ac + "33" if checked else "transparent"
        bdr  = f"1px solid {ac}" if checked else "1px solid transparent"
        clr  = ac if checked else txt
        self.setStyleSheet(f"""
            QPushButton {{
                background:{bg}; border:{bdr}; border-radius:6px;
                color:{clr}; font-family:'{FONT_FAMILY}'; font-size:{FONT_SIZE_SMALL}px;
                padding-top:4px;
            }}
            QPushButton:hover {{ background:{ac}22; border:1px solid {ac}66; }}
        """)

    def set_locked(self, locked: bool):
        """
        鎖定按鈕：顯示低飽和綠色，防止再次觸發。
        解鎖後恢復預設外觀。
        """
        self._locked = locked
        if locked:
            # 低飽和綠
            green = "#5a9e6f"
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {green}22;
                    border: 1px solid {green}88;
                    border-radius: 6px;
                    color: {green};
                    font-family: '{FONT_FAMILY}';
                    font-size: {FONT_SIZE_SMALL}px;
                    padding-top: 4px;
                }}
                QPushButton:hover {{
                    background: {green}22;
                    border: 1px solid {green}88;
                }}
            """)
            self.setEnabled(False)
        else:
            self.setEnabled(True)
            self._apply_style(self.isChecked())

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        ix = (TOOLBAR_BTN_SIZE - TOOLBAR_BTN_ICON_SZ) // 2
        self._icon.paint(p, ix, 4, TOOLBAR_BTN_ICON_SZ, TOOLBAR_BTN_ICON_SZ)
        lbl_color = _theme.get("accent") if self.isChecked() else _theme.get("text_muted")
        p.setPen(QPen(QColor(lbl_color)))
        p.setFont(QFont(FONT_FAMILY, FONT_SIZE_SMALL - 1))
        text_y = 4 + TOOLBAR_BTN_ICON_SZ + 3
        p.drawText(0, text_y, TOOLBAR_BTN_SIZE, 12,
                   Qt.AlignmentFlag.AlignHCenter, self._label)
        p.end()

    def setChecked(self, checked):
        super().setChecked(checked)
        self._apply_style(checked)


class _Sep(QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFixedHeight(1)
        self._refresh()

    def _refresh(self):
        self.setStyleSheet(f"background:{_theme.get('separator')}; border:none;")


# ── Toolbar ────────────────────────────────────────────────────────────────────

class Toolbar(QWidget):
    """
    按鈕順序：
      File（彈出 New/Open/Save）
      Copy
      ─
      Select → Text → Line → Note → Table（彈出格子選擇）→ Shape → Image
      ─
      [stretch]
      VibeOut
      ─
      Settings
    """
    tool_changed        = pyqtSignal(ToolMode)
    shape_type_changed  = pyqtSignal(ShapeType)
    table_size_changed  = pyqtSignal(int, int)   # rows, cols
    action_new          = pyqtSignal()
    action_open         = pyqtSignal()
    action_save         = pyqtSignal()
    action_screenshot   = pyqtSignal()
    action_ai           = pyqtSignal()
    action_settings     = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(TOOLBAR_WIDTH)
        self.setObjectName("Toolbar")
        self._seps: list[_Sep] = []
        self._tool_buttons: dict[ToolMode, ToolButton] = {}
        self._all_buttons:  list[ToolButton] = []
        self._btn_shape:    ToolButton | None = None
        self._btn_table:    ToolButton | None = None
        self._btn_file:     ToolButton | None = None
        self._btn_ai:       ToolButton | None = None
        self._picker        = None
        self._file_picker   = None
        self._table_picker  = None
        self._apply_toolbar_bg()
        self._build_layout()

    def _build_layout(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 12)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # ── File 按鈕（彈出 New / Open / Save）──────────────────────────────
        btn_file = ToolButton("File", _icon_file, "檔案選單", checkable=False,
                              label_en="File", tooltip_en="File Menu")
        btn_file.clicked.connect(self._show_file_picker)
        layout.addWidget(btn_file)
        self._all_buttons.append(btn_file)
        self._btn_file = btn_file

        # ── Copy 按鈕（緊接在 File 下方）────────────────────────────────────
        btn_shot = ToolButton("Copy", _icon_screenshot, "複製畫布", checkable=False,
                              label_en="Copy", tooltip_en="Copy Canvas")
        btn_shot.clicked.connect(self.action_screenshot)
        layout.addWidget(btn_shot)
        self._all_buttons.append(btn_shot)

        sep1 = _Sep(); layout.addWidget(sep1); self._seps.append(sep1)

        # ── 工具（互斥）────────────────────────────────────────────────────
        tool_defs = [
            (ToolMode.SELECT,   "Select", "Select", _icon_select, "選取 V",  "Select V"),
            (ToolMode.ADD_TEXT, "Text",   "Text",   _icon_text,   "文字 T",  "Text T"),
            (ToolMode.ADD_LINE, "Line",   "Line",   _icon_line,   "連線 L",  "Connect L"),
        ]
        for mode, lbl_zh, lbl_en, draw_fn, tip_zh, tip_en in tool_defs:
            btn = ToolButton(lbl_zh, draw_fn, tip_zh, label_en=lbl_en, tooltip_en=tip_en)
            btn.clicked.connect(lambda _, m=mode: self._on_tool(m))
            layout.addWidget(btn)
            self._tool_buttons[mode] = btn
            self._all_buttons.append(btn)

        # Note 按鈕
        btn_note = ToolButton("Note", _icon_note, "便利貼 N",
                              label_en="Note", tooltip_en="Note N")
        btn_note.clicked.connect(lambda: self._on_tool(ToolMode.ADD_NOTE))
        layout.addWidget(btn_note)
        self._tool_buttons[ToolMode.ADD_NOTE] = btn_note
        self._all_buttons.append(btn_note)

        # Table 按鈕（彈出格子選擇器）
        btn_table = ToolButton("Table", _icon_table, "插入表格",
                               label_en="Table", tooltip_en="Insert Table")
        btn_table.clicked.connect(self._show_table_picker)
        layout.addWidget(btn_table)
        self._tool_buttons[ToolMode.ADD_TABLE] = btn_table
        self._all_buttons.append(btn_table)
        self._btn_table = btn_table

        # Shape 按鈕（彈出 picker）
        btn_shape = ToolButton("Shape", _icon_shape, "形狀 B",
                               label_en="Shape", tooltip_en="Shape B")
        btn_shape.clicked.connect(self._show_picker)
        layout.addWidget(btn_shape)
        self._tool_buttons[ToolMode.ADD_SHAPE] = btn_shape
        self._all_buttons.append(btn_shape)
        self._btn_shape = btn_shape

        # Image 按鈕
        btn_image = ToolButton("Image", _icon_image, "插入圖片 I",
                               label_en="Image", tooltip_en="Image I")
        btn_image.clicked.connect(lambda: self._on_tool(ToolMode.ADD_IMAGE))
        layout.addWidget(btn_image)
        self._tool_buttons[ToolMode.ADD_IMAGE] = btn_image
        self._all_buttons.append(btn_image)

        sep2 = _Sep(); layout.addWidget(sep2); self._seps.append(sep2)

        layout.addStretch()   # 撐開，讓 AI + Settings 固定在最下方

        # ── AI（VibeOut）──────────────────────────────────────────────────────
        self._btn_ai = ToolButton(
            "VibeOut", _icon_ai, "AI 分析：生成功能需求 Prompt", checkable=False,
            label_en="VibeOut", tooltip_en="AI Analysis: Generate Feature Prompt"
        )
        self._btn_ai.clicked.connect(self.action_ai)
        layout.addWidget(self._btn_ai)
        self._all_buttons.append(self._btn_ai)

        sep3 = _Sep(); layout.addWidget(sep3); self._seps.append(sep3)

        self._btn_settings = ToolButton(
            "設定", _icon_settings, "AI 連線設定", checkable=False,
            label_en="Settings", tooltip_en="Settings"
        )
        self._btn_settings.clicked.connect(self.action_settings)
        layout.addWidget(self._btn_settings)
        self._all_buttons.append(self._btn_settings)

        self.set_active_tool(ToolMode.SELECT)

    # ── File Picker ──────────────────────────────────────────────────────────

    def _show_file_picker(self):
        if self._file_picker is None:
            from ui.file_picker import FilePicker
            self._file_picker = FilePicker()
            self._file_picker.new_clicked.connect(self.action_new)
            self._file_picker.open_clicked.connect(self.action_open)
            self._file_picker.save_clicked.connect(self.action_save)

        btn_global = self._btn_file.mapToGlobal(QPoint(TOOLBAR_WIDTH - 4, 0))
        self._file_picker.show_near(btn_global)

    # ── Table Picker ──────────────────────────────────────────────────────────

    def _show_table_picker(self):
        if self._table_picker is None:
            from ui.table_picker import TablePicker
            self._table_picker = TablePicker()
            self._table_picker.table_selected.connect(self._on_table_selected)

        btn_global = self._btn_table.mapToGlobal(QPoint(TOOLBAR_WIDTH - 4, 0))
        self._table_picker.show_near(btn_global)
        self._on_tool(ToolMode.ADD_TABLE)

    def _on_table_selected(self, rows: int, cols: int):
        self.table_size_changed.emit(rows, cols)

    # ── Shape Picker ──────────────────────────────────────────────────────────

    def _show_picker(self):
        if self._picker is None:
            from ui.shape_picker import ShapePicker
            self._picker = ShapePicker()
            self._picker.shape_selected.connect(self._on_shape_selected)

        btn_global = self._btn_shape.mapToGlobal(QPoint(TOOLBAR_WIDTH - 4, 0))
        self._picker.show_near(btn_global)
        self._on_tool(ToolMode.ADD_SHAPE)

    def _on_shape_selected(self, shape_type: ShapeType):
        self.shape_type_changed.emit(shape_type)

    # ── 工具切換 ──────────────────────────────────────────────────────────────

    def _on_tool(self, mode: ToolMode):
        self.set_active_tool(mode)
        self.tool_changed.emit(mode)

    def set_active_tool(self, mode: ToolMode):
        for m, btn in self._tool_buttons.items():
            btn.setChecked(m == mode)

    # ── VibeOut 鎖定 / 解鎖 ───────────────────────────────────────────────────

    def set_vibeout_locked(self, locked: bool):
        """鎖定時 VibeOut 按鈕變低飽和綠，解鎖後恢復。"""
        if self._btn_ai:
            self._btn_ai.set_locked(locked)

    # ── 語言刷新 ──────────────────────────────────────────────────────────────

    def refresh_lang(self):
        """切換語言後，刷新所有按鈕的標籤與 tooltip。"""
        for btn in self._all_buttons:
            btn._refresh_lang()
        self.update()

    # ── 主題刷新 ──────────────────────────────────────────────────────────────

    def _apply_toolbar_bg(self):
        self.setStyleSheet(
            f"#Toolbar {{ background:{_theme.get('bg_dark')};"
            f" border-right:1px solid {_theme.get('separator')}; }}"
        )

    def apply_theme(self):
        """切換主題後，刷新 toolbar 背景、分隔線、所有按鈕 icon & 樣式。"""
        self._apply_toolbar_bg()
        for sep in self._seps:
            sep._refresh()
        for btn in self._all_buttons:
            btn.rebuild_icon()
            btn._apply_style(btn.isChecked())
        self.update()
