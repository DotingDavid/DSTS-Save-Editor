"""Stats tab — responsive layout, horizontal bars + editable table.

Everything scales with the panel width. No fixed pixel widths.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                              QLabel, QSpinBox, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal

from ui.style import (STAT_COLORS, TEXT_SECONDARY, TEXT_VALUE,
                       ACCENT, STAT_BASE, STAT_WHITE, STAT_FARM, STAT_BLUE,
                       BORDER)
from ui.stat_bar import StatBar


STAT_KEYS = ["hp", "sp", "atk", "def", "int", "spi", "spd"]
STAT_LABELS = ["HP", "SP", "ATK", "DEF", "INT", "SPI", "SPD"]


class _Cell(QSpinBox):
    """Borderless editable cell — adapts to column width."""

    def __init__(self, color, parent=None):
        super().__init__(parent)
        self.setRange(-99999, 99999)
        self.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(24)
        self.setStyleSheet(f"""
            QSpinBox {{
                background: transparent;
                color: {color};
                border: none;
                border-radius: 3px;
                font-size: 13px;
                font-weight: bold;
            }}
            QSpinBox:hover {{ background: rgba(255,255,255,0.04); }}
            QSpinBox:focus {{
                background: rgba(0,191,255,0.1);
                border: 1px solid rgba(0,191,255,0.4);
            }}
        """)


class StatEditor(QWidget):
    """Responsive stat editor — bars + table scale to panel width."""

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
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(6)

        # ── Bars — responsive, stretch to 60% of width ──
        bars = QGridLayout()
        bars.setSpacing(2)
        bars.setColumnStretch(0, 0)   # name: fixed content
        bars.setColumnStretch(1, 3)   # bar: takes most space
        bars.setColumnStretch(2, 0)   # total: fixed content

        for row, (key, label) in enumerate(zip(STAT_KEYS, STAT_LABELS)):
            n = QLabel(label)
            n.setStyleSheet(
                f"color: {STAT_COLORS[key]}; font-size: 10px; font-weight: bold; "
                f"background: transparent;")
            n.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            bars.addWidget(n, row, 0)

            bar = StatBar()
            bar.setMaximumWidth(300)
            self._bars[key] = bar
            bars.addWidget(bar, row, 1)

            t = QLabel("—")
            t.setStyleSheet(
                f"color: {TEXT_SECONDARY}; font-size: 9px; background: transparent;")
            t.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._bar_totals[key] = t
            bars.addWidget(t, row, 2)

        layout.addLayout(bars)

        # ── Table — responsive columns using stretch factors ──
        table = QGridLayout()
        table.setSpacing(0)
        table.setContentsMargins(0, 2, 0, 0)

        # Column proportions: name(1) base(2) growth(2) farm(2) blue(2) total(2)
        table.setColumnStretch(0, 1)
        table.setColumnStretch(1, 2)
        table.setColumnStretch(2, 2)
        table.setColumnStretch(3, 2)
        table.setColumnStretch(4, 2)
        table.setColumnStretch(5, 2)

        # Headers
        for col, (text, color) in enumerate([
                ("", TEXT_SECONDARY), ("Base", STAT_BASE), ("Growth", STAT_WHITE),
                ("Farm", STAT_FARM), ("Blue", STAT_BLUE), ("Total", TEXT_VALUE)]):
            h = QLabel(text)
            h.setStyleSheet(
                f"color: {color}; font-size: 9px; font-weight: bold; "
                f"background: transparent;")
            h.setAlignment(Qt.AlignmentFlag.AlignCenter)
            h.setFixedHeight(16)
            table.addWidget(h, 0, col)

        # Data rows
        for row, (key, label) in enumerate(zip(STAT_KEYS, STAT_LABELS), start=1):
            bg = "rgba(255,255,255,0.02)" if row % 2 == 0 else "transparent"

            name = QLabel(label)
            name.setStyleSheet(
                f"color: {STAT_COLORS[key]}; font-size: 13px; font-weight: bold; "
                f"background: {bg};")
            name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name.setMinimumHeight(28)
            table.addWidget(name, row, 0)

            base = QLabel("—")
            base.setStyleSheet(
                f"color: {STAT_BASE}; font-size: 13px; font-weight: bold; "
                f"background: {bg};")
            base.setAlignment(Qt.AlignmentFlag.AlignCenter)
            base.setMinimumHeight(28)
            self._base_labels[key] = base
            table.addWidget(base, row, 1)

            white = _Cell(STAT_WHITE)
            white.valueChanged.connect(lambda v, k=key: self._on_white_changed(k, v))
            self._white_cells[key] = white
            table.addWidget(white, row, 2)

            farm = _Cell(STAT_FARM)
            farm.valueChanged.connect(lambda v, k=key: self._on_farm_changed(k, v))
            self._farm_cells[key] = farm
            table.addWidget(farm, row, 3)

            blue = _Cell(STAT_BLUE)
            blue.valueChanged.connect(lambda v, k=key: self._on_blue_changed(k, v))
            self._blue_cells[key] = blue
            table.addWidget(blue, row, 4)

            total = QLabel("—")
            total.setStyleSheet(
                f"color: {TEXT_VALUE}; font-size: 14px; font-weight: bold; "
                f"background: {bg};")
            total.setAlignment(Qt.AlignmentFlag.AlignCenter)
            total.setMinimumHeight(28)
            self._total_labels[key] = total
            table.addWidget(total, row, 5)

        layout.addLayout(table)
        layout.addStretch()

    def set_entry(self, entry):
        self._updating = True
        self._entry = entry
        mx = max((entry["total"].get(k, 0) for k in STAT_KEYS), default=100)
        mx = max(mx, 100)

        for key in STAT_KEYS:
            b = entry["base"].get(key, 0)
            w = entry["white"].get(key, 0)
            f = entry["farm"].get(key, 0)
            bl = entry["blue"].get(key, 0)
            t = entry["total"].get(key, 0)

            self._bars[key].set_values(b, w, f, bl, mx)
            self._bar_totals[key].setText(str(t))
            self._base_labels[key].setText(str(b))
            self._white_cells[key].setValue(w)
            self._farm_cells[key].setValue(f)
            self._blue_cells[key].setValue(bl)
            self._total_labels[key].setText(str(t))
        self._updating = False

    def _recalc(self, key):
        if not self._entry:
            return
        b = self._entry["base"].get(key, 0)
        w = self._entry["white"].get(key, 0)
        f = self._entry["farm"].get(key, 0)
        bl = self._entry["blue"].get(key, 0)
        t = b + w + f + bl
        self._entry["total"][key] = t
        mx = max((self._entry["total"].get(k, 0) for k in STAT_KEYS), default=100)
        mx = max(mx, 100)
        self._bars[key].set_values(b, w, f, bl, mx)
        self._bar_totals[key].setText(str(t))
        self._total_labels[key].setText(str(t))

    def _on_white_changed(self, key, v):
        if not self._updating and self._entry:
            self._entry["white"][key] = v
            self._recalc(key)
            self.white_stat_changed.emit(key, v)

    def _on_farm_changed(self, key, v):
        if not self._updating and self._entry:
            self._entry["farm"][key] = v
            self._recalc(key)
            self.farm_stat_changed.emit(key, v)

    def _on_blue_changed(self, key, v):
        if not self._updating and self._entry:
            self._entry["blue"][key] = v
            self._recalc(key)
            self.blue_stat_changed.emit(key, v)
