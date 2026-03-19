"""Stats tab — unified stat rows with inline bars and editable values.

Each stat is one row: Name | [===BAR===] | Base | Growth | Farm | Blue | Total
No separate table — everything in one clean view.
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


class _Cell(QSpinBox):
    """Compact borderless spinbox that looks like a text cell until focused."""

    def __init__(self, color, parent=None):
        super().__init__(parent)
        self.setRange(-99999, 99999)
        self.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(28)
        self.setFixedWidth(62)
        self._color = color
        self.setStyleSheet(f"""
            QSpinBox {{
                background: transparent;
                color: {color};
                border: none;
                border-radius: 3px;
                font-size: 13px;
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
    """Unified stat editor — each row is bar + editable breakdown."""

    blue_stat_changed = pyqtSignal(str, int)
    white_stat_changed = pyqtSignal(str, int)
    farm_stat_changed = pyqtSignal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entry = None
        self._updating = False
        self._bars = {}
        self._base_labels = {}
        self._white_cells = {}
        self._farm_cells = {}
        self._blue_cells = {}
        self._total_labels = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(0)

        # ── Column Headers ──
        header = QGridLayout()
        header.setSpacing(0)
        header.setColumnMinimumWidth(0, 38)   # stat name
        header.setColumnStretch(1, 1)          # bar
        header.setColumnMinimumWidth(2, 52)   # base
        header.setColumnMinimumWidth(3, 62)   # growth
        header.setColumnMinimumWidth(4, 62)   # farm
        header.setColumnMinimumWidth(5, 62)   # blue
        header.setColumnMinimumWidth(6, 56)   # total

        col_headers = [
            (0, ""),
            (1, ""),
            (2, "Base"),
            (3, "Growth"),
            (4, "Farm"),
            (5, "Blue"),
            (6, "Total"),
        ]
        col_colors = {
            2: STAT_BASE, 3: STAT_WHITE, 4: STAT_FARM,
            5: STAT_BLUE, 6: TEXT_VALUE
        }
        for col, text in col_headers:
            h = QLabel(text)
            color = col_colors.get(col, TEXT_SECONDARY)
            h.setStyleSheet(
                f"color: {color}; font-size: 9px; font-weight: bold; "
                f"background: transparent;")
            h.setAlignment(Qt.AlignmentFlag.AlignCenter)
            h.setFixedHeight(16)
            header.addWidget(h, 0, col)

        layout.addLayout(header)

        # ── Stat Rows ──
        for i, (key, label) in enumerate(zip(STAT_KEYS, STAT_LABELS)):
            row_widget = QWidget()
            if i % 2 == 1:
                row_widget.setStyleSheet(
                    "background: rgba(255,255,255,0.015); border-radius: 3px;")
            else:
                row_widget.setStyleSheet("background: transparent;")

            row = QHBoxLayout(row_widget)
            row.setContentsMargins(0, 2, 0, 2)
            row.setSpacing(0)

            # Stat name
            name = QLabel(label)
            name.setFixedWidth(38)
            name.setStyleSheet(
                f"color: {STAT_COLORS[key]}; font-size: 13px; font-weight: bold; "
                f"background: transparent;")
            name.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(name)

            # Spacer
            row.addSpacing(6)

            # Bar
            bar = StatBar()
            bar.setFixedHeight(20)
            self._bars[key] = bar
            row.addWidget(bar, 1)

            row.addSpacing(8)

            # Base (read-only)
            base = QLabel("—")
            base.setFixedWidth(52)
            base.setStyleSheet(
                f"color: {STAT_BASE}; font-size: 12px; font-weight: bold; "
                f"background: transparent;")
            base.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._base_labels[key] = base
            row.addWidget(base)

            # Growth (editable)
            white = _Cell(STAT_WHITE)
            white.valueChanged.connect(
                lambda v, k=key: self._on_white_changed(k, v))
            self._white_cells[key] = white
            row.addWidget(white)

            # Farm (editable)
            farm = _Cell(STAT_FARM)
            farm.valueChanged.connect(
                lambda v, k=key: self._on_farm_changed(k, v))
            self._farm_cells[key] = farm
            row.addWidget(farm)

            # Blue (editable)
            blue = _Cell(STAT_BLUE)
            blue.valueChanged.connect(
                lambda v, k=key: self._on_blue_changed(k, v))
            self._blue_cells[key] = blue
            row.addWidget(blue)

            # Total
            total = QLabel("—")
            total.setFixedWidth(56)
            total.setStyleSheet(
                f"color: {TEXT_VALUE}; font-size: 13px; font-weight: bold; "
                f"background: transparent;")
            total.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._total_labels[key] = total
            row.addWidget(total)

            layout.addWidget(row_widget)

        # ── Legend ──
        layout.addSpacing(8)
        legend = QHBoxLayout()
        legend.setSpacing(12)
        legend.addStretch()
        for label, color in [("Base", STAT_BASE), ("Growth", STAT_WHITE),
                              ("Farm", STAT_FARM), ("Blue", STAT_BLUE)]:
            dot = QLabel("■")
            dot.setStyleSheet(
                f"color: {color}; font-size: 10px; background: transparent;")
            dot.setFixedWidth(10)
            legend.addWidget(dot)
            lbl = QLabel(label)
            lbl.setStyleSheet(
                f"color: {TEXT_SECONDARY}; font-size: 9px; background: transparent;")
            legend.addWidget(lbl)
        legend.addStretch()
        layout.addLayout(legend)

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
