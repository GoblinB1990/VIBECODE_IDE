"""
canvas_exporter.py

讀取 CanvasScene 所有物件，產生結構化 JSON 描述，
作為 Ollama / 雲端 API 的 user prompt context。
不依賴圖像識別，純粹從物件結構提取資訊。
"""
from __future__ import annotations
import json


# ShapeType 名稱對照（英文 + 中文說明）
SHAPE_TYPE_NAMES: dict[str, str] = {
    "OVAL":          "Start/End 起始/結束（橢圓）",
    "RECT":          "Process 處理步驟（矩形）",
    "DIAMOND":       "Decision 判斷分支（菱形）",
    "PARALLELOGRAM": "Input/Output 輸入/輸出（平行四邊形）",
    "CYLINDER":      "Database 資料庫（圓柱）",
    "PREDEFINED":    "Predefined Process 預定義流程（雙線矩形）",
    "RECT_DESCRIBE": "Description Box 描述框（帶標題列矩形）",
}


def export_scene(scene) -> dict:
    """
    傳入 CanvasScene，回傳可直接 json.dumps 的結構化描述 dict。

    回傳格式：
    {
        "canvas_summary": "...",
        "nodes":          [ {id, kind, shape_type, label, title, body, position, size} ],
        "sticky_notes":   [ {id, kind, text, position, size} ],
        "text_items":     [ {id, kind, text, position} ],
        "tables":         [ {kind, title, headers, rows, position} ],
        "connections":    [ {from, to, from_id, to_id} ],
    }
    """
    from items.shape_item       import ShapeItem
    from items.text_item        import TextItem
    from items.line_item        import LineItem
    from items.sticky_note_item import StickyNoteItem
    from items.table_item       import TableItem
    from items.image_item       import ImageItem

    guide_pool = set(getattr(scene, "_guide_pool", []))

    nodes:     list[dict] = []
    stickies:  list[dict] = []
    texts:     list[dict] = []
    tables:    list[dict] = []
    images:    list[dict] = []
    raw_lines: list[dict] = []

    # id → 顯示名稱，用於組裝連線的人類可讀描述
    id_to_label: dict[str, str] = {}

    for item in scene.items():
        if item in guide_pool:
            continue
        if item.parentItem() is not None:
            continue

        if isinstance(item, ShapeItem):
            d          = item.to_dict()
            shape_name = SHAPE_TYPE_NAMES.get(d.get("shape_type", ""), d.get("shape_type", ""))
            title_text = d.get("title", "")
            body_text  = d.get("body", "")
            label      = title_text or body_text or "(空)"
            id_to_label[d["id"]] = label
            nodes.append({
                "id":         d["id"],
                "kind":       "shape",
                "shape_type": shape_name,
                "label":      label,
                "title":      title_text,
                "body":       body_text,
                "position":   {"x": round(d["x"]), "y": round(d["y"])},
                "size":       {"w": round(d["w"]), "h": round(d["h"])},
            })

        elif isinstance(item, StickyNoteItem):
            d     = item.to_dict()
            text  = d.get("text", "")
            label = f"[便利貼] {text[:40]}" if text else "[便利貼] (空)"
            id_to_label[d["id"]] = label
            stickies.append({
                "id":       d["id"],
                "kind":     "sticky_note",
                "text":     text,
                "position": {"x": round(d["x"]), "y": round(d["y"])},
                "size":     {"w": round(d["w"]), "h": round(d["h"])},
            })

        elif isinstance(item, TextItem):
            d     = item.to_dict()
            text  = d.get("text", "")
            label = f"[文字] {text[:40]}" if text else "[文字] (空)"
            id_to_label[d["id"]] = label
            texts.append({
                "id":       d["id"],
                "kind":     "text",
                "text":     text,
                "position": {"x": round(d["x"]), "y": round(d["y"])},
            })

        elif isinstance(item, TableItem):
            d          = item.to_dict()
            rows_data  = d.get("cells", [])
            n_cols     = d.get("cols", 0)
            # 用欄位字母當 header（A, B, C …）
            headers    = [_col_label(c) for c in range(n_cols)]
            # 把每列轉成 {A: val, B: val, ...} 方便 AI 理解
            structured = []
            for row in rows_data:
                structured.append({headers[c]: row[c] for c in range(len(row))})
            title = d.get("title", "") or "（無標題）"
            tables.append({
                "kind":     "table",
                "title":    title,
                "headers":  headers,
                "rows":     structured,
                "position": {"x": round(d["x"]), "y": round(d["y"])},
            })

        elif isinstance(item, ImageItem):
            d = item.to_dict()
            images.append({
                "kind":     "image",
                "position": {"x": round(d["x"]), "y": round(d["y"])},
                "size":     {"w": round(d["width"]), "h": round(d["height"])},
            })

        elif isinstance(item, LineItem):
            d = item.to_dict()
            raw_lines.append({
                "from_id": d.get("start_id"),
                "to_id":   d.get("end_id"),
            })

    # 組裝連線（加入人類可讀的 label）
    connections: list[dict] = []
    for ln in raw_lines:
        fid = ln["from_id"]
        tid = ln["to_id"]
        connections.append({
            "from":    id_to_label.get(fid, fid or "?"),
            "to":      id_to_label.get(tid, tid or "?"),
            "from_id": fid,
            "to_id":   tid,
        })

    total_items = len(nodes) + len(stickies) + len(texts) + len(tables) + len(images)
    summary = (
        f"畫布共有 {total_items} 個物件（"
        f"{len(nodes)} 個流程節點、"
        f"{len(stickies)} 個便利貼、"
        f"{len(texts)} 個獨立文字、"
        f"{len(tables)} 個表格、"
        f"{len(images)} 張圖片），"
        f"以及 {len(connections)} 條連線。"
    )

    return {
        "canvas_summary": summary,
        "nodes":          nodes,
        "sticky_notes":   stickies,
        "text_items":     texts,
        "tables":         tables,
        "images":         images,
        "connections":    connections,
    }


def export_scene_as_json(scene, indent: int = 2) -> str:
    """便利函式：直接回傳 JSON 字串。"""
    return json.dumps(export_scene(scene), ensure_ascii=False, indent=indent)


# ── 內部工具 ──────────────────────────────────────────────────────────────────

def _col_label(c: int) -> str:
    """欄位字母：0→A, 1→B, 26→AA …"""
    label = ""
    while True:
        label = chr(ord("A") + (c % 26)) + label
        c = c // 26 - 1
        if c < 0:
            break
    return label
