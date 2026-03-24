"""Identity tab — species info, nickname, core stats, evolution history.

Clean layout with grouped sections and visual hierarchy.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                              QLabel, QSpinBox, QComboBox, QSlider, QFrame,
                              QLineEdit, QPushButton, QGridLayout)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from ui.style import (ACCENT, ACCENT_DIM, TEXT_PRIMARY, TEXT_SECONDARY,
                       TEXT_VALUE, STAGE_COLORS, PERS_COLORS, PERS_CATEGORY,
                       BG_PANEL, BG_INPUT, BORDER, STAT_BLUE, STAT_FARM)
from ui.icon_cache import get_icon
from save_layout import PERSONALITY_NAMES

_SPIN_STYLE = f"""
    QSpinBox {{
        background: transparent;
        color: {TEXT_VALUE};
        border: none;
        border-bottom: 1px solid {BORDER};
        font-size: 12px;
        font-weight: bold;
        padding: 1px 4px;
    }}
    QSpinBox::up-button, QSpinBox::down-button {{
        width: 0; height: 0; border: none;
    }}
    QSpinBox:focus {{
        background: rgba(0,191,255,0.1);
        border-bottom: 1px solid {ACCENT};
    }}
"""


def _card(title):
    """Create a styled group card with a title."""
    card = QWidget()
    card.setStyleSheet(
        f"background-color: rgba(18, 18, 32, 180); "
        f"border: 1px solid {BORDER}; border-radius: 6px;")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(10, 6, 10, 10)
    layout.setSpacing(4)
    if title:
        lbl = QLabel(title)
        lbl.setStyleSheet(
            f"color: rgba(0,191,255,0.5); font-size: 9px; font-weight: bold; "
            f"letter-spacing: 2px; border: none; background: transparent;")
        layout.addWidget(lbl)
    return card, layout


class IdentityEditor(QWidget):
    """Edit identity fields for a single Digimon."""

    field_changed = pyqtSignal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entry = None
        self._updating = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)

        # ── Species Header Card ──
        header_card, header_layout = _card(None)
        header = QHBoxLayout()
        header.setSpacing(12)

        self._icon_label = QLabel()
        self._icon_label.setFixedSize(72, 72)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setStyleSheet(
            f"border: 2px solid {BORDER}; border-radius: 8px; "
            f"background-color: rgba(12,12,20,200);")
        header.addWidget(self._icon_label)

        info = QVBoxLayout()
        info.setSpacing(1)

        name_row = QHBoxLayout()
        name_row.setSpacing(8)
        self._species_label = QLabel("—")
        self._species_label.setStyleSheet(
            f"color: {TEXT_VALUE}; font-size: 16px; font-weight: bold; "
            f"border: none; background: transparent;")
        name_row.addWidget(self._species_label)
        self._nick_edit = QLineEdit()
        self._nick_edit.setMaxLength(30)
        self._nick_edit.setPlaceholderText("Nickname")
        self._nick_edit.setStyleSheet(
            f"border: none; border-bottom: 1px solid {BORDER}; "
            f"background: transparent; color: {ACCENT}; "
            f"font-size: 13px; font-style: italic; padding: 0 4px;")
        self._nick_edit.editingFinished.connect(self._on_nickname_changed)
        name_row.addWidget(self._nick_edit)
        name_row.addStretch()
        info.addLayout(name_row)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(6)
        self._stage_label = QLabel("")
        self._stage_label.setStyleSheet("border: none; background: transparent;")
        meta_row.addWidget(self._stage_label)
        self._attr_label = QLabel("")
        self._attr_label.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 11px; border: none; background: transparent;")
        meta_row.addWidget(self._attr_label)
        meta_row.addStretch()
        info.addLayout(meta_row)

        # Personality dropdown on main card
        pers_row = QHBoxLayout()
        pers_row.setSpacing(6)
        self._pers_combo = QComboBox()
        for pid, pname in sorted(PERSONALITY_NAMES.items()):
            cat = PERS_CATEGORY.get(pid, "Valor")
            self._pers_combo.addItem(f"{pname}  ({cat})", pid)
        self._pers_combo.setFixedHeight(22)
        self._pers_combo.currentIndexChanged.connect(self._on_pers_changed)
        pers_row.addWidget(self._pers_combo)
        pers_row.addStretch()

        self._change_btn = QPushButton("Change Species...")
        self._change_btn.setFixedWidth(120)
        self._change_btn.setFixedHeight(22)
        self._change_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {TEXT_SECONDARY};
                border: 1px solid {BORDER}; border-radius: 3px;
                font-size: 9px; padding: 0 6px;
            }}
            QPushButton:hover {{ color: {ACCENT}; border-color: {ACCENT}; }}
        """)
        self._change_btn.clicked.connect(self._on_change_species)
        pers_row.addWidget(self._change_btn)
        info.addLayout(pers_row)

        header.addLayout(info)
        header.addStretch()
        header_layout.addLayout(header)
        layout.addWidget(header_card)

        # Nickname is now inline with species name above

        # ── Core Stats Card ──
        core_card, core_layout = _card("CORE STATS")
        grid = QGridLayout()
        grid.setSpacing(6)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

        def _label(text, color=TEXT_SECONDARY):
            l = QLabel(text)
            l.setStyleSheet(
                f"color: {color}; font-size: 11px; border: none; background: transparent;")
            l.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            return l

        # Row 0: Level + EXP
        grid.addWidget(_label("Level:"), 0, 0)
        self._level_spin = QSpinBox()
        self._level_spin.setRange(1, 99)
        self._level_spin.setStyleSheet(_SPIN_STYLE)
        self._level_spin.valueChanged.connect(lambda v: self._emit("level", v))
        grid.addWidget(self._level_spin, 0, 1)

        grid.addWidget(_label("EXP:"), 0, 2)
        self._exp_spin = QSpinBox()
        self._exp_spin.setRange(0, 9_999_999)
        self._exp_spin.setSingleStep(1000)
        self._exp_spin.setStyleSheet(_SPIN_STYLE)
        self._exp_spin.valueChanged.connect(lambda v: self._emit("exp", v))
        grid.addWidget(self._exp_spin, 0, 3)

        # Row 1: Talent + Bond
        grid.addWidget(_label("Talent:"), 1, 0)
        self._talent_spin = QSpinBox()
        self._talent_spin.setRange(0, 200)
        self._talent_spin.setStyleSheet(_SPIN_STYLE)
        self._talent_spin.valueChanged.connect(lambda v: self._emit("talent", v))
        grid.addWidget(self._talent_spin, 1, 1)

        grid.addWidget(_label("Bond:"), 1, 2)
        bond_w = QHBoxLayout()
        self._bond_slider = QSlider(Qt.Orientation.Horizontal)
        self._bond_slider.setRange(0, 100)
        self._bond_slider.valueChanged.connect(self._on_bond_changed)
        bond_w.addWidget(self._bond_slider)
        self._bond_label = QLabel("0%")
        self._bond_label.setFixedWidth(32)
        self._bond_label.setStyleSheet(
            f"color: {ACCENT}; font-weight: bold; font-size: 11px; "
            f"border: none; background: transparent;")
        self._bond_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        bond_w.addWidget(self._bond_label)
        grid.addLayout(bond_w, 1, 3)

        # Row 2: HP bar (click to heal) | SP bar (click to refill)
        grid.addWidget(_label("HP:", "#E57373"), 2, 0)
        hp_w = QHBoxLayout()
        hp_w.setSpacing(4)
        self._hp_bar = QWidget()
        self._hp_bar.setFixedHeight(12)
        self._hp_bar.setMinimumWidth(60)
        self._hp_bar.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hp_bar.setToolTip("Click to fully heal")
        self._hp_bar.setStyleSheet(
            "background: #1A1A2E; border: 1px solid rgba(229,115,115,0.3); border-radius: 3px;")
        self._hp_fill = QWidget(self._hp_bar)
        self._hp_fill.setStyleSheet("background: #E57373; border-radius: 2px;")
        self._hp_fill.setGeometry(1, 1, 0, 10)
        self._hp_bar.mousePressEvent = lambda e: self._on_heal_hp()
        hp_w.addWidget(self._hp_bar, 1)
        self._hp_text = QLabel("—")
        self._hp_text.setStyleSheet(
            f"color: #E57373; font-size: 10px; border: none; background: transparent;")
        self._hp_text.mouseDoubleClickEvent = lambda e: self._show_hp_edit()
        hp_w.addWidget(self._hp_text)
        # Hidden spinbox for double-click editing
        self._hp_spin = QSpinBox()
        self._hp_spin.setRange(0, 99_999)
        self._hp_spin.setStyleSheet(_SPIN_STYLE)
        self._hp_spin.valueChanged.connect(lambda v: self._emit("cur_hp", v))
        self._hp_spin.editingFinished.connect(self._hide_hp_edit)
        self._hp_spin.hide()
        hp_w.addWidget(self._hp_spin)
        grid.addLayout(hp_w, 2, 1)

        grid.addWidget(_label("SP:", "#CE93D8"), 2, 2)
        sp_w = QHBoxLayout()
        sp_w.setSpacing(4)
        self._sp_bar = QWidget()
        self._sp_bar.setFixedHeight(12)
        self._sp_bar.setMinimumWidth(60)
        self._sp_bar.setCursor(Qt.CursorShape.PointingHandCursor)
        self._sp_bar.setToolTip("Click to fully refill")
        self._sp_bar.setStyleSheet(
            "background: #1A1A2E; border: 1px solid rgba(206,147,216,0.3); border-radius: 3px;")
        self._sp_fill = QWidget(self._sp_bar)
        self._sp_fill.setStyleSheet("background: #CE93D8; border-radius: 2px;")
        self._sp_fill.setGeometry(1, 1, 0, 10)
        self._sp_bar.mousePressEvent = lambda e: self._on_refill_sp()
        sp_w.addWidget(self._sp_bar, 1)
        self._sp_text = QLabel("—")
        self._sp_text.setStyleSheet(
            f"color: #CE93D8; font-size: 10px; border: none; background: transparent;")
        self._sp_text.mouseDoubleClickEvent = lambda e: self._show_sp_edit()
        sp_w.addWidget(self._sp_text)
        self._sp_spin = QSpinBox()
        self._sp_spin.setRange(0, 99_999)
        self._sp_spin.setStyleSheet(_SPIN_STYLE)
        self._sp_spin.valueChanged.connect(lambda v: self._emit("cur_sp", v))
        self._sp_spin.editingFinished.connect(self._hide_sp_edit)
        self._sp_spin.hide()
        sp_w.addWidget(self._sp_spin)
        grid.addLayout(sp_w, 2, 3)

        core_layout.addLayout(grid)
        layout.addWidget(core_card)

        # ── Evo & Metadata Card ──
        evo_card, evo_layout = _card("EVOLUTION & METADATA")

        meta_grid = QGridLayout()
        meta_grid.setSpacing(4)
        meta_grid.setColumnStretch(1, 1)
        meta_grid.setColumnStretch(3, 1)

        meta_grid.addWidget(_label("Evo Counter:"), 0, 0)
        self._evo_spin = QSpinBox()
        self._evo_spin.setRange(0, 100)
        self._evo_spin.setStyleSheet(_SPIN_STYLE)
        self._evo_spin.setToolTip("Reset to 0 for unlimited blue stat gains from evolution")
        self._evo_spin.valueChanged.connect(lambda v: self._emit("evo_fwd_count", v))
        meta_grid.addWidget(self._evo_spin, 0, 1)

        meta_grid.addWidget(_label("Transforms:"), 0, 2)
        self._transforms = QLabel("—")
        self._transforms.setStyleSheet(
            f"color: {TEXT_VALUE}; font-size: 11px; border: none; background: transparent;")
        meta_grid.addWidget(self._transforms, 0, 3)

        meta_grid.addWidget(_label("Talent Acc*:"), 1, 0)
        self._tick_spin = QSpinBox()
        self._tick_spin.setRange(0, 999_999_999)
        self._tick_spin.setStyleSheet(_SPIN_STYLE)
        self._tick_spin.setToolTip("Hidden talent accumulator*. +500 on evolution. On evo, talent = floor(this / 1000).\n*Must be unique per species — duplicates auto-fixed on save.")
        self._tick_spin.valueChanged.connect(lambda v: self._emit("talent_acc", v))
        meta_grid.addWidget(self._tick_spin, 1, 1)

        meta_grid.addWidget(_label("Hash:"), 1, 2)
        self._hash = QLabel("—")
        self._hash.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 10px; font-family: monospace; "
            f"border: none; background: transparent;")
        meta_grid.addWidget(self._hash, 1, 3)

        evo_layout.addLayout(meta_grid)

        # Evo history row
        evo_hist_label = QLabel("Evolution History:")
        evo_hist_label.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 10px; border: none; "
            f"background: transparent; padding-top: 4px;")
        evo_layout.addWidget(evo_hist_label)

        self._evo_row = QHBoxLayout()
        self._evo_row.setSpacing(3)
        self._evo_container = QWidget()
        self._evo_container.setStyleSheet("border: none; background: transparent;")
        self._evo_container.setLayout(self._evo_row)
        evo_layout.addWidget(self._evo_container)

        layout.addWidget(evo_card)
        layout.addStretch()

    def set_entry(self, entry):
        self._updating = True
        self._entry = entry

        pm = get_icon(entry["species"], 72)
        self._icon_label.setPixmap(pm)
        self._species_label.setText(entry["species"])

        stage = entry.get("stage", "")
        color = STAGE_COLORS.get(stage, TEXT_SECONDARY)
        self._stage_label.setText(stage)
        self._stage_label.setStyleSheet(
            f"color: {color}; font-size: 11px; font-weight: bold; "
            f"border: none; background: transparent;")

        attr = entry.get("attribute", "")
        dtype = entry.get("type", "")
        self._attr_label.setText(f"{attr} / {dtype}" if attr else "")

        self._nick_edit.setText(entry.get("display_name", entry["species"]))
        self._level_spin.setValue(entry["level"])
        self._exp_spin.setValue(entry.get("exp", 0))

        idx = self._pers_combo.findData(entry["personality_id"])
        if idx >= 0:
            self._pers_combo.setCurrentIndex(idx)

        self._talent_spin.setValue(entry["talent"])
        self._bond_slider.setValue(entry["bond"])
        self._bond_label.setText(f"{entry['bond']}%")

        cur_hp = entry.get("cur_hp", 0)
        self._hp_spin.setValue(cur_hp)
        self._hp_spin.hide()
        self._update_hp_bar(cur_hp)

        cur_sp = entry.get("cur_sp", 0)
        self._sp_spin.setValue(cur_sp)
        self._sp_spin.hide()
        self._update_sp_bar(cur_sp)

        self._evo_spin.setValue(entry["evo_fwd_count"])
        self._transforms.setText(str(entry.get("total_transforms", 0)))
        self._tick_spin.setValue(entry.get("talent_acc", 0))
        self._hash.setText(f"0x{entry.get('creation_hash', 0):08X}")

        # Evo history
        self._clear_evo_row()
        for name in entry.get("evo_history", []):
            lbl = QLabel()
            lbl.setPixmap(get_icon(name, 22))
            lbl.setToolTip(name)
            lbl.setFixedSize(24, 24)
            lbl.setStyleSheet("border: none; background: transparent;")
            self._evo_row.addWidget(lbl)
            arrow = QLabel("→")
            arrow.setStyleSheet(
                f"color: {TEXT_SECONDARY}; font-size: 9px; border: none; background: transparent;")
            self._evo_row.addWidget(arrow)

        if entry.get("evo_history"):
            cur = QLabel()
            cur.setPixmap(get_icon(entry["species"], 22))
            cur.setToolTip(entry["species"])
            cur.setFixedSize(24, 24)
            cur.setStyleSheet("border: none; background: transparent;")
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
            self.field_changed.emit("personality", self._pers_combo.itemData(idx))

    def _on_bond_changed(self, value):
        self._bond_label.setText(f"{value}%")
        if not self._updating:
            self.field_changed.emit("bond", value)

    def _on_nickname_changed(self):
        if self._updating or not self._entry:
            return
        new = self._nick_edit.text().strip()
        if not new or new == self._entry.get("display_name", ""):
            return
        # Don't emit species name as nickname when there was no actual nickname
        if new == self._entry.get("species", "") and not self._entry.get("nickname"):
            return
        self.field_changed.emit("nickname", new)

    def _on_change_species(self):
        if not self._entry:
            return
        from ui.species_chooser import SpeciesChooserDialog
        dlg = SpeciesChooserDialog(self._entry["species"], self)
        if dlg.exec() and dlg.selected_id:
            self.field_changed.emit("species_change", dlg.selected_id)

    def _update_hp_bar(self, cur):
        """Update HP bar — solid fill on dark background."""
        raw = self._entry["total"].get("hp", 1) if self._entry else 1
        bar_max = max(cur, raw, 1)
        pct = max(min(cur / bar_max, 1.0), 0.0)
        bar_w = max(self._hp_bar.width() - 2, 1)
        self._hp_fill.setGeometry(1, 1, int(pct * bar_w), 10)
        self._hp_text.setText(f"{cur}")

    def _update_sp_bar(self, cur):
        raw = self._entry["total"].get("sp", 1) if self._entry else 1
        bar_max = max(cur, raw, 1)
        pct = max(min(cur / bar_max, 1.0), 0.0)
        bar_w = max(self._sp_bar.width() - 2, 1)
        self._sp_fill.setGeometry(1, 1, int(pct * bar_w), 10)
        self._sp_text.setText(f"{cur}")

    def _on_heal_hp(self):
        if not self._entry or self._updating:
            return
        # Use raw total as heal target — game caps to actual max on load
        raw = self._entry["total"].get("hp", 0)
        heal_to = max(raw, self._hp_spin.value())
        self._hp_spin.setValue(heal_to)
        self._update_hp_bar(heal_to)

    def _on_refill_sp(self):
        if not self._entry or self._updating:
            return
        raw = self._entry["total"].get("sp", 0)
        refill_to = max(raw, self._sp_spin.value())
        self._sp_spin.setValue(refill_to)
        self._update_sp_bar(refill_to)

    def _show_hp_edit(self):
        self._hp_text.hide()
        self._hp_bar.hide()
        self._hp_spin.show()
        self._hp_spin.setFocus()
        self._hp_spin.selectAll()

    def _hide_hp_edit(self):
        self._hp_spin.hide()
        self._hp_text.show()
        self._hp_bar.show()
        self._update_hp_bar(self._hp_spin.value())

    def _show_sp_edit(self):
        self._sp_text.hide()
        self._sp_bar.hide()
        self._sp_spin.show()
        self._sp_spin.setFocus()
        self._sp_spin.selectAll()

    def _hide_sp_edit(self):
        self._sp_spin.hide()
        self._sp_text.show()
        self._sp_bar.show()
        self._update_sp_bar(self._sp_spin.value())
