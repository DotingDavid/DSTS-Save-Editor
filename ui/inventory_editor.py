"""Inventory / Items editor.

Browse all game items by category with icon grid, edit quantities,
add/remove items. Categories and sub-categories match the ANAMNESIS
companion app's Items panel.
"""

import os
import re
import logging
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QAbstractItemView, QMessageBox,
                              QFrame, QScrollArea, QGridLayout, QSpinBox)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QCursor, QFont, QFontMetrics, QPixmap

from ui.style import (ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_VALUE,
                       BG_INPUT, BG_PANEL, BORDER)
from app_paths import get_data_dir

logger = logging.getLogger(__name__)

# ── DB category → display name (matches ANAMNESIS) ──
ITEM_CATEGORIES = {
    0: "Recovery",
    1: "Stat Boost",
    2: "Gems",
    4: "Attachments",
    5: "Crafting Materials",
    6: "Farm",
    7: "Clothing",
    8: "Quest Items",
    9: "Digimon Cards",
    "eggs": "Evolution Items",
    "discs": "Attachment Skills",
    None: "Other",
}

_CAT_ORDER = [0, 1, "eggs", 2, 4, "discs", 5, 6, 7, 8, None]

_CAT_COLORS = {
    0: "#66BB6A",   # Recovery — green
    1: "#FFA726",   # Stat Boost — orange
    2: "#AB47BC",   # Gems — purple
    4: "#00BFFF",   # Attachments — cyan
    5: "#FFEE58",   # Crafting Materials — yellow
    6: "#EC407A",   # Food — pink
    7: "#42A5F5",   # Clothing — blue
    8: "#78909C",   # Quest Items — gray
    9: "#616161",   # Digimon Cards — dim
    "eggs": "#FFD54F",  # Digi-Eggs — gold
    "discs": "#42A5F5",  # Attachment Skills — blue
    None: "#9E9E9E",
}

# Sub-categories: icon_index groupings (matches ANAMNESIS)
_SUB_CATEGORIES = {
    0: [  # Recovery
        ("HP Recovery", [40, 41]),
        ("SP Recovery", [42, 43]),
        ("Full Recovery", [44]),
        ("Status Cures", [45, 47, 48, 49, 50, 51, 52, 53, 54, 76, 77]),
        ("Revival", [55, 56]),
        ("Dungeon Exit", [58]),
    ],
    1: [  # Stat Boost
        ("Battle Boosts", [57]),
        ("Courage Points", [59]),
        ("Friendship", [60]),
        ("Training Items", [62]),
    ],
    4: [  # Attachments
        ("Stat Attachments", [0]),
        ("Element Guards", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]),
        ("Union Guards", [12]),
        ("Status Walls", [25]),
        ("Data Fragments", [73]),
    ],
    6: [  # Food
        ("Basic Food", [30, 34, 35, 37, 38, 81]),
        ("Farm Goods", [70]),
        ("Training Sets", [86]),
    ],
}

# Representative icon per category
_CAT_ICONS = {
    0: 40, 1: 57, 2: 63, 4: 0, 5: 64, 6: 34, 7: 78, 8: 73, 9: 74,
    "eggs": 72, "discs": 0, None: 73,
}

# Icon grid constants
_GRID_COLS = 6
_CELL_W = 100
_ICON_SZ = 36

# ── Icon loading ──
_ITEM_ICON_DIR = os.path.join(get_data_dir(), "item_icons")
_icon_cache = {}


def _get_item_icon_path(icon_index):
    if icon_index is None or icon_index < 0:
        return None
    path = os.path.join(_ITEM_ICON_DIR, f"ui_icon_item_{icon_index:03d}.png")
    return path if os.path.isfile(path) else None


def _get_item_pixmap(icon_index, size=36):
    key = (icon_index, size)
    if key in _icon_cache:
        return _icon_cache[key]
    path = _get_item_icon_path(icon_index)
    if not path:
        return None
    pm = QPixmap(path)
    if pm.isNull():
        return None
    pm = pm.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                   Qt.TransformationMode.SmoothTransformation)
    _icon_cache[key] = pm
    return pm


