"""Custom stat bar widgets — horizontal and vertical variants."""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPainterPath
from PyQt6.QtCore import Qt, QRectF

from ui.style import STAT_BASE, STAT_WHITE, STAT_FARM, STAT_BLUE, BG_INPUT


class VerticalStatBar(QWidget):
    """Vertical stacked bar — layers from bottom (base) to top (blue)."""

    def __init__(self, stat_color="#FFFFFF", parent=None):
        super().__init__(parent)
        self._base = 0
        self._white = 0
        self._farm = 0
        self._blue = 0
        self._max_val = 3000
        self._stat_color = stat_color
        self.setMinimumWidth(30)
        self.setMinimumHeight(80)

    def set_values(self, base, white, farm, blue, max_val=None):
        self._base = max(0, base)
        self._white = max(0, white)
        self._farm = max(0, farm)
        self._blue = max(0, blue)
        self._max_val = max_val if max_val else max(self.total, 1)
        self.setToolTip(
            f"Base: {self._base}\nGrowth: {self._white}\n"
            f"Farm: {self._farm}\nBlue: {self._blue}\n"
            f"Total: {self.total}")
        self.update()

    @property
    def total(self):
        return self._base + self._white + self._farm + self._blue

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        r = 4.0
        margin = 2

        # Background
        bg_path = QPainterPath()
        bg_path.addRoundedRect(QRectF(margin, 0, w - margin * 2, h), r, r)
        p.fillPath(bg_path, QColor(BG_INPUT))

        if self._max_val <= 0:
            p.end()
            return

        bar_x = margin + 1
        bar_w = w - margin * 2 - 2
        bar_h = h - 2

        # Draw segments from bottom to top
        segments = [
            (self._base, QColor(STAT_BASE)),
            (self._white, QColor(STAT_WHITE)),
            (self._farm, QColor(STAT_FARM)),
            (self._blue, QColor(STAT_BLUE)),
        ]

        y = h - 1  # start from bottom
        for val, color in segments:
            if val <= 0:
                continue
            seg_h = max(2, (val / self._max_val) * bar_h)
            if y - seg_h < 1:
                seg_h = y - 1
            p.fillRect(QRectF(bar_x, y - seg_h, bar_w, seg_h), color)
            y -= seg_h

        # Subtle top glow line
        glow = QColor(self._stat_color)
        glow.setAlpha(40)
        filled_top = h - 1 - (self.total / self._max_val) * bar_h
        p.fillRect(QRectF(bar_x, max(1, filled_top), bar_w, 2), glow)

        # Border
        border_path = QPainterPath()
        border_path.addRoundedRect(
            QRectF(margin + 0.5, 0.5, w - margin * 2 - 1, h - 1), r, r)
        p.setPen(QColor(255, 255, 255, 20))
        p.drawPath(border_path)

        p.end()
