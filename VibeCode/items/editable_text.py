from PyQt6.QtWidgets import QGraphicsTextItem
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QTextCursor, QTextCharFormat

from constants import FONT_FAMILY


class EditableText(QGraphicsTextItem):
    """
    可編輯文字 QGraphicsTextItem 基底類別。
    TextItem 繼承此類。
    進入 / 退出編輯時透過 scene.text_editing_started/stopped 通知外部。
    """

    def __init__(self, text: str = "", color: str = "#c0caf5",
                 size: int = 12, parent=None):
        super().__init__(text, parent)
        self.setDefaultTextColor(QColor(color))
        self.setFont(QFont(FONT_FAMILY, size))
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)

    # ── 屬性 ──────────────────────────────────────────────────────────────────

    @property
    def plain_text(self) -> str:
        return self.toPlainText()

    # ── 編輯進入 / 退出 ────────────────────────────────────────────────────────

    def start_edit(self):
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
        self.setFocus()
        cur = self.textCursor()
        cur.select(QTextCursor.SelectionType.Document)
        self.setTextCursor(cur)
        # 通知 scene → TextStyleToolbar 顯示
        scene = self.scene()
        if scene and hasattr(scene, 'text_editing_started'):
            scene.text_editing_started.emit(self)

    def stop_edit(self):
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        cur = self.textCursor()
        cur.clearSelection()
        self.setTextCursor(cur)
        self.clearFocus()
        # 通知 scene → TextStyleToolbar 隱藏
        scene = self.scene()
        if scene and hasattr(scene, 'text_editing_stopped'):
            scene.text_editing_stopped.emit()

    def apply_char_format(self, fmt: QTextCharFormat):
        """套用字元格式到目前選取文字（無選取則不動作）。"""
        cur = self.textCursor()
        if not cur.hasSelection():
            return
        cur.mergeCharFormat(fmt)
        self.setTextCursor(cur)

    # ── 事件 ──────────────────────────────────────────────────────────────────

    def focusOutEvent(self, event):
        # 不在此自動 stop_edit，由 canvas_view 統一控制
        # 避免滑鼠移到 toolbar 時 Qt 焦點切換誤觸發
        super().focusOutEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.stop_edit()
        else:
            super().keyPressEvent(event)
