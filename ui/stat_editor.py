"""Stats tab — horizontal bars on top, large editable table below.

Bars are compact at the top. The table is the main feature —
large, readable, fills remaining space, values are click-to-edit.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                              QLabel, QSpinBox, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal

from ui.style import (STAT_COLORS, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_VALUE,
                       ACCENT, STAT_BASE, STAT_WHITE, STAT_FARM, STAT_BLUE,
                       BORDER, BG_INPUT)
from ui.stat_bar import StatBar


STAT_KEYS = ["hp", "sp", "atk", "def", "int", "spi", "spd"]
STAT_LABELS = ["HP", "SP", "ATK", "DEF", "INT", "SPI", "SPD"]


class _Cell(QSpinBox):
    """Borderless editable cell that looks like text until focused."""

    def __init__(self, color, parent=None):
        super().__init__(parent)
        self.setRange(-99999, 99999)
        self.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedWidth(70)
        self.setMaximumHeight(30)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        self.setStyleSheet(f"""
            QSpinBox {{
                background: transparent;
                color: {color};
                border: none;
                border-radius: 3px;
                font-size: 14px;
                font-weight: bold;
            }}
            QSpinBox:hover {{
                background: rgba(255,255,255,0.04);
            }}
            QSpinBox:focus {{
                background: rgba(0,191,255,0.1);
                border: 1px solid rgba(0,191,255,0.4);
            }}
        """)


class StatEditor(QWidget):
    """Bars on top, large editable table filling the rest."""

    blue_stat_changed = pyqtSignal(str, int)
    white_stat_changed = pyqtSignal(str, int)
    farm_stat_changed = pyqtSignal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entry = None
        self._updating = False
        self._bars = {}
        self._bar_totals = {}
        self._base_labels = {}
        self._white_cells = {}
        self._farm_cells = {}
        self._blue_cells = {}
        self._total_labels = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(2)

        # ── Compact bars at top ──
        bar_wrapper = QHBoxLayout()
        bar_wrapper.addStretch()

        bar_grid = QGridLayout()
        bar_grid.setSpacing(1)
        bar_grid.setColumnMinimumWidth(0, 32)
        bar_grid.setColumnMinimumWidth(1, 400)
        bar_grid.setColumnMinimumWidth(2, 36)

        for row, (key, label) in enumerate(zip(STAT_KEYS, STAT_LABELS)):
            name = QLabel(label)
            name.setStyleSheet(
                f"color: {STAT_COLORS[key]}; font-size: 10px; font-weight: bold; "
                f"background: transparent;")
            name.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            bar_grid.addWidget(name, row, 0)

            bar = StatBar()
            self._bars[key] = bar
            bar_grid.addWidget(bar, row, 1)

            total = QLabel("—")
            total.setStyleSheet(
                f"color: {TEXT_SECONDARY}; font-size: 9px; "
                f"background: transparent;")
            total.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._bar_totals[key] = total
            bar_grid.addWidget(total, row, 2)

        bar_wrapper.addLayout(bar_grid)
        bar_wrapper.addStretch()
        layout.addLayout(bar_wrapper)

        # ── Table fills remaining height, constrained width ──
        table_wrapper = QHBoxLayout()
        table_wrapper.addStretch()

        table = QGridLayout()
        table.setSpacing(0)
        table.setContentsMargins(0, 0, 0, 0)

        # Rows stretch vertically to fill space
        for r in range(1, 8):
            table.setRowStretch(r, 1)

        # Fixed column widths — no stretching horizontally
        table.setColumnFixedWidth = None  # not a real method, use minimums
        table.setColumnMinimumWidth(0, 40)   # stat name
        table.setColumnMinimumWidth(1, 65)   # base
        table.setColumnMinimumWidth(2, 70)   # growth
        table.setColumnMinimumWidth(3, 70)   # farm
        table.setColumnMinimumWidth(4, 70)   # blue
        table.setColumnMinimumWidth(5, 65)   # total

        # Column headers
        headers = [("", TEXT_SECONDARY), ("Base", STAT_BASE),
                   ("Growth", STAT_WHITE), ("Farm", STAT_FARM),
                   ("Blue", STAT_BLUE), ("Total", TEXT_VALUE)]
        for col, (text, color) in enumerate(headers):
            h = QLabel(text)
            h.setStyleSheet(
                f"color: {color}; font-size: 10px; font-weight: bold; "
                f"background: transparent;")
            h.setAlignment(Qt.AlignmentFlag.AlignCenter)
            h.setFixedHeight(16)
            table.addWidget(h, 0, col)

        # Data rows
        for row, (key, label) in enumerate(zip(STAT_KEYS, STAT_LABELS), start=1):
            # Row container for alternating bg
            bg = "rgba(255,255,255,0.02)" if row % 2 == 0 else "transparent"

            # Stat name
            name = QLabel(label)
            name.setStyleSheet(
                f"color: {STAT_COLORS[key]}; font-size: 14px; font-weight: bold; "
                f"background: {bg};")
            name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            table.addWidget(name, row, 0)

            # Base (read-only)
            base = QLabel("—")
            base.setStyleSheet(
                f"color: {STAT_BASE}; font-size: 14px; font-weight: bold; "
                f"background: {bg};")
            base.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._base_labels[key] = base
            table.addWidget(base, row, 1)

            # Growth (editable)
            white = _Cell(STAT_WHITE)
            if bg != "transparent":
                white.setStyleSheet(white.styleSheet().replace(
                    "background: transparent", f"background: {bg}"))
            white.valueChanged.connect(
                lambda v, k=key: self._on_white_changed(k, v))
            self._white_cells[key] = white
            table.addWidget(white, row, 2)

            # Farm (editable)
            farm = _Cell(STAT_FARM)
            if bg != "transparent":
                farm.setStyleSheet(farm.styleSheet().replace(
                    "background: transparent", f"background: {bg}"))
            farm.valueChanged.connect(
                lambda v, k=key: self._on_farm_changed(k, v))
            self._farm_cells[key] = farm
            table.addWidget(farm, row, 3)

            # Blue (editable)
            blue = _Cell(STAT_BLUE)
            if bg != "transparent":
                blue.setStyleSheet(blue.styleSheet().replace(
                    "background: transparent", f"background: {bg}"))
            blue.valueChanged.connect(
                lambda v, k=key: self._on_blue_changed(k, v))
            self._blue_cells[key] = blue
            table.addWidget(blue, row, 4)

            # Total
            total = QLabel("—")
            total.setStyleSheet(
                f"color: {TEXT_VALUE}; font-size: 15px; font-weight: bold; "
                f"background: {bg};")
            total.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._total_labels[key] = total
            table.addWidget(total, row, 5)

        table_wrapper.addLayout(table)
        table_wrapper.addStretch()
        layout.addLayout(table_wrapper, 1)  # stretch factor 1 = fills remaining height

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
            self._bar_totals[key].setText(str(total))
            self._base_labels[key].setText(str(base))
            self._white_cells[key].setValue(white)
            self._farm_cells[key].setValue(farm)
            self._blue_cells[key].setValue(blue)
            self._total_labels[key].setText(str(total))

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
        self._bar_totals[key].setText(str(total))
        self._total_labels[key].setText(str(total))

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
