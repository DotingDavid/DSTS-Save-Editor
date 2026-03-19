"""Stats tab — visual bars at top, editable breakdown table below.

Bars show the composition. The breakdown table IS the editor —
click any white/farm/blue value to edit it directly.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                              QLabel, QSpinBox, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal

from ui.style import (STAT_COLORS, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_VALUE,
                       ACCENT, STAT_BASE, STAT_WHITE, STAT_FARM, STAT_BLUE,
                       BORDER, BG_INPUT)
from ui.stat_bar import StatBar


STAT_KEYS = ["hp", "sp", "atk", "def", "int", "spi", "spd"]
STAT_LABELS = ["HP", "SP", "ATK", "DEF", "INT", "SPI", "SPD"]


class _EditableCell(QSpinBox):
    """Compact spinbox styled to look like a table cell."""

    def __init__(self, color, parent=None):
        super().__init__(parent)
        self.setRange(-99999, 99999)
        self.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.setFixedHeight(22)
        self.setMinimumWidth(55)
        self.setStyleSheet(f"""
            QSpinBox {{
                background: transparent;
                color: {color};
                border: 1px solid transparent;
                border-radius: 2px;
                font-size: 12px;
                font-weight: bold;
                padding: 0 4px;
            }}
            QSpinBox:hover {{
                border-color: rgba(255,255,255,0.15);
                background: rgba(255,255,255,0.03);
            }}
            QSpinBox:focus {{
                border-color: {ACCENT};
                background: rgba(0,191,255,0.08);
            }}
        """)


class _ReadOnlyCell(QLabel):
    """Read-only table cell."""

    def __init__(self, color=TEXT_SECONDARY, parent=None):
        super().__init__("—", parent)
        self.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.setFixedHeight(22)
        self.setMinimumWidth(55)
        self.setStyleSheet(
            f"color: {color}; font-size: 12px; font-weight: bold; "
            f"background: transparent; border: none; padding: 0 4px;")


class StatEditor(QWidget):
    """Bars at top, editable breakdown table below."""

    blue_stat_changed = pyqtSignal(str, int)
    white_stat_changed = pyqtSignal(str, int)
    farm_stat_changed = pyqtSignal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entry = None
        self._updating = False
        self._bars = {}
        self._total_labels = {}
        self._base_cells = {}
        self._white_cells = {}
        self._farm_cells = {}
        self._blue_cells = {}
        self._total_cells = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(6)

        # ── Legend ──
        legend = QHBoxLayout()
        legend.setSpacing(8)
        for label, color in [("Base", STAT_BASE), ("Growth", STAT_WHITE),
                              ("Farm", STAT_FARM), ("Blue", STAT_BLUE)]:
            dot = QLabel("■")
            dot.setStyleSheet(
                f"color: {color}; font-size: 11px; background: transparent;")
            dot.setFixedWidth(11)
            legend.addWidget(dot)
            lbl = QLabel(label)
            lbl.setStyleSheet(
                f"color: {TEXT_SECONDARY}; font-size: 10px; background: transparent;")
            legend.addWidget(lbl)
        legend.addStretch()
        layout.addLayout(legend)

        # ── Stat Bars (read-only visual) ──
        bar_grid = QGridLayout()
        bar_grid.setSpacing(3)
        bar_grid.setColumnMinimumWidth(0, 32)
        bar_grid.setColumnStretch(1, 1)
        bar_grid.setColumnMinimumWidth(2, 45)

        for row, (key, label) in enumerate(zip(STAT_KEYS, STAT_LABELS)):
            name = QLabel(label)
            name.setStyleSheet(
                f"color: {STAT_COLORS[key]}; font-weight: bold; font-size: 11px; "
                f"background: transparent;")
            name.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            bar_grid.addWidget(name, row, 0)

            bar = StatBar()
            self._bars[key] = bar
            bar_grid.addWidget(bar, row, 1)

            total = QLabel("—")
            total.setStyleSheet(
                f"color: {TEXT_VALUE}; font-weight: bold; font-size: 11px; "
                f"background: transparent;")
            total.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._total_labels[key] = total
            bar_grid.addWidget(total, row, 2)

        layout.addLayout(bar_grid)

        # ── Separator ──
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {BORDER}; border: none;")
        layout.addWidget(sep)

        # ── Editable Breakdown Table ──
        table_label = QLabel("STAT BREAKDOWN  —  click any value to edit")
        table_label.setStyleSheet(
            f"color: rgba(0,191,255,0.4); font-size: 9px; font-weight: bold; "
            f"letter-spacing: 2px; background: transparent;")
        layout.addWidget(table_label)

        table = QGridLayout()
        table.setSpacing(1)
        table.setColumnMinimumWidth(0, 36)

        # Column headers
        headers = [("", TEXT_SECONDARY), ("Base", STAT_BASE),
                   ("Growth", STAT_WHITE), ("Farm", STAT_FARM),
                   ("Blue", STAT_BLUE), ("= Total", TEXT_VALUE)]
        for col, (text, color) in enumerate(headers):
            h = QLabel(text)
            h.setStyleSheet(
                f"color: {color}; font-size: 9px; font-weight: bold; "
                f"background: transparent; border: none;")
            h.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            h.setFixedHeight(18)
            table.addWidget(h, 0, col)

        # Data rows
        for row, (key, label) in enumerate(zip(STAT_KEYS, STAT_LABELS), start=1):
            # Stat name
            name = QLabel(label)
            name.setStyleSheet(
                f"color: {STAT_COLORS[key]}; font-size: 11px; font-weight: bold; "
                f"background: transparent; border: none;")
            name.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            name.setFixedHeight(22)
            table.addWidget(name, row, 0)

            # Base (read-only)
            base_cell = _ReadOnlyCell(STAT_BASE)
            self._base_cells[key] = base_cell
            table.addWidget(base_cell, row, 1)

            # White (editable)
            white_cell = _EditableCell(STAT_WHITE)
            white_cell.valueChanged.connect(
                lambda v, k=key: self._on_white_changed(k, v))
            self._white_cells[key] = white_cell
            table.addWidget(white_cell, row, 2)

            # Farm (editable)
            farm_cell = _EditableCell(STAT_FARM)
            farm_cell.valueChanged.connect(
                lambda v, k=key: self._on_farm_changed(k, v))
            self._farm_cells[key] = farm_cell
            table.addWidget(farm_cell, row, 3)

            # Blue (editable)
            blue_cell = _EditableCell(STAT_BLUE)
            blue_cell.valueChanged.connect(
                lambda v, k=key: self._on_blue_changed(k, v))
            self._blue_cells[key] = blue_cell
            table.addWidget(blue_cell, row, 4)

            # Total (read-only)
            total_cell = _ReadOnlyCell(TEXT_VALUE)
            self._total_cells[key] = total_cell
            table.addWidget(total_cell, row, 5)

        # Alternating row backgrounds
        for row in range(1, 8):
            if row % 2 == 0:
                for col in range(6):
                    w = table.itemAtPosition(row, col)
                    if w and w.widget():
                        current = w.widget().styleSheet()
                        if "background: transparent" in current:
                            w.widget().setStyleSheet(
                                current.replace(
                                    "background: transparent",
                                    "background: rgba(255,255,255,0.02)"))

        layout.addLayout(table)
        layout.addStretch()

    def set_entry(self, entry):
        self._updating = True
        self._entry = entry

        max_total = max(
            (entry["total"].get(k, 0) for k in STAT_KEYS), default=1)
        max_total = max(max_total, 100)

        for key in STAT_KEYS:
            base = entry["base"].get(key, 0)
            white = entry["white"].get(key, 0)
            farm = entry["farm"].get(key, 0)
            blue = entry["blue"].get(key, 0)
            total = entry["total"].get(key, 0)

            self._bars[key].set_values(base, white, farm, blue, max_total)
            self._total_labels[key].setText(str(total))

            self._base_cells[key].setText(str(base))
            self._white_cells[key].setValue(white)
            self._farm_cells[key].setValue(farm)
            self._blue_cells[key].setValue(blue)
            self._total_cells[key].setText(str(total))

        self._updating = False

    def _recalc(self, key):
        if not self._entry:
            return
        base = self._entry["base"].get(key, 0)
        white = self._entry["white"].get(key, 0)
        farm = self._entry["farm"].get(key, 0)
        blue = self._entry["blue"].get(key, 0)
        total = base + white + farm + blue
        self._entry["total"][key] = total

        max_total = max(
            (self._entry["total"].get(k, 0) for k in STAT_KEYS), default=1)
        max_total = max(max_total, 100)

        self._bars[key].set_values(base, white, farm, blue, max_total)
        self._total_labels[key].setText(str(total))
        self._total_cells[key].setText(str(total))

    def _on_white_changed(self, key, value):
        if not self._updating and self._entry:
            self._entry["white"][key] = value
            self._recalc(key)
            self.white_stat_changed.emit(key, value)

    def _on_farm_changed(self, key, value):
        if not self._updating and self._entry:
            self._entry["farm"][key] = value
            self._recalc(key)
            self.farm_stat_changed.emit(key, value)

    def _on_blue_changed(self, key, value):
        if not self._updating and self._entry:
            self._entry["blue"][key] = value
            self._recalc(key)
            self.blue_stat_changed.emit(key, value)
