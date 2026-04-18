from PyQt6.QtWidgets import (
    QWidget, QGridLayout, QPushButton, QLabel,
    QVBoxLayout, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QSize, QEvent
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QPainter, QPixmap, QIcon, QPen, QColor, QPolygonF, QFont

from constants import (
    ShapeType,
    PICKER_BG, PICKER_ITEM_BG, PICKER_ITEM_HOVER,
    PICKER_BTN_W, PICKER_BTN_H,
    COLOR_ACCENT, COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED,
    COLOR_SEPARATOR, COLOR_BG_LIGHT,
    FONT_FAMILY, FONT_SIZE_SMALL
)
from ui.i18n import tr


# ── 縮圖繪製 ──────────────────────────────────────────────────────────────────

def _icon_oval(p, w, h):          p.drawEllipse(4, 8, w - 8, h - 16)
def _icon_rect(p, w, h):          p.drawRect(4, 6, w - 8, h - 12)
def _icon_diamond(p, w, h):
    cx, cy, mx, my = w//2, h//2, w//2-4, h//2-6
    p.drawPolygon(QPolygonF([QPointF(cx, cy-my), QPointF(cx+mx, cy),
                              QPointF(cx, cy+my), QPointF(cx-mx, cy)]))
def _icon_parallelogram(p, w, h):
    off = 10
    p.drawPolygon(QPolygonF([QPointF(off, 6), QPointF(w-4, 6),
                              QPointF(w-off, h-6), QPointF(4, h-6)]))
def _icon_cylinder(p, w, h):
    eh = 12
    p.drawRect(4, 6+eh//2, w-8, h-12-eh//2)
    p.drawEllipse(4, 6, w-8, eh)
    p.drawArc(4, h-6-eh, w-8, eh, 0, -180*16)
def _icon_predefined(p, w, h):
    m = 6
    p.drawRect(4, 6, w-8, h-12)
    p.drawLine(4+m, 6, 4+m, h-6)
    p.drawLine(w-4-m, 6, w-4-m, h-6)
def _icon_rect_desc(p, w, h):
    p.drawRoundedRect(4, 6, w-8, h-12, 4, 4)
    hh = (h-12)//3
    p.drawLine(4, 6+hh, w-4, 6+hh)

def _icon_document(p, w, h):
    from PyQt6.QtGui import QPainterPath
    wave = 6
    body_h = h - 12 - wave
    p.drawRect(4, 6, w-8, body_h)
    path = QPainterPath()
    x0, y0, bw = 4, 6 + body_h, w - 8
    path.moveTo(x0, y0)
    path.cubicTo(x0+bw*0.25, y0+wave*1.8, x0+bw*0.5, y0-wave*0.8, x0+bw*0.75, y0+wave*1.8)
    path.cubicTo(x0+bw*0.875, y0+wave*2.4, x0+bw, y0+wave, x0+bw, y0)
    p.drawPath(path)

def _icon_manual_input(p, w, h):
    slope = (h-12) * 0.20
    p.drawPolygon(QPolygonF([
        QPointF(4, 6+slope), QPointF(w-4, 6),
        QPointF(w-4, h-6),   QPointF(4, h-6),
    ]))

def _icon_hexagon(p, w, h):
    notch = (w-8) * 0.25
    cx = (4 + w-4) / 2
    cy = h / 2
    p.drawPolygon(QPolygonF([
        QPointF(4+notch, 6),  QPointF(w-4-notch, 6),
        QPointF(w-4, cy),
        QPointF(w-4-notch, h-6), QPointF(4+notch, h-6),
        QPointF(4, cy),
    ]))

def _icon_delay(p, w, h):
    from PyQt6.QtGui import QPainterPath
    r = (h-12) / 2
    flat_w = (w-8) - r
    path = QPainterPath()
    path.moveTo(4, 6)
    path.lineTo(4+flat_w, 6)
    path.arcTo(4+flat_w-r, 6, r*2, h-12, 90, -180)
    path.lineTo(4, h-6)
    path.closeSubpath()
    p.drawPath(path)


# ── 形狀定義：(ShapeType, 標籤, icon繪製, zh說明, en說明) ────────────────────

SHAPE_DEFS = [
    (ShapeType.OVAL,
     "Start / End",
     _icon_oval,
     "流程的起點或終點\n例：開始、結束、進入點",
     "Start or end point of a flow\nE.g. Begin, End, Entry point"),

    (ShapeType.RECT,
     "Process",
     _icon_rect,
     "一般處理步驟或動作\n例：計算數值、執行操作",
     "General processing step or action\nE.g. Calculate, Execute operation"),

    (ShapeType.DIAMOND,
     "Decision",
     _icon_diamond,
     "條件判斷或流程分支\n例：是/否、if/else 分支",
     "Conditional branch in the flow\nE.g. Yes/No, if/else decision"),

    (ShapeType.PARALLELOGRAM,
     "I / O",
     _icon_parallelogram,
     "資料輸入或輸出\n例：讀取檔案、顯示結果",
     "Data input or output\nE.g. Read file, Display result"),

    (ShapeType.CYLINDER,
     "Database",
     _icon_cylinder,
     "資料庫或持久儲存元件\n例：讀寫 DB、存取快取",
     "Database or persistent storage\nE.g. Read/write DB, Cache access"),

    (ShapeType.PREDEFINED,
     "Predefined",
     _icon_predefined,
     "已定義的子流程或函式\n例：呼叫模組、共用程序",
     "Pre-defined sub-process or function\nE.g. Call module, Shared routine"),

    (ShapeType.RECT_DESCRIBE,
     "Describe",
     _icon_rect_desc,
     "帶標題列的說明框\n例：模組說明、備注區塊",
     "Titled description box\nE.g. Module notes, Comment block"),

    (ShapeType.DOCUMENT,
     "Document",
     _icon_document,
     "文件或報告輸出\n例：產生報表、列印文件",
     "Document or report output\nE.g. Generate report, Print document"),

    (ShapeType.MANUAL_INPUT,
     "Manual Input",
     _icon_manual_input,
     "手動輸入資料（鍵盤操作）\n例：使用者填表、輸入參數",
     "Manual data entry (keyboard)\nE.g. User form, Input parameters"),

    (ShapeType.HEXAGON,
     "Preparation",
     _icon_hexagon,
     "準備步驟或組態設定\n例：初始化、環境設定",
     "Preparation or configuration step\nE.g. Initialization, Setup"),

    (ShapeType.DELAY,
     "Delay",
     _icon_delay,
     "等待或延遲狀態\n例：等待回應、逾時緩衝",
     "Waiting or delay state\nE.g. Await response, Timeout buffer"),
]


def _make_icon(draw_fn, sz=40) -> QIcon:
    px = QPixmap(sz, sz)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor(COLOR_ACCENT), 1.5))
    p.setBrush(Qt.BrushStyle.NoBrush)
    draw_fn(p, sz, sz)
    p.end()
    return QIcon(px)


