"""Horizontal stacked stat bar widget."""

from PyQt6.QtWidgets import QWidget
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
        self._max_val = 3000
        self.setFixedHeight(16)
        self.setMinimumWidth(80)
        self.setMouseTracking(True)

    def set_values(self, base, white, farm, blue, max_val=None):
        self._base = max(0, base)
        self._white = max(0, white)
        self._farm = max(0, farm)
        self._blue = max(0, blue)
        self._max_val = max_val if max_val else max(self.total, 1)
        self.setToolTip(
            f"Base: {self._base}  |  Growth: {self._white}  |  "
            f"Farm: {self._farm}  |  Blue: {self._blue}  =  {self.total}")
        self.update()

    @property
    def total(self):
        return self._base + self._white + self._farm + self._blue

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        r = 3.0

        bg = QPainterPath()
        bg.addRoundedRect(QRectF(0, 0, w, h), r, r)
        p.fillPath(bg, QColor(BG_INPUT))

        if self._max_val <= 0:
            p.end()
            return

        scale = (w - 2) / self._max_val
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
            sw = max(2.0, val * scale)
            if x + sw > w - 1:
                sw = w - 1 - x
            p.fillRect(QRectF(x, 1, sw, h - 2), color)
            x += sw

        border = QPainterPath()
        border.addRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), r, r)
        p.setPen(QColor(255, 255, 255, 20))
        p.drawPath(border)
        p.end()
