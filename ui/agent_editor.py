"""Agent/Player data editor.

Edit money, Tamer Points, and view agent skill tree info.
"""

import struct
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLabel,
                              QSpinBox, QGroupBox, QFrame, QHBoxLayout)
from PyQt6.QtCore import Qt, pyqtSignal

from ui.style import (ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_VALUE,
                       BORDER, PERS_COLORS)
from save_layout import AGENT_BASE_OFFSET


class AgentEditor(QWidget):
    """Edit player/agent data: money, TP, rank."""

    data_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._save_file = None
        self._updating = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        header = QLabel("Agent / Player Data")
        header.setStyleSheet(
            f"color: {ACCENT}; font-size: 16px; font-weight: bold;")
        layout.addWidget(header)

        # ── Editable fields ──
        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._money_spin = QSpinBox()
        self._money_spin.setRange(0, 9_999_999)
        self._money_spin.setSingleStep(1000)
        self._money_spin.setPrefix("¥ ")
        self._money_spin.valueChanged.connect(self._on_money_changed)
        form.addRow("Money:", self._money_spin)

        self._tp_spin = QSpinBox()
        self._tp_spin.setRange(0, 999_999)
        self._tp_spin.setSingleStep(100)
        self._tp_spin.valueChanged.connect(self._on_tp_changed)
        form.addRow("Tamer Points:", self._tp_spin)

        self._tp_avail_spin = QSpinBox()
        self._tp_avail_spin.setRange(0, 999_999)
        self._tp_avail_spin.setSingleStep(100)
        self._tp_avail_spin.valueChanged.connect(self._on_tp_avail_changed)
        form.addRow("Available TP:", self._tp_avail_spin)

        layout.addLayout(form)

        # ── Read-only info ──
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {BORDER};")
        layout.addWidget(sep)

        info_form = QFormLayout()
        info_form.setSpacing(4)
        info_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._rank_label = QLabel("—")
        self._rank_label.setStyleSheet(f"color: {TEXT_VALUE}; font-weight: bold;")
        info_form.addRow("Agent Rank:", self._rank_label)

        layout.addLayout(info_form)

        # ── Skill Tree ──
        tree_group = QGroupBox("Agent Skill Tree (Read-Only)")
        tree_layout = QFormLayout()
        tree_layout.setSpacing(4)

        self._skill_labels = {}
        categories = [
            ("Valor", "valor", PERS_COLORS["Valor"]),
            ("Philanthropy", "phil", PERS_COLORS["Philanthropy"]),
            ("Amicability", "amic", PERS_COLORS["Amicability"]),
            ("Wisdom", "wisdom", PERS_COLORS["Wisdom"]),
            ("Loyalty", "loyalty", TEXT_VALUE),
        ]
        for name, key, color in categories:
            lbl = QLabel("—")
            lbl.setStyleSheet(f"color: {color};")
            self._skill_labels[key] = lbl
            name_lbl = QLabel(f"{name}:")
            name_lbl.setStyleSheet(f"color: {color}; font-weight: bold;")
            tree_layout.addRow(name_lbl, lbl)

        tree_group.setLayout(tree_layout)
        layout.addWidget(tree_group)

        layout.addStretch()

    def set_save_file(self, save_file):
        """Load agent data from a SaveFile."""
        self._updating = True
        self._save_file = save_file
        d = save_file._data
        base = AGENT_BASE_OFFSET

        self._money_spin.setValue(
            struct.unpack('<I', d[base + 0x058:base + 0x05C])[0])
        self._tp_avail_spin.setValue(
            struct.unpack('<I', d[base + 0x05C:base + 0x060])[0])
        self._tp_spin.setValue(
            struct.unpack('<I', d[base + 0x060:base + 0x064])[0])

        rank = struct.unpack('<I', d[base + 0x064:base + 0x068])[0]
        self._rank_label.setText(str(rank))

        valor = struct.unpack('<I', d[base + 0x068:base + 0x06C])[0]
        phil = struct.unpack('<I', d[base + 0x06C:base + 0x070])[0]
        amic = struct.unpack('<I', d[base + 0x070:base + 0x074])[0]
        wisdom = struct.unpack('<I', d[base + 0x074:base + 0x078])[0]
        loyalty = struct.unpack('<I', d[base + 0x080:base + 0x084])[0]

        self._skill_labels["valor"].setText(f"{valor} purchased")
        self._skill_labels["phil"].setText(f"{phil} purchased")
        self._skill_labels["amic"].setText(f"{amic} purchased")
        self._skill_labels["wisdom"].setText(f"{wisdom} purchased")
        self._skill_labels["loyalty"].setText(f"{loyalty} purchased")

        self._updating = False

    def _on_money_changed(self, value):
        if not self._updating and self._save_file:
            base = AGENT_BASE_OFFSET
            struct.pack_into('<I', self._save_file._data, base + 0x058, value)
            self._save_file._mark_dirty()
            self.data_changed.emit()

    def _on_tp_changed(self, value):
        if not self._updating and self._save_file:
            base = AGENT_BASE_OFFSET
            struct.pack_into('<I', self._save_file._data, base + 0x060, value)
            self._save_file._mark_dirty()
            self.data_changed.emit()

    def _on_tp_avail_changed(self, value):
        if not self._updating and self._save_file:
            base = AGENT_BASE_OFFSET
            struct.pack_into('<I', self._save_file._data, base + 0x05C, value)
            self._save_file._mark_dirty()
            self.data_changed.emit()
