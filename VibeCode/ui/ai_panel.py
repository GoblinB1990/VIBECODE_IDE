"""
ai_panel.py

右側 AI 輸出面板（Docked right-side panel）。
- 串流顯示 Ollama 輸出
- 標題列：✦ AI Prompt  |  Copy  –  ✕
- Copy：複製全文到剪貼簿
- –（最小化）：收合內容區，只保留標題列
- ✕（關閉）：隱藏整個面板

呼叫方式：
    panel.show_panel()        — 顯示（如已最小化則展開）
    panel.clear_output()      — 清空文字
    panel.append_text(str)    — 串流追加文字
    panel.set_status(str)     — 更新底部狀態文字
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLabel, QPushButton, QFrame, QApplication,
)
from PyQt6.QtCore import Qt, pyqtSignal

from constants import (
    COLOR_BG_DARK, COLOR_BG_LIGHT, COLOR_BG_MID,
    COLOR_ACCENT, COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED,
    COLOR_SEPARATOR, FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_SMALL,
)

AI_PANEL_WIDTH = 320


class AiPanel(QWidget):
    closed    = pyqtSignal()   # 面板被關閉
    minimized = pyqtSignal()   # 面板被最小化
    restored  = pyqtSignal()   # 面板從最小化還原

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(AI_PANEL_WIDTH)
        self.setObjectName("AiPanel")
        self.setStyleSheet(f"""
            #AiPanel {{
                background: {COLOR_BG_DARK};
                border-left: 1px solid {COLOR_SEPARATOR};
            }}
        """)
        self._is_minimized = False
        self._build_ui()
        self.hide()

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._make_title_bar())
        root.addWidget(self._make_content())

    def _make_title_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(38)
        bar.setStyleSheet(f"""
            background: {COLOR_BG_LIGHT};
            border-bottom: 1px solid {COLOR_SEPARATOR};
        """)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 0, 6, 0)
        layout.setSpacing(4)

        icon = QLabel("✦")
        icon.setStyleSheet(f"color: {COLOR_ACCENT}; font-size: 11px; background: transparent;")

        title = QLabel("AI Prompt")
        title.setStyleSheet(f"""
            color: {COLOR_TEXT_PRIMARY};
            font-family: '{FONT_FAMILY}';
            font-size: {FONT_SIZE_NORMAL}px;
            font-weight: bold;
            background: transparent;
        """)

        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addStretch()

        _btn_css = f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {COLOR_TEXT_PRIMARY};
                font-size: 14px;
                padding: 1px 5px;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background: {COLOR_ACCENT}33;
                color: {COLOR_ACCENT};
            }}
        """

        self._btn_copy = QPushButton("⎘")
        self._btn_copy.setFixedSize(26, 26)
        self._btn_copy.setToolTip("複製全文")
        self._btn_copy.setStyleSheet(_btn_css)
        self._btn_copy.clicked.connect(self._on_copy)

        self._btn_min = QPushButton("–")
        self._btn_min.setFixedSize(26, 26)
        self._btn_min.setToolTip("最小化")
        self._btn_min.setStyleSheet(_btn_css)
        self._btn_min.clicked.connect(self._on_toggle_minimize)

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(26, 26)
        btn_close.setToolTip("關閉")
        btn_close.setStyleSheet(_btn_css)
        btn_close.clicked.connect(self._on_close)

        layout.addWidget(self._btn_copy)
        layout.addWidget(self._btn_min)
        layout.addWidget(btn_close)
        return bar

    def _make_content(self) -> QWidget:
        self._content_widget = QWidget()
        self._content_widget.setStyleSheet(f"background: {COLOR_BG_DARK};")

        layout = QVBoxLayout(self._content_widget)
        layout.setContentsMargins(8, 8, 8, 6)
        layout.setSpacing(4)

        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setStyleSheet(f"""
            QTextEdit {{
                background: {COLOR_BG_MID};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_SEPARATOR};
                border-radius: 4px;
                font-family: '{FONT_FAMILY}';
                font-size: {FONT_SIZE_NORMAL}px;
                padding: 6px;
                line-height: 1.6;
            }}
            QScrollBar:vertical {{
                background: {COLOR_BG_DARK};
                width: 6px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: {COLOR_SEPARATOR};
                border-radius: 3px;
                min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        layout.addWidget(self._output, stretch=1)

        self._status_label = QLabel("就緒")
        self._status_label.setStyleSheet(f"""
            color: {COLOR_TEXT_MUTED};
            font-family: '{FONT_FAMILY}';
            font-size: {FONT_SIZE_SMALL}px;
            padding: 2px 2px;
            background: transparent;
        """)
        layout.addWidget(self._status_label)
        return self._content_widget

    # ── Public API ────────────────────────────────────────────────────────────

    def show_panel(self):
        """顯示面板；若已最小化則先展開。"""
        if self._is_minimized:
            self._expand()
        self.show()

    def clear_output(self):
        self._output.clear()

    def append_text(self, text: str):
        """串流追加文字，自動捲動到底部。"""
        cursor = self._output.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self._output.setTextCursor(cursor)
        self._output.insertPlainText(text)
        self._output.ensureCursorVisible()

    def set_status(self, msg: str):
        self._status_label.setText(msg)

    def get_text(self) -> str:
        return self._output.toPlainText()

    # ── Private Slots ─────────────────────────────────────────────────────────

    def _on_copy(self):
        text = self._output.toPlainText().strip()
        if text:
            QApplication.clipboard().setText(text)
            prev = self._status_label.text()
            self._status_label.setText("已複製到剪貼簿 ✓")
            # 2 秒後還原
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(2000, lambda: self._status_label.setText(prev))

    def _on_toggle_minimize(self):
        if self._is_minimized:
            self._expand()
        else:
            self._collapse()

    def _collapse(self):
        self._content_widget.hide()
        self._is_minimized = True
        self._btn_min.setText("□")
        self._btn_min.setToolTip("展開")
        # 發出訊號讓 main_window 隱藏整個 panel，並在右下角顯示浮動小按鈕
        self.minimized.emit()

    def _expand(self):
        self._content_widget.show()
        self._is_minimized = False
        self._btn_min.setText("–")
        self._btn_min.setToolTip("最小化")
        self.restored.emit()

    def _on_close(self):
        self.hide()
        self.closed.emit()
