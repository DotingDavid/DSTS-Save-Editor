"""Drag-and-drop skill tree layout editor.

Standalone dev tool for arranging skill tree nodes on a 10x10 grid
per category to match the in-game layout. Saves to JSON.
"""

import os
import json

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QGridLayout, QFrame, QScrollArea,
                              QWidget, QTabWidget, QMessageBox, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QSize, QPoint, QRect
from PyQt6.QtGui import (QDrag, QPixmap, QPainter, QColor, QCursor, QPen,
                           QFont)

from ui.style import (ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_VALUE,
                       BORDER, BG_INPUT, BG_HOVER)
from save_data import get_tamer_skill_catalog
from app_paths import get_data_dir

GRID_ROWS = 10
GRID_COLS = 10
CELL_SIZE = 52
CELL_SPACING = 12
ROOT_SIZE = CELL_SIZE * 2 + CELL_SPACING
PALETTE_ICON = 44
LAYOUT_FILE = "skill_tree_layout.json"

CAT_COLORS = {
    1: "#E57373", 2: "#CE93D8", 3: "#81C784",
    4: "#4FC3F7", 5: "#FFD54F",
}
CAT_NAMES = {
    1: "Valor", 2: "Philanthropy", 3: "Amicability",
    4: "Wisdom", 5: "Loyalty",
}
ROOT_ICON_FILES = {
    1: "root_valor.png",
    2: "root_philanthropy.png",
    3: "root_amicability.png",
    4: "root_wisdom.png",
    5: "root_loyalty.png",
}

_FALLBACK_ICON = '005'
_icon_cache = {}
_skill_icon_map = None


def _get_skill_icon_map():
    global _skill_icon_map
    if _skill_icon_map is None:
        import json
        path = os.path.join(get_data_dir(), "skill_icon_map.json")
        try:
            with open(path) as f:
                _skill_icon_map = json.load(f)
        except Exception:
            _skill_icon_map = {}
    return _skill_icon_map


def _load_icon_for_skill(skill_id, size=32):
    key = ('skill', skill_id, size)
    if key in _icon_cache:
        return _icon_cache[key]
    icon_dir = os.path.join(get_data_dir(), "tamerskill_icons")
    icon_num = _get_skill_icon_map().get(str(skill_id), _FALLBACK_ICON)
    path = os.path.join(icon_dir, f"ui_icon_tamerskill_{icon_num}.png")
    if not os.path.exists(path):
        path = os.path.join(icon_dir, f"ui_icon_tamerskill_{_FALLBACK_ICON}.png")
    pm = QPixmap(path)
    if not pm.isNull():
        pm = pm.scaled(QSize(size, size),
                       Qt.AspectRatioMode.KeepAspectRatio,
                       Qt.TransformationMode.SmoothTransformation)
    _icon_cache[key] = pm
    return pm


def _load_root_icon(cat_id, size=64):
    key = ('root', cat_id, size)
    if key in _icon_cache:
        return _icon_cache[key]
    icon_dir = os.path.join(get_data_dir(), "tamerskill_icons")
    fname = ROOT_ICON_FILES.get(cat_id, "ui_icon_tamerskill_006.png")
    path = os.path.join(icon_dir, fname)
    pm = QPixmap(path)
    if not pm.isNull():
        pm = pm.scaled(QSize(size, size),
                       Qt.AspectRatioMode.KeepAspectRatio,
                       Qt.TransformationMode.SmoothTransformation)
    _icon_cache[key] = pm
    return pm


def get_layout_path():
    return os.path.join(get_data_dir(), LAYOUT_FILE)


def load_skill_layout():
    path = get_layout_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r') as f:
            raw = json.load(f)
        result = {}
        for cat_str, placements in raw.items():
            cat_id = int(cat_str)
            result[cat_id] = {}
            for skill_str, pos in placements.items():
                result[cat_id][int(skill_str)] = tuple(pos)
        return result
    except Exception:
        return None


def save_skill_layout(layout):
    path = get_layout_path()
    raw = {}
    for cat_id, placements in layout.items():
        raw[str(cat_id)] = {str(k): list(v) for k, v in placements.items()}
    with open(path, 'w') as f:
        json.dump(raw, f, indent=2)


# ── Grid Cell ────────────────────────────────────────────────────────

