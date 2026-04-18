"""
table_item.py  v2

畫布上的可編輯表格。

佈局（從上到下）：
  ┌──────────────────────────────┐  ← TITLE BAR（可編輯主題名，TITLE_H）
  ├────┬──────┬──────┬──────────┤  ← 欄位字母 A / B / C…（HEADER_H）
  │  1 │      │      │          │  ← 資料列（CELL_H × CELL_W）
  │  2 │      │      │          │
  └────┴──────┴──────┴──────────┘

互動：
  ‣ 點擊 TITLE BAR → 選取 title（高亮）
      · Enter / F2 / 雙擊 → 編輯 title
      · Delete          → 刪除整個 Table
      · ↓               → 移到 (0,0)
  ‣ 點擊儲存格 → 選取該格（高亮）
      · Enter / F2 / 雙擊 → 進入行內編輯
      · ↑↓←→            → 移動選取
      · ↑ @ row 0       → 跳回 TITLE BAR
      · Delete / Backspace → 清空儲存格文字
      · 一般字元          → 直接開啟編輯（Excel 風格取代）
      · Esc             → 取消選取，釋放焦點
  ‣ 行內編輯中（QLineEdit）：
      · Tab / Shift+Tab → 移至下一/上一格（換行）
      · Enter / ↓       → 移至下一列
      · ↑               → 移至上一列
      · Esc             → 取消，不儲存
      · 點擊其他地方     → 儲存並關閉
  ‣ 選取整個 Table（無 cell/title focus）後按 Delete → 由 canvas_view 正常刪除
"""
from __future__ import annotations

from PyQt6.QtWidgets import QGraphicsItem, QGraphicsProxyWidget, QLineEdit, QGraphicsObject
from PyQt6.QtCore import Qt, QRectF, QPointF, QObject, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QBrush

from constants import (
    COLOR_BG_MID, COLOR_BG_LIGHT, COLOR_TEXT_PRIMARY,
    COLOR_SEPARATOR, COLOR_ACCENT,
    FONT_FAMILY,
)

# ── 尺寸常數（以 14pt 字體為基準）───────────────────────────────────────────
CELL_W       = 100   # 資料格欄寬
CELL_H       = 36    # 資料格列高（14pt ≈ 19px；上下各留 ~8px）
TITLE_H      = 30    # 最頂部主題欄高度
HEADER_H     = 22    # 欄位字母列高（A / B / C…）
ROWNUM_W     = 28    # 左側列號欄寬
CELL_FONT    = 14    # 資料格字體大小（pt）
TITLE_FONT   = 13    # 主題欄字體大小（pt）
HEADER_FONT  = 9     # 欄位字母字體大小（pt）
COL_MIN_W    = 40    # 欄位最小寬度
_RESIZE_HIT  = 5     # 距欄位邊線幾個 px 內啟動 resize 游標


# ── 行內 QLineEdit ─────────────────────────────────────────────────────────────

class _CellEditor(QLineEdit):
    """帶 focus_lost 訊號的 QLineEdit。"""
    focus_lost = pyqtSignal()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.focus_lost.emit()


# ── TableItem ──────────────────────────────────────────────────────────────────

