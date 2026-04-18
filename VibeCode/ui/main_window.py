import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStatusBar, QLabel,
    QFileDialog, QApplication,
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut, QColor, QImage, QPainter

from constants import (
    ToolMode, CANVAS_BG,
    COLOR_BG_MID, COLOR_BG_DARK,
    COLOR_TEXT_MUTED, COLOR_SEPARATOR, FONT_FAMILY, FONT_SIZE_NORMAL,
    FILE_VBC_FILTER,
)
from theme import theme as _theme
from ui.toolbar             import Toolbar
from ui.color_popup         import ColorPopup
from ui.text_style_toolbar  import TextStyleToolbar
from ui.ai_panel            import AiPanel
from canvas.canvas_scene    import CanvasScene
from canvas.canvas_view     import CanvasView
from canvas.tool_controller import ToolController


class MainWindow(QMainWindow):

    APP_TITLE    = "Vibe Code Tool"
    MIN_SIZE     = QSize(900, 600)
    DEFAULT_SIZE = QSize(1280, 800)

    def __init__(self):
        super().__init__()
        self._init_lang()          # ★ 語言優先初始化，toolbar 建立前先設好
        self._init_theme()         # ★ 主題初始化（在 UI 建立前設好 theme 狀態）
        self.setWindowTitle(self.APP_TITLE)
        self.setMinimumSize(self.MIN_SIZE)
        self.resize(self.DEFAULT_SIZE)
        self._sel_shapes: list = []
        self._sel_lines:  list = []
        self._sel_sticky: list = []
        self._clipboard:  list[dict] = []
        self._current_file: Path | None = None

        self._build_core()
        self._build_ui()
        self._connect_signals()
        self._setup_shortcuts()
        self._apply_theme()        # ★ 套用目前主題到所有元件

        QTimer.singleShot(0, self._try_restore_session)

    # ── 核心 ───────────────────────────────────────────────────────────────────

    def _build_core(self):
        from storage.file_manager import FileManager
        self._scene        = CanvasScene()
        self._tool_ctrl    = ToolController(self._scene, None)
        self._canvas_view  = CanvasView(self._scene, self._tool_ctrl)
        self._tool_ctrl._view         = self._canvas_view
        self._tool_ctrl.set_mode(ToolMode.SELECT)
        self._tool_ctrl.on_shape_placed = self._switch_tool
        self._file_manager = FileManager()

    # ── UI ─────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        central.setStyleSheet(f"background: {COLOR_BG_MID};")
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._toolbar = Toolbar()
        main_layout.addWidget(self._toolbar)
        main_layout.addWidget(self._canvas_view, stretch=1)

        # AI 輸出面板（右側，預設隱藏）
        self._ai_panel = AiPanel()
        main_layout.addWidget(self._ai_panel)
        self._ollama_thread = None

        # ★ 浮動小按鈕：AI panel 最小化後顯示在 canvas 右下角
        from PyQt6.QtWidgets import QPushButton
        from constants import COLOR_BG_LIGHT, COLOR_ACCENT, COLOR_TEXT_PRIMARY, FONT_FAMILY
        self._ai_mini_btn = QPushButton("✦ AI", self._canvas_view)
        self._ai_mini_btn.setFixedSize(72, 28)
        self._ai_mini_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._ai_mini_btn.setToolTip("展開 AI 面板")
        self._ai_mini_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLOR_BG_LIGHT};
                border: 1px solid {COLOR_ACCENT}88;
                border-radius: 14px;
                color: {COLOR_ACCENT};
                font-family: '{FONT_FAMILY}';
                font-size: 10px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {COLOR_ACCENT}22;
                border-color: {COLOR_ACCENT};
            }}
        """)
        self._ai_mini_btn.clicked.connect(self._on_ai_mini_restore)
        self._ai_mini_btn.hide()

        # ★ 修正 Bug 1：TextStyleToolbar 改為浮動覆蓋層，掛在 canvas_view 上
        #   與 ColorPopup 完全相同的架構，不佔版面空間
        self._text_toolbar = TextStyleToolbar(self._canvas_view)
        self._canvas_view.set_text_toolbar(self._text_toolbar)

        # 顏色浮動選單（CanvasView 子元件）
        self._color_popup = ColorPopup(self._canvas_view)

        # 狀態列
        self._status_label = QLabel(
            "選取模式  |  Ctrl+滾輪 縮放  |  空白處左鍵/中鍵/空白鍵+左鍵 平移"
            "  |  Delete 刪除  |  Ctrl+Z 復原  |  Ctrl+C/V 複製貼上"
        )
        self._status_label.setStyleSheet(f"color:{COLOR_TEXT_MUTED}; padding:0 8px;")
        bar = QStatusBar()
        bar.addWidget(self._status_label)
        self.setStatusBar(bar)

    # ── 訊號 ───────────────────────────────────────────────────────────────────

    def _connect_signals(self):
        self._toolbar.tool_changed.connect(self._on_tool_changed)
        self._toolbar.shape_type_changed.connect(self._tool_ctrl.set_shape_type)
        self._toolbar.table_size_changed.connect(self._tool_ctrl.set_table_size)
        self._toolbar.action_new.connect(self._on_new)
        self._toolbar.action_open.connect(self._on_open)
        self._toolbar.action_save.connect(self._on_save)
        self._toolbar.action_screenshot.connect(self._on_screenshot)
        self._toolbar.action_ai.connect(self._on_ai_generate)
        self._toolbar.action_settings.connect(self._on_settings)
        self._scene.selection_changed_signal.connect(self._on_selection_changed)

        self._color_popup.border_color_picked.connect(self._apply_border_color)
        self._color_popup.fill_color_picked.connect(self._apply_fill_color)
        self._color_popup.line_color_picked.connect(self._apply_line_color)

        self._color_popup.sticky_bg_picked.connect(self._apply_sticky_bg)
        self._color_popup.sticky_text_picked.connect(self._apply_sticky_text)
        self._color_popup.sticky_size_picked.connect(self._apply_sticky_size)

        # ★ AI panel 最小化 / 關閉
        self._ai_panel.minimized.connect(self._on_ai_minimized)
        self._ai_panel.closed.connect(self._ai_mini_btn.hide)

    # ── 快捷鍵 ─────────────────────────────────────────────────────────────────

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+O"), self).activated.connect(self._on_open)
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self._on_save_shortcut)
        QShortcut(QKeySequence("V"), self).activated.connect(
            lambda: self._switch_tool(ToolMode.SELECT))
        QShortcut(QKeySequence("T"), self).activated.connect(
            lambda: self._switch_tool(ToolMode.ADD_TEXT))
        QShortcut(QKeySequence("B"), self).activated.connect(
            lambda: self._switch_tool(ToolMode.ADD_SHAPE))
        QShortcut(QKeySequence("L"), self).activated.connect(
            lambda: self._switch_tool(ToolMode.ADD_LINE))
        QShortcut(QKeySequence("N"), self).activated.connect(
            lambda: self._switch_tool(ToolMode.ADD_NOTE))
        QShortcut(QKeySequence.StandardKey.Undo, self).activated.connect(
            self._scene.undo_stack.undo)
        QShortcut(QKeySequence.StandardKey.Redo, self).activated.connect(
            self._scene.undo_stack.redo)
        QShortcut(QKeySequence.StandardKey.Copy,  self).activated.connect(self._on_copy)
        QShortcut(QKeySequence.StandardKey.Paste, self).activated.connect(self._on_paste)

    # ── Tool 切換 ──────────────────────────────────────────────────────────────

    _STATUS = {
        ToolMode.SELECT:    "選取模式  |  點擊選取，拖曳框選，Delete 刪除",
        ToolMode.ADD_TEXT:  "文字模式  |  點擊畫布放置文字，自動切回選取並進入編輯",
        ToolMode.ADD_SHAPE: "圖形模式  |  從彈出選單選形狀，點擊畫布放置，雙擊編輯",
        ToolMode.ADD_LINE:  "連線模式  |  第一下設起點，第二下設終點，Esc 取消",
        ToolMode.ADD_NOTE:  "便利貼模式  |  點擊畫布放置便利貼，雙擊編輯",
        ToolMode.ADD_IMAGE: "圖片模式  |  點擊畫布放置圖片，拖曳調整大小",
        ToolMode.ADD_TABLE: "表格模式  |  點擊畫布放置表格，雙擊儲存格編輯，Tab 切換儲存格",
    }

    def _on_tool_changed(self, mode: ToolMode):
        self._tool_ctrl.set_mode(mode)
        suffix = "  |  Ctrl+滾輪 縮放  |  空白處左鍵/中鍵/空白鍵+左鍵 平移  |  Ctrl+Z 復原"
        self._status_label.setText(self._STATUS.get(mode, "") + suffix)

    def _switch_tool(self, mode: ToolMode):
        self._toolbar.set_active_tool(mode)
        self._on_tool_changed(mode)

    # ── 選取變更 ────────────────────────────────────────────────────────────────

    def _on_selection_changed(self, items: list):
        from items.shape_item       import ShapeItem
        from items.line_item        import LineItem
        from items.sticky_note_item import StickyNoteItem

        self._sel_shapes = [i for i in items if isinstance(i, ShapeItem)]
        self._sel_lines  = [i for i in items if isinstance(i, LineItem)]
        self._sel_sticky = [i for i in items if isinstance(i, StickyNoteItem)]

        if self._sel_shapes and self._sel_lines:
            self._color_popup.show_for_mixed(self._sel_shapes, self._sel_lines)
        elif self._sel_shapes:
            self._color_popup.show_for_shapes(self._sel_shapes)
        elif self._sel_lines:
            self._color_popup.show_for_lines(self._sel_lines)
        elif self._sel_sticky:
            self._color_popup.show_for_sticky(self._sel_sticky)
        else:
            self._color_popup.hide()

    # ── 顏色套用 ────────────────────────────────────────────────────────────────

    def _apply_border_color(self, color: QColor):
        for item in self._sel_shapes:
            if item.scene():
                item.set_border_color(color)
        if self._sel_shapes:
            self._color_popup._row_border.mark_active(color)

    def _apply_fill_color(self, color: QColor):
        for item in self._sel_shapes:
            if item.scene():
                item.set_bg_color(color)
        if self._sel_shapes:
            self._color_popup._row_fill.mark_active(color)

    def _apply_line_color(self, color: QColor):
        for item in self._sel_lines:
            if item.scene():
                item.set_line_color(color)
        if self._sel_lines:
            self._color_popup._row_line.mark_active(color)

    def _apply_sticky_bg(self, color: QColor):
        for item in self._sel_sticky:
            if item.scene():
                item.set_bg_color(color)
        if self._sel_sticky:
            self._color_popup._row_sticky_bg.mark_active(color)

    def _apply_sticky_text(self, color: QColor):
        for item in self._sel_sticky:
            if item.scene():
                item.set_text_color(color)
        if self._sel_sticky:
            self._color_popup._row_sticky_text.mark_active(color)

    def _apply_sticky_size(self, size: int):
        for item in self._sel_sticky:
            if item.scene():
                item.set_font_size(size)

    # ── 複製 / 貼上 ─────────────────────────────────────────────────────────────

    def _on_copy(self):
        from items.shape_item       import ShapeItem
        from items.sticky_note_item import StickyNoteItem
        self._clipboard = [
            item.to_dict()
            for item in self._scene.selectedItems()
            if isinstance(item, (ShapeItem, StickyNoteItem))
        ]

    def _on_paste(self):
        if not self._clipboard:
            return
        stack = self._scene.undo_stack
        stack.beginMacro("貼上")
        self._scene.clearSelection()
        new_clipboard: list[dict] = []
        for d in self._clipboard:
            from items.shape_item       import ShapeItem
            from items.sticky_note_item import StickyNoteItem
            d_copy = dict(d)
            d_copy["x"] = d["x"] + 20
            d_copy["y"] = d["y"] + 20
            d_copy.pop("id", None)
            if d.get("type") == "sticky":
                item = StickyNoteItem.from_dict(d_copy)
            else:
                item = ShapeItem.from_dict(d_copy)
            self._scene.add_item_undoable(item)
            item.setSelected(True)
            new_clipboard.append(item.to_dict())
        stack.endMacro()
        self._clipboard = new_clipboard

    # ── 截圖 ────────────────────────────────────────────────────────────────────

    def _on_screenshot(self):
        guide_pool = set(getattr(self._scene, "_guide_pool", []))
        items = [i for i in self._scene.items()
                 if i not in guide_pool and i.parentItem() is None]
        if not items:
            return

        from PyQt6.QtCore import QRectF
        united = QRectF()
        for item in items:
            united = united.united(item.sceneBoundingRect())
        if united.isEmpty():
            return

        PAD = 40
        capture_rect = united.adjusted(-PAD, -PAD, PAD, PAD)

        img = QImage(
            int(capture_rect.width()),
            int(capture_rect.height()),
            QImage.Format.Format_RGB32,
        )
        img.fill(QColor(CANVAS_BG))
        painter = QPainter(img)
        self._scene.render(painter, source=capture_rect)
        painter.end()

        QApplication.clipboard().setImage(img)
        self._flash_status("畫布已複製到剪貼簿 ✓")

    # ── AI 生成 ─────────────────────────────────────────────────────────────────

    def _on_ai_generate(self):
        """
        VibeOut 執行流程（執行緒安全版）：
        1. 立即快取目前畫布結構（按下後的當前狀態）
        2. 鎖住 VibeOut 按鈕（顯示低飽和綠）
        3. 背景執行緒跑 AI，所有輸出累積到緩衝區
        4. 執行完畢後才顯示輸出視窗並解鎖按鈕
        """
        from pathlib import Path
        from ai.canvas_exporter import export_scene_as_json
        from ai.ollama_client   import OllamaThread
        from ui.settings_dialog import load_settings

        settings = load_settings()
        model    = settings.get("model", "").strip()
        if not model:
            self._flash_status("⚠ 請先點選「設定」選擇 Ollama 模型")
            return

        # ★ 立即快取畫布結構（不管之後 user 如何編輯都不影響）
        user_prompt = export_scene_as_json(self._scene)

        # 讀取 system prompt
        translate_md = Path(__file__).parent.parent / "translate.md"
        if translate_md.exists():
            system_prompt = translate_md.read_text(encoding="utf-8")
        else:
            system_prompt = "請根據以下流程圖 JSON 結構，用繁體中文生成精確的功能需求描述。"

        # ★ 鎖住按鈕，防止連續觸發
        self._toolbar.set_vibeout_locked(True)
        self._flash_status("VibeOut 分析中… 完成後自動顯示結果")

        # 若有舊執行緒先中止
        if self._ollama_thread and self._ollama_thread.isRunning():
            self._ollama_thread.abort()
            self._ollama_thread.wait()

        # ★ 輸出緩衝區（不即時串流到面板）
        self._ai_buffer: list[str] = []

        self._ollama_thread = OllamaThread(
            base_url=settings.get("ollama_url", "http://localhost:11434"),
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        # 只累積，不即時顯示
        self._ollama_thread.chunk_received.connect(
            lambda chunk: self._ai_buffer.append(chunk)
        )
        self._ollama_thread.finished_signal.connect(self._on_ai_done)
        self._ollama_thread.error_occurred.connect(self._on_ai_error)
        self._ollama_thread.start()

    def _on_ai_done(self):
        """AI 跑完：把緩衝區內容一次性倒入面板，解鎖按鈕。"""
        full_text = "".join(getattr(self, "_ai_buffer", []))
        self._ai_buffer = []

        self._ai_panel.clear_output()
        if full_text:
            self._ai_panel.append_text(full_text)
        self._ai_panel.set_status("完成 ✓")
        self._ai_panel.show_panel()   # ★ 完成後才顯示

        self._toolbar.set_vibeout_locked(False)
        self._flash_status("AI 分析完成 ✓")

    def _on_ai_error(self, msg: str):
        """AI 發生錯誤：顯示錯誤訊息，解鎖按鈕。"""
        self._ai_buffer = []
        self._ai_panel.clear_output()
        self._ai_panel.append_text(f"⚠ 錯誤：{msg}")
        self._ai_panel.set_status(f"⚠ {msg}")
        self._ai_panel.show_panel()

        self._toolbar.set_vibeout_locked(False)
        self._flash_status(f"⚠ {msg}")

    # ── 語言初始化 ──────────────────────────────────────────────────────────────

    def _init_lang(self):
        from ui.settings_dialog import load_settings
        from ui.i18n import set_lang
        settings = load_settings()
        set_lang(settings.get("lang", "zh"))

    # ── 語言切換回調 ─────────────────────────────────────────────────────────────

    def _on_lang_change(self):
        """Settings 儲存後，語言已透過 set_lang() 切換，這裡刷新 toolbar 標籤。"""
        self._toolbar.refresh_lang()

    # ── 主題初始化 ──────────────────────────────────────────────────────────────

    def _init_theme(self):
        """在 UI 建立前先設好 theme 狀態（讓 icon 初次繪製就用正確顏色）。"""
        from ui.settings_dialog import load_settings
        settings = load_settings()
        _theme.set(settings.get("theme", "dark"))

    # ── 主題套用（派發給所有子元件）──────────────────────────────────────────────

    def _apply_theme(self):
        """重新套用當前主題到所有 UI 元件。"""
        tm = _theme
        # 主視窗 + 狀態列
        self.setStyleSheet(f"""
            QMainWindow {{ background: {tm.get('bg_mid')}; }}
            QStatusBar {{
                background: {tm.get('bg_dark')};
                color: {tm.get('text_muted')};
                font-family: '{FONT_FAMILY}';
                font-size: {FONT_SIZE_NORMAL}px;
                border-top: 1px solid {tm.get('separator')};
            }}
        """)
        if hasattr(self, '_status_label'):
            self._status_label.setStyleSheet(
                f"color:{tm.get('text_muted')}; padding:0 8px;"
            )
        # Central widget
        if self.centralWidget():
            self.centralWidget().setStyleSheet(f"background: {tm.get('bg_mid')};")
        # Canvas
        if hasattr(self, '_scene'):
            self._scene.apply_theme()
        if hasattr(self, '_canvas_view'):
            self._canvas_view.apply_theme()
        # Toolbar
        if hasattr(self, '_toolbar'):
            self._toolbar.apply_theme()
        # Floating widgets
        if hasattr(self, '_color_popup'):
            self._color_popup.apply_theme()
        if hasattr(self, '_text_toolbar'):
            self._text_toolbar.apply_theme()
        # AI mini button
        if hasattr(self, '_ai_mini_btn'):
            self._ai_mini_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {tm.get('bg_light')};
                    border: 1px solid {tm.get('accent')}88;
                    border-radius: 14px;
                    color: {tm.get('accent')};
                    font-family: '{FONT_FAMILY}';
                    font-size: 10px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background: {tm.get('accent')}22;
                    border-color: {tm.get('accent')};
                }}
            """)

    # ── 主題切換回調 ─────────────────────────────────────────────────────────────

    def _on_theme_change(self, name: str):
        """Settings 儲存後呼叫：切換 theme 並重繪所有元件。"""
        _theme.set(name)
        self._apply_theme()

    # ── 設定 ────────────────────────────────────────────────────────────────────

    def _on_settings(self):
        from ui.settings_dialog import SettingsDialog
        dlg = SettingsDialog(
            self,
            on_lang_change=self._on_lang_change,
            on_theme_change=self._on_theme_change,
        )
        dlg.exec()

    # ── AI Mini 按鈕（最小化後浮動在右下角）────────────────────────────────────

    def _on_ai_minimized(self):
        """AI panel 發出 minimized → 隱藏 panel，顯示右下角浮動按鈕。"""
        self._ai_panel.hide()
        self._ai_mini_btn.show()
        self._ai_mini_btn.raise_()
        self._reposition_ai_mini()

    def _on_ai_mini_restore(self):
        """點擊浮動按鈕 → 隱藏按鈕，重新顯示 AI panel。"""
        self._ai_mini_btn.hide()
        self._ai_panel.show_panel()

    def _reposition_ai_mini(self):
        """將浮動按鈕定位在 canvas_view 右下角。"""
        cv  = self._canvas_view
        btn = self._ai_mini_btn
        margin = 14
        btn.move(cv.width() - btn.width() - margin,
                 cv.height() - btn.height() - margin)

    # ── 新建 ────────────────────────────────────────────────────────────────────

    def _on_new(self):
        """清空畫布，重置目前檔案路徑（等同新建空白文件）。"""
        from PyQt6.QtWidgets import QMessageBox
        if self._scene.items():
            # 有內容才詢問
            guide_pool = set(getattr(self._scene, "_guide_pool", []))
            real_items = [i for i in self._scene.items()
                          if i not in guide_pool and i.parentItem() is None]
            if real_items:
                ans = QMessageBox.question(
                    self, "新建圖樣",
                    "目前畫布內容將被清除，確定嗎？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if ans != QMessageBox.StandardButton.Yes:
                    return
        # 清空
        self._file_manager._clear_scene(self._scene)
        self._scene.undo_stack.clear()
        self._current_file = None
        self._flash_status("已建立新圖樣")

    # ── 存檔 ────────────────────────────────────────────────────────────────────

    def _on_save(self):
        """
        ★ 修正 Bug 3：Save 按鈕記住上次路徑。
        - 若已有 current_file（上次儲存過），直接靜默儲存到同一路徑。
        - 若還沒有，彈出 dialog（初次存檔）。
        Toolbar Save 按鈕 = 「快速存檔」語義。
        若需要「另存新檔」，可用 Ctrl+Shift+S（未來擴充）。
        """
        if self._current_file:
            self._file_manager.save(self._scene, self._current_file)
            self._flash_status(f"已儲存：{self._current_file.name}")
        else:
            self._save_with_dialog()


    def _on_save_shortcut(self):
        """Ctrl+S：與 Save 按鈕行為相同（有路徑靜默存，沒有才 dialog）。"""
        self._on_save()


    def _save_with_dialog(self):
        """
        彈出儲存對話框。
        - 預設目錄：上次儲存的目錄（從 settings.json 讀取），或 Home
        - 存檔成功後更新 current_file 並記住目錄到 settings.json
        """
        from ui.settings_dialog import load_settings, save_settings
        settings = load_settings()
        last_dir = settings.get("last_save_dir", "")
        start_dir = last_dir if (last_dir and os.path.isdir(last_dir)) else str(Path.home())

        path, _ = QFileDialog.getSaveFileName(
            self,
            "儲存 VibeCode 專案",
            str(Path(start_dir) / "untitled.vbc"),
            FILE_VBC_FILTER,
        )
        if not path:
            return
        p = Path(path)
        self._file_manager.save(self._scene, p)
        self._current_file = p
        # 記住目錄
        settings["last_save_dir"] = str(p.parent)
        save_settings(settings)
        self._flash_status(f"已儲存：{p.name}")

    def _on_open(self):
        """開啟 .vbc 檔案；從上次目錄開始瀏覽。"""
        from ui.settings_dialog import load_settings, save_settings
        settings = load_settings()
        last_dir = settings.get("last_save_dir", "")
        start_dir = last_dir if (last_dir and os.path.isdir(last_dir)) else str(Path.home())

        path, _ = QFileDialog.getOpenFileName(
            self,
            "開啟 VibeCode 專案",
            start_dir,
            FILE_VBC_FILTER,
        )
        if not path:
            return
        p = Path(path)
        self._file_manager.load(self._scene, p)
        self._current_file = p
        settings["last_save_dir"] = str(p.parent)
        save_settings(settings)
        self._flash_status(f"已開啟：{p.name}")

    def _try_restore_session(self):
        """啟動時嘗試恢復上次未儲存的 session。"""
        try:
            self._file_manager.load_session(self._scene)
        except Exception:
            pass

    # ── 狀態列訊息（閃現後恢復預設）────────────────────────────────────────────

    def _flash_status(self, msg: str, ms: int = 3000):
        """在狀態列顯示訊息，ms 毫秒後恢復預設文字。"""
        if hasattr(self, '_status_label'):
            self._status_label.setText(msg)
            QTimer.singleShot(ms, self._restore_status)

    def _restore_status(self):
        if hasattr(self, '_status_label'):
            self._restore_status_text()

    def _restore_status_text(self):
        if hasattr(self, '_status_label'):
            self._status_label.setText("VibeCode Tool  —  準備就緒")
