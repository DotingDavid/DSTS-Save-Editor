"""Global color scheme and stylesheet for the ANAMNESIS Save Editor.

Dark theme matching the ANAMNESIS overlay aesthetic.
"""

# ── Background Colors ──
BG_WINDOW = "#0C0C14"
BG_PANEL = "#121220"
BG_INPUT = "#1E1E37"
BG_HOVER = "#252545"
BG_SELECTED = "rgba(0, 191, 255, 0.15)"
BG_HEADER = "#0A0A12"

# ── Accent Colors ──
ACCENT = "#00BFFF"
ACCENT_DIM = "#0077AA"
ACCENT_BRIGHT = "#33CCFF"

# ── Text Colors ──
TEXT_PRIMARY = "#E8E8F0"
TEXT_SECONDARY = "#8888AA"
TEXT_DISABLED = "#555570"
TEXT_VALUE = "#FFFFFF"

# ── Border Colors ──
BORDER = "rgba(0, 191, 255, 0.25)"
BORDER_BRIGHT = "rgba(0, 191, 255, 0.5)"

# ── Stat Layer Colors ──
STAT_BASE = "#4A6A8A"
STAT_WHITE = "#B0B8C8"
STAT_FARM = "#66BB6A"
STAT_BLUE = "#42A5F5"

# ── Stat Name Colors ──
STAT_COLORS = {
    "hp": "#E57373", "sp": "#CE93D8", "atk": "#FF8A65",
    "def": "#81C784", "int": "#4FC3F7", "spi": "#B39DDB", "spd": "#FFD54F",
}

# ── Personality Category Colors ──
PERS_COLORS = {
    "Valor": "#E57373", "Philanthropy": "#CE93D8",
    "Amicability": "#81C784", "Wisdom": "#4FC3F7",
}

PERS_CATEGORY = {
    1: "Valor", 2: "Valor", 3: "Valor", 4: "Valor",
    5: "Philanthropy", 6: "Philanthropy", 7: "Philanthropy", 8: "Philanthropy",
    9: "Amicability", 10: "Amicability", 11: "Amicability", 12: "Amicability",
    13: "Wisdom", 14: "Wisdom", 15: "Wisdom", 16: "Wisdom",
}

# ── Stage Colors ──
STAGE_COLORS = {
    "In-Training I": "#90CAF9", "In-Training II": "#90CAF9",
    "Rookie": "#81C784", "Champion": "#FFD54F", "Ultimate": "#FF8A65",
    "Mega": "#E57373", "Mega+": "#F44336", "Armor": "#CE93D8",
}

# ── Status Colors ──
DIRTY_COLOR = "#FF8A65"
CLEAN_COLOR = "#81C784"


GLOBAL_STYLESHEET = f"""
QMainWindow {{
    background-color: {BG_WINDOW};
    color: {TEXT_PRIMARY};
    font-family: "Segoe UI", sans-serif;
    font-size: 12px;
}}
QWidget {{
    color: {TEXT_PRIMARY};
    font-family: "Segoe UI", sans-serif;
    font-size: 12px;
}}

QToolBar {{
    background-color: {BG_HEADER};
    border-bottom: 1px solid {BORDER};
    spacing: 6px;
    padding: 2px 8px;
}}
QToolBar QToolButton {{
    background: transparent;
    color: {TEXT_PRIMARY};
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 4px 10px;
    font-size: 12px;
}}
QToolBar QToolButton:hover {{
    background-color: {BG_HOVER};
    border-color: {BORDER};
}}
QToolBar QToolButton:pressed {{
    background-color: {BG_INPUT};
}}

QStatusBar {{
    background-color: {BG_HEADER};
    border-top: 1px solid {BORDER};
    color: {TEXT_SECONDARY};
    font-size: 11px;
}}

QLabel {{
    color: {TEXT_PRIMARY};
}}

QTabWidget::pane {{
    border: 1px solid {BORDER};
    background-color: {BG_PANEL};
    border-radius: 4px;
}}
QTabBar::tab {{
    background-color: {BG_INPUT};
    color: {TEXT_SECONDARY};
    padding: 6px 16px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    border: 1px solid transparent;
    border-bottom: none;
}}
QTabBar::tab:selected {{
    background-color: {BG_PANEL};
    color: {ACCENT};
    border-color: {BORDER};
}}
QTabBar::tab:hover:!selected {{
    background-color: {BG_HOVER};
    color: {TEXT_PRIMARY};
}}

QComboBox {{
    background-color: {BG_INPUT};
    color: {TEXT_VALUE};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 4px 8px;
    min-height: 22px;
}}
QComboBox:hover {{
    border-color: {BORDER_BRIGHT};
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox QAbstractItemView {{
    background-color: #1E1E37;
    color: {TEXT_PRIMARY};
    selection-background-color: #252545;
    selection-color: {ACCENT};
    border: 1px solid {BORDER};
    outline: none;
}}
QComboBox QAbstractItemView::item {{
    background-color: #1E1E37;
    padding: 4px 8px;
}}
QComboBox QAbstractItemView::item:selected {{
    background-color: #252545;
}}

QSpinBox {{
    background-color: {BG_INPUT};
    color: {TEXT_VALUE};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 3px 6px;
    min-height: 22px;
}}
QSpinBox:hover {{
    border-color: {BORDER_BRIGHT};
}}
QSpinBox:focus {{
    border-color: {ACCENT};
}}

QLineEdit {{
    background-color: {BG_INPUT};
    color: {TEXT_VALUE};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 4px 8px;
}}
QLineEdit:focus {{
    border-color: {ACCENT};
}}

QScrollArea {{
    border: none;
    background-color: transparent;
}}
QScrollBar:vertical {{
    background-color: {BG_PANEL};
    width: 8px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background-color: {BORDER_BRIGHT};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QPushButton {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 5px 14px;
    min-height: 24px;
}}
QPushButton:hover {{
    background-color: {BG_HOVER};
    border-color: {BORDER_BRIGHT};
    color: {ACCENT};
}}
QPushButton:pressed {{
    background-color: {ACCENT_DIM};
}}

QSlider::groove:horizontal {{
    background: {BG_INPUT};
    height: 6px;
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: {ACCENT};
    width: 14px;
    height: 14px;
    margin: -4px 0;
    border-radius: 7px;
}}
QSlider::sub-page:horizontal {{
    background: {ACCENT_DIM};
    border-radius: 3px;
}}

QTableWidget {{
    background-color: {BG_PANEL};
    alternate-background-color: {BG_INPUT};
    gridline-color: {BORDER};
    border: 1px solid {BORDER};
    selection-background-color: {BG_HOVER};
    selection-color: {ACCENT};
}}
QHeaderView::section {{
    background-color: {BG_HEADER};
    color: {TEXT_SECONDARY};
    border: 1px solid {BORDER};
    padding: 4px;
    font-weight: bold;
}}

QGroupBox {{
    border: 1px solid {BORDER};
    border-radius: 4px;
    margin-top: 12px;
    padding-top: 16px;
    color: {TEXT_SECONDARY};
    font-weight: bold;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}}

QMessageBox {{
    background-color: {BG_PANEL};
    color: {TEXT_PRIMARY};
}}
QMessageBox QLabel {{
    color: {TEXT_PRIMARY};
    font-size: 12px;
    min-width: 250px;
}}
QMessageBox QPushButton {{
    min-width: 70px;
}}

QSplitter::handle {{
    background-color: {BORDER};
    width: 2px;
}}
QSplitter::handle:hover {{
    background-color: {ACCENT};
}}
"""
