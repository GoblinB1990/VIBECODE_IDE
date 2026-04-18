"""
orthogonal_router.py
用 A*（含轉彎懲罰）在格狀座標上找出正交繞路路徑。

入口：
    route(start, end, obstacles, grid) -> list[QPointF]

回傳的點列表保證只有水平或垂直線段，可以直接用 QPainterPath 畫出。
"""

import heapq
from PyQt6.QtCore import QPointF, QRectF

# 障礙物膨脹量（像素），讓連線不貼著 Shape 邊緣走
_MARGIN = 24
# 轉彎額外代價，鼓勵較少彎折
_TURN_COST = 8
# 搜尋區域超出起終點的擴展格數
_SEARCH_PAD = 12


def route(start: QPointF, end: QPointF,
          obstacles: list[QRectF],
          grid: int = 20) -> list[QPointF]:
    """
    回傳正交路徑的 QPointF 列表（含 start 與 end）。
    若搜尋失敗，退回簡單 L 形路徑。
    """
    # ── 座標轉換 ──────────────────────────────────────────────────────────────
    def to_grid(p: QPointF):
        return (round(p.x() / grid), round(p.y() / grid))

    def to_scene(g) -> QPointF:
        return QPointF(g[0] * grid, g[1] * grid)

    gs = to_grid(start)
    ge = to_grid(end)

    if gs == ge:
        return [start, end]

    # ── 膨脹後的障礙物（格子座標用，逐點判斷）────────────────────────────────
    inflated: list[QRectF] = [
        QRectF(r.x() - _MARGIN, r.y() - _MARGIN,
               r.width() + _MARGIN * 2, r.height() + _MARGIN * 2)
        for r in obstacles
    ]

    def is_blocked(gx: int, gy: int) -> bool:
        px, py = gx * grid, gy * grid
        for r in inflated:
            if r.contains(QPointF(px, py)):
                return True
        return False

    # ── 搜尋邊界 ──────────────────────────────────────────────────────────────
    bx0 = min(gs[0], ge[0]) - _SEARCH_PAD
    bx1 = max(gs[0], ge[0]) + _SEARCH_PAD
    by0 = min(gs[1], ge[1]) - _SEARCH_PAD
    by1 = max(gs[1], ge[1]) + _SEARCH_PAD

    # ── A* ────────────────────────────────────────────────────────────────────
    # 狀態：(gx, gy, last_direction)  direction: 0=水平, 1=垂直, -1=未知
    DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    DIR_AXIS = {(1, 0): 0, (-1, 0): 0, (0, 1): 1, (0, -1): 1}

    def heuristic(gx, gy):
        return abs(gx - ge[0]) + abs(gy - ge[1])

    # heap: (f, g_cost, gx, gy, last_axis)
    start_state = (heuristic(*gs), 0, gs[0], gs[1], -1)
    open_heap = [start_state]
    best: dict[tuple, int] = {(gs[0], gs[1], -1): 0}
    came_from: dict[tuple, tuple | None] = {(gs[0], gs[1], -1): None}

    found_state = None

    while open_heap:
        f, g, cx, cy, caxis = heapq.heappop(open_heap)

        state = (cx, cy, caxis)
        # 若已有更短的路到此狀態則跳過
        if best.get(state, 10**9) < g:
            continue

        if (cx, cy) == ge:
            found_state = state
            break

        for dx, dy in DIRS:
            nx, ny = cx + dx, cy + dy
            if not (bx0 <= nx <= bx1 and by0 <= ny <= by1):
                continue
            # 終點即使被「障礙」覆蓋也允許進入
            if is_blocked(nx, ny) and (nx, ny) != ge:
                continue

            naxis = DIR_AXIS[(dx, dy)]
            turn  = 0 if (caxis == -1 or naxis == caxis) else _TURN_COST
            ng    = g + 1 + turn
            nstate = (nx, ny, naxis)

            if ng < best.get(nstate, 10**9):
                best[nstate] = ng
                came_from[nstate] = state
                nf = ng + heuristic(nx, ny)
                heapq.heappush(open_heap, (nf, ng, nx, ny, naxis))

    # ── 回溯路徑 ──────────────────────────────────────────────────────────────
    if found_state is None:
        # 退回 L 形
        return _l_shape(start, end)

    path_grid: list[tuple] = []
    cur = found_state
    while cur is not None:
        gx, gy, _ = cur
        path_grid.append((gx, gy))
        cur = came_from.get(cur)
    path_grid.reverse()

    raw = [to_scene(p) for p in path_grid]

    # 確保起終點精確（避免 grid snap 誤差）
    if raw:
        raw[0] = start
        raw[-1] = end

    return _simplify(raw)


# ── 工具函式 ──────────────────────────────────────────────────────────────────

def _l_shape(start: QPointF, end: QPointF) -> list[QPointF]:
    """簡單 L 形備用路徑（先水平後垂直）。"""
    mid = QPointF(end.x(), start.y())
    return [start, mid, end]


def _simplify(pts: list[QPointF]) -> list[QPointF]:
    """
    移除共線中間點，只保留轉角頂點。
    例：A→B→C 若 AB 與 BC 同方向，則去掉 B。
    """
    if len(pts) <= 2:
        return pts

    result = [pts[0]]
    for i in range(1, len(pts) - 1):
        p0, p1, p2 = pts[i - 1], pts[i], pts[i + 1]
        same_x = abs(p0.x() - p1.x()) < 0.5 and abs(p1.x() - p2.x()) < 0.5
        same_y = abs(p0.y() - p1.y()) < 0.5 and abs(p1.y() - p2.y()) < 0.5
        if not (same_x or same_y):
            result.append(p1)
    result.append(pts[-1])
    return result
