"""Batch operations dialog for bulk editing Digimon."""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QGroupBox, QSpinBox, QComboBox,
                              QCheckBox, QFrame, QMessageBox)
from PyQt6.QtCore import Qt

from ui.style import (ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_VALUE,
                       BORDER, BG_INPUT, BG_PANEL, STAT_BLUE, STAT_FARM)
from save_layout import PERSONALITY_NAMES


class BatchOpsDialog(QDialog):
    """Dialog for batch operations on the entire roster."""

    def __init__(self, save_file, roster, parent=None):
        super().__init__(parent)
        self._save_file = save_file
        self._roster = roster
        self._changes_made = False
        self.setWindowTitle("Batch Operations")
        self.setMinimumWidth(400)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        header = QLabel("Batch Operations")
        header.setStyleSheet(
            f"color: {ACCENT}; font-size: 16px; font-weight: bold;")
        layout.addWidget(header)

        desc = QLabel(
            "Apply changes to ALL Digimon in the roster at once.\n"
            "These operations modify the in-memory save data. "
            "Use Save to write to disk.")
        desc.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # ── Reset Evo Counters ──
        evo_group = QGroupBox("Evolution Counters")
        evo_layout = QVBoxLayout()
        evo_desc = QLabel(
            "Reset the blue stat grant counter on all Digimon to 0, "
            "allowing unlimited blue stat gains from evolution.")
        evo_desc.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        evo_desc.setWordWrap(True)
        evo_layout.addWidget(evo_desc)
        btn_reset_evo = QPushButton("Reset All Evo Counters to 0")
        btn_reset_evo.clicked.connect(self._reset_evo_counters)
        evo_layout.addWidget(btn_reset_evo)
        evo_group.setLayout(evo_layout)
        layout.addWidget(evo_group)

        # ── Max Bond ──
        bond_group = QGroupBox("Bond")
        bond_layout = QVBoxLayout()
        btn_max_bond = QPushButton("Set All Bond to 100%")
        btn_max_bond.clicked.connect(self._max_bond)
        bond_layout.addWidget(btn_max_bond)
        bond_group.setLayout(bond_layout)
        layout.addWidget(bond_group)

        # ── Max Talent ──
        talent_group = QGroupBox("Talent")
        talent_layout = QVBoxLayout()
        row = QHBoxLayout()
        row.addWidget(QLabel("Set all talent to:"))
        self._talent_spin = QSpinBox()
        self._talent_spin.setRange(0, 200)
        self._talent_spin.setValue(200)
        row.addWidget(self._talent_spin)
        talent_layout.addLayout(row)
        btn_talent = QPushButton("Apply Talent")
        btn_talent.clicked.connect(self._set_talent)
        talent_layout.addWidget(btn_talent)
        talent_group.setLayout(talent_layout)
        layout.addWidget(talent_group)

        # ── Blue Stats ──
        blue_group = QGroupBox("Blue Stats")
        blue_layout = QVBoxLayout()
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Set all blue stats to:"))
        self._blue_spin = QSpinBox()
        self._blue_spin.setRange(0, 9999)
        self._blue_spin.setValue(9999)
        row2.addWidget(self._blue_spin)
        blue_layout.addLayout(row2)
        btn_blue = QPushButton("Apply Blue Stats")
        btn_blue.clicked.connect(self._set_blue_stats)
        blue_layout.addWidget(btn_blue)
        blue_group.setLayout(blue_layout)
        layout.addWidget(blue_group)

        # Close
        layout.addStretch()
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def _reset_evo_counters(self):
        count = 0
        for entry in self._roster:
            off = entry["_offset"]
            self._save_file.write_evo_counter(off, 0)
            count += 1
        self._changes_made = True
        QMessageBox.information(
            self, "Done", f"Reset evo counter to 0 on {count} Digimon.")

    def _max_bond(self):
        count = 0
        for entry in self._roster:
            off = entry["_offset"]
            self._save_file.write_bond(off, 100)
            count += 1
        self._changes_made = True
        QMessageBox.information(
            self, "Done", f"Set bond to 100% on {count} Digimon.")

    def _set_talent(self):
        val = self._talent_spin.value()
        count = 0
        for entry in self._roster:
            off = entry["_offset"]
            self._save_file.write_talent(off, val)
            count += 1
        self._changes_made = True
        QMessageBox.information(
            self, "Done", f"Set talent to {val} on {count} Digimon.")

    def _set_blue_stats(self):
        val = self._blue_spin.value()
        count = 0
        for entry in self._roster:
            off = entry["_offset"]
            for i in range(7):
                self._save_file.write_blue_stat(off, i, val)
            count += 1
        self._changes_made = True
        QMessageBox.information(
            self, "Done", f"Set all blue stats to {val} on {count} Digimon.")

    @property
    def changes_made(self):
        return self._changes_made