# ── ShapePicker ───────────────────────────────────────────────────────────────

class ShapePicker(QWidget):
    """
    彈出式形狀選擇器。
    - 選後自動關閉並發出 shape_selected 訊號
    - 游標懸停按鈕時，底部說明欄顯示使用場景
    """

    shape_selected = pyqtSignal(ShapeType)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setStyleSheet(f"""
            ShapePicker {{
                background: {PICKER_BG};
                border: 1px solid {COLOR_SEPARATOR};
                border-radius: 8px;
            }}
        """)
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(6)

        # ── 標題 ──────────────────────────────────────────────────────────────
        title = QLabel(tr("選擇圖形", "Select Shape"))
        title.setStyleSheet(
            f"color:{COLOR_TEXT_MUTED}; font-family:'{FONT_FAMILY}';"
            f"font-size:{FONT_SIZE_SMALL}px; font-weight:600;"
        )
        outer.addWidget(title)

        # ── 按鈕格 ────────────────────────────────────────────────────────────
        grid = QGridLayout()
        grid.setSpacing(5)
        outer.addLayout(grid)

        cols = 4
        for i, (st, label, draw_fn, desc_zh, desc_en) in enumerate(SHAPE_DEFS):
            desc = tr(desc_zh, desc_en)
            btn = QPushButton()
            btn.setFixedSize(PICKER_BTN_W, PICKER_BTN_H)
            btn.setIcon(_make_icon(draw_fn))
            btn.setIconSize(QSize(40, 40))
            btn.setToolTip(label)   # 系統 tooltip 備用
            btn.setStyleSheet(f"""
                QPushButton {{
                    background:{PICKER_ITEM_BG};
                    border:1px solid transparent;
                    border-radius:6px;
                    color:{COLOR_TEXT_MUTED};
                    font-family:'{FONT_FAMILY}';
                    font-size:{FONT_SIZE_SMALL-1}px;
                    padding-bottom:4px;
                }}
                QPushButton:hover {{
                    background:{PICKER_ITEM_HOVER};
                    border:1px solid {COLOR_ACCENT}66;
                    color:{COLOR_TEXT_PRIMARY};
                }}
            """)
            btn.clicked.connect(lambda _, s=st: self._on_select(s))

            # 安裝 hover 事件過濾器
            btn.installEventFilter(self)
            btn.setProperty("shape_label", label)
            btn.setProperty("shape_desc",  desc)

            grid.addWidget(btn, i // cols, i % cols)

        # ── 分隔線 ────────────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{COLOR_SEPARATOR}; border:none;")
        outer.addWidget(sep)

        # ── 說明欄（懸停時更新）──────────────────────────────────────────────
        self._hint_name = QLabel("　")
        self._hint_name.setStyleSheet(
            f"color:{COLOR_TEXT_PRIMARY}; font-family:'{FONT_FAMILY}';"
            f"font-size:{FONT_SIZE_SMALL + 2}px; font-weight:700;"
        )

        hint_placeholder = tr("將游標移到圖形上以查看說明", "Hover over a shape to see its description")
        self._hint_desc = QLabel(hint_placeholder)
        self._hint_desc.setWordWrap(True)
        self._hint_desc.setFixedWidth(PICKER_BTN_W * 4 + 15)
        self._hint_desc.setStyleSheet(
            f"color:{COLOR_TEXT_MUTED}; font-family:'{FONT_FAMILY}';"
            f"font-size:{FONT_SIZE_SMALL + 1}px;"
        )
        self._hint_placeholder = hint_placeholder

        outer.addWidget(self._hint_name)
        outer.addWidget(self._hint_desc)

    # ── Hover 事件過濾 ────────────────────────────────────────────────────────

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Enter:
            label = obj.property("shape_label") or ""
            desc  = obj.property("shape_desc")  or ""
            self._hint_name.setText(label)
            self._hint_desc.setText(desc)
        elif event.type() == QEvent.Type.Leave:
            # 短暫保留說明，讓使用者有時間看完
            self._hint_name.setText("　")
            self._hint_desc.setText(getattr(self, "_hint_placeholder",
                                            tr("將游標移到圖形上以查看說明",
                                               "Hover over a shape to see its description")))
        return super().eventFilter(obj, event)

    # ── 選取 ──────────────────────────────────────────────────────────────────

    def _on_select(self, shape_type: ShapeType):
        self.shape_selected.emit(shape_type)
        self.hide()

    def show_near(self, global_pos: QPoint):
        self.adjustSize()
        self.move(global_pos)
        self.show()