class TableItem(QGraphicsObject):
    TYPE_NAME = "table"

    def __init__(self, rows: int = 3, cols: int = 3, parent=None):
        super().__init__(parent)
        self._rows = rows
        self._cols = cols
        self._title  = ""                                    # 主題欄文字
        self._cells: list[list[str]] = [[""] * cols for _ in range(rows)]
        self._col_ws: list[int] = [CELL_W]  * cols
        self._row_hs: list[int] = [CELL_H]  * rows

        # 選取狀態
        self._sel_title = False                  # 主題欄被選取
        self._sel: tuple[int, int] | None = None # 儲存格被選取

        # 資料格行內編輯器
        self._editor_proxy:  QGraphicsProxyWidget | None = None
        self._editor:        _CellEditor | None = None
        self._editor_cell:   tuple[int, int] | None = None
        self._closing_editor = False
        self._key_filter = None   # 保持 GC 參考

        # 主題欄編輯器
        self._title_proxy:   QGraphicsProxyWidget | None = None
        self._title_editor:  _CellEditor | None = None
        self._closing_title  = False

        # 欄位寬度拖曳 resize 狀態
        self._resize_col:     int | None = None   # 正在 resize 的欄索引
        self._resize_start_x: float = 0.0         # 拖曳起始 sceneX
        self._resize_orig_w:  int   = 0           # 拖曳前的欄寬

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable,            True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable,         True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable,          True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)   # 讓 hover 事件觸發游標切換

    # ── 尺寸計算 ───────────────────────────────────────────────────────────────

    def _total_w(self) -> float:
        return float(ROWNUM_W + sum(self._col_ws))

    def _total_h(self) -> float:
        return float(TITLE_H + HEADER_H + sum(self._row_hs))

    def _col_x(self, c: int) -> float:
        return float(ROWNUM_W + sum(self._col_ws[:c]))

    def _row_y(self, r: int) -> float:
        return float(TITLE_H + HEADER_H + sum(self._row_hs[:r]))

    def _is_title_area(self, ly: float) -> bool:
        return 0 <= ly < TITLE_H

    def _cell_at(self, lx: float, ly: float) -> tuple[int, int] | None:
        if ly < TITLE_H + HEADER_H:
            return None
        if lx < ROWNUM_W:
            return None
        cx = lx - ROWNUM_W
        cy = ly - TITLE_H - HEADER_H
        col = None
        acc = 0
        for c, w in enumerate(self._col_ws):
            acc += w
            if cx < acc:
                col = c
                break
        row = None
        acc = 0
        for r, h in enumerate(self._row_hs):
            acc += h
            if cy < acc:
                row = r
                break
        if col is None or row is None:
            return None
        return (row, col)

    def _col_border_hit(self, lx: float, ly: float) -> int | None:
        """
        若 (lx, ly) 落在 HEADER 列且距某欄右側邊線 ≤ _RESIZE_HIT px，
        回傳該欄索引（0-based）；否則回傳 None。
        """
        if not (TITLE_H <= ly <= TITLE_H + HEADER_H):
            return None
        x = float(ROWNUM_W)
        for c in range(self._cols):
            x += self._col_ws[c]
            if abs(lx - x) <= _RESIZE_HIT:
                return c
        return None

    # ── boundingRect ───────────────────────────────────────────────────────────

    def boundingRect(self) -> QRectF:
        return QRectF(-1, -1, self._total_w() + 2, self._total_h() + 2)

    # ── paint ─────────────────────────────────────────────────────────────────

    def paint(self, painter: QPainter, option, widget=None):
        tw = self._total_w()
        th = self._total_h()

        # ── 全背景 ────────────────────────────────────────────────────────────
        painter.fillRect(QRectF(0, 0, tw, th), QColor(COLOR_BG_MID))

        # ── TITLE BAR ─────────────────────────────────────────────────────────
        title_bg = QColor(COLOR_BG_LIGHT)
        if self._sel_title and self._title_editor is None:
            title_bg = QColor(COLOR_ACCENT)
            title_bg.setAlpha(0x44)
        painter.fillRect(QRectF(0, 0, tw, TITLE_H), title_bg)

        title_pen_color = QColor(COLOR_ACCENT) if self._sel_title else QColor(COLOR_TEXT_PRIMARY)
        painter.setPen(QPen(title_pen_color))
        title_font = QFont(FONT_FAMILY, TITLE_FONT, QFont.Weight.Bold)
        painter.setFont(title_font)
        display_title = self._title if self._title else "Table"
        if self._title_editor is None:  # 編輯中不重繪
            painter.drawText(
                QRectF(8, 0, tw - 16, TITLE_H),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                display_title,
            )

        # ── 欄位字母表頭背景 ───────────────────────────────────────────────────
        hdr_bg = QColor(COLOR_BG_LIGHT)
        painter.fillRect(QRectF(0, TITLE_H, tw, HEADER_H), hdr_bg)
        # 列號欄背景（整列）
        painter.fillRect(QRectF(0, TITLE_H, ROWNUM_W, th - TITLE_H), hdr_bg)

        # 欄位字母（A, B, C …）
        hdr_font = QFont(FONT_FAMILY, HEADER_FONT, QFont.Weight.Bold)
        painter.setFont(hdr_font)
        painter.setPen(QPen(QColor(COLOR_ACCENT)))
        for c in range(self._cols):
            x = self._col_x(c)
            w = self._col_ws[c]
            label = _col_label(c)
            painter.drawText(
                QRectF(x, TITLE_H, w, HEADER_H),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                label,
            )

        # 列號（1, 2, 3 …）
        row_font = QFont(FONT_FAMILY, HEADER_FONT)
        painter.setFont(row_font)
        painter.setPen(QPen(QColor(COLOR_ACCENT)))
        for r in range(self._rows):
            y = self._row_y(r)
            h = self._row_hs[r]
            painter.drawText(
                QRectF(0, y, ROWNUM_W, h),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                str(r + 1),
            )

        # ── 格線 ──────────────────────────────────────────────────────────────
        grid_pen = QPen(QColor(COLOR_SEPARATOR), 1.0)
        painter.setPen(grid_pen)
        # 垂直線
        x = float(ROWNUM_W)
        for c in range(self._cols + 1):
            painter.drawLine(QPointF(x, TITLE_H), QPointF(x, th))
            if c < self._cols:
                x += self._col_ws[c]
        # 水平線
        y = float(TITLE_H + HEADER_H)
        for r in range(self._rows + 1):
            painter.drawLine(QPointF(0, y), QPointF(tw, y))
            if r < self._rows:
                y += self._row_hs[r]

        # 分隔線（title 底部、header 底部、列號右側 → 稍粗）
        accent_line = QPen(QColor(COLOR_ACCENT), 1.2)
        painter.setPen(accent_line)
        painter.drawLine(QPointF(0,        TITLE_H),          QPointF(tw, TITLE_H))
        painter.drawLine(QPointF(0,        TITLE_H + HEADER_H), QPointF(tw, TITLE_H + HEADER_H))
        painter.drawLine(QPointF(ROWNUM_W, TITLE_H),          QPointF(ROWNUM_W, th))

        # ── 儲存格文字 ────────────────────────────────────────────────────────
        cell_font = QFont(FONT_FAMILY, CELL_FONT)
        painter.setFont(cell_font)
        painter.setPen(QPen(QColor(COLOR_TEXT_PRIMARY)))
        for r in range(self._rows):
            for c in range(self._cols):
                if self._editor_cell == (r, c):
                    continue
                text = self._cells[r][c]
                if not text:
                    continue
                rect = QRectF(
                    self._col_x(c) + 4,
                    self._row_y(r) + 2,
                    self._col_ws[c] - 8,
                    self._row_hs[r] - 4,
                )
                painter.drawText(
                    rect,
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                    text,
                )

        # ── 選中儲存格高亮 ────────────────────────────────────────────────────
        if self._sel is not None and self._editor_cell is None:
            r, c = self._sel
            sel_fill = QColor(COLOR_ACCENT); sel_fill.setAlpha(0x33)
            painter.fillRect(
                QRectF(self._col_x(c), self._row_y(r), self._col_ws[c], self._row_hs[r]),
                sel_fill,
            )
            painter.setPen(QPen(QColor(COLOR_ACCENT), 1.8))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(
                QRectF(self._col_x(c), self._row_y(r), self._col_ws[c], self._row_hs[r])
            )

        # ── 主題欄選取框線 ────────────────────────────────────────────────────
        if self._sel_title and self._title_editor is None:
            painter.setPen(QPen(QColor(COLOR_ACCENT), 1.8))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(QRectF(0, 0, tw, TITLE_H))

        # ── 外框 ──────────────────────────────────────────────────────────────
        outer = QColor(COLOR_ACCENT)
        outer.setAlpha(0x99 if not self.isSelected() else 0xff)
        outer_pen = QPen(outer, 1.5 if not self.isSelected() else 2.0)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(outer_pen)
        painter.drawRect(QRectF(0, 0, tw, th))

    # ── Hover：游標提示 ────────────────────────────────────────────────────────

    def hoverMoveEvent(self, event):
        if self._col_border_hit(event.pos().x(), event.pos().y()) is not None:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        else:
            self.unsetCursor()
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        self.unsetCursor()
        super().hoverLeaveEvent(event)

    # ── 滑鼠事件 ──────────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            lx = event.pos().x()
            ly = event.pos().y()

            # ── 欄位 resize 拖曳起始 ─────────────────────────────────────────
            c = self._col_border_hit(lx, ly)
            if c is not None:
                self._close_editor(save=True, refocus=False)
                self._close_title_editor(save=True, refocus=False)
                self._resize_col     = c
                self._resize_start_x = event.scenePos().x()
                self._resize_orig_w  = self._col_ws[c]
                # 拖曳期間暫停移動，避免整個 item 被拖走
                self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
                event.accept()
                return

            # 點擊主題欄
            if self._is_title_area(ly):
                self._close_editor(save=True, refocus=False)
                self._close_title_editor(save=True, refocus=False)
                self._sel_title = True
                self._sel = None
                self.setFocus()
                self.update()
                event.accept()
                return

            # 點擊資料格
            cell = self._cell_at(lx, ly)
            if cell is not None:
                self._close_title_editor(save=True, refocus=False)
                if self._sel == cell and self._editor_cell is None:
                    # 已選中再點 → 直接編輯
                    self._open_editor(*cell)
                else:
                    self._close_editor(save=True, refocus=False)
                    self._sel_title = False
                    self._sel = cell
                    self.setFocus()
                    self.update()
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resize_col is not None:
            dx      = event.scenePos().x() - self._resize_start_x
            new_w   = max(COL_MIN_W, int(self._resize_orig_w + dx))
            if new_w != self._col_ws[self._resize_col]:
                self.prepareGeometryChange()
                self._col_ws[self._resize_col] = new_w
                # 如果剛好這欄有行內編輯器，同步調整寬度與位置
                if self._editor_cell is not None:
                    er, ec = self._editor_cell
                    if ec == self._resize_col and self._editor is not None:
                        self._editor.setFixedWidth(new_w)
                    if self._editor_proxy is not None:
                        self._editor_proxy.setPos(
                            self.mapToScene(QPointF(self._col_x(ec), self._row_y(er)))
                        )
                self.update()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._resize_col is not None and event.button() == Qt.MouseButton.LeftButton:
            self._resize_col = None
            # 還原可移動
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            lx = event.pos().x()
            ly = event.pos().y()
            if self._is_title_area(ly):
                self._open_title_editor()
                event.accept()
                return
            cell = self._cell_at(lx, ly)
            if cell is not None:
                self._open_editor(*cell)
                event.accept()
                return
        super().mouseDoubleClickEvent(event)

    # ── 鍵盤事件（TableItem 持有 focus 時） ───────────────────────────────────

    def keyPressEvent(self, event):
        key = event.key()

        # ── 主題欄選取中 ──────────────────────────────────────────────────────
        if self._sel_title and self._title_editor is None:
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_F2):
                self._open_title_editor()
                event.accept(); return
            if key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
                # 刪除整個 Table（利用 scene undo stack）
                if self.scene():
                    self.scene().clearSelection()
                    self.setSelected(True)
                    self.scene().delete_selected()
                event.accept(); return
            if key == Qt.Key.Key_Down:
                self._sel_title = False
                self._sel = (0, 0)
                self.update()
                event.accept(); return
            if key == Qt.Key.Key_Escape:
                self._sel_title = False
                self.clearFocus()
                self.update()
                event.accept(); return
            event.accept(); return   # 吃掉其他按鍵，不讓 canvas 誤判

        # ── 儲存格選取中（不在編輯模式）──────────────────────────────────────
        if self._sel is not None and self._editor_cell is None:
            r, c = self._sel
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_F2):
                self._open_editor(r, c)
                event.accept(); return
            if key == Qt.Key.Key_Up:
                if r > 0:
                    self._sel = (r - 1, c)
                elif r == 0:
                    # 從第一列上移 → 選取 title
                    self._sel = None
                    self._sel_title = True
                self.update()
                event.accept(); return
            if key == Qt.Key.Key_Down:
                if r + 1 < self._rows:
                    self._sel = (r + 1, c)
                    self.update()
                event.accept(); return
            if key == Qt.Key.Key_Left:
                if c > 0:
                    self._sel = (r, c - 1)
                    self.update()
                event.accept(); return
            if key == Qt.Key.Key_Right:
                if c + 1 < self._cols:
                    self._sel = (r, c + 1)
                    self.update()
                event.accept(); return
            if key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
                # 只清空儲存格文字
                self._cells[r][c] = ""
                self.update()
                event.accept(); return
            if key == Qt.Key.Key_Escape:
                self._sel = None
                self.clearFocus()
                self.update()
                event.accept(); return
            # 一般可列印字元 → 直接開始輸入（Excel 風格取代舊內容）
            text = event.text()
            ctrl = event.modifiers() & Qt.KeyboardModifier.ControlModifier
            if text and not ctrl:
                self._open_editor(r, c, initial_text=text)
                event.accept(); return

        super().keyPressEvent(event)

    # ── 焦點離開 ──────────────────────────────────────────────────────────────

    def focusOutEvent(self, event):
        # 編輯器開著時 focus 會移到 proxy，不清除選取
        if self._editor_cell is None and self._title_editor is None:
            self._sel = None
            self._sel_title = False
            self.update()
        super().focusOutEvent(event)

    # ── 資料格行內編輯器 ───────────────────────────────────────────────────────

    def _open_editor(self, row: int, col: int, initial_text: str | None = None):
        if self._editor_proxy is not None:
            self._close_editor(save=True, refocus=False)
        self._close_title_editor(save=True, refocus=False)

        self._editor_cell = (row, col)
        self._sel = (row, col)
        self._sel_title = False

        cw_ = self._col_ws[col]
        ch_ = self._row_hs[row]

        editor = _CellEditor()
        if initial_text is not None:
            # Excel 風格：直接取代舊內容
            editor.setText(initial_text)
            editor.setCursorPosition(len(initial_text))
        else:
            editor.setText(self._cells[row][col])
            editor.selectAll()

        editor.setFixedSize(cw_, ch_)
        editor.setStyleSheet(f"""
            QLineEdit {{
                background: {COLOR_BG_LIGHT};
                color: {COLOR_TEXT_PRIMARY};
                border: 2px solid {COLOR_ACCENT};
                font-family: '{FONT_FAMILY}';
                font-size: {CELL_FONT}px;
                padding: 0 4px;
            }}
        """)
        editor.installEventFilter(self._make_key_filter(row, col))

        proxy = QGraphicsProxyWidget()
        proxy.setWidget(editor)
        proxy.setPos(self.mapToScene(QPointF(self._col_x(col), self._row_y(row))))
        proxy.setZValue(self.zValue() + 10)
        if self.scene():
            self.scene().addItem(proxy)

        self._editor_proxy = proxy
        self._editor = editor
        editor.focus_lost.connect(lambda: self._close_editor(save=True, refocus=False))
        editor.setFocus()
        self.update()

    def _make_key_filter(self, row: int, col: int):
        table = self

        class _F(QObject):
            def eventFilter(self_, obj, event):
                if event.type() != event.Type.KeyPress:
                    return False
                key   = event.key()
                shift = event.modifiers() & Qt.KeyboardModifier.ShiftModifier

                if key == Qt.Key.Key_Escape:
                    table._close_editor(save=False, refocus=True)
                    return True
                if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Down):
                    table._close_editor(save=True, refocus=True)
                    nr = row + 1
                    if nr < table._rows:
                        table._open_editor(nr, col)
                    return True
                if key == Qt.Key.Key_Up:
                    table._close_editor(save=True, refocus=True)
                    nr = row - 1
                    if nr >= 0:
                        table._open_editor(nr, col)
                    else:
                        # 上移到 title
                        table._sel = None
                        table._sel_title = True
                        table.update()
                    return True
                if key == Qt.Key.Key_Tab:
                    table._close_editor(save=True, refocus=True)
                    if shift:
                        nc, nr = col - 1, row
                        if nc < 0:
                            nc = table._cols - 1
                            nr = row - 1
                        if nr >= 0:
                            table._open_editor(nr, nc)
                    else:
                        nc, nr = col + 1, row
                        if nc >= table._cols:
                            nc = 0
                            nr = row + 1
                        if nr < table._rows:
                            table._open_editor(nr, nc)
                    return True
                return False

        f = _F()
        self._key_filter = f
        return f

    def _close_editor(self, save: bool = True, refocus: bool = True):
        if self._closing_editor or self._editor_proxy is None:
            return
        self._closing_editor = True
        try:
            if save and self._editor_cell is not None:
                r, c = self._editor_cell
                if 0 <= r < self._rows and 0 <= c < self._cols:
                    self._cells[r][c] = self._editor.text()
            proxy = self._editor_proxy
            self._editor_proxy = None
            self._editor       = None
            self._editor_cell  = None
            if proxy.scene():
                proxy.scene().removeItem(proxy)
            proxy.deleteLater()
        finally:
            self._closing_editor = False
        if refocus:
            self.setFocus()
        self.update()

    # ── 主題欄編輯器 ───────────────────────────────────────────────────────────

    def _open_title_editor(self):
        if self._title_editor is not None:
            return
        self._close_editor(save=True, refocus=False)

        tw = self._total_w()
        editor = _CellEditor()
        editor.setText(self._title)
        editor.selectAll()
        editor.setFixedSize(int(tw), TITLE_H)
        editor.setStyleSheet(f"""
            QLineEdit {{
                background: {COLOR_BG_LIGHT};
                color: {COLOR_TEXT_PRIMARY};
                border: 2px solid {COLOR_ACCENT};
                font-family: '{FONT_FAMILY}';
                font-size: {TITLE_FONT}px;
                font-weight: bold;
                padding: 0 8px;
            }}
        """)

        proxy = QGraphicsProxyWidget()
        proxy.setWidget(editor)
        proxy.setPos(self.mapToScene(QPointF(0, 0)))
        proxy.setZValue(self.zValue() + 10)
        if self.scene():
            self.scene().addItem(proxy)

        self._title_proxy  = proxy
        self._title_editor = editor
        editor.returnPressed.connect(lambda: self._close_title_editor(save=True,  refocus=True))
        editor.focus_lost.connect(   lambda: self._close_title_editor(save=True,  refocus=False))
        editor.setFocus()
        self.update()

    def _close_title_editor(self, save: bool = True, refocus: bool = True):
        if self._closing_title or self._title_editor is None:
            return
        self._closing_title = True
        try:
            if save:
                self._title = self._title_editor.text()
            proxy = self._title_proxy
            self._title_proxy  = None
            self._title_editor = None
            if proxy.scene():
                proxy.scene().removeItem(proxy)
            proxy.deleteLater()
        finally:
            self._closing_title = False
        if refocus:
            self.setFocus()
        self.update()

    # ── 序列化 ────────────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        pos = self.pos()
        return {
            "type":    self.TYPE_NAME,
            "x":       pos.x(),
            "y":       pos.y(),
            "rows":    self._rows,
            "cols":    self._cols,
            "title":   self._title,
            "col_ws":  self._col_ws[:],   # 儲存各欄寬度
            "cells":   [row[:] for row in self._cells],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TableItem":
        item = cls(d.get("rows", 3), d.get("cols", 3))
        item.setPos(d.get("x", 0.0), d.get("y", 0.0))
        item._title = d.get("title", "")
        # 還原各欄寬度（舊檔沒有此欄位則維持預設）
        saved_ws = d.get("col_ws", [])
        for c, w in enumerate(saved_ws):
            if c < item._cols:
                item._col_ws[c] = max(COL_MIN_W, int(w))
        for r, row_data in enumerate(d.get("cells", [])):
            for c, text in enumerate(row_data):
                if r < item._rows and c < item._cols:
                    item._cells[r][c] = text
        return item


# ── 輔助：欄位字母標籤（A, B, …, Z, AA, AB…）─────────────────────────────────

def _col_label(c: int) -> str:
    label = ""
    while True:
        label = chr(ord("A") + (c % 26)) + label
        c = c // 26 - 1
        if c < 0:
            break
    return label
