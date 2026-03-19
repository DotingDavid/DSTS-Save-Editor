"""Tabbed Digimon detail editor panel (right side).

Contains tabs: Identity, Stats, Skills & Equipment.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QLabel
from PyQt6.QtCore import pyqtSignal

from ui.style import TEXT_SECONDARY
from ui.identity_editor import IdentityEditor
from ui.stat_editor import StatEditor
from ui.skills_editor import SkillsEditor


class DigimonEditor(QWidget):
    """Right panel: tabbed editor for one Digimon."""

    field_changed = pyqtSignal(str, object)  # field_name, new_value

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entry = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Placeholder shown when no Digimon is selected
        self._placeholder = QLabel("Select a Digimon to edit")
        self._placeholder.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 14px; padding: 40px;")
        self._placeholder.setWordWrap(True)

        # Tabbed editor
        self._tabs = QTabWidget()

        self._identity = IdentityEditor()
        self._identity.field_changed.connect(self._on_field_changed)
        self._tabs.addTab(self._identity, "Identity")

        self._stats = StatEditor()
        self._stats.blue_stat_changed.connect(
            lambda key, val: self._on_field_changed(f"blue_{key}", val))
        self._tabs.addTab(self._stats, "Stats")

        self._skills = SkillsEditor()
        self._tabs.addTab(self._skills, "Skills")

        self._tabs.hide()
        layout.addWidget(self._placeholder)
        layout.addWidget(self._tabs)

    def set_entry(self, entry):
        """Load a Digimon entry into all tabs."""
        self._entry = entry
        self._placeholder.hide()
        self._tabs.show()
        self._identity.set_entry(entry)
        self._stats.set_entry(entry)
        self._skills.set_entry(entry)

    def clear(self):
        """Show placeholder when nothing is selected."""
        self._entry = None
        self._tabs.hide()
        self._placeholder.show()

    def _on_field_changed(self, field, value):
        self.field_changed.emit(field, value)
