"""Main application window for the DSTS Save Editor.

Three-panel layout: left (slot selector + roster), center (grid/scan/agent),
right (Digimon detail editor).
"""

import os
import logging

from PyQt6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                              QSplitter, QToolBar, QStatusBar, QLabel,
                              QMessageBox, QFileDialog, QPushButton, QSizePolicy)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QIcon

from save_data import SaveFile
from ui.style import (GLOBAL_STYLESHEET, BG_PANEL, BG_INPUT, BORDER, ACCENT,
                       TEXT_SECONDARY, TEXT_DISABLED, DIRTY_COLOR, CLEAN_COLOR)
from ui.slot_selector import SlotSelector
from ui.roster_list import RosterList
from ui.digimon_editor import DigimonEditor
from ui.scan_editor import ScanEditor
from ui.agent_editor import AgentEditor

logger = logging.getLogger(__name__)

STAT_KEY_TO_INDEX = {"hp": 0, "sp": 1, "atk": 2, "def": 3, "int": 4, "spi": 5, "spd": 6}


class MainWindow(QMainWindow):
    """Primary application window."""

    def __init__(self):
        super().__init__()
        self._save_file = None
        self._roster = []
        self._current_entry = None

        self.setWindowTitle("DSTS Save Editor")
        self.resize(1280, 800)
        self.setMinimumSize(1024, 700)

        # Window icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                  'data', 'app_icon.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setStyleSheet(GLOBAL_STYLESHEET)
        self._build_toolbar()
        self._build_panels()
        self._build_statusbar()

    def _build_toolbar(self):
        tb = QToolBar("Main Toolbar")
        tb.setMovable(False)
        tb.setIconSize(QSize(16, 16))
        self.addToolBar(tb)

        # Prominent Save button
        self._save_btn = QPushButton("  SAVE  ")
        self._save_btn.setShortcut("Ctrl+S")
        self._save_btn.clicked.connect(self._on_save)
        self._save_btn.setEnabled(False)
        self._save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #1B5E20;
                color: #81C784;
                border: 1px solid #388E3C;
                border-radius: 4px;
                padding: 6px 20px;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: #2E7D32;
                color: #A5D6A7;
            }}
            QPushButton:disabled {{
                background-color: {BG_INPUT};
                color: {TEXT_DISABLED};
                border-color: {BORDER};
            }}
        """)
        tb.addWidget(self._save_btn)

        self._act_save_as = QAction("Save As...", self)
        self._act_save_as.setShortcut("Ctrl+Shift+S")
        self._act_save_as.triggered.connect(self._on_save_as)
        self._act_save_as.setEnabled(False)
        tb.addAction(self._act_save_as)

        tb.addSeparator()

        # Discard button
        self._discard_btn = QPushButton("Discard Changes")
        self._discard_btn.clicked.connect(self._on_discard)
        self._discard_btn.setEnabled(False)
        self._discard_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {TEXT_SECONDARY};
                border: 1px solid {BORDER};
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: #3E2723;
                color: #EF5350;
                border-color: #EF5350;
            }}
            QPushButton:disabled {{
                color: {TEXT_DISABLED};
                border-color: transparent;
            }}
        """)
        tb.addWidget(self._discard_btn)

        tb.addSeparator()

        # View switching buttons
        self._view_btns = {}
        for name, label in [("digimon", "Digimon"), ("scan", "Scan Table"),
                             ("agent", "Agent")]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {TEXT_SECONDARY};
                    border: 1px solid transparent;
                    border-radius: 4px;
                    padding: 4px 12px;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background-color: {BG_INPUT};
                    color: {ACCENT};
                }}
                QPushButton:checked {{
                    background-color: {BG_INPUT};
                    color: {ACCENT};
                    border-color: {ACCENT};
                    font-weight: bold;
                }}
            """)
            btn.clicked.connect(lambda checked, n=name: self._switch_view(n))
            self._view_btns[name] = btn
            tb.addWidget(btn)
        self._view_btns["digimon"].setChecked(True)

        # Stretch spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tb.addWidget(spacer)

        # Version label
        ver = QLabel("  DSTS Save Editor v0.1.0  ")
        ver.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        tb.addWidget(ver)

    def _build_panels(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Left Panel (260px) ──
        left = QWidget()
        left.setFixedWidth(260)
        left.setStyleSheet(
            f"background-color: {BG_PANEL}; border-right: 1px solid {BORDER};")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        self._slot_selector = SlotSelector()
        self._slot_selector.file_selected.connect(self._load_file)
        left_layout.addWidget(self._slot_selector)

        self._roster_list = RosterList()
        self._roster_list.digimon_selected.connect(self._on_digimon_selected)
        left_layout.addWidget(self._roster_list)

        main_layout.addWidget(left)

        # ── Right Panel (stacked views) ── fills remaining space
        from PyQt6.QtWidgets import QStackedWidget
        self._stack = QStackedWidget()

        self._editor = DigimonEditor()
        self._editor.field_changed.connect(self._on_field_changed)
        self._stack.addWidget(self._editor)  # index 0

        self._scan_editor = ScanEditor()
        self._scan_editor.data_changed.connect(self._update_dirty_indicator)
        self._stack.addWidget(self._scan_editor)  # index 1

        self._agent_editor = AgentEditor()
        self._agent_editor.data_changed.connect(self._update_dirty_indicator)
        self._stack.addWidget(self._agent_editor)  # index 2

        main_layout.addWidget(self._stack, 1)  # stretch factor 1

    def _build_statusbar(self):
        sb = QStatusBar()
        self.setStatusBar(sb)

        self._status_file = QLabel("No file loaded")
        sb.addWidget(self._status_file, 1)

        self._status_dirty = QLabel("")
        self._status_dirty.setStyleSheet(f"color: {CLEAN_COLOR}; font-weight: bold;")
        sb.addPermanentWidget(self._status_dirty)

        self._status_count = QLabel("")
        sb.addPermanentWidget(self._status_count)

    # ── File operations ──

    def _load_file(self, path):
        """Load a save file and populate the UI."""
        try:
            self._save_file = SaveFile(path)
            self._roster = self._save_file.read_roster()
            self._roster_list.set_roster(self._roster)
            self._editor.clear()
            self._scan_editor.set_save_file(self._save_file)
            self._agent_editor.set_save_file(self._save_file)
            self._current_entry = None
            self._switch_view("digimon")

            basename = os.path.basename(path)
            self._status_file.setText(f"File: {basename}")
            self._status_count.setText(f"{len(self._roster)} Digimon")
            self._update_dirty_indicator()
            self._save_btn.setEnabled(True)
            self._act_save_as.setEnabled(True)

            logger.info("Loaded %s: %d Digimon", basename, len(self._roster))

        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load save file:\n{e}")
            logger.error("Load failed: %s", e)

    def _on_save(self):
        if not self._save_file:
            return
        try:
            self._save_file.save(backup=True)
            self._update_dirty_indicator()
            self.statusBar().showMessage("Saved with backup", 5000)
            logger.info("Saved to %s", self._save_file.path)
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save:\n{e}")

    def _on_save_as(self):
        if not self._save_file:
            return
        start_dir = os.path.dirname(self._save_file.path)
        path, _ = QFileDialog.getSaveFileName(
            self, "Save As", start_dir, "Save Files (*.bin);;All Files (*)")
        if path:
            self._save_file.path = path
            self._on_save()

    # ── View switching ──

    def _switch_view(self, name):
        """Switch between Digimon editor, scan table, and agent data."""
        view_map = {"digimon": 0, "scan": 1, "agent": 2}
        idx = view_map.get(name, 0)
        self._stack.setCurrentIndex(idx)
        # Update button states
        for key, btn in self._view_btns.items():
            btn.setChecked(key == name)

    # ── Selection ──

    def _on_digimon_selected(self, entry):
        """Called when user clicks a Digimon in the roster list."""
        self._current_entry = entry
        self._editor.set_entry(entry)
        self._switch_view("digimon")

    # ── Editing ──

    def _on_field_changed(self, field, value):
        """Handle edits from the detail editor."""
        if not self._save_file or not self._current_entry:
            return

        offset = self._current_entry["_offset"]

        if field == "level":
            self._save_file.write_level(offset, value)
        elif field == "personality":
            self._save_file.write_personality(offset, value)
        elif field == "talent":
            self._save_file.write_talent(offset, value)
        elif field == "bond":
            self._save_file.write_bond(offset, value)
        elif field == "evo_fwd_count":
            self._save_file.write_evo_counter(offset, value)
        elif field.startswith("blue_"):
            stat_key = field[5:]  # e.g., "blue_hp" -> "hp"
            idx = STAT_KEY_TO_INDEX.get(stat_key)
            if idx is not None:
                self._save_file.write_blue_stat(offset, idx, value)

        self._update_dirty_indicator()

    def _on_discard(self):
        """Reload the file, discarding all in-memory changes."""
        if not self._save_file:
            return
        reply = QMessageBox.question(
            self, "Discard Changes",
            "Discard all unsaved changes and reload from disk?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self._load_file(self._save_file.path)

    def _update_dirty_indicator(self):
        is_dirty = self._save_file and self._save_file.dirty
        self._discard_btn.setEnabled(bool(is_dirty))
        if is_dirty:
            self._status_dirty.setText("● Unsaved Changes")
            self._status_dirty.setStyleSheet(f"color: {DIRTY_COLOR}; font-weight: bold;")
            self._save_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #1B5E20;
                    color: #81C784;
                    border: 2px solid #4CAF50;
                    border-radius: 4px;
                    padding: 6px 20px;
                    font-weight: bold;
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    background-color: #2E7D32;
                    color: #A5D6A7;
                }}
            """)
        else:
            self._status_dirty.setText("● Saved")
            self._status_dirty.setStyleSheet(f"color: {CLEAN_COLOR}; font-weight: bold;")
            self._save_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {BG_INPUT};
                    color: {TEXT_SECONDARY};
                    border: 1px solid {BORDER};
                    border-radius: 4px;
                    padding: 6px 20px;
                    font-weight: bold;
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    background-color: #1B5E20;
                    color: #81C784;
                }}
            """)

    # ── Close guard ──

    def closeEvent(self, event):
        if self._save_file and self._save_file.dirty:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "You have unsaved changes. Save before closing?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel)
            if reply == QMessageBox.StandardButton.Save:
                self._on_save()
                event.accept()
            elif reply == QMessageBox.StandardButton.Discard:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
