"""Tabbed Digimon detail editor panel (right side).

Contains tabs: Identity, Stats, Skills & Equipment.
"""

import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                              QTabWidget, QLabel, QPushButton)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPixmap

from ui.style import TEXT_SECONDARY, BORDER
from ui.identity_editor import IdentityEditor
from ui.stat_editor import StatEditor
from ui.skills_editor import SkillsEditor


class DigimonEditor(QWidget):
    """Right panel: tabbed editor for one Digimon."""

    field_changed = pyqtSignal(str, object)  # field_name, new_value
    back_requested = pyqtSignal()
    export_requested = pyqtSignal()
    import_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entry = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header bar with back button and Digimon name
        header = QHBoxLayout()
        header.setContentsMargins(8, 6, 8, 6)
        self._back_btn = QPushButton("< Back to Grid")
        self._back_btn.clicked.connect(self.back_requested.emit)
        self._back_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {TEXT_SECONDARY};
                border: none;
                font-size: 11px;
                padding: 4px 8px;
            }}
            QPushButton:hover {{
                color: #00BFFF;
            }}
        """)
        header.addWidget(self._back_btn)
        header.addStretch()

        self._export_btn = QPushButton("Export")
        self._export_btn.clicked.connect(self.export_requested.emit)
        self._export_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {TEXT_SECONDARY};
                border: 1px solid {BORDER}; border-radius: 3px;
                padding: 3px 10px; font-size: 10px;
            }}
            QPushButton:hover {{ color: #00BFFF; border-color: #00BFFF; }}
        """)
        header.addWidget(self._export_btn)

        self._import_btn = QPushButton("Import")
        self._import_btn.clicked.connect(self.import_requested.emit)
        self._import_btn.setStyleSheet(self._export_btn.styleSheet())
        header.addWidget(self._import_btn)

        self._header_name = QLabel("")
        self._header_name.setStyleSheet(
            "color: #E8E8F0; font-size: 13px; font-weight: bold;")
        self._header_name.setAlignment(Qt.AlignmentFlag.AlignRight)
        header.addWidget(self._header_name)

        self._header_widget = QWidget()
        self._header_widget.setLayout(header)
        self._header_widget.hide()
        layout.addWidget(self._header_widget)

        # Welcome screen shown when no Digimon is selected
        self._placeholder = QWidget()
        self._placeholder.setStyleSheet("background: transparent;")
        ph_layout = QVBoxLayout(self._placeholder)
        ph_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_layout.setSpacing(4)

        ph_layout.addStretch(2)

        # Logo image
        from app_paths import get_data_dir
        logo_path = os.path.join(get_data_dir(), 'anamnesis_logo.png')
        if os.path.exists(logo_path):
            logo_label = QLabel()
            logo_pm = QPixmap(logo_path)
            if not logo_pm.isNull():
                from PyQt6.QtCore import QSize
                logo_pm = logo_pm.scaled(
                    QSize(500, 120),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation)
                logo_label.setPixmap(logo_pm)
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            logo_label.setStyleSheet("background: transparent;")
            ph_layout.addWidget(logo_label)

        # Cyan line
        line = QLabel()
        line.setFixedHeight(2)
        line.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            "stop:0 transparent, stop:0.2 #00BFFF, stop:0.8 #00BFFF, "
            "stop:1 transparent); border: none; margin: 0 60px;")
        ph_layout.addWidget(line)

        # Subtitle
        sub = QLabel("SAVE EDITOR  ·  DIGIMON STORY TIME STRANGER")
        sub.setStyleSheet(
            "color: rgba(0, 191, 255, 0.5); font-size: 13px; "
            "font-weight: bold; letter-spacing: 3px; background: transparent;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_layout.addWidget(sub)

        # Tagline
        tag = QLabel("memory access granted")
        tag.setStyleSheet(
            "color: #00BFFF; font-size: 14px; font-weight: bold; "
            "font-style: italic; background: transparent; padding-top: 8px;")
        tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_layout.addWidget(tag)

        # Footer
        foot = QLabel("DIGITAL  ·  EVOLUTION  ·  PROTOCOL")
        foot.setStyleSheet(
            "color: rgba(136, 136, 170, 0.6); font-size: 10px; "
            "letter-spacing: 4px; background: transparent; padding-top: 16px;")
        foot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_layout.addWidget(foot)

        # Instructions
        instr = QLabel("Select a save slot and click Load to get started")
        instr.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 11px; "
            "background: transparent; padding-top: 24px;")
        instr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_layout.addWidget(instr)

        ph_layout.addStretch(3)

        # Tabbed editor
        self._tabs = QTabWidget()

        self._identity = IdentityEditor()
        self._identity.field_changed.connect(self._on_field_changed)
        self._tabs.addTab(self._identity, "Identity")

        self._stats = StatEditor()
        self._stats.blue_stat_changed.connect(
            lambda key, val: self._on_field_changed(f"blue_{key}", val))
        self._stats.white_stat_changed.connect(
            lambda key, val: self._on_field_changed(f"white_{key}", val))
        self._stats.farm_stat_changed.connect(
            lambda key, val: self._on_field_changed(f"farm_{key}", val))
        self._tabs.addTab(self._stats, "Stats")

        self._skills = SkillsEditor()
        self._skills.field_changed.connect(self._on_field_changed)
        self._tabs.addTab(self._skills, "Skills")

        self._tabs.hide()
        layout.addWidget(self._placeholder)
        layout.addWidget(self._tabs)

    def set_entry(self, entry):
        """Load a Digimon entry into all tabs."""
        self._entry = entry
        self._placeholder.hide()
        self._header_widget.show()
        self._tabs.show()
        name = entry.get("nickname") or entry["species"]
        self._header_name.setText(f"{name}  Lv{entry['level']}")
        self._identity.set_entry(entry)
        self._stats.set_entry(entry)
        self._skills.set_entry(entry)

    def clear(self):
        """Show placeholder when nothing is selected."""
        self._entry = None
        self._tabs.hide()
        self._header_widget.hide()
        self._placeholder.show()

    def _on_field_changed(self, field, value):
        self.field_changed.emit(field, value)
