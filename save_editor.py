"""DSTS Save Editor — Digimon Story: Time Stranger Save File Editor.

Main application entry point. PyQt6-based GUI for viewing and editing
save files from Digimon Story: Time Stranger.
"""

import sys


def main():
    """Launch the save editor application."""
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("DSTS Save Editor")

    # TODO: Build main window UI
    from PyQt6.QtWidgets import QMessageBox
    QMessageBox.information(None, "DSTS Save Editor",
                           "Save editor project initialized.\nUI coming soon.")

    sys.exit(0)


if __name__ == "__main__":
    main()
