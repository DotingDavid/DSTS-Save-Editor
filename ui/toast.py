"""Toast notifications with fade animation — matching ANAMNESIS style."""

from PyQt6.QtWidgets import QLabel, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve


_STYLES = {
    "info":    ("#00BFFF", "rgba(0, 40, 60, 220)"),
    "success": ("#81C784", "rgba(0, 40, 20, 220)"),
    "warning": ("#FFD54F", "rgba(50, 40, 0, 220)"),
    "error":   ("#EF5350", "rgba(50, 10, 10, 220)"),
}


class Toast(QLabel):
    """Animated toast notification that fades out after a delay."""

    def __init__(self, parent, text, kind="info", duration=2500):
        super().__init__(text, parent)
        fg, bg = _STYLES.get(kind, _STYLES["info"])
        self.setStyleSheet(
            f"background: {bg}; color: {fg}; font-size: 12px; font-weight: bold;"
            f" padding: 8px 18px; border-radius: 8px; border: 1px solid {fg};"
        )
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.adjustSize()

        # Center horizontally at the top of the parent
        pw = parent.width()
        self.move((pw - self.width()) // 2, 10)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self._opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity)
        self._opacity.setOpacity(1.0)
        self.show()
        self.raise_()

        QTimer.singleShot(duration, self._fade_out)

    def _fade_out(self):
        self._anim = QPropertyAnimation(self._opacity, b"opacity")
        self._anim.setDuration(400)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.finished.connect(self.deleteLater)
        self._anim.start()


def show_toast(parent, text, kind="info", duration=2500):
    """Show a toast notification on the parent widget."""
    return Toast(parent, text, kind, duration)
