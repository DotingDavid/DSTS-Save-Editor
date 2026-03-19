"""Stats tab — vertical bar dashboard with editable values below.

Seven stat columns, each with a tall vertical bar and stacked edit fields.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QSpinBox, QGridLayout)
from PyQt6.QtCore import Qt, pyqtSignal

from ui.style import (STAT_COLORS, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_VALUE,
                       ACCENT, STAT_BASE, STAT_WHITE, STAT_FARM, STAT_BLUE,
                       BORDER, BG_INPUT)
from ui.stat_bar import VerticalStatBar


STAT_KEYS = ["hp", "sp", "atk", "def", "int", "spi", "spd"]
STAT_LABELS = ["HP", "SP", "ATK", "DEF", "INT", "SPI", "SPD"]


class _Cell(QSpinBox):
    """Compact borderless spinbox."""

    def __init__(self, color, parent=None):
        super().__init__(parent)
        self.setRange(-99999, 99999)
        self.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(22)
        self.setStyleSheet(f"""
            QSpinBox {{
                background: transparent;
                color: {color};
                border: none;
                border-radius: 2px;
                font-size: 11px;
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
    """Vertical bar dashboard with editable breakdown below each bar."""

    blue_stat_changed = pyqtSignal(str, int)
    white_stat_changed = pyqtSignal(str, int)
    farm_stat_changed = pyqtSignal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entry = None
        self._updating = False
        self._bars = {}
        self._total_labels = {}
        self._base_labels = {}
        self._white_cells = {}
        self._farm_cells = {}
        self._blue_cells = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(0)

        # Main grid: 7 columns, one per stat
        grid = QGridLayout()
        grid.setSpacing(6)
        # Rows: 0=total, 1=bar, 2=name, 3=base_label, 4=base_val,
        #        5=growth_label, 6=growth_val, 7=farm_label, 8=farm_val,
        #        9=blue_label, 10=blue_val

        for col, (key, label) in enumerate(zip(STAT_KEYS, STAT_LABELS)):
            color = STAT_COLORS[key]
            grid.setColumnStretch(col, 1)

            # Total value (big, on top)
            total = QLabel("—")
            total.setStyleSheet(
                f"color: {TEXT_VALUE}; font-size: 16px; font-weight: bold; "
                f"background: transparent;")
            total.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._total_labels[key] = total
            grid.addWidget(total, 0, col)

            # Vertical bar (stretches to fill)
            bar = VerticalStatBar(color)
            self._bars[key] = bar
            grid.addWidget(bar, 1, col)

            # Stat name
            name = QLabel(label)
            name.setStyleSheet(
                f"color: {color}; font-size: 14px; font-weight: bold; "
                f"background: transparent;")
            name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(name, 2, col)

            # Base (read-only)
            base_h = QLabel("Base")
            base_h.setStyleSheet(
                f"color: {STAT_BASE}; font-size: 8px; background: transparent;")
            base_h.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(base_h, 3, col)

            base_v = QLabel("—")
            base_v.setStyleSheet(
                f"color: {STAT_BASE}; font-size: 11px; font-weight: bold; "
                f"background: transparent;")
            base_v.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._base_labels[key] = base_v
            grid.addWidget(base_v, 4, col)

            # Growth (editable)
            growth_h = QLabel("Growth")
            growth_h.setStyleSheet(
                f"color: {STAT_WHITE}; font-size: 8px; background: transparent;")
            growth_h.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(growth_h, 5, col)

            white = _Cell(STAT_WHITE)
            white.valueChanged.connect(
                lambda v, k=key: self._on_white_changed(k, v))
            self._white_cells[key] = white
            grid.addWidget(white, 6, col)

            # Farm (editable)
            farm_h = QLabel("Farm")
            farm_h.setStyleSheet(
                f"color: {STAT_FARM}; font-size: 8px; background: transparent;")
            farm_h.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(farm_h, 7, col)

            farm = _Cell(STAT_FARM)
            farm.valueChanged.connect(
                lambda v, k=key: self._on_farm_changed(k, v))
            self._farm_cells[key] = farm
            grid.addWidget(farm, 8, col)

            # Blue (editable)
            blue_h = QLabel("Blue")
            blue_h.setStyleSheet(
                f"color: {STAT_BLUE}; font-size: 8px; background: transparent;")
            blue_h.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(blue_h, 9, col)

            blue = _Cell(STAT_BLUE)
            blue.valueChanged.connect(
                lambda v, k=key: self._on_blue_changed(k, v))
            self._blue_cells[key] = blue
            grid.addWidget(blue, 10, col)

        # Bar row stretches to fill vertical space
        grid.setRowStretch(1, 1)

        layout.addLayout(grid)

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
            self._base_labels[key].setText(str(base))
            self._white_cells[key].setValue(white)
            self._farm_cells[key].setValue(farm)
            self._blue_cells[key].setValue(blue)

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
