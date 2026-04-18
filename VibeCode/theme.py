"""
theme.py — 全域主題管理員
Dark mode（預設）使用 Tokyo Night 深色調
Light mode 使用米白暖色調
"""
from __future__ import annotations

_DARK: dict[str, str] = {
    # Canvas
    "canvas_bg":         "#1e1e2e",
    "canvas_grid":       "#2a2a3e",
    # App BG
    "bg_dark":           "#16161e",
    "bg_mid":            "#1a1b26",
    "bg_light":          "#24283b",
    # Text
    "text_primary":      "#c0caf5",
    "text_muted":        "#565f89",
    # Accent
    "accent":            "#7aa2f7",
    "accent_hover":      "#7dcfff",
    # Separator
    "separator":         "#3b4261",
    # Box Item
    "box_header_bg":     "#3b4261",
    "box_body_bg":       "#24283b",
    "box_border":        "#7aa2f7",
    "box_header_text":   "#c0caf5",
    "box_body_text":     "#a9b1d6",
    "box_selected":      "#7dcfff",
    # Line
    "line_color":        "#7aa2f7",
    "line_selected":     "#7dcfff",
    "line_cursor_start": "#9ece6a",
    "line_cursor_move":  "#ff9e64",
    # Text item
    "text_item_color":   "#c0caf5",
    "text_selected":     "#7dcfff",
    # Guide
    "guide_color":       "#7dcfff",
    # Picker
    "picker_bg":         "#1a1b26",
    "picker_item_bg":    "#24283b",
    "picker_item_hover": "#3b4261",
    # Panel
    "panel_bg":          "#1a1b26",
    "panel_border":      "#3b4261",
    "panel_text":        "#a9b1d6",
}

_LIGHT: dict[str, str] = {
    # Canvas
    "canvas_bg":         "#f5f0e8",
    "canvas_grid":       "#e0dbd3",
    # App BG
    "bg_dark":           "#e5e0d8",
    "bg_mid":            "#ede8e0",
    "bg_light":          "#f5f1eb",
    # Text
    "text_primary":      "#2d3142",
    "text_muted":        "#8a8fa8",
    # Accent
    "accent":            "#4a6fa5",
    "accent_hover":      "#2952a3",
    # Separator
    "separator":         "#d0cbc2",
    # Box Item
    "box_header_bg":     "#ddd8d0",
    "box_body_bg":       "#f5f1eb",
    "box_border":        "#4a6fa5",
    "box_header_text":   "#2d3142",
    "box_body_text":     "#4a5170",
    "box_selected":      "#2952a3",
    # Line
    "line_color":        "#4a6fa5",
    "line_selected":     "#2952a3",
    "line_cursor_start": "#4a8c5c",
    "line_cursor_move":  "#c4702a",
    # Text item
    "text_item_color":   "#2d3142",
    "text_selected":     "#2952a3",
    # Guide
    "guide_color":       "#2952a3",
    # Picker
    "picker_bg":         "#ede8e0",
    "picker_item_bg":    "#f5f1eb",
    "picker_item_hover": "#ddd8d0",
    # Panel
    "panel_bg":          "#ede8e0",
    "panel_border":      "#d0cbc2",
    "panel_text":        "#4a5170",
}


class ThemeManager:
    """全域單例，持有目前主題色彩。"""

    def __init__(self) -> None:
        self._name    = "dark"
        self._palette = dict(_DARK)

    def set(self, name: str) -> None:
        """切換主題（'dark' 或 'light'）。"""
        self._name    = name
        self._palette = dict(_DARK if name == "dark" else _LIGHT)

    def get(self, key: str, fallback: str = "#888888") -> str:
        return self._palette.get(key, fallback)

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_dark(self) -> bool:
        return self._name == "dark"


# ── 全域單例 ──────────────────────────────────────────────────────────────────
theme = ThemeManager()
