"""Custom stacked stat bar widget.

Draws a horizontal bar with 4 colored segments: Base, White, Farm, Blue.
"""

from PyQt6.QtWidgets import QWidget, QToolTip
from PyQt6.QtGui import QPainter, QColor, QPainterPath
from PyQt6.QtCore import Qt, QRectF

from ui.style import STAT_BASE, STAT_WHITE, STAT_FARM, STAT_BLUE, BG_INPUT


class StatBar(QWidget):
    """Horizontal stacked bar showing stat composition."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._base = 0
        self._white = 0
        self._farm = 0
        self._blue = 0
        self._max_val = 3000  # scale reference
        self.setFixedHeight(18)
        self.setMinimumWidth(120)
        self.setMouseTracking(True)

    def set_values(self, base, white, farm, blue, max_val=None):
        self._base = max(0, base)
        self._white = max(0, white)
        self._farm = max(0, farm)
        self._blue = max(0, blue)
        if max_val:
            self._max_val = max_val
        else:
            self._max_val = max(self.total, 1)
        self.setToolTip(
            f"Base: {self._base}  |  White: {self._white}  |  "
            f"Farm: {self._farm}  |  Blue: {self._blue}  =  {self.total}")
        self.update()

    @property
    def total(self):
        return self._base + self._white + self._farm + self._blue

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        r = 3.0

        # Background
        bg_path = QPainterPath()
        bg_path.addRoundedRect(QRectF(0, 0, w, h), r, r)
        p.fillPath(bg_path, QColor(BG_INPUT))

        if self._max_val <= 0:
            p.end()
            return

        # Compute segment widths
        scale = (w - 2) / self._max_val  # leave 1px margin each side
        segments = [
            (self._base, QColor(STAT_BASE)),
            (self._white, QColor(STAT_WHITE)),
            (self._farm, QColor(STAT_FARM)),
            (self._blue, QColor(STAT_BLUE)),
        ]

        x = 1.0
        for val, color in segments:
            if val <= 0:
                continue
            seg_w = max(2.0, val * scale)
            if x + seg_w > w - 1:
                seg_w = w - 1 - x
            p.fillRect(QRectF(x, 1, seg_w, h - 2), color)
            x += seg_w

        # Border
        border_path = QPainterPath()
        border_path.addRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), r, r)
        p.setPen(QColor(255, 255, 255, 30))
        p.drawPath(border_path)

        p.end()
