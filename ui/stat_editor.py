"""Stats section — compact table with bars extending to the right.

Layout: Name | Base | Growth | Farm | Blue | Total | [=== bar ===]
Numbers are compact on the left, bars fill remaining space on the right.
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
    """Compact editable stat cell."""

    def __init__(self, color, parent=None):
        super().__init__(parent)
        self.setRange(0, 9999)
        self.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.setFixedWidth(46)
        self.setFixedHeight(20)
        self.setStyleSheet(f"""
            QSpinBox {{
                background: transparent;
                color: {color};
                border: none;
                font-size: 11px;
                font-weight: bold;
                padding: 0 2px;
            }}
            QSpinBox:hover {{ background: rgba(255,255,255,0.04); }}
            QSpinBox:focus {{
                background: rgba(0,191,255,0.1);
                border: 1px solid rgba(0,191,255,0.4);
            }}
        """)


class StatEditor(QWidget):
    """Compact stat editor — table on left, bars on right."""

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
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(0)

        # Layout: Name | Base | Growth | Farm | Blue | Total | Bar
        grid = QGridLayout()
        grid.setHorizontalSpacing(4)
        grid.setVerticalSpacing(0)
        grid.setContentsMargins(0, 0, 0, 0)

        # Numbers ~35%, bar ~65%
        for col in range(6):
            grid.setColumnStretch(col, 0)
        grid.setColumnStretch(6, 65)  # bar gets ~65%

        # Headers
        headers = [
            ("", TEXT_SECONDARY),
            ("Base", STAT_BASE),
            ("Growth", STAT_WHITE),
            ("Farm", STAT_FARM),
            ("Blue", STAT_BLUE),
            ("Total", TEXT_VALUE),
            ("", TEXT_SECONDARY),
        ]
        for col, (text, color) in enumerate(headers):
            h = QLabel(text)
            h.setStyleSheet(
                f"color: {color}; font-size: 8px; font-weight: bold; "
                f"background: transparent;")
            h.setAlignment(Qt.AlignmentFlag.AlignCenter)
            h.setFixedHeight(14)
            grid.addWidget(h, 0, col)

        # Data rows
        for row, (key, label) in enumerate(zip(STAT_KEYS, STAT_LABELS), start=1):
            # Name
            name = QLabel(label)
            name.setStyleSheet(
                f"color: {STAT_COLORS[key]}; font-size: 10px; font-weight: bold; "
                f"background: transparent; padding-right: 4px;")
            name.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            name.setFixedHeight(20)
            grid.addWidget(name, row, 0)

            # Base (read-only label, slightly wider for 3-digit values)
            base = QLabel("—")
            base.setFixedWidth(36)
            base.setStyleSheet(
                f"color: {STAT_BASE}; font-size: 11px; font-weight: bold; "
                f"background: transparent; padding: 0 2px;")
            base.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._base_labels[key] = base
            grid.addWidget(base, row, 1)

            # Growth (editable)
            white = _Cell(STAT_WHITE)
            white.valueChanged.connect(lambda v, k=key: self._on_white_changed(k, v))
            self._white_cells[key] = white
            grid.addWidget(white, row, 2)

            # Farm (editable)
            farm = _Cell(STAT_FARM)
            farm.valueChanged.connect(lambda v, k=key: self._on_farm_changed(k, v))
            self._farm_cells[key] = farm
            grid.addWidget(farm, row, 3)

            # Blue (editable)
            blue = _Cell(STAT_BLUE)
            blue.valueChanged.connect(lambda v, k=key: self._on_blue_changed(k, v))
            self._blue_cells[key] = blue
            grid.addWidget(blue, row, 4)

            # Total (read-only)
            total = QLabel("—")
            total.setFixedWidth(42)
            total.setStyleSheet(
                f"color: {TEXT_VALUE}; font-size: 11px; font-weight: bold; "
                f"background: transparent; padding: 0 2px;")
            total.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._total_labels[key] = total
            self._bar_totals[key] = total
            grid.addWidget(total, row, 5)

            # Bar (fills remaining width)
            bar = StatBar()
            bar.setMinimumHeight(18)
            self._bars[key] = bar
            grid.addWidget(bar, row, 6)

        layout.addLayout(grid)

        hint = QLabel("Click on Growth, Farm, or Blue numbers to edit")
        hint.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 9px; "
            f"background: transparent; padding: 4px 0 0 0;")
        hint.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(hint)
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
