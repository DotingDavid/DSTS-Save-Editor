"""Tabbed Digimon detail editor panel (right side).

Contains tabs: Identity, Stats, Skills & Equipment.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                              QTabWidget, QLabel, QPushButton)
from PyQt6.QtCore import pyqtSignal, Qt

from ui.style import TEXT_SECONDARY, BORDER
from ui.identity_editor import IdentityEditor
from ui.stat_editor import StatEditor
from ui.skills_editor import SkillsEditor


class DigimonEditor(QWidget):
    """Right panel: tabbed editor for one Digimon."""

    field_changed = pyqtSignal(str, object)  # field_name, new_value
    back_requested = pyqtSignal()
    export_requested = pyqtSignal()
    import_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entry = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header bar with back button and Digimon name
        header = QHBoxLayout()
        header.setContentsMargins(8, 6, 8, 6)
        self._back_btn = QPushButton("< Back to Grid")
        self._back_btn.clicked.connect(self.back_requested.emit)
        self._back_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {TEXT_SECONDARY};
                border: none;
                font-size: 11px;
                padding: 4px 8px;
            }}
            QPushButton:hover {{
                color: #00BFFF;
            }}
        """)
        header.addWidget(self._back_btn)
        header.addStretch()

        self._export_btn = QPushButton("Export")
        self._export_btn.clicked.connect(self.export_requested.emit)
        self._export_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {TEXT_SECONDARY};
                border: 1px solid {BORDER}; border-radius: 3px;
                padding: 3px 10px; font-size: 10px;
            }}
            QPushButton:hover {{ color: #00BFFF; border-color: #00BFFF; }}
        """)
        header.addWidget(self._export_btn)

        self._import_btn = QPushButton("Import")
        self._import_btn.clicked.connect(self.import_requested.emit)
        self._import_btn.setStyleSheet(self._export_btn.styleSheet())
        header.addWidget(self._import_btn)

        self._header_name = QLabel("")
        self._header_name.setStyleSheet(
            "color: #E8E8F0; font-size: 13px; font-weight: bold;")
        self._header_name.setAlignment(Qt.AlignmentFlag.AlignRight)
        header.addWidget(self._header_name)

        self._header_widget = QWidget()
        self._header_widget.setLayout(header)
        self._header_widget.hide()
        layout.addWidget(self._header_widget)

        # Placeholder shown when no Digimon is selected
        self._placeholder = QLabel(
            "ANAMNESIS\nSave Editor\n\n"
            "Select a save slot and click Load,\n"
            "then pick a Digimon from the grid to edit.")
        self._placeholder.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 16px; padding: 60px;"
            f" background: transparent;")
        self._placeholder.setWordWrap(True)
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Tabbed editor
        self._tabs = QTabWidget()

        self._identity = IdentityEditor()
        self._identity.field_changed.connect(self._on_field_changed)
        self._tabs.addTab(self._identity, "Identity")

        self._stats = StatEditor()
        self._stats.blue_stat_changed.connect(
            lambda key, val: self._on_field_changed(f"blue_{key}", val))
        self._stats.white_stat_changed.connect(
            lambda key, val: self._on_field_changed(f"white_{key}", val))
        self._stats.farm_stat_changed.connect(
            lambda key, val: self._on_field_changed(f"farm_{key}", val))
        self._tabs.addTab(self._stats, "Stats")

        self._skills = SkillsEditor()
        self._skills.field_changed.connect(self._on_field_changed)
        self._tabs.addTab(self._skills, "Skills")

        self._tabs.hide()
        layout.addWidget(self._placeholder)
        layout.addWidget(self._tabs)

    def set_entry(self, entry):
        """Load a Digimon entry into all tabs."""
        self._entry = entry
        self._placeholder.hide()
        self._header_widget.show()
        self._tabs.show()
        name = entry.get("nickname") or entry["species"]
        self._header_name.setText(f"{name}  Lv{entry['level']}")
        self._identity.set_entry(entry)
        self._stats.set_entry(entry)
        self._skills.set_entry(entry)

    def clear(self):
        """Show placeholder when nothing is selected."""
        self._entry = None
        self._tabs.hide()
        self._header_widget.hide()
        self._placeholder.show()

    def _on_field_changed(self, field, value):
        self.field_changed.emit(field, value)
