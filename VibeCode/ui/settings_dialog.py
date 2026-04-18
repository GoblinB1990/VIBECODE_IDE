"""
settings_dialog.py

AI 設定頁 Dialog。
設定內容：
    - Ollama API URL（預設 http://localhost:11434）
    - 模型下拉（從 Ollama 即時抓取，可手動輸入）
    - 介面語言（中文 / English）
    - 介面主題（深色 Dark / 淺色 Light）

設定存於：%APPDATA%/VibeCodeTool/settings.json
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Callable

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QComboBox, QPushButton, QFrame,
)
from PyQt6.QtCore import Qt

from constants import (
    COLOR_BG_DARK, COLOR_BG_LIGHT, COLOR_BG_MID,
    COLOR_ACCENT, COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED,
    COLOR_SEPARATOR, FONT_FAMILY,
)
from ui.i18n import tr, set_lang

# ── 設定檔路徑 ────────────────────────────────────────────────────────────────

_SETTINGS_DIR  = Path(os.environ.get("APPDATA", Path.home())) / "VibeCodeTool"
_SETTINGS_FILE = _SETTINGS_DIR / "settings.json"

DEFAULT_SETTINGS: dict = {
    "ollama_url": "http://localhost:11434",
    "model":      "",
    "lang":       "zh",
    "theme":      "dark",
}

# 對話框內部使用較大字體
_SZ  = 13   # 一般標籤 / 輸入框
_SZS = 11   # 小字說明


def load_settings() -> dict:
    try:
        if _SETTINGS_FILE.exists():
            data = json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
            return {**DEFAULT_SETTINGS, **data}
    except Exception:
        pass
    return dict(DEFAULT_SETTINGS)


def save_settings(data: dict) -> None:
    _SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    _SETTINGS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ── Dialog ────────────────────────────────────────────────────────────────────

_DIALOG_STYLE = """
QDialog {{
    background: {bg_dark};
    color: {text};
}}
QLabel {{
    color: {text};
    font-family: '{font}';
    background: transparent;
    font-size: {sz}px;
}}
QLineEdit, QComboBox {{
    background: {bg_light};
    color: {text};
    border: 1px solid {sep};
    border-radius: 4px;
    padding: 6px 10px;
    font-family: '{font}';
    font-size: {sz}px;
    selection-background-color: {accent}55;
    min-height: 30px;
}}
QLineEdit:focus, QComboBox:focus {{
    border-color: {accent};
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {muted};
    margin-right: 6px;
}}
QComboBox QAbstractItemView {{
    background: {bg_light};
    color: {text};
    border: 1px solid {sep};
    selection-background-color: {accent}44;
    font-size: {sz}px;
    outline: none;
}}
QPushButton {{
    background: {bg_light};
    color: {text};
    border: 1px solid {sep};
    border-radius: 4px;
    padding: 7px 18px;
    font-family: '{font}';
    font-size: {sz}px;
    min-height: 32px;
}}
QPushButton:hover {{
    background: {accent}22;
    border-color: {accent}88;
    color: {accent};
}}
QPushButton#btn_save {{
    background: {accent}22;
    border-color: {accent};
    color: {accent};
    font-weight: bold;
}}
QPushButton#btn_save:hover {{
    background: {accent}44;
}}
QPushButton#btn_refresh {{
    padding: 6px 10px;
    font-size: {szs}px;
    min-height: 30px;
}}
"""


class SettingsDialog(QDialog):

    def __init__(self, parent=None,
                 on_lang_change:  Callable | None = None,
                 on_theme_change: Callable | None = None):
        super().__init__(parent)
        self._on_lang_change  = on_lang_change
        self._on_theme_change = on_theme_change
        self.setWindowTitle(tr("設定", "Settings"))
        self.setFixedSize(460, 430)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowCloseButtonHint
        )
        from theme import theme as tm
        self.setStyleSheet(_DIALOG_STYLE.format(
            bg_dark=tm.get("bg_dark"),
            bg_light=tm.get("bg_light"),
            bg_mid=tm.get("bg_mid"),
            text=tm.get("text_primary"),
            muted=tm.get("text_muted"),
            accent=tm.get("accent"),
            sep=tm.get("separator"),
            font=FONT_FAMILY,
            sz=_SZ,
            szs=_SZS,
        ))

        self._settings = load_settings()
        self._build_ui()
        self._load_values()

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(14)

        # Title（使用 theme accent 確保明亮模式正確）
        from theme import theme as _tm
        title = QLabel(f"⚙  {tr('AI 連線設定', 'AI Connection Settings')}")
        title.setStyleSheet(
            f"color: {_tm.get('accent')}; font-size: 15px; font-weight: bold;"
            f" font-family: '{FONT_FAMILY}';"
        )
        layout.addWidget(title)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {_tm.get('separator')};")
        layout.addWidget(sep)

        # ── Ollama URL ────────────────────────────────────────────────────────
        url_label = QLabel("Ollama API URL")
        url_label.setStyleSheet(
            f"color: {_tm.get('text_muted')}; font-size: {_SZS}px;"
        )
        layout.addWidget(url_label)

        self._url_edit = QLineEdit()
        self._url_edit.setPlaceholderText("http://localhost:11434")
        layout.addWidget(self._url_edit)

        # ── Model ─────────────────────────────────────────────────────────────
        model_label = QLabel(tr("模型", "Model"))
        model_label.setStyleSheet(
            f"color: {_tm.get('text_muted')}; font-size: {_SZS}px;"
        )
        layout.addWidget(model_label)

        model_row = QHBoxLayout()
        model_row.setSpacing(8)

        self._model_combo = QComboBox()
        self._model_combo.setEditable(True)
        self._model_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._model_combo.lineEdit().setPlaceholderText(
            tr("請選擇或輸入模型名稱", "Select or type model name")
        )

        self._btn_refresh = QPushButton(tr("🔄 刷新", "🔄 Refresh"))
        self._btn_refresh.setObjectName("btn_refresh")
        self._btn_refresh.setFixedWidth(96)
        self._btn_refresh.setToolTip(tr("從 Ollama 取得可用模型清單",
                                        "Fetch available models from Ollama"))
        self._btn_refresh.clicked.connect(self._on_refresh)

        model_row.addWidget(self._model_combo, 1)
        model_row.addWidget(self._btn_refresh)
        layout.addLayout(model_row)

        self._hint_label = QLabel(
            tr("點擊「🔄 刷新」取得已安裝的模型清單",
               "Click Refresh to get installed models")
        )
        self._hint_label.setStyleSheet(
            f"color: {_tm.get('text_muted')}; font-size: {_SZS}px;"
        )
        layout.addWidget(self._hint_label)

        # ── Language ──────────────────────────────────────────────────────────
        lang_label = QLabel(tr("介面語言", "Interface Language"))
        lang_label.setStyleSheet(
            f"color: {_tm.get('text_muted')}; font-size: {_SZS}px;"
        )
        layout.addWidget(lang_label)

        self._lang_combo = QComboBox()
        self._lang_combo.addItems(["中文", "English"])
        layout.addWidget(self._lang_combo)

        # ── Theme ─────────────────────────────────────────────────────────────
        theme_label = QLabel(tr("介面主題", "Interface Theme"))
        theme_label.setStyleSheet(
            f"color: {_tm.get('text_muted')}; font-size: {_SZS}px;"
        )
        layout.addWidget(theme_label)

        self._theme_combo = QComboBox()
        self._theme_combo.addItems([
            tr("🌙  深色 Dark",  "🌙  Dark"),
            tr("☀️  淺色 Light", "☀️  Light"),
        ])
        layout.addWidget(self._theme_combo)

        layout.addStretch()

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancel = QPushButton(tr("取消", "Cancel"))
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton(tr("儲存", "Save"))
        btn_save.setObjectName("btn_save")
        btn_save.setDefault(True)
        btn_save.clicked.connect(self._on_save)

        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

    # ── Logic ─────────────────────────────────────────────────────────────────

    def _load_values(self):
        self._url_edit.setText(
            self._settings.get("ollama_url", DEFAULT_SETTINGS["ollama_url"])
        )
        current_model = self._settings.get("model", "")
        if current_model:
            self._model_combo.addItem(current_model)
            self._model_combo.setCurrentText(current_model)

        lang = self._settings.get("lang", "zh")
        self._lang_combo.setCurrentText("English" if lang == "en" else "中文")

        current_theme = self._settings.get("theme", "dark")
        self._theme_combo.setCurrentIndex(0 if current_theme == "dark" else 1)

    def _on_refresh(self):
        from ai.ollama_client import fetch_models
        url = self._url_edit.text().strip() or DEFAULT_SETTINGS["ollama_url"]
        self._hint_label.setText(tr("連線中...", "Connecting..."))
        models = fetch_models(url)
        self._model_combo.clear()
        if models:
            self._model_combo.addItems(models)
            self._hint_label.setText(
                tr(f"找到 {len(models)} 個模型", f"Found {len(models)} models")
            )
            current = self._settings.get("model", "")
            if current in models:
                self._model_combo.setCurrentText(current)
            else:
                self._model_combo.setCurrentIndex(0)
        else:
            self._hint_label.setText(tr(
                "⚠ 無法連線或找不到模型，請確認 Ollama 是否啟動",
                "⚠ Cannot connect or no models found. Is Ollama running?",
            ))

    def _on_save(self):
        self._settings["ollama_url"] = (
            self._url_edit.text().strip() or DEFAULT_SETTINGS["ollama_url"]
        )
        self._settings["model"] = self._model_combo.currentText().strip()

        # 語言切換
        new_lang = "en" if self._lang_combo.currentText() == "English" else "zh"
        lang_changed = new_lang != self._settings.get("lang", "zh")
        self._settings["lang"] = new_lang

        # 主題切換
        new_theme = "dark" if self._theme_combo.currentIndex() == 0 else "light"
        theme_changed = new_theme != self._settings.get("theme", "dark")
        self._settings["theme"] = new_theme

        save_settings(self._settings)
        set_lang(new_lang)

        if lang_changed and self._on_lang_change:
            self._on_lang_change()

        if theme_changed and self._on_theme_change:
            self._on_theme_change(new_theme)

        self.accept()