class _GridCell(QFrame):
    """Single cell on the layout grid."""

    cell_clicked = pyqtSignal(int, int)

    def __init__(self, row, col, cat_id=1, large=False, parent=None):
        super().__init__(parent)
        self.grid_row = row
        self.grid_col = col
        self.skill_id = None
        self.skill_info = None
        self._cat_id = cat_id
        self._cat_color = CAT_COLORS.get(cat_id, "#888")
        self._large = large

        sz = ROOT_SIZE if large else CELL_SIZE
        self.setFixedSize(sz, sz)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAcceptDrops(True)
        self._update_style()

    def set_skill(self, skill_id, info):
        self.skill_id = skill_id
        self.skill_info = info
        self._update_style()
        desc = info.get('description', '') if info else ''
        cost = info.get('tp_cost', 0) if info else 0
        name_en = info.get('name_en', '') if info else ''
        title = f"<b>{name_en}</b>" if name_en else f"<b>Skill {skill_id}</b>"
        self.setToolTip(
            f"{title}  ({cost} TP)<br>"
            f"<span style='color:#ccc'>{desc}</span>")
        self.update()

    def clear_skill(self):
        self.skill_id = None
        self.skill_info = None
        self.setToolTip("")
        self._update_style()
        self.update()

    def _update_style(self):
        if self.skill_id is not None:
            bw = 2 if self._large else 1
            rad = 6 if self._large else 4
            self.setStyleSheet(f"""
                QFrame {{
                    background: {self._cat_color};
                    border: {bw}px solid rgba(255,255,255,0.4);
                    border-radius: {rad}px;
                }}
                QFrame:hover {{ border-color: white; }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame {{
                    background: rgba(255,255,255,0.03);
                    border: 1px dashed rgba(255,255,255,0.1);
                    border-radius: 4px;
                }}
                QFrame:hover {{
                    background: rgba(255,255,255,0.06);
                    border-color: rgba(255,255,255,0.25);
                }}
            """)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.skill_id is None or not self.skill_info:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        is_root = self.skill_id in (1, 51, 101, 151, 201)

        if is_root:
            pm = _load_root_icon(self._cat_id, 72 if self._large else 36)
        else:
            icon_sz = 56 if self._large else 36
            pm = _load_icon_for_skill(self.skill_id, icon_sz)

        if pm and not pm.isNull():
            x = (self.width() - pm.width()) // 2
            y = (self.height() - pm.height()) // 2 - 4
            p.drawPixmap(x, y, pm)

        # Digimon requirement at bottom-right (matches game display)
        req = self.skill_info.get('digimon_req', 0) if self.skill_info else 0
        if req and not is_root:
            p.setPen(QColor(255, 255, 255, 220))
            font = p.font()
            font.setPointSize(7 if not self._large else 9)
            font.setBold(True)
            p.setFont(font)
            h = 12 if not self._large else 16
            text_rect = QRect(0, self.height() - h - 1, self.width() - 3, h)
            p.drawText(text_rect, Qt.AlignmentFlag.AlignRight |
                       Qt.AlignmentFlag.AlignTop, str(req))

        p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.skill_id is not None:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(str(self.skill_id))
            drag.setMimeData(mime)
            pm = QPixmap(self.size())
            self.render(pm)
            drag.setPixmap(pm)
            drag.setHotSpot(QPoint(self.width() // 2, self.height() // 2))
            drag.exec(Qt.DropAction.MoveAction)
        else:
            self.cell_clicked.emit(self.grid_row, self.grid_col)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
            self._dropped_id = int(event.mimeData().text())
            self.cell_clicked.emit(self.grid_row, self.grid_col)


# ── Palette Icon Tile ────────────────────────────────────────────────

class _PaletteTile(QFrame):
    """Draggable icon tile in the palette."""

    def __init__(self, skill_info, cat_id, parent=None):
        super().__init__(parent)
        self._info = skill_info
        self._cat_id = cat_id
        self._cat_color = CAT_COLORS.get(cat_id, "#888")
        self._is_root = skill_info.get('effect_type_id') == 33

        self.setFixedSize(PALETTE_ICON, PALETTE_ICON)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

        desc = skill_info.get('description', '')
        cost = skill_info.get('tp_cost', 0)
        name_en = skill_info.get('name_en', '')
        root_tag = "ROOT  |  " if self._is_root else ""
        title = f"<b>{root_tag}{name_en}</b>" if name_en else f"<b>{root_tag}Skill {skill_info['id']}</b>"
        self.setToolTip(
            f"{title}  ({cost} TP)<br>"
            f"<span style='color:#ccc'>{desc}</span>")

        self.setStyleSheet(f"""
            QFrame {{
                background: {self._cat_color};
                border: 1px solid rgba(255,255,255,0.3);
                border-radius: 4px;
            }}
            QFrame:hover {{ border-color: white; }}
        """)

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._is_root:
            pm = _load_root_icon(self._cat_id, 30)
        else:
            pm = _load_icon_for_skill(self._info['id'], 30)

        if pm and not pm.isNull():
            x = (self.width() - pm.width()) // 2
            y = (self.height() - pm.height()) // 2 - 3
            p.drawPixmap(x, y, pm)

        # Digimon requirement at bottom-right
        req = self._info.get('digimon_req', 0)
        if req and not self._is_root:
            p.setPen(QColor(255, 255, 255, 220))
            font = p.font()
            font.setPointSize(6)
            font.setBold(True)
            p.setFont(font)
            text_rect = QRect(0, self.height() - 11, self.width() - 2, 11)
            p.drawText(text_rect, Qt.AlignmentFlag.AlignRight |
                       Qt.AlignmentFlag.AlignTop, str(req))

        p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(str(self._info['id']))
            drag.setMimeData(mime)
            pm = QPixmap(self.size())
            self.render(pm)
            drag.setPixmap(pm)
            drag.setHotSpot(QPoint(self.width() // 2, self.height() // 2))
            drag.exec(Qt.DropAction.MoveAction)


# ── Category Tab ─────────────────────────────────────────────────────

class _CategoryTab(QWidget):
    """Layout editor for one category."""

    def __init__(self, cat_id, skills, existing_layout=None, parent=None):
        super().__init__(parent)
        self._cat_id = cat_id
        self._skills = skills
        self._cat_color = CAT_COLORS[cat_id]
        self._cells = {}
        self._blocked = set()
        self._root_cells = {}
        self._placement = {}
        self._grid_layout = None

        self._build(existing_layout)

    def _is_root(self, info):
        return info and info.get('id') in (1, 51, 101, 151, 201)

    def _build(self, existing_layout):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        # ── Grid ──
        grid_container = QWidget()
        grid_container.setStyleSheet("background: transparent;")
        self._grid_container = grid_container

        orig_paint = grid_container.paintEvent
        def _paint(event):
            orig_paint(event)
            self._paint_lines()
        grid_container.paintEvent = _paint

        gl = QGridLayout(grid_container)
        gl.setSpacing(CELL_SPACING)
        gl.setContentsMargins(12, 12, 12, 12)
        self._grid_layout = gl

        for r in range(GRID_ROWS):
            gl.setRowMinimumHeight(r, CELL_SIZE)
            gl.setRowStretch(r, 0)
            for c in range(GRID_COLS):
                if r == 0:
                    gl.setColumnMinimumWidth(c, CELL_SIZE)
                    gl.setColumnStretch(c, 0)
                cell = _GridCell(r, c, self._cat_id)
                cell.cell_clicked.connect(self._on_cell_action)
                gl.addWidget(cell, r, c)
                self._cells[(r, c)] = cell

        grid_container.setSizePolicy(QSizePolicy.Policy.Fixed,
                                     QSizePolicy.Policy.Fixed)
        layout.addWidget(grid_container)
        layout.addStretch()

        # ── Palette (icon grid) ──
        palette = QWidget()
        palette.setSizePolicy(QSizePolicy.Policy.Expanding,
                              QSizePolicy.Policy.Preferred)
        palette.setStyleSheet("background: transparent;")
        pl = QVBoxLayout(palette)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.setSpacing(4)

        pl_header = QLabel("Drag to grid:")
        pl_header.setStyleSheet(
            f"color: {ACCENT}; font-size: 10px; font-weight: bold;")
        pl.addWidget(pl_header)

        self._palette_scroll = QScrollArea()
        self._palette_scroll.setWidgetResizable(True)
        self._palette_scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }")

        self._palette_widget = QWidget()
        self._palette_widget.setStyleSheet("background: transparent;")
        self._palette_grid = QGridLayout(self._palette_widget)
        self._palette_grid.setSpacing(4)
        self._palette_grid.setContentsMargins(4, 4, 4, 4)

        self._palette_scroll.setWidget(self._palette_widget)
        pl.addWidget(self._palette_scroll)

        layout.addWidget(palette)

        # Place existing layout or auto-place root at center
        placed_ids = set()
        if existing_layout:
            for skill_id, (r, c) in existing_layout.items():
                info = next((s for s in self._skills if s['id'] == skill_id), None)
                if info and 0 <= r < GRID_ROWS and 0 <= c < GRID_COLS:
                    self._do_place(skill_id, info, r, c)
                    placed_ids.add(skill_id)
        else:
            # Auto-place root at center
            root = next((s for s in self._skills if self._is_root(s)), None)
            if root:
                self._do_place(root['id'], root, 4, 4)
                placed_ids.add(root['id'])

        self._rebuild_palette(placed_ids)

    def _do_place(self, skill_id, info, row, col):
        is_root = self._is_root(info)

        if is_root and row + 1 < GRID_ROWS and col + 1 < GRID_COLS:
            for dr in range(2):
                for dc in range(2):
                    pos = (row + dr, col + dc)
                    cell = self._cells.get(pos)
                    if cell:
                        if cell.skill_id is not None:
                            del self._placement[cell.skill_id]
                            cell.clear_skill()
                        cell.hide()
                    self._blocked.add(pos)

            root_cell = _GridCell(row, col, self._cat_id, large=True)
            root_cell.set_skill(skill_id, info)
            root_cell.cell_clicked.connect(self._on_cell_action)
            self._grid_layout.addWidget(root_cell, row, col, 2, 2)
            self._root_cells[skill_id] = root_cell
        else:
            cell = self._cells.get((row, col))
            if cell:
                cell.set_skill(skill_id, info)

        self._placement[skill_id] = (row, col)

    def _do_remove(self, skill_id):
        if skill_id not in self._placement:
            return
        row, col = self._placement[skill_id]
        info = next((s for s in self._skills if s['id'] == skill_id), None)
        is_root = self._is_root(info)

        if is_root and skill_id in self._root_cells:
            root_cell = self._root_cells.pop(skill_id)
            self._grid_layout.removeWidget(root_cell)
            root_cell.deleteLater()
            for dr in range(2):
                for dc in range(2):
                    pos = (row + dr, col + dc)
                    self._blocked.discard(pos)
                    cell = self._cells.get(pos)
                    if cell:
                        cell.show()
        else:
            cell = self._cells.get((row, col))
            if cell:
                cell.clear_skill()

        del self._placement[skill_id]

    def _rebuild_palette(self, placed_ids=None):
        if placed_ids is None:
            placed_ids = set(self._placement.keys())

        while self._palette_grid.count() > 0:
            item = self._palette_grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        unplaced = [s for s in self._skills if s['id'] not in placed_ids]
        PCOLS = 7
        for i, info in enumerate(unplaced):
            tile = _PaletteTile(info, self._cat_id)
            self._palette_grid.addWidget(tile, i // PCOLS, i % PCOLS)

    def _on_cell_action(self, row, col):
        cell = self._cells.get((row, col))

        # Check for drop on this cell
        dropped_id = None
        if cell and hasattr(cell, '_dropped_id'):
            dropped_id = cell._dropped_id
            del cell._dropped_id
        # Check root cells for drops too
        for sid, rc in self._root_cells.items():
            if hasattr(rc, '_dropped_id'):
                dropped_id = rc._dropped_id
                del rc._dropped_id
                break

        if dropped_id is not None:
            self._move_skill(dropped_id, row, col)
            return

        if (row, col) in self._blocked:
            return

    def _move_skill(self, skill_id, to_row, to_col):
        info = next((s for s in self._skills if s['id'] == skill_id), None)
        if not info:
            return

        is_root = self._is_root(info)

        if (to_row, to_col) in self._blocked:
            return
        if is_root and (to_row + 1 >= GRID_ROWS or to_col + 1 >= GRID_COLS):
            return

        # Displace existing
        target_cell = self._cells.get((to_row, to_col))
        if target_cell and target_cell.skill_id is not None:
            self._do_remove(target_cell.skill_id)

        if skill_id in self._placement:
            self._do_remove(skill_id)

        self._do_place(skill_id, info, to_row, to_col)
        self._rebuild_palette()
        self._grid_container.update()

    def _paint_lines(self):
        p = QPainter(self._grid_container)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(self._cat_color))
        pen.setWidth(2)
        pen.setColor(QColor(255, 255, 255, 60))
        p.setPen(pen)

        id_to_center = {}
        for sid, (r, c) in self._placement.items():
            info = next((s for s in self._skills if s['id'] == sid), None)
            if self._is_root(info) and sid in self._root_cells:
                id_to_center[sid] = self._root_cells[sid].geometry().center()
            else:
                cell = self._cells.get((r, c))
                if cell and cell.isVisible():
                    id_to_center[sid] = cell.geometry().center()

        for skill in self._skills:
            sid = skill['id']
            prereq = skill.get('prerequisite', 0)
            if prereq and prereq in id_to_center and sid in id_to_center:
                p.drawLine(id_to_center[sid], id_to_center[prereq])

        p.end()

    def get_placement(self):
        return dict(self._placement)


# ── Main Dialog ──────────────────────────────────────────────────────

class SkillLayoutEditor(QDialog):

    def __init__(self, save_file=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ANAMNESIS — Skill Tree Layout Editor")
        self.setMinimumSize(1200, 780)
        self.setStyleSheet(f"""
            QDialog {{ background: #0C0C14; color: {TEXT_PRIMARY}; }}
            QLabel {{ color: {TEXT_PRIMARY}; }}
        """)

        self._tabs = {}
        self._changed = False

        existing = load_skill_layout() or {}
        catalog = get_tamer_skill_catalog()

        cat_skills = {1: [], 2: [], 3: [], 4: [], 5: []}
        for skill in catalog:
            tg = skill['tree_group']
            if 1 <= tg <= 50:
                cat_skills[1].append(skill)
            elif 51 <= tg <= 100:
                cat_skills[2].append(skill)
            elif 101 <= tg <= 150:
                cat_skills[3].append(skill)
            elif 151 <= tg <= 200:
                cat_skills[4].append(skill)
            elif 201 <= tg <= 224:
                cat_skills[5].append(skill)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        instr = QLabel(
            "Drag skill tiles from the palette onto the grid to match the "
            "in-game layout. Root skills are 2x2 and auto-placed at center. "
            "Prerequisite lines appear as you place skills.")
        instr.setWordWrap(True)
        instr.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 11px; padding: 4px;")
        layout.addWidget(instr)

        tabs = QTabWidget()
        for cat_id in [1, 2, 3, 4, 5]:
            skills = cat_skills[cat_id]
            ex = existing.get(cat_id, {})
            tab = _CategoryTab(cat_id, skills, ex)
            tabs.addTab(tab, f"  {CAT_NAMES[cat_id]} ({len(skills)})  ")
            self._tabs[cat_id] = tab
        layout.addWidget(tabs, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        save_btn = QPushButton("Save Layout")
        save_btn.setFixedHeight(32)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(0,191,255,0.1); color: {ACCENT};
                border: 1px solid {ACCENT}; border-radius: 4px;
                font-size: 12px; font-weight: bold; padding: 0 24px;
            }}
            QPushButton:hover {{ background: rgba(0,191,255,0.2); }}
        """)
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)

        close_btn = QPushButton("Close")
        close_btn.setFixedHeight(32)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: {BG_INPUT}; color: {TEXT_PRIMARY};
                border: 1px solid {BORDER}; border-radius: 4px;
                font-size: 12px; padding: 0 20px;
            }}
            QPushButton:hover {{ border-color: {ACCENT}; color: {ACCENT}; }}
        """)
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)

    def _save(self):
        result = {}
        total = 0
        for cat_id, tab in self._tabs.items():
            placement = tab.get_placement()
            if placement:
                result[cat_id] = placement
                total += len(placement)

        save_skill_layout(result)
        self._changed = True
        QMessageBox.information(
            self, "Saved",
            f"Layout saved with {total} skills placed.\n\n"
            f"File: {get_layout_path()}")

    @property
    def changed(self):
        return self._changed
