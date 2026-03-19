"""Skills & Equipment tab for the Digimon editor.

Displays attachment skills (4 slots) and equipment (2 slots).
Read-only for now — editing skill/equipment IDs needs verification.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QFrame, QGridLayout, QGroupBox)
from PyQt6.QtCore import Qt

from ui.style import (ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_VALUE,
                       BORDER, BG_INPUT, BG_PANEL, STAT_BLUE)
from ui.icon_cache import get_icon

_skill_cache = None
_equip_cache = None


def _get_skill_name(skill_id):
    """Look up a skill name by game ID."""
    global _skill_cache
    if _skill_cache is None:
        from save_data import _get_db
        db = _get_db()
        _skill_cache = {}
        for row in db.execute("SELECT id, name FROM skills"):
            _skill_cache[row["id"]] = row["name"]
    return _skill_cache.get(skill_id, f"Skill #{skill_id}")


def _get_equip_info(item_id):
    """Look up equipment name and stats by item ID."""
    global _equip_cache
    if _equip_cache is None:
        from save_data import _get_db
        db = _get_db()
        _equip_cache = {}
        try:
            for row in db.execute(
                    "SELECT item_id, name, hp, sp, atk, def_, int_, spi, spd "
                    "FROM equipment"):
                _equip_cache[row["item_id"]] = dict(row)
        except Exception:
            pass
    info = _equip_cache.get(item_id)
    if info:
        return info
    # Fallback: just the name from item_names
    from save_data import get_item_name
    return {"name": get_item_name(item_id), "item_id": item_id}


class SkillSlotWidget(QWidget):
    """Display a single attachment skill slot."""

    def __init__(self, slot_num, parent=None):
        super().__init__(parent)
        self._slot_num = slot_num

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)

        header = QHBoxLayout()
        self._slot_label = QLabel(f"Slot {slot_num}")
        self._slot_label.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 10px;")
        header.addWidget(self._slot_label)
        header.addStretch()
        layout.addLayout(header)

        self._name_label = QLabel("Empty")
        self._name_label.setStyleSheet(
            f"color: {TEXT_VALUE}; font-size: 12px; font-weight: bold;")
        layout.addWidget(self._name_label)

        self._detail_label = QLabel("")
        self._detail_label.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 10px;")
        layout.addWidget(self._detail_label)

        self.setStyleSheet(
            f"background-color: {BG_INPUT}; border: 1px solid {BORDER}; "
            f"border-radius: 4px;")

    def set_skill(self, skill_id):
        if not skill_id or skill_id <= 0:
            self._name_label.setText("Empty")
            self._name_label.setStyleSheet(
                f"color: {TEXT_SECONDARY}; font-size: 12px;")
            self._detail_label.setText("")
        else:
            name = _get_skill_name(skill_id)
            self._name_label.setText(name)
            self._name_label.setStyleSheet(
                f"color: {STAT_BLUE}; font-size: 12px; font-weight: bold;")
            self._detail_label.setText(f"ID: {skill_id}")


class EquipSlotWidget(QWidget):
    """Display a single equipment slot."""

    def __init__(self, slot_num, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)

        header = QLabel(f"Equipment {slot_num}")
        header.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 10px;")
        layout.addWidget(header)

        self._name_label = QLabel("Empty")
        self._name_label.setStyleSheet(
            f"color: {TEXT_VALUE}; font-size: 12px; font-weight: bold;")
        layout.addWidget(self._name_label)

        self._stats_label = QLabel("")
        self._stats_label.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 10px;")
        self._stats_label.setWordWrap(True)
        layout.addWidget(self._stats_label)

        self.setStyleSheet(
            f"background-color: {BG_INPUT}; border: 1px solid {BORDER}; "
            f"border-radius: 4px;")

    def set_equipment(self, item_id):
        if not item_id or item_id <= 0:
            self._name_label.setText("Empty")
            self._name_label.setStyleSheet(
                f"color: {TEXT_SECONDARY}; font-size: 12px;")
            self._stats_label.setText("")
        else:
            info = _get_equip_info(item_id)
            name = info.get("name", f"Item #{item_id}")
            self._name_label.setText(name)
            self._name_label.setStyleSheet(
                f"color: {ACCENT}; font-size: 12px; font-weight: bold;")

            # Show stat bonuses
            stat_parts = []
            for key, label in [("hp", "HP"), ("sp", "SP"), ("atk", "ATK"),
                                ("def_", "DEF"), ("int_", "INT"),
                                ("spi", "SPI"), ("spd", "SPD")]:
                val = info.get(key, 0)
                if val and val != 0:
                    stat_parts.append(f"{label} +{val}")
            self._stats_label.setText("  ".join(stat_parts) if stat_parts else f"ID: {item_id}")


class SkillsEditor(QWidget):
    """Skills & Equipment display panel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # ── Attachment Skills ──
        skills_header = QLabel("Attachment Skills")
        skills_header.setStyleSheet(
            f"color: {ACCENT}; font-size: 13px; font-weight: bold;")
        layout.addWidget(skills_header)

        self._skill_slots = []
        for i in range(1, 5):
            slot = SkillSlotWidget(i)
            self._skill_slots.append(slot)
            layout.addWidget(slot)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {BORDER};")
        layout.addWidget(sep)

        # ── Equipment ──
        equip_header = QLabel("Equipment")
        equip_header.setStyleSheet(
            f"color: {ACCENT}; font-size: 13px; font-weight: bold;")
        layout.addWidget(equip_header)

        self._equip_slots = []
        for i in range(1, 3):
            slot = EquipSlotWidget(i)
            self._equip_slots.append(slot)
            layout.addWidget(slot)

        layout.addStretch()

        # Note
        note = QLabel("Skill and equipment editing coming in a future update.")
        note.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 10px; padding: 8px;")
        note.setWordWrap(True)
        layout.addWidget(note)

    def set_entry(self, entry):
        """Load skills and equipment from a Digimon entry."""
        # Attachment skills
        skills = entry.get("attach_skills", [0, 0, 0, 0])
        for i, slot in enumerate(self._skill_slots):
            sid = skills[i] if i < len(skills) else 0
            slot.set_skill(sid)

        self._equip_slots[0].set_equipment(entry.get("equip_1", 0))
        self._equip_slots[1].set_equipment(entry.get("equip_2", 0))
