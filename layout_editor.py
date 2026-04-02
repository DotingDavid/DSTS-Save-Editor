"""Standalone skill tree layout editor.

Run this separately from the save editor to arrange skills on a 10x10 grid
per category, matching the in-game layout. Saves to data/skill_tree_layout.json.

Usage:
    python layout_editor.py
"""

import sys
import os

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from ui.style import GLOBAL_STYLESHEET
from ui.skill_layout_editor import SkillLayoutEditor


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(GLOBAL_STYLESHEET)

    editor = SkillLayoutEditor()
    editor.setWindowTitle("ANAMNESIS — Skill Tree Layout Editor")
    editor.resize(900, 650)
    editor.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
