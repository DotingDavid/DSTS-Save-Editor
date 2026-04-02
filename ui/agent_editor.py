"""Agent/Player data editor.

Edit money, Tamer Points, agent rank, and manage individual agent skills
with a visual skill tree grid. Horizontal tabs per category, hover for
details, click to toggle buy/refund with prerequisite enforcement.
"""

import os

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLabel,
                              QSpinBox, QFrame, QHBoxLayout,
                              QPushButton, QMessageBox, QLineEdit,
                              QScrollArea, QSizePolicy, QGridLayout,
                              QTabWidget)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QRect
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen

from ui.style import (ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_VALUE,
                       BORDER, BG_INPUT, PERS_COLORS)
from save_data import get_tamer_skill_catalog, _get_skill_id_to_index
from app_paths import get_data_dir
from ui.skill_layout_editor import load_skill_layout

CATEGORIES = {
    1: ("Valor",        0x068),
    2: ("Philanthropy", 0x06C),
    3: ("Amicability",  0x070),
    4: ("Wisdom",       0x074),
    5: ("Loyalty",      0x080),
}

CAT_COLORS = {
    1: "#E57373", 2: "#CE93D8", 3: "#81C784",
    4: "#4FC3F7", 5: "#C88A14",
}

CELL_SIZE = 54
CELL_SPACING = 8
ROOT_IDS = {1, 51, 101, 151, 201}

_FALLBACK_ICON = '005'
_icon_cache = {}
_skill_icon_map = None

ROOT_ICON_FILES = {
    1: "root_valor.png", 2: "root_philanthropy.png",
    3: "root_amicability.png", 4: "root_wisdom.png",
    5: "root_loyalty.png",
}


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


def _load_skill_icon(skill_id, size=28):
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
        pm = pm.scaled(QSize(size, size), Qt.AspectRatioMode.KeepAspectRatio,
                       Qt.TransformationMode.SmoothTransformation)
    _icon_cache[key] = pm
    return pm


def _load_root_icon(cat_id, size=64):
    key = ('root', cat_id, size)
    if key in _icon_cache:
        return _icon_cache[key]
    icon_dir = os.path.join(get_data_dir(), "tamerskill_icons")
    fname = ROOT_ICON_FILES.get(cat_id, "root_valor.png")
    pm = QPixmap(os.path.join(icon_dir, fname))
    if not pm.isNull():
        pm = pm.scaled(QSize(size, size), Qt.AspectRatioMode.KeepAspectRatio,
                       Qt.TransformationMode.SmoothTransformation)
    _icon_cache[key] = pm
    return pm


# ── Skill Grid & Cell ────────────────────────────────────────────────

class _SkillTreeGrid(QWidget):
    """Draws prerequisite lines behind cells."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._connections = []

    def set_connections(self, connections):
        self._connections = connections

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._connections:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor(255, 255, 255, 40), 2))
        for child_w, parent_w in self._connections:
            if child_w.isVisible() and parent_w.isVisible():
                p.drawLine(child_w.geometry().center(),
                           parent_w.geometry().center())
        p.end()


class _SkillCell(QPushButton):
    """Single skill node. Click to toggle, hover for info."""

    skill_clicked = pyqtSignal(int)
    skill_hovered = pyqtSignal(int)

    def __init__(self, skill_index, info, purchased, cat_color,
                 cat_id=1, large=False, parent=None):
        super().__init__(parent)
        self._skill_index = skill_index
        self._info = info
        self._purchased = purchased
        self._cat_color = cat_color
        self._cat_id = cat_id
        self._large = large

        sz = CELL_SIZE * 2 + CELL_SPACING if large else CELL_SIZE
        self.setFixedSize(sz, sz)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(lambda: self.skill_clicked.emit(self._skill_index))
        self._apply_style()

    def set_purchased(self, p):
        self._purchased = p
        self._apply_style()
        self.update()

    def _apply_style(self):
        c = self._cat_color
        if self._purchased:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {c};
                    border: 1px solid rgba(255,255,255,0.3);
                    border-radius: {6 if self._large else 4}px;
                }}
                QPushButton:hover {{ border: 2px solid white; }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: rgba(40,40,60,0.8);
                    border: 1px solid rgba(255,255,255,0.08);
                    border-radius: {6 if self._large else 4}px;
                }}
                QPushButton:hover {{ border: 1px solid {c}; }}
            """)

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        sid = self._info.get('id', self._skill_index + 1)
        is_root = sid in ROOT_IDS
        if is_root:
            pm = _load_root_icon(self._cat_id, 56 if self._large else 32)
        else:
            pm = _load_skill_icon(sid, 56 if self._large else 32)
        if not self._purchased:
            p.setOpacity(0.3)
        if pm and not pm.isNull():
            x = (self.width() - pm.width()) // 2
            y = (self.height() - pm.height()) // 2
            p.drawPixmap(x, y, pm)
        p.end()

    def enterEvent(self, event):
        super().enterEvent(event)
        self.skill_hovered.emit(self._skill_index)