def _hex_rgb(hex_color):
    h = hex_color.lstrip('#')
    return f"{int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)}"


def _effective_category(item):
    cat = item.get("category")
    if cat == "discs":
        return "discs"
    if cat == 1 and item.get("icon_index") == 72:
        return "eggs"
    return cat


def _clean_desc(desc):
    if not desc:
        return ""
    clean = desc.replace("\n", " ").strip()
    clean = re.sub(r'\{[^}]*\}', '', clean)
    return clean.strip()


def _elide(text, width_px, max_lines=2, font_size=10):
    font = QFont()
    font.setPixelSize(font_size)
    fm = QFontMetrics(font)
    if fm.horizontalAdvance(text) <= width_px:
        return text
    words = text.split()
    if not words:
        return text
    lines = []
    cur = ""
    for w in words:
        candidate = f"{cur} {w}" if cur else w
        if fm.horizontalAdvance(candidate) > width_px and cur:
            lines.append(cur)
            cur = w
        else:
            cur = candidate
    if cur:
        lines.append(cur)
    if len(lines) <= max_lines:
        return "\n".join(lines)
    kept = lines[:max_lines - 1]
    used_words = sum(len(ln.split()) for ln in kept)
    rest = " ".join(words[used_words:])
    elided = fm.elidedText(rest, Qt.TextElideMode.ElideRight, width_px)
    return "\n".join(kept + [elided])


def _load_all_items():
    from save_data import _get_db
    db = _get_db()
    items = []
    for row in db.execute(
        "SELECT CAST(item_id AS INT) as id, name, description, category, "
        "buy_price, sell_price, icon_index FROM item_names "
        "WHERE name != '' AND name NOT IN ('Unused text', 'Unused texts') "
        "ORDER BY category, CAST(item_id AS INT)"
    ):
        items.append(dict(row))

    # Add skill discs (attachment skills) from skill_names table
    # Only include real attachment skills — those learnable by Digimon
    # (excludes battle messages, combat text, and other garbage)
    existing_ids = {i["id"] for i in items}
    for row in db.execute(
        "SELECT CAST(sn.skill_id AS INT) as id, sn.name, s.description, "
        "s.actual_element "
        "FROM skill_names sn "
        "JOIN skills s ON sn.skill_id = s.id "
        "JOIN digimon_skills ds ON s.id = ds.skill_id "
        "WHERE ds.learn_level > 0 AND sn.name != '' "
        "GROUP BY sn.skill_id "
        "ORDER BY sn.name"
    ):
        if row["id"] in existing_ids:
            continue
        desc = (row["description"] or "").replace("\n", " ").strip()
        elem = row["actual_element"] if row["actual_element"] is not None else -1
        items.append({
            "id": row["id"],
            "name": row["name"],
            "description": desc,
            "category": "discs",
            "buy_price": 0,
            "sell_price": 0,
            "icon_index": 0,
            "actual_element": elem,
        })

    return items


