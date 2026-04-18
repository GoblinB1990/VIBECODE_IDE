import os
import json
from pathlib import Path
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor

from constants import CANVAS_DATA_VERSION, LINE_DEFAULT_COLOR, LINE_WIDTH


class FileManager:
    """
    手動存檔管理器（無 debounce）。
    - save(scene, path)：存到指定路徑，同時覆寫 session 檔
    - load(scene, path)：清空再載入，undo stack 清除
    - load_session(scene)：啟動時還原上次手動儲存狀態
    """

    SESSION_DIR  = Path(os.environ.get("APPDATA", Path.home())) / "VibeCodeTool"
    SESSION_FILE = SESSION_DIR / "session.vbc"

    # ── 存檔 ──────────────────────────────────────────────────────────────────

    def save(self, scene, path: Path):
        data = self._serialize(scene)
        text = json.dumps(data, ensure_ascii=False, indent=2)
        path.write_text(text, encoding="utf-8")
        # 同時覆寫 session
        try:
            self.SESSION_DIR.mkdir(parents=True, exist_ok=True)
            self.SESSION_FILE.write_text(text, encoding="utf-8")
        except Exception as e:
            print(f"[FileManager] session write failed: {e}")

    # ── 開啟 ──────────────────────────────────────────────────────────────────

    def load(self, scene, path: Path) -> bool:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self._clear_scene(scene)
            self._deserialize(scene, data)
            scene.undo_stack.clear()
            return True
        except Exception as e:
            print(f"[FileManager] load failed: {e}")
            return False

    def load_session(self, scene) -> bool:
        if self.SESSION_FILE.exists():
            return self.load(scene, self.SESSION_FILE)
        return False

    # ── 序列化 ────────────────────────────────────────────────────────────────

    def _serialize(self, scene) -> dict:
        from items.shape_item       import ShapeItem
        from items.text_item        import TextItem
        from items.line_item        import LineItem
        from items.sticky_note_item import StickyNoteItem
        from items.image_item       import ImageItem
        from items.table_item       import TableItem

        guide_pool = set(getattr(scene, "_guide_pool", []))
        items_data = []

        for item in scene.items():
            if item in guide_pool:
                continue
            if item.parentItem() is not None:
                continue
            if isinstance(item, ShapeItem):
                items_data.append(item.to_dict())
            elif isinstance(item, StickyNoteItem):
                items_data.append(item.to_dict())
            elif isinstance(item, TextItem):
                items_data.append(item.to_dict())
            elif isinstance(item, ImageItem):
                items_data.append(item.to_dict())
            elif isinstance(item, TableItem):
                items_data.append(item.to_dict())
            elif isinstance(item, LineItem):
                items_data.append(item.to_dict())

        return {"version": CANVAS_DATA_VERSION, "items": items_data}

    # ── 反序列化 ──────────────────────────────────────────────────────────────

    def _deserialize(self, scene, data: dict):
        from items.shape_item       import ShapeItem
        from items.text_item        import TextItem
        from items.line_item        import LineItem
        from items.sticky_note_item import StickyNoteItem
        from items.image_item       import ImageItem
        from items.table_item       import TableItem

        items_list = data.get("items", [])
        id_map: dict[str, object] = {}
        line_dicts: list[dict]    = []

        # 第一階段：Shape / Text / StickyNote / Image / Table
        for d in items_list:
            t = d.get("type")
            if t == "line":
                line_dicts.append(d)
                continue

            item = None
            if t == "shape":
                item = ShapeItem.from_dict(d)
            elif t == "text":
                item = TextItem.from_dict(d)
            elif t == "sticky":
                item = StickyNoteItem.from_dict(d)
            elif t == "image":
                item = ImageItem.from_dict(d)
            elif t == "table":
                item = TableItem.from_dict(d)

            if item is None:
                continue

            saved_id = d.get("id")
            if saved_id:
                item._id = saved_id

            scene.addItem(item)
            # 僅有帶 _id 屬性的 item 才需要加入 id_map（供 Line 連接用）
            if hasattr(item, "_id"):
                id_map[item._id] = item

        # 第二階段：Line
        for d in line_dicts:
            start_item = id_map.get(d.get("start_id"))
            end_item   = id_map.get(d.get("end_id"))

            item = LineItem(
                QPointF(d["x1"], d["y1"]),
                QPointF(d["x2"], d["y2"]),
                start_item=start_item,
                end_item=end_item,
            )
            saved_id = d.get("id")
            if saved_id:
                item._id = saved_id
            item.set_line_color(QColor(d.get("color", LINE_DEFAULT_COLOR)))
            item.set_line_width(d.get("width", LINE_WIDTH))
            scene.addItem(item)
            item.register_connections()

    # ── 清空場景 ──────────────────────────────────────────────────────────────

    def _clear_scene(self, scene):
        from items.line_item import LineItem
        guide_pool = set(getattr(scene, "_guide_pool", []))
        items = [i for i in scene.items()
                 if i not in guide_pool and i.parentItem() is None]
        for item in items:
            if isinstance(item, LineItem):
                item.unregister_connections()
        for item in items:
            scene.removeItem(item)
