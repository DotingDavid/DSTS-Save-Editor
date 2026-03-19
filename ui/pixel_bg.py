"""Animated pixel dissolve background — matching ANAMNESIS Companion style.

Renders small colored squares that randomly respawn at ~1fps,
creating a subtle digital/matrix effect behind the UI.
"""

import random
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor


class PixelDissolveBG(QWidget):
    """Animated pixel dissolve background at ~1fps."""

    _COLORS = [
        QColor(0, 191, 255, 40),    # cyan
        QColor(0, 191, 255, 28),    # cyan dimmer
        QColor(160, 140, 220, 30),  # purple
        QColor(140, 160, 180, 22),  # gray
        QColor(0, 255, 180, 20),    # teal
        QColor(100, 120, 255, 18),  # blue
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setStyleSheet("background: transparent;")
        self._pixels = []
        self._generate_pixels()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def _generate_pixels(self):
        w = max(self.width(), 800)
        h = max(self.height(), 600)
        self._pixels = []
        for _ in range(120):
            x = random.randint(0, w)
            y = random.randint(0, h)
            sz = random.choice([2, 3, 4, 5, 6])
            color = random.choice(self._COLORS)
            self._pixels.append((x, y, sz, color))

    def _tick(self):
        w = max(self.width(), 800)
        h = max(self.height(), 600)
        new_pixels = []
        for x, y, sz, color in self._pixels:
            if random.random() < 0.3:
                x = random.randint(0, w)
                y = random.randint(0, h)
                sz = random.choice([2, 3, 4, 5, 6])
                color = random.choice(self._COLORS)
            new_pixels.append((x, y, sz, color))
        self._pixels = new_pixels
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        for x, y, sz, color in self._pixels:
            painter.fillRect(x, y, sz, sz, color)
        painter.end()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._generate_pixels()

    def showEvent(self, event):
        super().showEvent(event)
        if not self._timer.isActive():
            self._timer.start(1000)

    def hideEvent(self, event):
        super().hideEvent(event)
        self._timer.stop()
