# VibeCode Tool - 專案說明

## 結構
E:\CodeBase\Python\VibeCode\
├── canvas/   canvas_scene.py, canvas_view.py, tool_controller.py
├── items/    shape_item.py, text_item.py, line_item.py, sticky_note_item.py, editable_text.py
├── ui/       main_window.py, toolbar.py, color_popup.py, text_style_toolbar.py, shape_picker.py
├── routing/  orthogonal_router.py
├── storage/  file_manager.py
└── constants.py, main.py

## 技術棧
PyQt6, Python 3.14

## 目前已完成
- 7種流程圖形狀 + 便利貼 + 獨立文字
- 正交折線連接 (A* 路由)
- Smart Guide 對齊輔助線
- Undo/Redo (10步)
- 浮動 ColorPopup / TextStyleToolbar
- 文字編輯：選取後套用格式（B/I/刪除線/顏色/大小）
- Save 記住上次路徑

## 當次要修的問題
1.跟我要求我需要VIEW 修改的檔案
2.如果由AGENT自動修整,則需自己核對一次輸出