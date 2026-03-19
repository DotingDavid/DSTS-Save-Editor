"""Stats tab for the Digimon editor.

Shows 7 stats with 4-layer colored stacked bars.
Editable: white stats, farm stats, blue stats.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                              QLabel, QSpinBox, QFrame, QGroupBox, QTabWidget)
from PyQt6.QtCore import Qt, pyqtSignal

from ui.style import (STAT_COLORS, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_VALUE,
                       ACCENT, STAT_BASE, STAT_WHITE, STAT_FARM, STAT_BLUE,
                       BORDER, BG_INPUT)
from ui.stat_bar import StatBar


STAT_KEYS = ["hp", "sp", "atk", "def", "int", "spi", "spd"]
STAT_LABELS = ["HP", "SP", "ATK", "DEF", "INT", "SPI", "SPD"]


class StatEditor(QWidget):
    """View stat breakdown and edit white, farm, and blue stats."""

    blue_stat_changed = pyqtSignal(str, int)
    white_stat_changed = pyqtSignal(str, int)
    farm_stat_changed = pyqtSignal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entry = None
        self._updating = False
        self._bars = {}
        self._total_labels = {}
        self._blue_spins = {}
        self._white_spins = {}
        self._farm_spins = {}
        self._breakdown_labels = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(3)

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

        # ── Stat bars with inline blue editing ──
        grid = QGridLayout()
        grid.setSpacing(6)
        grid.setColumnMinimumWidth(0, 36)
        grid.setColumnStretch(1, 1)
        grid.setColumnMinimumWidth(2, 90)
        grid.setColumnMinimumWidth(3, 55)

        for col, text in [(0, ""), (1, ""), (2, "Blue"), (3, "Total")]:
            h = QLabel(text)
            h.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 10px; font-weight: bold;")
            h.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(h, 0, col)

        for row, (key, label) in enumerate(zip(STAT_KEYS, STAT_LABELS), start=1):
            name_lbl = QLabel(label)
            name_lbl.setStyleSheet(
                f"color: {STAT_COLORS[key]}; font-weight: bold; font-size: 12px;")
            name_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(name_lbl, row, 0)

            bar = StatBar()
            self._bars[key] = bar
            grid.addWidget(bar, row, 1)

            spin = QSpinBox()
            spin.setRange(-9999, 9999)
            spin.setFixedWidth(90)
            spin.setAlignment(Qt.AlignmentFlag.AlignRight)
            spin.setStyleSheet(f"""
                QSpinBox {{
                    background-color: rgba(66, 165, 245, 0.15);
                    border: 1px solid rgba(66, 165, 245, 0.4);
                    color: {STAT_BLUE};
                    font-weight: bold;
                }}
                QSpinBox:focus {{ border-color: {STAT_BLUE}; }}
            """)
            key_ref = key
            spin.valueChanged.connect(
                lambda v, k=key_ref: self._on_blue_changed(k, v))
            self._blue_spins[key] = spin
            grid.addWidget(spin, row, 2)

            total_lbl = QLabel("—")
            total_lbl.setStyleSheet(f"color: {TEXT_VALUE}; font-weight: bold; font-size: 12px;")
            total_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._total_labels[key] = total_lbl
            grid.addWidget(total_lbl, row, 3)

        layout.addLayout(grid)

        # ── Breakdown table ──
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {BORDER};")
        layout.addWidget(sep)

        bd_header = QLabel("Stat Breakdown")
        bd_header.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 11px; font-weight: bold;")
        layout.addWidget(bd_header)

        bd_grid = QGridLayout()
        bd_grid.setSpacing(1)
        for col, (text, color) in enumerate(
                [("", TEXT_SECONDARY), ("Base", STAT_BASE), ("Growth", STAT_WHITE),
                 ("Farm", STAT_FARM), ("Blue", STAT_BLUE), ("Total", TEXT_VALUE)]):
            h = QLabel(text)
            h.setStyleSheet(f"color: {color}; font-size: 10px; font-weight: bold;")
            h.setAlignment(Qt.AlignmentFlag.AlignRight)
            bd_grid.addWidget(h, 0, col)

        for row, (key, label) in enumerate(zip(STAT_KEYS, STAT_LABELS), start=1):
            name_lbl = QLabel(label)
            name_lbl.setStyleSheet(
                f"color: {STAT_COLORS[key]}; font-size: 10px; font-weight: bold;")
            name_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            bd_grid.addWidget(name_lbl, row, 0)
            self._breakdown_labels[key] = {}
            for col, layer in enumerate(["base", "white", "farm", "blue", "total"], start=1):
                lbl = QLabel("—")
                lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 10px;")
                lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
                self._breakdown_labels[key][layer] = lbl
                bd_grid.addWidget(lbl, row, col)
        layout.addLayout(bd_grid)

        # ── Growth & Farm editing (collapsible) ──
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(f"color: {BORDER};")
        layout.addWidget(sep2)

        adv_header = QLabel("Advanced Stat Editing")
        adv_header.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 11px; font-weight: bold;")
        layout.addWidget(adv_header)

        adv_tabs = QTabWidget()

        # White stats tab
        white_widget = QWidget()
        white_grid = QGridLayout(white_widget)
        white_grid.setSpacing(4)
        for i, (key, label) in enumerate(zip(STAT_KEYS, STAT_LABELS)):
            row = i // 2
            col = (i % 2) * 2
            lbl = QLabel(f"{label}:")
            lbl.setStyleSheet(f"color: {STAT_WHITE}; font-size: 11px;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            white_grid.addWidget(lbl, row, col)
            spin = QSpinBox()
            spin.setRange(0, 99999)
            spin.setFixedWidth(80)
            key_ref = key
            spin.valueChanged.connect(
                lambda v, k=key_ref: self._on_white_changed(k, v))
            self._white_spins[key] = spin
            white_grid.addWidget(spin, row, col + 1)
        adv_tabs.addTab(white_widget, "Growth (White)")

        # Farm stats tab
        farm_widget = QWidget()
        farm_grid = QGridLayout(farm_widget)
        farm_grid.setSpacing(4)
        for i, (key, label) in enumerate(zip(STAT_KEYS, STAT_LABELS)):
            row = i // 2
            col = (i % 2) * 2
            lbl = QLabel(f"{label}:")
            lbl.setStyleSheet(f"color: {STAT_FARM}; font-size: 11px;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            farm_grid.addWidget(lbl, row, col)
            spin = QSpinBox()
            spin.setRange(0, 99999)
            spin.setFixedWidth(80)
            key_ref = key
            spin.valueChanged.connect(
                lambda v, k=key_ref: self._on_farm_changed(k, v))
            self._farm_spins[key] = spin
            farm_grid.addWidget(spin, row, col + 1)
        adv_tabs.addTab(farm_widget, "Farm Training")

        layout.addWidget(adv_tabs, 1)  # tabs get remaining space

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
            self._blue_spins[key].setValue(blue)
            self._white_spins[key].setValue(white)
            self._farm_spins[key].setValue(farm)

            self._breakdown_labels[key]["base"].setText(str(base))
            self._breakdown_labels[key]["white"].setText(str(white))
            self._breakdown_labels[key]["farm"].setText(str(farm))
            self._breakdown_labels[key]["blue"].setText(str(blue))
            self._breakdown_labels[key]["total"].setText(str(total))

        self._updating = False

    def _recalc(self, key):
        """Recalculate total and update display for one stat."""
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
        self._breakdown_labels[key]["white"].setText(str(white))
        self._breakdown_labels[key]["farm"].setText(str(farm))
        self._breakdown_labels[key]["blue"].setText(str(blue))
        self._breakdown_labels[key]["total"].setText(str(total))

    def _on_blue_changed(self, key, value):
        if not self._updating and self._entry:
            self._entry["blue"][key] = value
            self._recalc(key)
            self.blue_stat_changed.emit(key, value)

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
