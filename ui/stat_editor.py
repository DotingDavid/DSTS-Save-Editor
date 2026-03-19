"""Stats tab for the Digimon editor.

Shows 7 stats with 4-layer colored stacked bars and editable blue stats.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                              QLabel, QSpinBox, QFrame, QGroupBox)
from PyQt6.QtCore import Qt, pyqtSignal

from ui.style import (STAT_COLORS, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_VALUE,
                       ACCENT, STAT_BASE, STAT_WHITE, STAT_FARM, STAT_BLUE, BORDER)
from ui.stat_bar import StatBar


STAT_KEYS = ["hp", "sp", "atk", "def", "int", "spi", "spd"]
STAT_LABELS = ["HP", "SP", "ATK", "DEF", "INT", "SPI", "SPD"]


class StatEditor(QWidget):
    """View stat breakdown and edit blue stats."""

    blue_stat_changed = pyqtSignal(str, int)  # stat_key, new_value

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entry = None
        self._updating = False
        self._bars = {}
        self._total_labels = {}
        self._blue_spins = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # ── Legend ──
        legend = QHBoxLayout()
        legend.setSpacing(12)
        for label, color in [("Base", STAT_BASE), ("Growth", STAT_WHITE),
                              ("Farm", STAT_FARM), ("Blue", STAT_BLUE)]:
            dot = QLabel("■")
            dot.setStyleSheet(f"color: {color}; font-size: 14px;")
            dot.setFixedWidth(14)
            legend.addWidget(dot)
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 10px;")
            legend.addWidget(lbl)
        legend.addStretch()
        layout.addLayout(legend)

        # ── Stat bars ──
        bar_grid = QGridLayout()
        bar_grid.setSpacing(4)
        bar_grid.setColumnStretch(1, 1)  # bar column stretches

        for row, (key, label) in enumerate(zip(STAT_KEYS, STAT_LABELS)):
            # Stat name
            name_lbl = QLabel(label)
            name_lbl.setStyleSheet(
                f"color: {STAT_COLORS[key]}; font-weight: bold; font-size: 12px;")
            name_lbl.setFixedWidth(32)
            name_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            bar_grid.addWidget(name_lbl, row, 0)

            # Stacked bar
            bar = StatBar()
            self._bars[key] = bar
            bar_grid.addWidget(bar, row, 1)

            # Total value
            total_lbl = QLabel("—")
            total_lbl.setStyleSheet(f"color: {TEXT_VALUE}; font-weight: bold; font-size: 12px;")
            total_lbl.setFixedWidth(48)
            total_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._total_labels[key] = total_lbl
            bar_grid.addWidget(total_lbl, row, 2)

        layout.addLayout(bar_grid)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {BORDER};")
        layout.addWidget(sep)

        # ── Blue Stats (Editable) ──
        blue_group = QGroupBox("Blue Stats (Editable)")
        blue_layout = QGridLayout()
        blue_layout.setSpacing(4)

        for i, (key, label) in enumerate(zip(STAT_KEYS, STAT_LABELS)):
            row = i // 2
            col = (i % 2) * 2

            lbl = QLabel(f"{label}:")
            lbl.setStyleSheet(f"color: {STAT_COLORS[key]}; font-size: 11px;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            blue_layout.addWidget(lbl, row, col)

            spin = QSpinBox()
            spin.setRange(-9999, 9999)
            spin.setFixedWidth(80)
            key_ref = key  # capture for lambda
            spin.valueChanged.connect(
                lambda v, k=key_ref: self._on_blue_changed(k, v))
            self._blue_spins[key] = spin
            blue_layout.addWidget(spin, row, col + 1)

        blue_group.setLayout(blue_layout)
        layout.addWidget(blue_group)

        layout.addStretch()

    def set_entry(self, entry):
        """Load stat data from a Digimon entry dict."""
        self._updating = True
        self._entry = entry

        # Find max total for bar scaling
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

        self._updating = False

    def _on_blue_changed(self, key, value):
        if not self._updating:
            self.blue_stat_changed.emit(key, value)
            # Update the bar and total in real-time
            if self._entry:
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
