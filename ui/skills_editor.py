"""Skills & Equipment tab for the Digimon editor.

Displays and edits attachment skills (4 slots) and equipment (2 slots).
"""

import logging
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QFrame, QComboBox, QGroupBox)
from PyQt6.QtCore import Qt, pyqtSignal

logger = logging.getLogger(__name__)

from ui.style import (ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_VALUE,
                       BORDER, BG_INPUT, BG_PANEL, STAT_BLUE)

_skill_list = None
_equip_list = None


def _load_skill_list():
    """Load attachment skills only (learn_level > 0) for the combo box.

    Special skills (learn_level=0) are NOT included — they're shown
    read-only in the special skills section above.
    """
    global _skill_list
    if _skill_list is not None:
        return _skill_list
    from save_data import _get_db
    db = _get_db()
    _skill_list = [(0, "(Empty)")]
    for row in db.execute(
            "SELECT s.id, s.name FROM skills s "
            "JOIN digimon_skills ds ON s.id = ds.skill_id "
            "WHERE ds.learn_level > 0 "
            "GROUP BY s.id ORDER BY s.name"):
        if row["name"]:
            _skill_list.append((row["id"], row["name"]))
    existing_ids = {s[0] for s in _skill_list}
    # Append modded skill names
    from save_data import _mod_overlay
    if _mod_overlay and _mod_overlay.is_active and _mod_overlay.skill_names:
        for sid_str, name in _mod_overlay.skill_names.items():
            try:
                sid = int(sid_str)
                if sid not in existing_ids and name:
                    _skill_list.append((sid, name))
            except (ValueError, TypeError):
                pass
    return _skill_list


def _load_equip_list():
    """Load all equipment items for the combo box."""
    global _equip_list
    if _equip_list is not None:
        return _equip_list
    from save_data import _get_db
    db = _get_db()
    _equip_list = [(0, "(Empty)")]
    try:
        for row in db.execute(
                "SELECT item_id, name FROM equipment ORDER BY name"):
            if row["name"]:
                _equip_list.append((int(row["item_id"]), row["name"]))
    except Exception as e:
        logger.warning("Failed to load equipment list: %s", e)
    return _equip_list


def _get_skill_name(skill_id):
    for sid, name in _load_skill_list():
        if sid == skill_id:
            return name
    return f"Skill #{skill_id}" if skill_id else "(Empty)"


class SkillsEditor(QWidget):
    """Edit attachment skills and equipment."""

    field_changed = pyqtSignal(str, object)  # field_name, new_value

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entry = None
        self._updating = False
        self._skill_combos = []
        self._equip_combos = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # ── Special Skills (read-only display) ──
        special_header = QLabel("Special Skills (Learned)")
        special_header.setStyleSheet(
            f"color: {ACCENT}; font-size: 13px; font-weight: bold;")
        layout.addWidget(special_header)

        self._special_label = QLabel("Load a Digimon to see skills")
        self._special_label.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 11px; padding: 4px;")
        self._special_label.setWordWrap(True)
        layout.addWidget(self._special_label)

        # Separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setStyleSheet(f"color: {BORDER};")
        layout.addWidget(sep1)

        # ── Attachment Skills (editable) ──
        attach_header = QLabel("Attachment Skills")
        attach_header.setStyleSheet(
            f"color: {STAT_BLUE}; font-size: 13px; font-weight: bold;")
        layout.addWidget(attach_header)

        skills = _load_skill_list()
        for i in range(4):
            row = QHBoxLayout()
            row.setSpacing(6)
            lbl = QLabel(f"Slot {i+1}:")
            lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
            lbl.setFixedWidth(48)
            row.addWidget(lbl)

            combo = QComboBox()
            combo.setMaxVisibleItems(20)
            for sid, name in skills:
                combo.addItem(name, sid)
            slot_idx = i
            combo.currentIndexChanged.connect(
                lambda idx, s=slot_idx: self._on_skill_changed(s, idx))
            self._skill_combos.append(combo)
            row.addWidget(combo, 1)
            layout.addLayout(row)

        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(f"color: {BORDER};")
        layout.addWidget(sep2)

        # ── Equipment (editable) ──
        equip_header = QLabel("Equipment")
        equip_header.setStyleSheet(
            f"color: {ACCENT}; font-size: 13px; font-weight: bold;")
        layout.addWidget(equip_header)

        equips = _load_equip_list()
        for i in range(2):
            row = QHBoxLayout()
            row.setSpacing(6)
            lbl = QLabel(f"Slot {i+1}:")
            lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
            lbl.setFixedWidth(48)
            row.addWidget(lbl)

            combo = QComboBox()
            combo.setMaxVisibleItems(20)
            for eid, name in equips:
                combo.addItem(name, eid)
            slot_idx = i
            combo.currentIndexChanged.connect(
                lambda idx, s=slot_idx: self._on_equip_changed(s, idx))
            self._equip_combos.append(combo)
            row.addWidget(combo, 1)
            layout.addLayout(row)

        layout.addStretch()

    def set_entry(self, entry):
        """Load skills and equipment from a Digimon entry."""
        self._updating = True
        self._entry = entry

        # Special skills — look up from database
        from save_data import _get_db
        db = _get_db()
        species = entry.get("species", "")
        rows = db.execute(
            "SELECT s.name, ds.learn_level FROM digimon_skills ds "
            "JOIN skills s ON ds.skill_id = s.id "
            "JOIN digimon d ON ds.digimon_id = d.id "
            "WHERE d.name = ? ORDER BY ds.learn_level",
            (species,)
        ).fetchall()
        if rows:
            parts = [f"{r['name']} (Lv{r['learn_level']})" for r in rows]
            self._special_label.setText("  |  ".join(parts))
        else:
            self._special_label.setText("No special skills found")

        # Attachment skills
        attach = entry.get("attach_skills", [0, 0, 0, 0])
        for i, combo in enumerate(self._skill_combos):
            sid = attach[i] if i < len(attach) else 0
            idx = combo.findData(sid)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            elif sid and sid != 0:
                combo.addItem(f"Unknown (#{sid})", sid)
                combo.setCurrentIndex(combo.count() - 1)
            else:
                combo.setCurrentIndex(0)

        # Equipment
        for i, combo in enumerate(self._equip_combos):
            eid = entry.get(f"equip_{i+1}", 0)
            idx = combo.findData(eid)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            elif eid and eid != 0:
                combo.addItem(f"Unknown (#{eid})", eid)
                combo.setCurrentIndex(combo.count() - 1)
            else:
                combo.setCurrentIndex(0)

        self._updating = False

    def _on_skill_changed(self, slot_idx, combo_idx):
        if self._updating or not self._entry:
            return
        combo = self._skill_combos[slot_idx]
        skill_id = combo.itemData(combo_idx)
        self.field_changed.emit(f"attach_skill_{slot_idx}", skill_id)

    def _on_equip_changed(self, slot_idx, combo_idx):
        if self._updating or not self._entry:
            return
        combo = self._equip_combos[slot_idx]
        equip_id = combo.itemData(combo_idx)
        self.field_changed.emit(f"equip_{slot_idx}", equip_id)
