"""Left navigation panel — save slot selector + view navigation + summary stats."""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton,
                              QFrame, QHBoxLayout, QSizePolicy)
from PyQt6.QtCore import pyqtSignal, Qt

from ui.style import (ACCENT, ACCENT_DIM, ACCENT_BRIGHT, TEXT_PRIMARY,
                       TEXT_SECONDARY, TEXT_VALUE, BG_PANEL, BG_INPUT,
                       BG_HOVER, BORDER, STAT_FARM, STAT_BLUE,
                       PERS_COLORS, DIRTY_COLOR, CLEAN_COLOR)
from ui.slot_selector import SlotSelector


class NavButton(QPushButton):
    """Navigation button with active state styling."""

    def __init__(self, text, icon_char="", parent=None):
        super().__init__(f"  {icon_char}  {text}" if icon_char else f"  {text}", parent)
        self.setCheckable(True)
        self.setFixedHeight(36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._update_style()
        self.toggled.connect(lambda: self._update_style())

    def _update_style(self):
        if self.isChecked():
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {BG_INPUT};
                    color: {ACCENT};
                    border: none;
                    border-left: 3px solid {ACCENT};
                    border-radius: 0px;
                    text-align: left;
                    padding-left: 12px;
                    font-weight: bold;
                    font-size: 12px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {TEXT_SECONDARY};
                    border: none;
                    border-left: 3px solid transparent;
                    border-radius: 0px;
                    text-align: left;
                    padding-left: 12px;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background-color: {BG_HOVER};
                    color: {TEXT_PRIMARY};
                }}
            """)


class NavPanel(QWidget):
    """Left panel with save slot selector, navigation, and summary."""

    view_requested = pyqtSignal(str)  # emits view name
    file_selected = pyqtSignal(str)   # emits file path
    batch_requested = pyqtSignal()    # emits when batch ops button clicked
    backup_requested = pyqtSignal()   # emits when backup manager clicked

    def __init__(self, parent=None):
        super().__init__(parent)
        self._buttons = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Save Slot Selector ──
        self._slot_selector = SlotSelector()
        self._slot_selector.file_selected.connect(self.file_selected.emit)
        layout.addWidget(self._slot_selector)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {BORDER};")
        layout.addWidget(sep)

        # ── Navigation Section ──
        nav_header = QLabel("  VIEWS")
        nav_header.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 10px; font-weight: bold; "
            f"padding: 8px 0 4px 8px; letter-spacing: 2px;")
        layout.addWidget(nav_header)

        nav_items = [
            ("grid", "Roster Grid"),
            ("digimon", "Digimon Editor"),
            ("scan", "Scan Table"),
            ("agent", "Agent / Player"),
        ]
        for key, label in nav_items:
            btn = NavButton(label)
            btn.clicked.connect(lambda checked, k=key: self._on_nav_clicked(k))
            self._buttons[key] = btn
            layout.addWidget(btn)

        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(f"color: {BORDER};")
        layout.addWidget(sep2)

        # ── Tools Section ──
        tools_header = QLabel("  TOOLS")
        tools_header.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 10px; font-weight: bold; "
            f"padding: 8px 0 4px 8px; letter-spacing: 2px;")
        layout.addWidget(tools_header)

        self._batch_btn = QPushButton("  Batch Operations...")
        self._batch_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {TEXT_SECONDARY};
                border: none;
                text-align: left;
                padding: 6px 12px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {BG_HOVER};
                color: {TEXT_PRIMARY};
            }}
        """)
        self._batch_btn.clicked.connect(self.batch_requested.emit)
        layout.addWidget(self._batch_btn)

        self._backup_btn = QPushButton("  Backup Manager...")
        self._backup_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {TEXT_SECONDARY};
                border: none;
                text-align: left;
                padding: 6px 12px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {BG_HOVER};
                color: {TEXT_PRIMARY};
            }}
        """)
        self._backup_btn.clicked.connect(self.backup_requested.emit)
        layout.addWidget(self._backup_btn)

        # Separator
        sep3 = QFrame()
        sep3.setFrameShape(QFrame.Shape.HLine)
        sep3.setStyleSheet(f"color: {BORDER};")
        layout.addWidget(sep3)

        # ── Summary Stats ──
        summary_header = QLabel("  SUMMARY")
        summary_header.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 10px; font-weight: bold; "
            f"padding: 8px 0 4px 8px; letter-spacing: 2px;")
        layout.addWidget(summary_header)

        self._summary_container = QWidget()
        summary_layout = QVBoxLayout(self._summary_container)
        summary_layout.setContentsMargins(12, 4, 12, 4)
        summary_layout.setSpacing(3)

        self._stat_labels = {}
        stats = [
            ("total", "Total Digimon"),
            ("party", "Party"),
            ("box", "Box"),
            ("farm", "Farm"),
            ("scanned", "Scanned"),
            ("scan_100", "Scan 100%+"),
        ]
        for key, label in stats:
            row = QHBoxLayout()
            row.setSpacing(4)
            name_lbl = QLabel(label)
            name_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
            row.addWidget(name_lbl)
            row.addStretch()
            val_lbl = QLabel("—")
            val_lbl.setStyleSheet(f"color: {TEXT_VALUE}; font-size: 11px; font-weight: bold;")
            self._stat_labels[key] = val_lbl
            row.addWidget(val_lbl)
            summary_layout.addLayout(row)

        layout.addWidget(self._summary_container)
        layout.addStretch()

        # ── App info at bottom ──
        info = QLabel("DSTS Save Editor v0.1.0")
        info.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 9px; padding: 8px;")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)

        # Default selection
        self._buttons["grid"].setChecked(True)

    def _on_nav_clicked(self, key):
        # Uncheck all others
        for k, btn in self._buttons.items():
            btn.setChecked(k == key)
        self.view_requested.emit(key)

    def set_active_view(self, key):
        """Programmatically set the active navigation button."""
        for k, btn in self._buttons.items():
            btn.setChecked(k == key)

    def update_summary(self, roster, scan_count=0, scan_100=0):
        """Update summary stats from roster data."""
        if not roster:
            for lbl in self._stat_labels.values():
                lbl.setText("—")
            return

        party = sum(1 for e in roster if e.get("location") == "party")
        box = sum(1 for e in roster if e.get("location") == "box")
        farm = sum(1 for e in roster if e.get("location") == "farm")

        self._stat_labels["total"].setText(str(len(roster)))
        self._stat_labels["party"].setText(str(party))
        self._stat_labels["box"].setText(str(box))
        self._stat_labels["farm"].setText(str(farm))
        self._stat_labels["scanned"].setText(str(scan_count))
        self._stat_labels["scan_100"].setText(str(scan_100))