class InventoryEditor(QWidget):
    """Browse all game items by category with icon grid, edit quantities."""

    data_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._save_file = None
        self._inventory = {}
        self._all_items = []
        self._view = "categories"
        self._current_cat = None
        self._expanded_id = None
        self._widgets = []
        self._item_to_detail_holder = {}
        self._cell_widgets = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header
        hdr = QHBoxLayout()
        hdr.setSpacing(8)

        self._back_btn = QPushButton("\u2190")
        self._back_btn.setFixedSize(28, 28)
        self._back_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._back_btn.setStyleSheet(
            f"QPushButton {{ background: {BG_INPUT}; color: {ACCENT}; "
            f"border: 1px solid {BORDER}; border-radius: 6px; "
            f"font-size: 14px; font-weight: bold; }}"
            f"QPushButton:hover {{ background: rgba(0,191,255,0.15); }}")
        self._back_btn.clicked.connect(self._go_back)
        self._back_btn.setVisible(False)
        hdr.addWidget(self._back_btn)

        self._title = QLabel("INVENTORY")
        self._title.setStyleSheet(
            f"color: {ACCENT}; font-size: 16px; font-weight: bold; letter-spacing: 1px;")
        hdr.addWidget(self._title)
        hdr.addStretch()

        self._count_label = QLabel("")
        self._count_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        hdr.addWidget(self._count_label)
        layout.addLayout(hdr)

        # Scroll area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self._scroll.viewport().setStyleSheet("background: transparent;")

        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(6)
        self._content_layout.addStretch()
        self._scroll.setWidget(self._content)
        layout.addWidget(self._scroll, 1)

    # ── Data loading ──

    def set_save_file(self, save_file):
        self._save_file = save_file
        self._load_data()

    def _load_data(self):
        if not self._all_items:
            self._all_items = _load_all_items()
        self._inventory = {}
        if self._save_file:
            for item in self._save_file.read_inventory():
                self._inventory[item['item_id']] = {
                    'quantity': item['quantity'],
                    'inv_offset': item['_inv_offset'],
                }
        self._view = "categories"
        self._current_cat = None
        self._expanded_id = None
        self._rebuild()

    def _get_qty(self, item_id):
        inv = self._inventory.get(item_id)
        return inv['quantity'] if inv else 0

    # ── Navigation ──

    def _go_back(self):
        self._view = "categories"
        self._current_cat = None
        self._expanded_id = None
        self._rebuild()

    def _open_category(self, cat_id):
        self._view = "items"
        self._current_cat = cat_id
        self._expanded_id = None
        self._rebuild()

    # ── Rebuild ──

    def _rebuild(self):
        for w in self._widgets:
            self._content_layout.removeWidget(w)
            w.deleteLater()
        self._widgets = []
        self._item_to_detail_holder = {}
        self._cell_widgets = {}

        if self._view == "categories":
            self._build_categories()
        else:
            self._build_items()

    def _insert(self, widget):
        idx = self._content_layout.count() - 1
        self._content_layout.insertWidget(idx, widget)
        self._widgets.append(widget)
        return idx + 1

    # ══════════════════════════════════════════════════════════════════
    # Categories view
    # ══════════════════════════════════════════════════════════════════

    def _build_categories(self):
        self._back_btn.setVisible(False)
        self._title.setText("INVENTORY")
        self._title.setStyleSheet(
            f"color: {ACCENT}; font-size: 16px; font-weight: bold; letter-spacing: 1px;")

        counts = {}
        owned_counts = {}
        for item in self._all_items:
            cat = _effective_category(item)
            counts[cat] = counts.get(cat, 0) + 1
            if self._get_qty(item['id']) > 0:
                owned_counts[cat] = owned_counts.get(cat, 0) + 1

        total_owned = sum(owned_counts.values())
        self._count_label.setText(f"{total_owned} owned / {sum(counts.values())} items")

        grid_widget = QWidget()
        grid_widget.setStyleSheet("background: transparent;")
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(0, 4, 0, 4)
        grid.setSpacing(8)

        row, col = 0, 0
        for cat_id in _CAT_ORDER:
            count = counts.get(cat_id, 0)
            if count == 0:
                continue
            owned = owned_counts.get(cat_id, 0)
            card = self._build_cat_card(cat_id, count, owned)
            grid.addWidget(card, row, col)
            col += 1
            if col >= 2:
                col = 0
                row += 1

        self._insert(grid_widget)

    def _build_cat_card(self, cat_id, count, owned):
        cat_name = ITEM_CATEGORIES.get(cat_id, "Other")
        cat_color = _CAT_COLORS.get(cat_id, "#9E9E9E")
        rgb = _hex_rgb(cat_color)

        card = QFrame()
        card.setObjectName("catCard")
        card.setFixedHeight(76)
        card.setStyleSheet(
            f"#catCard {{ background: rgba(18,18,36,200); "
            f"border: 1px solid rgba({rgb},0.25); border-radius: 10px; }}"
            f"#catCard:hover {{ background: rgba({rgb},0.08); "
            f"border: 1px solid rgba({rgb},0.45); }}")
        card.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        card.mousePressEvent = lambda e, c=cat_id: self._open_category(c)

        lay = QHBoxLayout(card)
        lay.setContentsMargins(14, 8, 14, 8)
        lay.setSpacing(12)

        # Icon
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(44, 44)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("background: transparent; border: none;")
        icon_idx = _CAT_ICONS.get(cat_id)
        pm = _get_item_pixmap(icon_idx, 38) if icon_idx is not None else None
        if pm:
            icon_lbl.setPixmap(pm)
        else:
            icon_lbl.setText("\u25CF")
            icon_lbl.setStyleSheet(
                f"color: {cat_color}; font-size: 28px; background: transparent; border: none;")
        lay.addWidget(icon_lbl)

        info = QVBoxLayout()
        info.setSpacing(2)
        name_lbl = QLabel(cat_name)
        name_lbl.setStyleSheet(
            f"color: {cat_color}; font-size: 13px; font-weight: bold; "
            f"background: transparent; border: none;")
        info.addWidget(name_lbl)

        count_text = f"{count} items"
        if owned > 0:
            count_text += f" \u00B7 {owned} owned"
        count_lbl = QLabel(count_text)
        count_lbl.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 10px; background: transparent; border: none;")
        info.addWidget(count_lbl)
        lay.addLayout(info)
        lay.addStretch()

        arrow = QLabel("\u203A")
        arrow.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 18px; background: transparent; border: none;")
        lay.addWidget(arrow)
        return card

    # ══════════════════════════════════════════════════════════════════
    # Items view (within a category)
    # ══════════════════════════════════════════════════════════════════

    def _build_items(self):
        cat_name = ITEM_CATEGORIES.get(self._current_cat, "Other")
        cat_color = _CAT_COLORS.get(self._current_cat, "#9E9E9E")
        rgb = _hex_rgb(cat_color)

        self._back_btn.setVisible(True)
        self._title.setText(cat_name.upper())
        self._title.setStyleSheet(
            f"color: {cat_color}; font-size: 16px; font-weight: bold; letter-spacing: 1px;")

        items = [i for i in self._all_items
                 if _effective_category(i) == self._current_cat]

        owned = sum(1 for i in items if self._get_qty(i['id']) > 0)
        self._count_label.setText(f"{owned} owned / {len(items)} items")

        if not items:
            lbl = QLabel("No items in this category.")
            lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px; padding: 20px;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._insert(lbl)
            return

        # Sub-categories?
        if self._current_cat == "discs":
            self._build_disc_subcategorized(items, cat_color, rgb)
        else:
            subcats = _SUB_CATEGORIES.get(self._current_cat)
            if subcats:
                self._build_subcategorized(items, subcats, cat_color, rgb)
            else:
                items.sort(key=lambda i: (i.get("icon_index") or 9999, i["name"].lower()))
                self._insert_icon_grid(items)

    _ELEMENT_NAMES = {
        -1: "Support", 0: "Neutral", 1: "Fire", 2: "Ice", 3: "Plant",
        4: "Water", 5: "Electric", 6: "Steel", 7: "Wind",
        8: "Earth", 9: "Light", 10: "Dark",
    }
    _ELEMENT_ORDER = [1, 4, 2, 5, 3, 7, 8, 6, 9, 10, 0, -1]

    def _build_disc_subcategorized(self, items, cat_color, rgb):
        """Group skill discs by element."""
        used_ids = set()

        for elem_id in self._ELEMENT_ORDER:
            elem_name = self._ELEMENT_NAMES.get(elem_id, f"Element {elem_id}")
            sub_items = [i for i in items
                         if i.get("actual_element", -1) == elem_id]
            sub_items.sort(key=lambda i: i["name"].lower())
            used_ids.update(i["id"] for i in sub_items)

            header = self._build_sub_header(elem_name, len(sub_items),
                                            cat_color, rgb)
            self._insert(header)

            if sub_items:
                self._insert_icon_grid(sub_items)

        remaining = [i for i in items if i["id"] not in used_ids]
        if remaining:
            remaining.sort(key=lambda i: i["name"].lower())
            header = self._build_sub_header("Other", len(remaining),
                                            cat_color, rgb)
            self._insert(header)
            self._insert_icon_grid(remaining)

    def _build_subcategorized(self, items, subcats, cat_color, rgb):
        used_ids = set()

        for sub_name, icon_indices in subcats:
            sub_items = [i for i in items if i.get("icon_index") in icon_indices]
            sub_items.sort(key=lambda i: (i.get("icon_index") or 9999, i["name"].lower()))
            used_ids.update(i["id"] for i in sub_items)

            # Always show sub-header (even if empty)
            header = self._build_sub_header(sub_name, len(sub_items), cat_color, rgb)
            self._insert(header)

            if sub_items:
                self._insert_icon_grid(sub_items)

        # Uncategorized remainder
        remaining = [i for i in items if i["id"] not in used_ids]
        if remaining:
            remaining.sort(key=lambda i: (i.get("icon_index") or 9999, i["name"].lower()))
            header = self._build_sub_header("Other", len(remaining), cat_color, rgb)
            self._insert(header)
            self._insert_icon_grid(remaining)

    def _build_sub_header(self, name, count, color, rgb):
        header = QWidget()
        header.setStyleSheet("background: transparent; border: none;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(4, 10, 4, 2)
        hl.setSpacing(8)

        lbl = QLabel(f"{name} ({count})" if count else name)
        lbl.setStyleSheet(
            f"color: {color}; font-size: 10px; font-weight: bold; "
            f"letter-spacing: 0.5px; background: transparent; border: none;")
        hl.addWidget(lbl)

        line = QWidget()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background: rgba({rgb}, 0.3); border: none;")
        hl.addWidget(line, 1)
        return header

    # ══════════════════════════════════════════════════════════════════
    # Icon grid
    # ══════════════════════════════════════════════════════════════════

    def _insert_icon_grid(self, items):
        container = QWidget()
        container.setStyleSheet("background: transparent; border: none;")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(2, 4, 2, 4)
        container_layout.setSpacing(4)

        chunks = [items[i:i + _GRID_COLS] for i in range(0, len(items), _GRID_COLS)]

        for chunk in chunks:
            # Row of cells
            row_w = QWidget()
            row_w.setStyleSheet("background: transparent; border: none;")
            row_lay = QHBoxLayout(row_w)
            row_lay.setContentsMargins(0, 0, 0, 0)
            row_lay.setSpacing(4)
            row_lay.setAlignment(Qt.AlignmentFlag.AlignLeft)

            for item in chunk:
                cell = self._build_icon_cell(item)
                row_lay.addWidget(cell)
                self._cell_widgets[item["id"]] = cell

            container_layout.addWidget(row_w)

            # Detail holder (hidden, expands below this row)
            detail_holder = QWidget()
            detail_holder.setStyleSheet("background: transparent; border: none;")
            detail_holder.setVisible(False)
            dh_layout = QVBoxLayout(detail_holder)
            dh_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.addWidget(detail_holder)

            for item in chunk:
                self._item_to_detail_holder[item["id"]] = detail_holder

        self._insert(container)

        # Re-expand if the expanded item is in THIS grid (not a previous one)
        local_ids = {i["id"] for i in items}
        if self._expanded_id and self._expanded_id in local_ids:
            eid = self._expanded_id
            QTimer.singleShot(50, lambda: self._expand_item(eid))

    def _build_icon_cell(self, item):
        cat = _effective_category(item)
        cat_color = _CAT_COLORS.get(cat, "#9E9E9E")

        cell = QFrame()
        cell.setObjectName("iconCell")
        cell.setFixedSize(_CELL_W, _CELL_W + 16)
        is_selected = (self._expanded_id == item["id"])
        if is_selected:
            cell.setStyleSheet(
                f"#iconCell {{ background: rgba(0,191,255,0.1); "
                f"border: 1px solid {ACCENT}; border-radius: 8px; }}")
        else:
            cell.setStyleSheet(
                f"#iconCell {{ background: transparent; "
                f"border: 1px solid transparent; border-radius: 8px; }}"
                f"#iconCell:hover {{ background: rgba(0,191,255,0.06); "
                f"border: 1px solid {BORDER}; }}")
        cell.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        cell.mousePressEvent = lambda e, i=item: self._icon_clicked(i)

        lay = QVBoxLayout(cell)
        lay.setContentsMargins(4, 4, 4, 2)
        lay.setSpacing(3)
        lay.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        # Icon
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(40, 40)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("background: transparent; border: none;")
        pm = _get_item_pixmap(item.get("icon_index"), _ICON_SZ)
        if pm:
            icon_lbl.setPixmap(pm)
        else:
            icon_lbl.setText("\u25CF")
            icon_lbl.setStyleSheet(
                f"color: {cat_color}; font-size: 24px; background: transparent; border: none;")
        lay.addWidget(icon_lbl, 0, Qt.AlignmentFlag.AlignHCenter)

        # Name (2-line elision)
        label_w = _CELL_W - 8
        display = _elide(item["name"], label_w, max_lines=2, font_size=10)
        name_lbl = QLabel(display)
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        name_lbl.setWordWrap(False)
        name_lbl.setFixedWidth(label_w)
        name_lbl.setMaximumHeight(28)
        qty = self._get_qty(item["id"])
        name_color = TEXT_PRIMARY if qty > 0 else TEXT_SECONDARY
        name_lbl.setStyleSheet(
            f"color: {name_color}; font-size: 10px; background: transparent; border: none;")
        name_lbl.setToolTip(item["name"])
        lay.addWidget(name_lbl, 0, Qt.AlignmentFlag.AlignHCenter)

        # Quantity badge (top-right)
        if qty > 0:
            badge = QLabel(str(qty), cell)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setMinimumWidth(20)
            badge.setStyleSheet(
                "background: rgba(0,0,0,180); color: #FFD54F; "
                "font-size: 9px; font-weight: bold; "
                "border: 1px solid rgba(255,213,79,0.4); "
                "border-radius: 7px; padding: 1px 4px;")
            badge.adjustSize()
            badge.move(cell.width() - badge.width() - 4, 4)
            badge.raise_()

        return cell

    def _icon_clicked(self, item):
        item_id = item["id"]
        if self._expanded_id == item_id:
            # Collapse
            self._expanded_id = None
            holder = self._item_to_detail_holder.get(item_id)
            if holder:
                holder.setVisible(False)
                layout = holder.layout()
                while layout.count():
                    child = layout.takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
            # Remove highlight
            cell = self._cell_widgets.get(item_id)
            if cell:
                cell.setStyleSheet(
                    f"#iconCell {{ background: transparent; "
                    f"border: 1px solid transparent; border-radius: 8px; }}"
                    f"#iconCell:hover {{ background: rgba(0,191,255,0.06); "
                    f"border: 1px solid {BORDER}; }}")
        else:
            # Collapse previous
            if self._expanded_id is not None:
                prev_holder = self._item_to_detail_holder.get(self._expanded_id)
                if prev_holder:
                    prev_holder.setVisible(False)
                    layout = prev_holder.layout()
                    while layout.count():
                        child = layout.takeAt(0)
                        if child.widget():
                            child.widget().deleteLater()
                prev_cell = self._cell_widgets.get(self._expanded_id)
                if prev_cell:
                    prev_cell.setStyleSheet(
                        f"#iconCell {{ background: transparent; "
                        f"border: 1px solid transparent; border-radius: 8px; }}"
                        f"#iconCell:hover {{ background: rgba(0,191,255,0.06); "
                        f"border: 1px solid {BORDER}; }}")

            # Expand new
            self._expanded_id = item_id
            cell = self._cell_widgets.get(item_id)
            if cell:
                cell.setStyleSheet(
                    f"#iconCell {{ background: rgba(0,191,255,0.1); "
                    f"border: 1px solid {ACCENT}; border-radius: 8px; }}")
            self._expand_item(item_id)

    def _expand_item(self, item_id):
        holder = self._item_to_detail_holder.get(item_id)
        if not holder:
            return
        # Find item data
        item = None
        for i in self._all_items:
            if i["id"] == item_id:
                item = i
                break
        if not item:
            return

        card = self._build_detail_card(item)
        holder.layout().addWidget(card)
        holder.setVisible(True)

    # ══════════════════════════════════════════════════════════════════
    # Detail card (expanded below icon row)
    # ══════════════════════════════════════════════════════════════════

    def _build_detail_card(self, item):
        cat = _effective_category(item)
        cat_color = _CAT_COLORS.get(cat, "#9E9E9E")
        rgb = _hex_rgb(cat_color)
        qty = self._get_qty(item["id"])

        card = QWidget()
        card.setObjectName("detailCard")
        card.setStyleSheet(
            f"#detailCard {{ background: rgba(18,18,36,200); "
            f"border: 1px solid rgba({rgb}, 0.25); border-radius: 10px; }}")

        outer = QVBoxLayout(card)
        outer.setContentsMargins(14, 10, 14, 10)
        outer.setSpacing(6)

        # ── Header: icon + name + price ──
        hdr = QHBoxLayout()
        hdr.setSpacing(10)

        icon_lbl = QLabel()
        icon_lbl.setFixedSize(36, 36)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("background: transparent; border: none;")
        pm = _get_item_pixmap(item.get("icon_index"), 32)
        if pm:
            icon_lbl.setPixmap(pm)
        hdr.addWidget(icon_lbl)

        name_lbl = QLabel(item["name"])
        name_lbl.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 13px; font-weight: bold; "
            f"background: transparent; border: none;")
        hdr.addWidget(name_lbl)
        hdr.addStretch()

        # Prices
        price_parts = []
        buy = item.get("buy_price")
        sell = item.get("sell_price")
        if buy and buy > 0:
            price_parts.append(f"\u00A5{buy:,}")
        if sell and sell > 0:
            price_parts.append(f"Sell \u00A5{sell:,}")
        if price_parts:
            price_lbl = QLabel(" \u00B7 ".join(price_parts))
            price_lbl.setStyleSheet(
                f"color: {TEXT_SECONDARY}; font-size: 11px; "
                f"background: transparent; border: none;")
            hdr.addWidget(price_lbl)

        outer.addLayout(hdr)

        # ── Description ──
        desc = _clean_desc(item.get("description"))
        if desc:
            desc_lbl = QLabel(desc)
            desc_lbl.setWordWrap(True)
            desc_lbl.setStyleSheet(
                f"color: {TEXT_PRIMARY}; font-size: 11px; "
                f"background: transparent; border: none;")
            outer.addWidget(desc_lbl)

        # ── Separator ──
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: rgba({rgb}, 0.2); border: none;")
        outer.addWidget(sep)

        # ── Inventory quantity + edit controls ──
        inv_row = QHBoxLayout()
        inv_row.setSpacing(8)

        if qty > 0:
            inv_lbl = QLabel(f"In inventory: {qty}")
            inv_lbl.setStyleSheet(
                "color: #FFD54F; font-size: 12px; font-weight: bold; "
                "background: transparent; border: none;")
        else:
            inv_lbl = QLabel("Not in inventory")
            inv_lbl.setStyleSheet(
                f"color: {TEXT_SECONDARY}; font-size: 12px; "
                f"background: transparent; border: none;")
        inv_row.addWidget(inv_lbl)
        inv_row.addStretch()

        # Quantity spinner
        qty_spin = QSpinBox()
        qty_spin.setRange(0, 999)
        qty_spin.setValue(qty)
        qty_spin.setFixedWidth(80)
        qty_spin.setButtonSymbols(QSpinBox.ButtonSymbols.PlusMinus)
        qty_spin.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        qty_spin.setStyleSheet(
            f"QSpinBox {{ background: {BG_INPUT}; color: {TEXT_VALUE}; "
            f"border: 1px solid {BORDER}; border-radius: 4px; padding: 2px 4px; "
            f"font-size: 12px; }}"
            f"QSpinBox::up-button, QSpinBox::down-button {{ "
            f"width: 18px; border: none; }}")
        inv_row.addWidget(qty_spin)

        if qty == 0:
            add_btn = QPushButton("Add to Inventory")
            add_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            add_btn.setToolTip("Add this item to your save with the specified quantity")
            add_btn.setStyleSheet(
                f"QPushButton {{ background: {BG_INPUT}; color: #81C784; "
                f"border: 1px solid rgba(129,199,132,0.4); border-radius: 4px; "
                f"padding: 3px 10px; font-size: 11px; }}"
                f"QPushButton:hover {{ background: rgba(129,199,132,0.15); }}")
            add_btn.clicked.connect(lambda: self._on_set_qty(item, max(qty_spin.value(), 1)))
            inv_row.addWidget(add_btn)
        else:
            set_btn = QPushButton("Update Quantity")
            set_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            set_btn.setToolTip("Change the quantity in your save to the value in the spinner")
            set_btn.setStyleSheet(
                f"QPushButton {{ background: {BG_INPUT}; color: {ACCENT}; "
                f"border: 1px solid {BORDER}; border-radius: 4px; padding: 3px 10px; font-size: 11px; }}"
                f"QPushButton:hover {{ background: rgba(0,191,255,0.15); }}")
            set_btn.clicked.connect(lambda: self._on_set_qty(item, qty_spin.value()))
            inv_row.addWidget(set_btn)

            rm_btn = QPushButton("Remove")
            rm_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            rm_btn.setToolTip("Remove this item from your save entirely")
            rm_btn.setStyleSheet(
                f"QPushButton {{ background: {BG_INPUT}; color: #EF5350; "
                f"border: 1px solid rgba(239,83,80,0.4); border-radius: 4px; "
                f"padding: 3px 10px; font-size: 11px; }}"
                f"QPushButton:hover {{ background: rgba(239,83,80,0.15); }}")
            rm_btn.clicked.connect(lambda: self._on_remove(item))
            inv_row.addWidget(rm_btn)

        outer.addLayout(inv_row)
        return card

    # ── Edit actions ──

    def _on_set_qty(self, item, new_qty):
        if not self._save_file:
            return
        item_id = item["id"]
        inv = self._inventory.get(item_id)

        if inv:
            if new_qty == 0:
                self._save_file.remove_item(inv['inv_offset'])
                del self._inventory[item_id]
            else:
                self._save_file.write_item_quantity(inv['inv_offset'], new_qty)
                inv['quantity'] = new_qty
        else:
            if new_qty == 0:
                return
            off = self._save_file.add_item(item_id, new_qty)
            if off is None:
                QMessageBox.warning(self, "Full", "Inventory is full.")
                return
            self._inventory[item_id] = {'quantity': new_qty, 'inv_offset': off}

        # Re-read inventory from save to ensure consistency
        self._inventory = {}
        for slot in self._save_file.read_inventory():
            self._inventory[slot['item_id']] = {
                'quantity': slot['quantity'],
                'inv_offset': slot['_inv_offset'],
            }
        self._expanded_id = item_id  # keep this item expanded
        self._rebuild()
        self.data_changed.emit()

    def _on_remove(self, item):
        if not self._save_file:
            return
        item_id = item["id"]
        inv = self._inventory.get(item_id)
        if not inv:
            return
        reply = QMessageBox.question(
            self, "Remove Item",
            f"Remove \"{item['name']}\" from inventory?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._save_file.remove_item(inv['inv_offset'])
        del self._inventory[item_id]
        self._rebuild()
        self.data_changed.emit()
