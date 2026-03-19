"""DSTS Save Editor — Digimon Story: Time Stranger Save File Editor.

Main application entry point. PyQt6-based GUI for viewing and editing
save files from Digimon Story: Time Stranger.
"""

import sys
import logging


def main():
    """Launch the save editor application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("DSTS Save Editor")

    from ui.main_window import MainWindow
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
