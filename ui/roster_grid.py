"""Visual roster grid view — PKHeX-style icon grid.

Displays Digimon as a grid of clickable icons, grouped by Party/Box/Farm.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
                              QLabel, QGridLayout, QSizePolicy, QLineEdit,
                              QComboBox, QMenu)
from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.QtGui import QCursor, QPixmap, QAction

from ui.style import (BG_PANEL, BG_INPUT, BG_HOVER, BG_SELECTED,
                       ACCENT, ACCENT_DIM, STAT_FARM, TEXT_PRIMARY,
                       TEXT_SECONDARY, BORDER, STAGE_COLORS)
from ui.icon_cache import get_icon


GRID_COLS = 10
ICON_SIZE = 56
SLOT_SIZE = 72


class GridSlot(QWidget):
    """Single Digimon slot in the grid."""

    clicked = pyqtSignal(dict)
    clone_requested = pyqtSignal(dict)
    export_requested = pyqtSignal(dict)

    def __init__(self, entry=None, parent=None):
        super().__init__(parent)
        self._entry = entry
        self._selected = False
        self.setFixedSize(SLOT_SIZE, SLOT_SIZE + 16)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._icon = QLabel()
        self._icon.setFixedSize(ICON_SIZE, ICON_SIZE)
        self._icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._icon, alignment=Qt.AlignmentFlag.AlignCenter)

        self._name_label = QLabel()
        self._name_label.setFixedHeight(14)
        self._name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._name_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 9px;")
        layout.addWidget(self._name_label)

        if entry:
            pm = get_icon(entry["species"], ICON_SIZE)
            self._icon.setPixmap(pm)
            name = entry.get("nickname") or entry["species"]
            if len(name) > 9:
                name = name[:8] + "…"
            lv = entry.get("level", 0)
            self._name_label.setText(f"{name} {lv}")
            self.setToolTip(
                f"{entry.get('nickname') or entry['species']}\n"
                f"Lv{entry['level']} {entry['personality']}\n"
                f"{entry.get('stage', '')}")
        else:
            self._icon.setStyleSheet(
                f"border: 1px dashed {BORDER}; border-radius: 4px;")
            self._name_label.setText("")

        self._update_style()

    def _update_style(self):
        if self._entry is None:
            self.setStyleSheet("background: transparent;")
            return
        if self._selected:
            self.setStyleSheet(
                f"background-color: rgba(0, 191, 255, 0.12); "
                f"border: 2px solid {ACCENT}; border-radius: 6px;")
        else:
            self.setStyleSheet(
                f"background-color: rgba(18, 18, 32, 160); "
                f"border: 1px solid rgba(255,255,255,0.06); border-radius: 6px;")

    def set_selected(self, selected):
        self._selected = selected
        self._update_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._entry:
            self.clicked.emit(self._entry)
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        if not self._entry:
            return
        menu = QMenu(self)
        clone_act = menu.addAction("Clone Digimon")
        export_act = menu.addAction("Export to File...")
        action = menu.exec(event.globalPos())
        if action == clone_act:
            self.clone_requested.emit(self._entry)
        elif action == export_act:
            self.export_requested.emit(self._entry)

    def enterEvent(self, event):
        if self._entry and not self._selected:
            self.setStyleSheet(
                f"background-color: {BG_HOVER}; "
                f"border: 1px solid {ACCENT_DIM}; border-radius: 6px;")
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._update_style()
        super().leaveEvent(event)


class RosterGrid(QWidget):
    """Scrollable grid of Digimon icons grouped by Party/Box/Farm."""

    digimon_selected = pyqtSignal(dict)
    clone_requested = pyqtSignal(dict)
    export_requested = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._slots = []
        self._roster = []
        self._current_slot = None
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Search and sort bar
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(8, 6, 8, 6)
        toolbar.setSpacing(6)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search Digimon...")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._filter)
        toolbar.addWidget(self._search, 1)

        sort_label = QLabel("Sort:")
        sort_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        toolbar.addWidget(sort_label)
        self._sort_combo = QComboBox()
        self._sort_combo.addItems(["Default", "Name", "Level ↓", "Level ↑",
                                    "Stage", "Personality"])
        self._sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        self._sort_combo.setFixedWidth(110)
        toolbar.addWidget(self._sort_combo)

        outer.addLayout(toolbar)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        outer.addWidget(self._scroll)

        self._container = QWidget()
        self._main_layout = QVBoxLayout(self._container)
        self._main_layout.setContentsMargins(8, 8, 8, 8)
        self._main_layout.setSpacing(8)
        self._main_layout.addStretch()
        self._scroll.setWidget(self._container)

    def set_roster(self, roster):
        """Populate grid with Digimon entries."""
        self._roster = roster
        self._search.blockSignals(True)
        self._search.clear()
        self._search.blockSignals(False)
        self._sort_combo.blockSignals(True)
        self._sort_combo.setCurrentIndex(0)
        self._sort_combo.blockSignals(False)
        self._rebuild_grid(roster)

    def _rebuild_grid(self, roster):
        """Internal: rebuild grid from a (possibly filtered/sorted) roster."""
        self._slots.clear()
        self._current_slot = None

        # Clear existing
        while self._main_layout.count() > 0:
            item = self._main_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
            elif item.layout():
                # Clear nested layout
                sub = item.layout()
                while sub.count() > 0:
                    sub_item = sub.takeAt(0)
                    sw = sub_item.widget()
                    if sw:
                        sw.deleteLater()

        groups = {"party": [], "box": [], "farm": []}
        for entry in roster:
            loc = entry.get("location", "box")
            groups.get(loc, groups["box"]).append(entry)

        section_config = [
            ("party", f"Party ({len(groups['party'])})", ACCENT),
            ("box", f"Box ({len(groups['box'])})", ACCENT_DIM),
            ("farm", f"Farm ({len(groups['farm'])})", STAT_FARM),
        ]

        for key, title, color in section_config:
            entries = groups[key]
            if not entries:
                continue

            header = QLabel(title)
            header.setStyleSheet(
                f"color: {color}; font-weight: bold; font-size: 11px; "
                f"letter-spacing: 1px; background: transparent; padding-top: 4px;")
            self._main_layout.addWidget(header)

            grid = QGridLayout()
            grid.setSpacing(4)
            for i, entry in enumerate(entries):
                row = i // GRID_COLS
                col = i % GRID_COLS
                slot = GridSlot(entry)
                slot.clicked.connect(self._on_slot_clicked)
                slot.clone_requested.connect(self.clone_requested.emit)
                slot.export_requested.connect(self.export_requested.emit)
                grid.addWidget(slot, row, col)
                self._slots.append(slot)

            grid_widget = QWidget()
            grid_widget.setLayout(grid)
            self._main_layout.addWidget(grid_widget)

        self._main_layout.addStretch()

    def _on_slot_clicked(self, entry):
        if self._current_slot:
            self._current_slot.set_selected(False)
        sender = self.sender()
        if isinstance(sender, GridSlot):
            sender.set_selected(True)
            self._current_slot = sender
        self.digimon_selected.emit(entry)

    def _filter(self, text):
        """Filter grid by search text."""
        text = text.lower().strip()
        if not text:
            self._rebuild_grid(self._roster)
            return
        filtered = [e for e in self._roster
                    if text in (e.get("nickname") or e["species"]).lower()
                    or text in e["species"].lower()]
        self._rebuild_grid(filtered)

    def _on_sort_changed(self, idx):
        """Sort grid by selected criteria."""
        STAGE_ORDER = {
            "In-Training I": 0, "In-Training II": 1, "Rookie": 2,
            "Champion": 3, "Armor": 4, "Ultimate": 5, "Mega": 6, "Mega+": 7,
        }
        roster = list(self._roster)
        if idx == 1:  # Name
            roster.sort(key=lambda e: (e.get("nickname") or e["species"]).lower())
        elif idx == 2:  # Level desc
            roster.sort(key=lambda e: e["level"], reverse=True)
        elif idx == 3:  # Level asc
            roster.sort(key=lambda e: e["level"])
        elif idx == 4:  # Stage
            roster.sort(key=lambda e: STAGE_ORDER.get(e.get("stage", ""), 99))
        elif idx == 5:  # Personality
            roster.sort(key=lambda e: e.get("personality", ""))
        self._rebuild_grid(roster)
