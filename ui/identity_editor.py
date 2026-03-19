"""Identity tab for the Digimon editor.

Displays and edits: name, species, level, personality, talent, bond,
evo counter, EXP, HP, SP, nickname, evo history.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                              QLabel, QSpinBox, QComboBox, QSlider, QFrame,
                              QLineEdit, QGroupBox)
from PyQt6.QtCore import Qt, pyqtSignal

from ui.style import (ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_VALUE,
                       STAGE_COLORS, PERS_COLORS, PERS_CATEGORY, BG_PANEL,
                       BORDER, BG_INPUT)
from ui.icon_cache import get_icon
from save_layout import PERSONALITY_NAMES


class IdentityEditor(QWidget):
    """Edit identity fields for a single Digimon."""

    field_changed = pyqtSignal(str, object)  # field_name, new_value

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entry = None
        self._updating = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # ── Header: icon + species info ──
        header = QHBoxLayout()
        header.setSpacing(12)

        self._icon_label = QLabel()
        self._icon_label.setFixedSize(80, 80)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setStyleSheet(
            f"border: 2px solid {BORDER}; border-radius: 8px; "
            f"background-color: {BG_PANEL};")
        header.addWidget(self._icon_label)

        info_col = QVBoxLayout()
        info_col.setSpacing(1)
        self._species_label = QLabel("—")
        self._species_label.setStyleSheet(
            f"color: {TEXT_VALUE}; font-size: 15px; font-weight: bold;")
        info_col.addWidget(self._species_label)

        self._stage_label = QLabel("")
        info_col.addWidget(self._stage_label)

        self._attr_label = QLabel("")
        self._attr_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        info_col.addWidget(self._attr_label)

        info_col.addStretch()
        header.addLayout(info_col)
        header.addStretch()
        layout.addLayout(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {BORDER};")
        layout.addWidget(sep)

        # ── Nickname (editable, bypasses censorship) ──
        nick_row = QHBoxLayout()
        nick_row.setSpacing(6)
        nick_lbl = QLabel("Nickname:")
        nick_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        nick_lbl.setFixedWidth(65)
        nick_row.addWidget(nick_lbl)
        self._nick_edit = QLineEdit()
        self._nick_edit.setMaxLength(30)
        self._nick_edit.setPlaceholderText("(species name = no nickname)")
        self._nick_edit.editingFinished.connect(self._on_nickname_changed)
        nick_row.addWidget(self._nick_edit)
        layout.addLayout(nick_row)

        # ── Core fields ──
        form = QFormLayout()
        form.setSpacing(5)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Level
        self._level_spin = QSpinBox()
        self._level_spin.setRange(1, 99)
        self._level_spin.valueChanged.connect(lambda v: self._emit("level", v))
        form.addRow("Level:", self._level_spin)

        # Personality
        self._pers_combo = QComboBox()
        for pid, pname in sorted(PERSONALITY_NAMES.items()):
            cat = PERS_CATEGORY.get(pid, "Valor")
            self._pers_combo.addItem(f"{pname}  ({cat})", pid)
        self._pers_combo.currentIndexChanged.connect(self._on_pers_changed)
        form.addRow("Personality:", self._pers_combo)

        # Talent
        self._talent_spin = QSpinBox()
        self._talent_spin.setRange(0, 200)
        self._talent_spin.valueChanged.connect(lambda v: self._emit("talent", v))
        form.addRow("Talent:", self._talent_spin)

        # Bond
        bond_row = QHBoxLayout()
        self._bond_slider = QSlider(Qt.Orientation.Horizontal)
        self._bond_slider.setRange(0, 100)
        self._bond_slider.valueChanged.connect(self._on_bond_changed)
        bond_row.addWidget(self._bond_slider)
        self._bond_label = QLabel("0%")
        self._bond_label.setFixedWidth(36)
        self._bond_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._bond_label.setStyleSheet(f"color: {TEXT_VALUE};")
        bond_row.addWidget(self._bond_label)
        form.addRow("Bond:", bond_row)

        # EXP
        self._exp_spin = QSpinBox()
        self._exp_spin.setRange(0, 9_999_999)
        self._exp_spin.setSingleStep(1000)
        self._exp_spin.valueChanged.connect(lambda v: self._emit("exp", v))
        form.addRow("EXP:", self._exp_spin)

        # Current HP
        hp_row = QHBoxLayout()
        self._hp_spin = QSpinBox()
        self._hp_spin.setRange(0, 99_999)
        self._hp_spin.valueChanged.connect(lambda v: self._emit("cur_hp", v))
        hp_row.addWidget(self._hp_spin)
        hp_row.addWidget(QLabel("/"))
        self._hp_max_label = QLabel("—")
        self._hp_max_label.setStyleSheet(f"color: {TEXT_SECONDARY};")
        hp_row.addWidget(self._hp_max_label)
        form.addRow("HP:", hp_row)

        # Current SP
        sp_row = QHBoxLayout()
        self._sp_spin = QSpinBox()
        self._sp_spin.setRange(0, 99_999)
        self._sp_spin.valueChanged.connect(lambda v: self._emit("cur_sp", v))
        sp_row.addWidget(self._sp_spin)
        sp_row.addWidget(QLabel("/"))
        self._sp_max_label = QLabel("—")
        self._sp_max_label.setStyleSheet(f"color: {TEXT_SECONDARY};")
        sp_row.addWidget(self._sp_max_label)
        form.addRow("SP:", sp_row)

        # Evo Counter
        self._evo_spin = QSpinBox()
        self._evo_spin.setRange(0, 255)
        self._evo_spin.setToolTip(
            "Blue stat grant counter. Each evo that grants blue stats increments this.\n"
            "Reset to 0 for unlimited blue stat gains from evolution.")
        self._evo_spin.valueChanged.connect(lambda v: self._emit("evo_fwd_count", v))
        form.addRow("Evo Counter:", self._evo_spin)

        # Total Transforms (read-only)
        self._transforms_label = QLabel("—")
        self._transforms_label.setStyleSheet(f"color: {TEXT_SECONDARY};")
        form.addRow("Transforms:", self._transforms_label)

        # Creation Hash (read-only)
        self._hash_label = QLabel("—")
        self._hash_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 10px;")
        form.addRow("Hash:", self._hash_label)

        layout.addLayout(form)

        # ── Evolution History ──
        evo_header = QLabel("Evolution History")
        evo_header.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 11px; font-weight: bold;")
        layout.addWidget(evo_header)

        self._evo_row = QHBoxLayout()
        self._evo_row.setSpacing(4)
        self._evo_container = QWidget()
        self._evo_container.setLayout(self._evo_row)
        layout.addWidget(self._evo_container)

        layout.addStretch()

    def set_entry(self, entry):
        """Load a Digimon entry dict into the editor."""
        self._updating = True
        self._entry = entry

        # Header
        pm = get_icon(entry["species"], 80)
        self._icon_label.setPixmap(pm)
        self._species_label.setText(entry["species"])

        stage = entry.get("stage", "")
        color = STAGE_COLORS.get(stage, TEXT_SECONDARY)
        self._stage_label.setText(stage)
        self._stage_label.setStyleSheet(
            f"color: {color}; font-size: 11px; font-weight: bold;")

        attr = entry.get("attribute", "")
        dtype = entry.get("type", "")
        self._attr_label.setText(f"{attr} / {dtype}" if attr else "")

        # Nickname
        nick = entry.get("nickname")
        self._nick_edit.setText(entry.get("display_name", entry["species"]))

        # Fields
        self._level_spin.setValue(entry["level"])

        idx = self._pers_combo.findData(entry["personality_id"])
        if idx >= 0:
            self._pers_combo.setCurrentIndex(idx)

        self._talent_spin.setValue(entry["talent"])
        self._bond_slider.setValue(entry["bond"])
        self._bond_label.setText(f"{entry['bond']}%")
        self._exp_spin.setValue(entry.get("exp", 0))

        # HP/SP
        self._hp_spin.setValue(entry.get("cur_hp", 0))
        self._hp_max_label.setText(str(entry["total"].get("hp", 0)))
        self._sp_spin.setValue(entry.get("cur_sp", 0))
        self._sp_max_label.setText(str(entry["total"].get("sp", 0)))

        self._evo_spin.setValue(entry["evo_fwd_count"])
        self._transforms_label.setText(str(entry.get("total_transforms", 0)))
        self._hash_label.setText(f"0x{entry.get('creation_hash', 0):08X}")

        # Evo history
        self._clear_evo_row()
        for name in entry.get("evo_history", []):
            icon = get_icon(name, 24)
            lbl = QLabel()
            lbl.setPixmap(icon)
            lbl.setToolTip(name)
            lbl.setFixedSize(28, 28)
            self._evo_row.addWidget(lbl)
            arrow = QLabel("→")
            arrow.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 10px;")
            self._evo_row.addWidget(arrow)

        if entry.get("evo_history"):
            cur = QLabel()
            cur.setPixmap(get_icon(entry["species"], 24))
            cur.setToolTip(entry["species"])
            cur.setFixedSize(28, 28)
            self._evo_row.addWidget(cur)

        self._evo_row.addStretch()
        self._updating = False

    def _clear_evo_row(self):
        while self._evo_row.count():
            item = self._evo_row.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _emit(self, field, value):
        if not self._updating:
            self.field_changed.emit(field, value)

    def _on_pers_changed(self, idx):
        if not self._updating and idx >= 0:
            pid = self._pers_combo.itemData(idx)
            self.field_changed.emit("personality", pid)

    def _on_bond_changed(self, value):
        self._bond_label.setText(f"{value}%")
        if not self._updating:
            self.field_changed.emit("bond", value)

    def _on_nickname_changed(self):
        if self._updating or not self._entry:
            return
        new_name = self._nick_edit.text().strip()
        if new_name and new_name != self._entry.get("display_name", ""):
            self.field_changed.emit("nickname", new_name)