# ── Category Tab ─────────────────────────────────────────────────────

class _CategoryTab(QWidget):
    """One skill tree: grid on left, detail panel on right."""

    data_changed = pyqtSignal()

    def __init__(self, cat_id, parent=None):
        super().__init__(parent)
        self._cat_id = cat_id
        self._cat_color = CAT_COLORS[cat_id]
        self._save_file = None
        self._skill_cells = {}
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(10)

        # Grid area (left)
        self._grid_scroll = QScrollArea()
        self._grid_scroll.setWidgetResizable(True)
        self._grid_scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }")
        layout.addWidget(self._grid_scroll, 7)

        # Detail panel (right)
        detail = QFrame()
        detail.setStyleSheet(
            "QFrame#detailPanel { background: #1A1A2E; "
            "border: 1px solid rgba(255,255,255,0.06); border-radius: 6px; }")
        detail.setObjectName("detailPanel")
        dl = QVBoxLayout(detail)
        dl.setContentsMargins(16, 16, 16, 16)
        dl.setSpacing(10)

        self._d_placeholder = QLabel("Hover a skill\nto view details")
        self._d_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._d_placeholder.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 11px; background: transparent;")
        dl.addWidget(self._d_placeholder)

        self._d_icon = QLabel()
        self._d_icon.setFixedSize(72, 72)
        self._d_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._d_icon.setVisible(False)
        dl.addWidget(self._d_icon, 0, Qt.AlignmentFlag.AlignHCenter)

        self._d_name = QLabel()
        self._d_name.setWordWrap(True)
        self._d_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._d_name.setStyleSheet(
            f"color: {TEXT_VALUE}; font-size: 14px; font-weight: bold; "
            "background: transparent;")
        self._d_name.setVisible(False)
        dl.addWidget(self._d_name)

        self._d_cost = QLabel()
        self._d_cost.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._d_cost.setStyleSheet(
            f"color: {self._cat_color}; font-size: 12px; font-weight: bold; "
            "background: transparent;")
        self._d_cost.setVisible(False)
        dl.addWidget(self._d_cost)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {BORDER};")
        self._d_sep = sep
        sep.setVisible(False)
        dl.addWidget(sep)

        self._d_desc = QLabel()
        self._d_desc.setWordWrap(True)
        self._d_desc.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 10px; "
            "background: transparent; line-height: 140%;")
        self._d_desc.setVisible(False)
        dl.addWidget(self._d_desc)

        dl.addStretch()

        self._d_prereq = QLabel()
        self._d_prereq.setWordWrap(True)
        self._d_prereq.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 9px; "
            "background: transparent;")
        self._d_prereq.setVisible(False)
        dl.addWidget(self._d_prereq)

        # Unlock/Refund row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)

        unlock_btn = QPushButton("Unlock All")
        unlock_btn.setFixedHeight(24)
        unlock_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        unlock_btn.setToolTip("Free unlock — no TP cost")
        unlock_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {TEXT_SECONDARY};
                border: 1px solid {BORDER}; border-radius: 3px;
                font-size: 9px; padding: 0 10px;
            }}
            QPushButton:hover {{ color: {self._cat_color}; border-color: {self._cat_color}; }}
        """)
        unlock_btn.clicked.connect(self._unlock_all_cat)
        btn_row.addWidget(unlock_btn)

        refund_btn = QPushButton("Refund All")
        refund_btn.setFixedHeight(24)
        refund_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refund_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {TEXT_SECONDARY};
                border: 1px solid {BORDER}; border-radius: 3px;
                font-size: 9px; padding: 0 10px;
            }}
            QPushButton:hover {{ color: #EF5350; border-color: #EF5350; }}
        """)
        refund_btn.clicked.connect(self._refund_all_cat)
        btn_row.addWidget(refund_btn)

        dl.addLayout(btn_row)

        layout.addWidget(detail, 3)

    def set_save_file(self, save_file):
        self._save_file = save_file
        self._build_grid()

    def _build_grid(self):
        self._skill_cells.clear()
        if not self._save_file:
            return

        catalog = get_tamer_skill_catalog()
        saved = load_skill_layout() or {}
        cat_layout_map = saved.get(self._cat_id, {})

        cat_skills = []
        for i in range(208):
            _, cat, purchased, _ = self._save_file.read_agent_skill(i)
            if cat == self._cat_id:
                cat_skills.append({
                    'index': i, 'purchased': purchased,
                    'catalog': catalog[i] if i < len(catalog) else {},
                })

        grid_widget = _SkillTreeGrid()
        grid_widget.setStyleSheet("background: transparent;")
        gl = QGridLayout(grid_widget)
        gl.setSpacing(CELL_SPACING)
        gl.setContentsMargins(6, 6, 6, 6)

        for r in range(10):
            gl.setRowMinimumHeight(r, CELL_SIZE)
            gl.setRowStretch(r, 0)
        for c in range(10):
            gl.setColumnMinimumWidth(c, CELL_SIZE)
            gl.setColumnStretch(c, 0)

        id_to_cell = {}

        if cat_layout_map:
            for skill in cat_skills:
                info = skill['catalog']
                sid = info.get('id', skill['index'] + 1)
                pos = cat_layout_map.get(sid)
                if pos:
                    r, c = pos
                    is_root = sid in ROOT_IDS
                    cell = _SkillCell(
                        skill['index'], info, skill['purchased'],
                        self._cat_color, self._cat_id, large=is_root)
                    cell.skill_clicked.connect(self._on_click)
                    cell.skill_hovered.connect(self._on_hover)
                    if is_root:
                        gl.addWidget(cell, r, c, 2, 2)
                    else:
                        gl.addWidget(cell, r, c)
                    id_to_cell[sid] = cell
                    self._skill_cells[skill['index']] = cell
        else:
            COLS = 8
            for i, skill in enumerate(cat_skills):
                info = skill['catalog']
                sid = info.get('id', skill['index'] + 1)
                cell = _SkillCell(
                    skill['index'], info, skill['purchased'],
                    self._cat_color, self._cat_id)
                cell.skill_clicked.connect(self._on_click)
                cell.skill_hovered.connect(self._on_hover)
                gl.addWidget(cell, i // COLS, i % COLS)
                id_to_cell[sid] = cell
                self._skill_cells[skill['index']] = cell

        connections = []
        for skill in cat_skills:
            info = skill['catalog']
            sid = info.get('id', skill['index'] + 1)
            for key in ('prerequisite', 'prerequisite2'):
                prereq = info.get(key, 0)
                if prereq and prereq in id_to_cell and sid in id_to_cell:
                    connections.append((id_to_cell[sid], id_to_cell[prereq]))
        grid_widget.set_connections(connections)
        grid_widget.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self._grid_scroll.setWidget(grid_widget)
        self._grid_scroll.setAlignment(
            Qt.AlignmentFlag.AlignCenter)

    def _on_hover(self, skill_index):
        """Show detail panel info on hover."""
        catalog = get_tamer_skill_catalog()
        info = catalog[skill_index]
        sid = info.get('id', skill_index + 1)
        _, _, purchased, _ = self._save_file.read_agent_skill(skill_index)

        self._d_placeholder.setVisible(False)
        self._d_icon.setVisible(True)
        self._d_name.setVisible(True)
        self._d_cost.setVisible(True)
        self._d_sep.setVisible(True)
        self._d_desc.setVisible(True)
        self._d_prereq.setVisible(True)

        # Icon
        is_root = sid in ROOT_IDS
        if is_root:
            pm = _load_root_icon(self._cat_id, 56)
        else:
            pm = _load_skill_icon(sid, 56)
        if pm and not pm.isNull():
            self._d_icon.setPixmap(pm)
        bg = self._cat_color if purchased else '#2A2A3E'
        self._d_icon.setStyleSheet(
            f"background: {bg}; border-radius: 10px;")

        self._d_name.setText(info.get('name_en', f'Skill {sid}'))

        cost = info.get('tp_cost', 0)
        status = "Purchased" if purchased else "Locked"
        self._d_cost.setText(f"{cost} TP  \u2014  {status}")

        self._d_desc.setText(info.get('description', ''))

        prereq_lines = []
        id_to_idx = _get_skill_id_to_index()
        for key in ('prerequisite', 'prerequisite2'):
            pid = info.get(key, 0)
            pidx = id_to_idx.get(pid)
            if pid and pidx is not None:
                pi = catalog[pidx]
                pname = pi.get('name_en', f'Skill {pid}')
                _, _, pp, _ = self._save_file.read_agent_skill(pidx)
                mark = "\u2713" if pp else "\u2717"
                prereq_lines.append(f"{mark} {pname}")
        if prereq_lines:
            self._d_prereq.setText("Requires: " + "\n".join(prereq_lines))
        else:
            self._d_prereq.setText("")

    def _on_click(self, skill_index):
        """Toggle buy/refund on click."""
        if not self._save_file:
            return

        catalog = get_tamer_skill_catalog()
        info = catalog[skill_index]
        _, _, purchased, _ = self._save_file.read_agent_skill(skill_index)

        if purchased:
            # Check if any purchased skill depends on this one (either prereq)
            sid = info.get('id', skill_index + 1)
            for i in range(208):
                other = catalog[i]
                if other.get('prerequisite') == sid or other.get('prerequisite2') == sid:
                    _, _, other_purchased, _ = self._save_file.read_agent_skill(i)
                    if other_purchased:
                        dep_name = other.get('name_en', f'Skill {other["id"]}')
                        from ui.toast import show_toast
                        show_toast(self.window(),
                                   f"Can't refund \u2014 {dep_name} depends on this",
                                   "info")
                        return
            self._save_file.refund_agent_skill(skill_index)
        else:
            # Check both prerequisites
            id_to_idx = _get_skill_id_to_index()
            for prereq_key in ('prerequisite', 'prerequisite2'):
                prereq_id = info.get(prereq_key, 0)
                if prereq_id:
                    prereq_idx = id_to_idx.get(prereq_id)
                    if prereq_idx is not None:
                        _, _, pp, _ = self._save_file.read_agent_skill(prereq_idx)
                        if not pp:
                            pname = catalog[prereq_idx].get('name_en', '')
                            from ui.toast import show_toast
                            show_toast(self.window(),
                                       f"Requires: {pname}", "info")
                            return
            self._save_file.buy_agent_skill(skill_index)

        # Update cell
        cell = self._skill_cells.get(skill_index)
        if cell:
            _, _, new_p, _ = self._save_file.read_agent_skill(skill_index)
            cell.set_purchased(new_p)

        # Refresh hover detail
        self._on_hover(skill_index)
        self.data_changed.emit()

    def _unlock_all_cat(self):
        if not self._save_file:
            return
        name = CATEGORIES[self._cat_id][0]
        reply = QMessageBox.question(
            self, "Unlock",
            f"Unlock all {name} skills?\nFree — no TP cost.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        for i in range(208):
            _, cat, purchased, _ = self._save_file.read_agent_skill(i)
            if cat == self._cat_id and not purchased:
                self._save_file.write_agent_skill_flags(i, 1, 1, 1)
        _, count_off = CATEGORIES[self._cat_id]
        # Recount
        total = sum(1 for i in range(208)
                    if self._save_file.read_agent_skill(i)[1] == self._cat_id)
        self._save_file.write_agent_u32(count_off, total)
        self._build_grid()
        self.data_changed.emit()

    def _refund_all_cat(self):
        if not self._save_file:
            return
        catalog = get_tamer_skill_catalog()
        name = CATEGORIES[self._cat_id][0]
        total_tp = 0
        count = 0
        for i in range(208):
            _, cat, purchased, _ = self._save_file.read_agent_skill(i)
            if cat == self._cat_id and purchased:
                total_tp += catalog[i]['tp_cost']
                count += 1
        if count == 0:
            return
        reply = QMessageBox.question(
            self, "Refund",
            f"Refund {count} {name} skills?\n+{total_tp} TP returned.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        for i in range(208):
            _, cat, purchased, _ = self._save_file.read_agent_skill(i)
            if cat == self._cat_id and purchased:
                self._save_file.refund_agent_skill(i)
        self._build_grid()
        self.data_changed.emit()


# ── Main Agent Editor ────────────────────────────────────────────────

class AgentEditor(QWidget):
    """Edit player/agent data with tabbed visual skill trees."""

    data_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._save_file = None
        self._updating = False
        self._cat_tabs = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(4)

        # ── Compact top row: Name + Money + Rank ──
        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        name_lbl = QLabel("Name:")
        name_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 10px;")
        top_row.addWidget(name_lbl)
        self._name_edit = QLineEdit()
        self._name_edit.setMaxLength(30)
        self._name_edit.setFixedWidth(120)
        self._name_edit.setFixedHeight(24)
        self._name_edit.editingFinished.connect(self._on_name_changed)
        top_row.addWidget(self._name_edit)

        money_lbl = QLabel("Money:")
        money_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 10px;")
        top_row.addWidget(money_lbl)
        self._money_spin = QSpinBox()
        self._money_spin.setRange(0, 9_999_999)
        self._money_spin.setSingleStep(1000)
        self._money_spin.setPrefix("\u00a5 ")
        self._money_spin.setFixedWidth(140)
        self._money_spin.setFixedHeight(24)
        self._money_spin.valueChanged.connect(self._on_money_changed)
        top_row.addWidget(self._money_spin)

        self._rank_label = QLabel("Rank: \u2014")
        self._rank_label.setStyleSheet(
            f"color: {TEXT_VALUE}; font-size: 10px; font-weight: bold;")
        top_row.addWidget(self._rank_label)

        top_row.addStretch()
        layout.addLayout(top_row)

        # ── Agent Skills header with TP fields ──
        tree_header = QHBoxLayout()
        tree_header.setSpacing(10)
        lbl = QLabel("AGENT SKILLS")
        lbl.setStyleSheet(
            "color: rgba(0,191,255,0.5); font-size: 9px; font-weight: bold; "
            "letter-spacing: 3px;")
        tree_header.addWidget(lbl)

        tp_lbl = QLabel("TP:")
        tp_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 10px;")
        tree_header.addWidget(tp_lbl)
        self._tp_spin = QSpinBox()
        self._tp_spin.setRange(0, 999_999)
        self._tp_spin.setSingleStep(100)
        self._tp_spin.setFixedWidth(100)
        self._tp_spin.setFixedHeight(22)
        self._tp_spin.valueChanged.connect(self._on_tp_changed)
        tree_header.addWidget(self._tp_spin)

        avail_lbl = QLabel("Available:")
        avail_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 10px;")
        tree_header.addWidget(avail_lbl)
        self._tp_avail_spin = QSpinBox()
        self._tp_avail_spin.setRange(0, 999_999)
        self._tp_avail_spin.setSingleStep(100)
        self._tp_avail_spin.setFixedWidth(100)
        self._tp_avail_spin.setFixedHeight(22)
        self._tp_avail_spin.valueChanged.connect(self._on_tp_avail_changed)
        tree_header.addWidget(self._tp_avail_spin)
        tree_header.addStretch()

        unlock_all = QPushButton("Unlock All")
        unlock_all.setFixedHeight(22)
        unlock_all.setCursor(Qt.CursorShape.PointingHandCursor)
        unlock_all.setToolTip("Free unlock ALL skills — no TP cost")
        unlock_all.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {ACCENT};
                border: 1px solid {ACCENT}; border-radius: 3px;
                font-size: 9px; font-weight: bold; padding: 0 10px;
            }}
            QPushButton:hover {{ background: rgba(0,191,255,0.1); }}
        """)
        unlock_all.clicked.connect(self._unlock_all)
        tree_header.addWidget(unlock_all)

        refund_all = QPushButton("Refund All")
        refund_all.setFixedHeight(22)
        refund_all.setCursor(Qt.CursorShape.PointingHandCursor)
        refund_all.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {TEXT_SECONDARY};
                border: 1px solid {BORDER}; border-radius: 3px;
                font-size: 9px; padding: 0 10px;
            }}
            QPushButton:hover {{ color: #EF5350; border-color: #EF5350; }}
        """)
        refund_all.clicked.connect(self._refund_all)
        tree_header.addWidget(refund_all)

        layout.addLayout(tree_header)

        # Tabs
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(f"""
            QTabBar::tab {{
                padding: 6px 20px; font-size: 11px; font-weight: bold;
            }}
        """)

        for cat_id in [1, 2, 3, 4, 5]:
            name = CATEGORIES[cat_id][0]
            color = CAT_COLORS[cat_id]
            tab = _CategoryTab(cat_id)
            tab.data_changed.connect(self._on_cat_changed)
            self._cat_tabs[cat_id] = tab
            self._tabs.addTab(tab, f"  {name}  ")

        layout.addWidget(self._tabs, 1)

    def set_save_file(self, save_file):
        self._updating = True
        self._save_file = save_file

        self._name_edit.setText(save_file.read_str(0x0FDE90, 32))
        self._money_spin.setValue(save_file.read_agent_u32(0x058))
        self._tp_avail_spin.setValue(save_file.read_agent_u32(0x05C))
        self._tp_spin.setValue(save_file.read_agent_u32(0x060))
        self._rank_label.setText(f"Rank: {save_file.read_agent_u32(0x064)}")

        for tab in self._cat_tabs.values():
            tab.set_save_file(save_file)

        self._updating = False

    def _on_cat_changed(self):
        self._updating = True
        self._tp_avail_spin.setValue(self._save_file.read_agent_u32(0x05C))
        self._updating = False
        self.data_changed.emit()

    def _unlock_all(self):
        if not self._save_file:
            return
        reply = QMessageBox.question(
            self, "Unlock All",
            "Unlock ALL agent skills?\nFree — no TP cost.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        for tab in self._cat_tabs.values():
            tab._unlock_all_cat()

    def _refund_all(self):
        if not self._save_file:
            return
        catalog = get_tamer_skill_catalog()
        total = sum(catalog[i]['tp_cost'] for i in range(208)
                    if self._save_file.read_agent_skill(i)[2])
        count = sum(1 for i in range(208)
                    if self._save_file.read_agent_skill(i)[2])
        if not count:
            return
        reply = QMessageBox.question(
            self, "Refund All",
            f"Refund ALL {count} skills?\n+{total} TP returned.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        for tab in self._cat_tabs.values():
            tab._refund_all_cat()

    def _on_name_changed(self):
        if not self._updating and self._save_file:
            name = self._name_edit.text().strip()
            if name:
                self._save_file.write_player_name(name)
                self.data_changed.emit()

    def _on_money_changed(self, value):
        if not self._updating and self._save_file:
            self._save_file.write_agent_u32(0x058, value)
            self.data_changed.emit()

    def _on_tp_changed(self, value):
        if not self._updating and self._save_file:
            self._save_file.write_agent_u32(0x060, value)
            self.data_changed.emit()

    def _on_tp_avail_changed(self, value):
        if not self._updating and self._save_file:
            self._save_file.write_agent_u32(0x05C, value)
            self.data_changed.emit()
