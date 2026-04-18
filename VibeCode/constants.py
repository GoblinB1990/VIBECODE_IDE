from enum import Enum, auto


# ── Tool Mode ─────────────────────────────────────────────────────────────────

class ToolMode(Enum):
    SELECT    = auto()
    ADD_TEXT  = auto()
    ADD_SHAPE = auto()
    ADD_LINE  = auto()
    ADD_NOTE  = auto()
    ADD_IMAGE = auto()
    ADD_TABLE = auto()   # 表格工具



class ShapeType(Enum):
    OVAL          = auto()   # Start/End
    RECT          = auto()   # Process
    DIAMOND       = auto()   # Decision
    PARALLELOGRAM = auto()   # Input/Output
    CYLINDER      = auto()   # Database
    PREDEFINED    = auto()   # Predefined Process
    RECT_DESCRIBE = auto()   # 帶主題列的描述框
    DOCUMENT      = auto()   # Document（波浪底邊）
    MANUAL_INPUT  = auto()   # Manual Input（斜切頂邊）
    HEXAGON       = auto()   # Preparation / Hexagon
    DELAY         = auto()   # Delay（D 形）


# ── Toolbar ───────────────────────────────────────────────────────────────────

TOOLBAR_WIDTH        = 64
TOOLBAR_BTN_SIZE     = 48
TOOLBAR_BTN_ICON_SZ  = 24
TOOLBAR_SEPARATOR_H  = 1


# ── Canvas ────────────────────────────────────────────────────────────────────

CANVAS_BG            = "#1e1e2e"
CANVAS_GRID_COLOR    = "#2a2a3e"
CANVAS_GRID_STEP     = 20


# ── Box Item ──────────────────────────────────────────────────────────────────

BOX_DEFAULT_W        = 200
BOX_DEFAULT_H        = 160
BOX_CORNER_RADIUS    = 10
BOX_HEADER_H         = 36
BOX_BORDER_WIDTH     = 1.5
BOX_MIN_W            = 100
BOX_MIN_H            = 80

BOX_HEADER_BG        = "#3b4261"
BOX_BODY_BG          = "#24283b"
BOX_BORDER_COLOR     = "#7aa2f7"
BOX_HEADER_TEXT      = "#c0caf5"
BOX_BODY_TEXT        = "#a9b1d6"
BOX_SELECTED_BORDER  = "#7dcfff"

BOX_HEADER_FONT_SIZE = 11
BOX_BODY_FONT_SIZE   = 10


# ── Text Item ─────────────────────────────────────────────────────────────────

TEXT_DEFAULT_COLOR   = "#c0caf5"
TEXT_DEFAULT_SIZE    = 12
TEXT_SELECTED_BORDER = "#7dcfff"


# ── Line Item ─────────────────────────────────────────────────────────────────

LINE_DEFAULT_COLOR   = "#7aa2f7"
LINE_WIDTH           = 1.8
LINE_SELECTED_COLOR  = "#7dcfff"
LINE_ARROW_SIZE      = 20

LINE_CURSOR_START    = "#9ece6a"
LINE_CURSOR_MOVE     = "#ff9e64"


# ── Sticky Note ───────────────────────────────────────────────────────────────

STICKY_DEFAULT_W     = 200
STICKY_DEFAULT_H     = 160
STICKY_MIN_W         = 100
STICKY_MIN_H         = 80
STICKY_DEFAULT_BG    = "#d4c4a0"   # 暖沙黃
STICKY_DEFAULT_TEXT  = "#3d3d3d"   # 深色文字（便貼底色偏淺）
STICKY_FONT_SIZE     = 12
STICKY_CORNER_RADIUS = 6

# 便利貼底色 6 色（莫蘭迪風格；杏橘換為矢車菊藍）
STICKY_PALETTE = [
    "#d4c4a0",   # 暖沙黃
    "#a8c4a8",   # 薄荷綠
    "#a0b8c8",   # 霧藍
    "#d4a8b0",   # 玫瑰粉
    "#8faad4",   # 矢車菊藍
    "#c0b0d0",   # 薰衣草紫
]


# ── Smart Guide ───────────────────────────────────────────────────────────────

GUIDE_COLOR          = "#7dcfff"
GUIDE_SNAP_RADIUS    = 8
GUIDE_MAX_POOL       = 12   # 預分配輔助線數量（6H + 6V 足夠）


# ── Property Panel ────────────────────────────────────────────────────────────

PANEL_BG             = "#1a1b26"
PANEL_BORDER         = "#3b4261"
PANEL_TEXT           = "#a9b1d6"
PANEL_LABEL_SIZE     = 10
PANEL_WIDTH          = 220


# ── UI Colors ─────────────────────────────────────────────────────────────────

COLOR_ACCENT         = "#7aa2f7"
COLOR_ACCENT_HOVER   = "#7dcfff"
COLOR_BG_DARK        = "#16161e"
COLOR_BG_MID         = "#1a1b26"
COLOR_BG_LIGHT       = "#24283b"
COLOR_TEXT_PRIMARY   = "#c0caf5"
COLOR_TEXT_MUTED     = "#565f89"
COLOR_SEPARATOR      = "#3b4261"


# ── Font ──────────────────────────────────────────────────────────────────────

FONT_FAMILY          = "Segoe UI"
FONT_SIZE_NORMAL     = 10
FONT_SIZE_SMALL      = 9


# ── Shape 預設尺寸 ─────────────────────────────────────────────────────────────

SHAPE_DEFAULT_W      = 160
SHAPE_DEFAULT_H      = 100
SHAPE_MIN_W          = 80
SHAPE_MIN_H          = 60

PICKER_BG            = "#1a1b26"
PICKER_ITEM_BG       = "#24283b"
PICKER_ITEM_HOVER    = "#3b4261"
PICKER_BTN_W         = 90
PICKER_BTN_H         = 72


# ── Text Style Toolbar ────────────────────────────────────────────────────────

TEXT_STYLE_SIZES  = [8, 10, 12, 14, 16, 18, 20, 24]

# 艷麗、色相分散、明顯可辨的 10 個文字顏色
TEXT_STYLE_COLORS = [
    "#ffffff",   # 白
    "#ee5555",   # 紅
    "#ee8833",   # 橘
    "#ddaa11",   # 金
    "#44bb66",   # 翠綠
    "#22bbbb",   # 青
    "#3399ee",   # 天藍
    "#5566ee",   # 藍
    "#9955dd",   # 紫
    "#1a1b26",   # 深黑
]
# 這些顏色在深色背景上對比鮮明，且彼此之間色相分散，方便用戶快速識別和選擇。

# ── IMAGE  ───────────────────────────────────────────────────────────────────

TOOL_IMAGE = 'image'  



# ── File IO ───────────────────────────────────────────────────────────────────

FILE_VBC_FILTER      = "VibeCode Files (*.vbc)"
CANVAS_DATA_VERSION  = 1
