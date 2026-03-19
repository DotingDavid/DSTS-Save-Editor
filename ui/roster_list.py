"""Scrollable Digimon roster list for the left sidebar.

Displays all Digimon in the save, grouped by Party / Box / Farm,
with icons and compact info. Clicking an entry selects it.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QScrollArea,
                              QLabel, QHBoxLayout, QSizePolicy)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QCursor

from ui.style import (BG_PANEL, BG_HOVER, BG_SELECTED, ACCENT,
                       ACCENT_DIM, STAT_FARM, TEXT_PRIMARY, TEXT_SECONDARY, BORDER)
from ui.icon_cache import get_icon


class RosterItem(QWidget):
    """Single Digimon entry in the roster list."""

    clicked = pyqtSignal(dict)  # emits the entry dict

    def __init__(self, entry, parent=None):
        super().__init__(parent)
        self._entry = entry
        self._selected = False
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFixedHeight(40)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(6)

        # Icon
        icon_label = QLabel()
        pm = get_icon(entry["species"], 32)
        icon_label.setPixmap(pm)
        icon_label.setFixedSize(32, 32)
        layout.addWidget(icon_label)

        # Name + nickname
        name = entry.get("nickname") or entry["species"]
        name_label = QLabel(name)
        name_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 12px;")
        name_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(name_label)

        # Level
        lv_label = QLabel(f"Lv{entry['level']}")
        lv_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        lv_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(lv_label)

        self._update_style()

    def _update_style(self):
        if self._selected:
            self.setStyleSheet(
                f"background-color: {BG_SELECTED}; "
                f"border-left: 3px solid {ACCENT}; border-radius: 2px;")
        else:
            self.setStyleSheet("background-color: transparent; border: none;")

    def set_selected(self, selected):
        self._selected = selected
        self._update_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._entry)
        super().mousePressEvent(event)

    def enterEvent(self, event):
        if not self._selected:
            self.setStyleSheet(f"background-color: {BG_HOVER}; border-radius: 2px;")
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._update_style()
        super().leaveEvent(event)


class RosterList(QWidget):
    """Scrollable roster list grouped by Party / Box / Farm."""

    digimon_selected = pyqtSignal(dict)  # emits entry dict

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = []
        self._current_item = None
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer.addWidget(self._scroll)

        self._container = QWidget()
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._layout.setSpacing(1)
        self._layout.addStretch()
        self._scroll.setWidget(self._container)

    def set_roster(self, roster):
        """Populate with a list of Digimon entry dicts."""
        # Clear existing
        self._items.clear()
        self._current_item = None
        while self._layout.count() > 0:
            item = self._layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        # Group by location
        groups = {"party": [], "box": [], "farm": [], "unknown": []}
        for entry in roster:
            loc = entry.get("location", "unknown")
            groups.get(loc, groups["unknown"]).append(entry)

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
                f"padding: 6px 6px 2px 6px;")
            self._layout.addWidget(header)

            for entry in entries:
                item = RosterItem(entry)
                item.clicked.connect(self._on_item_clicked)
                self._layout.addWidget(item)
                self._items.append(item)

        self._layout.addStretch()

    def _on_item_clicked(self, entry):
        # Deselect previous
        if self._current_item:
            self._current_item.set_selected(False)
        # Find and select the clicked item
        sender = self.sender()
        if isinstance(sender, RosterItem):
            sender.set_selected(True)
            self._current_item = sender
        self.digimon_selected.emit(entry)
