"""Stats tab for the Digimon editor.

Shows 7 stats with 4-layer colored stacked bars and inline blue stat editing.
Each row: Label | Bar | Blue SpinBox | Total
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


class StatEditor(QWidget):
    """View stat breakdown and edit blue stats inline."""

    blue_stat_changed = pyqtSignal(str, int)  # stat_key, new_value

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entry = None
        self._updating = False
        self._bars = {}
        self._total_labels = {}
        self._blue_spins = {}
        self._layer_labels = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # ── Legend ──
        legend = QHBoxLayout()
        legend.setSpacing(8)
        for label, color in [("Base", STAT_BASE), ("Growth", STAT_WHITE),
                              ("Farm", STAT_FARM), ("Blue", STAT_BLUE)]:
            dot = QLabel("■")
            dot.setStyleSheet(f"color: {color}; font-size: 12px;")
            dot.setFixedWidth(12)
            legend.addWidget(dot)
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 10px;")
            legend.addWidget(lbl)
        legend.addStretch()
        layout.addLayout(legend)

        # ── Stat rows: Name | Bar | Blue edit | = Total ──
        grid = QGridLayout()
        grid.setSpacing(6)
        grid.setColumnMinimumWidth(0, 36)   # stat name
        grid.setColumnStretch(1, 1)          # bar stretches
        grid.setColumnMinimumWidth(2, 70)   # blue spinbox
        grid.setColumnMinimumWidth(3, 50)   # total

        # Header row
        for col, text in [(0, ""), (1, ""), (2, "Blue"), (3, "Total")]:
            h = QLabel(text)
            h.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 10px; font-weight: bold;")
            h.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(h, 0, col)

        for row, (key, label) in enumerate(zip(STAT_KEYS, STAT_LABELS), start=1):
            # Stat name
            name_lbl = QLabel(label)
            name_lbl.setStyleSheet(
                f"color: {STAT_COLORS[key]}; font-weight: bold; font-size: 12px;")
            name_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(name_lbl, row, 0)

            # Stacked bar
            bar = StatBar()
            self._bars[key] = bar
            grid.addWidget(bar, row, 1)

            # Blue stat spinbox (inline)
            spin = QSpinBox()
            spin.setRange(-9999, 9999)
            spin.setFixedWidth(70)
            spin.setAlignment(Qt.AlignmentFlag.AlignRight)
            spin.setStyleSheet(f"""
                QSpinBox {{
                    background-color: rgba(66, 165, 245, 0.15);
                    border: 1px solid rgba(66, 165, 245, 0.4);
                    color: {STAT_BLUE};
                    font-weight: bold;
                }}
                QSpinBox:focus {{
                    border-color: {STAT_BLUE};
                }}
            """)
            key_ref = key
            spin.valueChanged.connect(
                lambda v, k=key_ref: self._on_blue_changed(k, v))
            self._blue_spins[key] = spin
            grid.addWidget(spin, row, 2)

            # Total value
            total_lbl = QLabel("—")
            total_lbl.setStyleSheet(f"color: {TEXT_VALUE}; font-weight: bold; font-size: 12px;")
            total_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._total_labels[key] = total_lbl
            grid.addWidget(total_lbl, row, 3)

        layout.addLayout(grid)

        # ── Layer breakdown (shows on hover/select) ──
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {BORDER};")
        layout.addWidget(sep)

        breakdown_header = QLabel("Stat Breakdown")
        breakdown_header.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 11px; font-weight: bold;")
        layout.addWidget(breakdown_header)

        breakdown_grid = QGridLayout()
        breakdown_grid.setSpacing(2)

        # Column headers
        for col, (text, color) in enumerate(
                [("", TEXT_SECONDARY), ("Base", STAT_BASE), ("Growth", STAT_WHITE),
                 ("Farm", STAT_FARM), ("Blue", STAT_BLUE), ("Total", TEXT_VALUE)]):
            h = QLabel(text)
            h.setStyleSheet(f"color: {color}; font-size: 10px; font-weight: bold;")
            h.setAlignment(Qt.AlignmentFlag.AlignRight)
            breakdown_grid.addWidget(h, 0, col)

        self._breakdown_labels = {}
        for row, (key, label) in enumerate(zip(STAT_KEYS, STAT_LABELS), start=1):
            name_lbl = QLabel(label)
            name_lbl.setStyleSheet(
                f"color: {STAT_COLORS[key]}; font-size: 10px; font-weight: bold;")
            name_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            breakdown_grid.addWidget(name_lbl, row, 0)

            self._breakdown_labels[key] = {}
            for col, layer in enumerate(["base", "white", "farm", "blue", "total"], start=1):
                lbl = QLabel("—")
                lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 10px;")
                lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
                self._breakdown_labels[key][layer] = lbl
                breakdown_grid.addWidget(lbl, row, col)

        layout.addLayout(breakdown_grid)
        layout.addStretch()

    def set_entry(self, entry):
        """Load stat data from a Digimon entry dict."""
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
            self._blue_spins[key].setValue(blue)

            # Breakdown table
            self._breakdown_labels[key]["base"].setText(str(base))
            self._breakdown_labels[key]["white"].setText(str(white))
            self._breakdown_labels[key]["farm"].setText(str(farm))
            self._breakdown_labels[key]["blue"].setText(str(blue))
            self._breakdown_labels[key]["total"].setText(str(total))

        self._updating = False

    def _on_blue_changed(self, key, value):
        if not self._updating and self._entry:
            self.blue_stat_changed.emit(key, value)
            # Live update bar and totals
            base = self._entry["base"].get(key, 0)
            white = self._entry["white"].get(key, 0)
            farm = self._entry["farm"].get(key, 0)
            new_total = base + white + farm + value
            self._entry["blue"][key] = value
            self._entry["total"][key] = new_total

            max_total = max(
                (self._entry["total"].get(k, 0) for k in STAT_KEYS), default=1)
            max_total = max(max_total, 100)

            self._bars[key].set_values(base, white, farm, value, max_total)
            self._total_labels[key].setText(str(new_total))
            self._breakdown_labels[key]["blue"].setText(str(value))
            self._breakdown_labels[key]["total"].setText(str(new_total))
