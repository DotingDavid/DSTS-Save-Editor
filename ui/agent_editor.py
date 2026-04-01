"""Agent/Player data editor.

Edit money, Tamer Points, agent rank, and unlock skill trees.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLabel,
                              QSpinBox, QGroupBox, QFrame, QHBoxLayout,
                              QPushButton, QMessageBox, QLineEdit)
from PyQt6.QtCore import Qt, pyqtSignal

from ui.style import (ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_VALUE,
                       BORDER, PERS_COLORS)


# Category ID → (name, tree_group range start, tree_group range end, count_offset)
CATEGORIES = {
    1: ("Valor",        1,   50,  0x068),
    2: ("Philanthropy", 51,  100, 0x06C),
    3: ("Amicability",  101, 150, 0x070),
    4: ("Wisdom",       151, 200, 0x074),
    5: ("Loyalty",      201, 224, 0x080),
}


class AgentEditor(QWidget):
    """Edit player/agent data: money, TP, rank, skills."""

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

        self._name_edit = QLineEdit()
        self._name_edit.setMaxLength(30)
        self._name_edit.setPlaceholderText("Player name")
        self._name_edit.editingFinished.connect(self._on_name_changed)
        form.addRow("Player Name:", self._name_edit)

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

        # ── Skill Trees ──
        tree_group = QGroupBox("Agent Skill Tree")
        tree_layout = QVBoxLayout()
        tree_layout.setSpacing(6)

        self._skill_labels = {}
        self._unlock_btns = {}

        cat_colors = {
            1: PERS_COLORS["Valor"],
            2: PERS_COLORS["Philanthropy"],
            3: PERS_COLORS["Amicability"],
            4: PERS_COLORS["Wisdom"],
            5: TEXT_VALUE,
        }

        for cat_id, (name, _, _, _) in CATEGORIES.items():
            color = cat_colors[cat_id]
            row = QHBoxLayout()
            row.setSpacing(8)

            name_lbl = QLabel(f"{name}:")
            name_lbl.setStyleSheet(f"color: {color}; font-weight: bold;")
            name_lbl.setFixedWidth(110)
            row.addWidget(name_lbl)

            count_lbl = QLabel("—")
            count_lbl.setStyleSheet(f"color: {color};")
            count_lbl.setFixedWidth(100)
            self._skill_labels[cat_id] = count_lbl
            row.addWidget(count_lbl)

            btn = QPushButton("Unlock All")
            btn.setFixedWidth(80)
            btn.setFixedHeight(22)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {TEXT_SECONDARY};
                    border: 1px solid {BORDER}; border-radius: 3px;
                    font-size: 9px;
                }}
                QPushButton:hover {{ color: {color}; border-color: {color}; }}
            """)
            btn.clicked.connect(lambda _, c=cat_id: self._unlock_category(c))
            self._unlock_btns[cat_id] = btn
            row.addWidget(btn)
            row.addStretch()

            tree_layout.addLayout(row)

        # Unlock All button
        all_row = QHBoxLayout()
        all_row.setSpacing(8)
        self._unlock_all_btn = QPushButton("Unlock All Skills")
        self._unlock_all_btn.setFixedHeight(28)
        self._unlock_all_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {ACCENT};
                border: 1px solid {ACCENT}; border-radius: 4px;
                font-size: 11px; font-weight: bold; padding: 0 16px;
            }}
            QPushButton:hover {{ background: rgba(0,191,255,0.1); }}
        """)
        self._unlock_all_btn.clicked.connect(self._unlock_all)
        all_row.addWidget(self._unlock_all_btn)
        all_row.addStretch()
        tree_layout.addLayout(all_row)

        tree_group.setLayout(tree_layout)
        layout.addWidget(tree_group)

        layout.addStretch()

    def set_save_file(self, save_file):
        """Load agent data from a SaveFile."""
        self._updating = True
        self._save_file = save_file

        self._name_edit.setText(save_file.read_str(0x0FDE90, 32))
        self._money_spin.setValue(save_file.read_agent_u32(0x058))
        self._tp_avail_spin.setValue(save_file.read_agent_u32(0x05C))
        self._tp_spin.setValue(save_file.read_agent_u32(0x060))

        rank = save_file.read_agent_u32(0x064)
        self._rank_label.setText(str(rank))

        self._refresh_skill_counts()
        self._updating = False

    def _refresh_skill_counts(self):
        """Read skill records and update category counts."""
        if not self._save_file:
            return

        # Count purchased per category
        counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        totals = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

        for i in range(208):
            _, cat, purchased, _ = self._save_file.read_agent_skill(i)
            if cat in counts:
                totals[cat] += 1
                if purchased:
                    counts[cat] += 1

        for cat_id, (name, _, _, _) in CATEGORIES.items():
            bought = counts.get(cat_id, 0)
            total = totals.get(cat_id, 0)
            lbl = self._skill_labels[cat_id]
            if bought == total and total > 0:
                lbl.setText(f"{bought}/{total} (complete)")
            else:
                lbl.setText(f"{bought}/{total}")

    def _unlock_category(self, cat_id, skip_confirm=False):
        """Unlock all skills in a category."""
        if not self._save_file:
            return

        if not skip_confirm:
            name = CATEGORIES[cat_id][0]
            reply = QMessageBox.question(
                self, "Unlock Skills",
                f"Unlock all {name} skills?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return

        unlocked = 0
        for i in range(208):
            _, cat, purchased, _ = self._save_file.read_agent_skill(i)
            if cat == cat_id and not purchased:
                self._save_file.write_agent_skill_flags(i, 1, 1)
                unlocked += 1

        if unlocked > 0:
            # Update the category purchase count
            _, _, _, count_off = CATEGORIES[cat_id]
            old_count = self._save_file.read_agent_u32(count_off)
            self._save_file.write_agent_u32(count_off, old_count + unlocked)

            self._refresh_skill_counts()
            self.data_changed.emit()

    def _unlock_all(self):
        """Unlock all skills in all categories."""
        if not self._save_file:
            return
        reply = QMessageBox.question(
            self, "Unlock All Skills",
            "Unlock ALL agent skills in every category?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        for cat_id in CATEGORIES:
            self._unlock_category(cat_id, skip_confirm=True)

    def _on_name_changed(self):
        if not self._updating and self._save_file:
            name = self._name_edit.text().strip()
            if not name:
                return
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
