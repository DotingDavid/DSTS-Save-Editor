"""Main application window for the DSTS Save Editor.

Left nav panel + center content area (stacked views).
"""

import os
import struct
import logging

from PyQt6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                              QToolBar, QStatusBar, QLabel, QStackedWidget,
                              QMessageBox, QFileDialog, QPushButton, QSizePolicy)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QIcon

from save_data import SaveFile
from save_layout import SCAN_TABLE_OFFSET, SCAN_TABLE_STRIDE
from ui.style import (GLOBAL_STYLESHEET, BG_PANEL, BG_INPUT, BG_HEADER,
                       BORDER, ACCENT, TEXT_SECONDARY, TEXT_DISABLED,
                       DIRTY_COLOR, CLEAN_COLOR)
from ui.nav_panel import NavPanel
from ui.digimon_editor import DigimonEditor
from ui.roster_grid import RosterGrid
from ui.scan_editor import ScanEditor
from ui.agent_editor import AgentEditor
from ui.batch_ops import BatchOpsDialog
from ui.backup_manager import BackupManager

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

        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                  'data', 'app_icon.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setStyleSheet(GLOBAL_STYLESHEET)
        self._build_toolbar()
        self._build_panels()
        self._build_statusbar()

    # ── Toolbar ──

    def _build_toolbar(self):
        tb = QToolBar("Main Toolbar")
        tb.setMovable(False)
        tb.setIconSize(QSize(16, 16))
        self.addToolBar(tb)

        # Save button
        self._save_btn = QPushButton("  SAVE  ")
        self._save_btn.setShortcut("Ctrl+S")
        self._save_btn.clicked.connect(self._on_save)
        self._save_btn.setEnabled(False)
        self._set_save_btn_style(False)
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
                background: transparent;
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

        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tb.addWidget(spacer)

        # Version
        ver = QLabel("  DSTS Save Editor v0.1.0  ")
        ver.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        tb.addWidget(ver)

    def _set_save_btn_style(self, has_changes):
        if has_changes:
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
                QPushButton:disabled {{
                    background-color: {BG_INPUT};
                    color: {TEXT_DISABLED};
                    border-color: {BORDER};
                }}
            """)

    # ── Panels ──

    def _build_panels(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left nav panel
        self._nav = NavPanel()
        self._nav.setFixedWidth(220)
        self._nav.setStyleSheet(
            f"background-color: {BG_PANEL}; border-right: 1px solid {BORDER};")
        self._nav.file_selected.connect(self._load_file)
        self._nav.view_requested.connect(self._switch_view)
        self._nav.batch_requested.connect(self._on_batch_ops)
        self._nav.backup_requested.connect(self._on_backup_manager)
        main_layout.addWidget(self._nav)

        # Center content (stacked views)
        self._stack = QStackedWidget()

        self._editor = DigimonEditor()
        self._editor.field_changed.connect(self._on_field_changed)
        self._editor.back_requested.connect(lambda: self._switch_view("grid"))
        self._stack.addWidget(self._editor)  # 0: digimon

        self._grid = RosterGrid()
        self._grid.digimon_selected.connect(self._on_grid_selected)
        self._stack.addWidget(self._grid)  # 1: grid

        self._scan_editor = ScanEditor()
        self._scan_editor.data_changed.connect(self._update_dirty_indicator)
        self._stack.addWidget(self._scan_editor)  # 2: scan

        self._agent_editor = AgentEditor()
        self._agent_editor.data_changed.connect(self._update_dirty_indicator)
        self._stack.addWidget(self._agent_editor)  # 3: agent

        main_layout.addWidget(self._stack, 1)

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

    # ── View switching ──

    def _switch_view(self, name):
        view_map = {"digimon": 0, "grid": 1, "scan": 2, "agent": 3}
        idx = view_map.get(name, 1)
        self._stack.setCurrentIndex(idx)
        self._nav.set_active_view(name)

    # ── File operations ──

    def _load_file(self, path):
        try:
            self._save_file = SaveFile(path)
            self._roster = self._save_file.read_roster()
            self._grid.set_roster(self._roster)
            self._editor.clear()
            self._scan_editor.set_save_file(self._save_file)
            self._agent_editor.set_save_file(self._save_file)
            self._current_entry = None

            # Compute scan stats for summary
            from save_data import _get_db
            db = _get_db()
            id_to_name = {}
            for row in db.execute("SELECT id, name FROM digimon"):
                id_to_name[row["id"]] = row["name"]
            d = self._save_file._data
            scan_count = 0
            scan_100 = 0
            for i in range(130, 583):
                off = SCAN_TABLE_OFFSET + i * SCAN_TABLE_STRIDE
                did = struct.unpack('<H', d[off:off+2])[0]
                pct = struct.unpack('<H', d[off+2:off+4])[0]
                if did > 0 and did in id_to_name and pct > 0 and pct <= 200:
                    scan_count += 1
                    if pct >= 100:
                        scan_100 += 1

            self._nav.update_summary(self._roster, scan_count, scan_100)

            basename = os.path.basename(path)
            self._status_file.setText(f"File: {basename}")
            self._status_count.setText(f"{len(self._roster)} Digimon")
            self._update_dirty_indicator()
            self._save_btn.setEnabled(True)
            self._act_save_as.setEnabled(True)
            self._switch_view("grid")

            logger.info("Loaded %s: %d Digimon", basename, len(self._roster))
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load save file:\n{e}")
            logger.error("Load failed: %s", e)

    def _on_save(self):
        if not self._save_file:
            return
        reply = QMessageBox.question(
            self, "Save Changes",
            "Save changes to disk?\n\n"
            "If the game is running on this save slot, it will overwrite "
            "your edits on its next autosave. Close the game or use a "
            "different slot.",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Cancel)
        if reply != QMessageBox.StandardButton.Save:
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

    def _on_discard(self):
        if not self._save_file:
            return
        reply = QMessageBox.question(
            self, "Discard Changes",
            "Discard all unsaved changes and reload from disk?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self._load_file(self._save_file.path)

    # ── Tools ──

    def _on_backup_manager(self):
        if not self._save_file:
            QMessageBox.information(self, "No Data", "Load a save file first.")
            return
        dlg = BackupManager(self._save_file.path, self)
        dlg.exec()
        if dlg.restored:
            self._load_file(self._save_file.path)

    def _on_batch_ops(self):
        if not self._save_file or not self._roster:
            QMessageBox.information(self, "No Data", "Load a save file first.")
            return
        dlg = BatchOpsDialog(self._save_file, self._roster, self)
        dlg.exec()
        if dlg.changes_made:
            self._update_dirty_indicator()

    # ── Selection ──

    def _on_grid_selected(self, entry):
        self._current_entry = entry
        self._editor.set_entry(entry)
        self._switch_view("digimon")

    # ── Editing ──

    def _on_field_changed(self, field, value):
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
            stat_key = field[5:]
            idx = STAT_KEY_TO_INDEX.get(stat_key)
            if idx is not None:
                self._save_file.write_blue_stat(offset, idx, value)
        elif field.startswith("white_"):
            stat_key = field[6:]
            idx = STAT_KEY_TO_INDEX.get(stat_key)
            if idx is not None:
                self._save_file.write_white_stat(offset, idx, value)
        elif field.startswith("farm_"):
            stat_key = field[5:]
            idx = STAT_KEY_TO_INDEX.get(stat_key)
            if idx is not None:
                self._save_file.write_farm_stat(offset, idx, value)
        elif field == "nickname":
            self._save_file.write_nickname(offset, value)
        elif field == "exp":
            self._save_file.write_exp(offset, value)
        elif field == "cur_hp":
            self._save_file.write_cur_hp(offset, value)
        elif field == "cur_sp":
            self._save_file.write_cur_sp(offset, value)
        elif field.startswith("attach_skill_"):
            slot = int(field.split("_")[-1])
            self._save_file.write_attach_skill(offset, slot, value)
        elif field.startswith("equip_"):
            slot = int(field.split("_")[-1])
            self._save_file.write_equipment(offset, slot, value)

        self._update_dirty_indicator()

    def _update_dirty_indicator(self):
        is_dirty = self._save_file and self._save_file.dirty
        self._discard_btn.setEnabled(bool(is_dirty))
        self._set_save_btn_style(bool(is_dirty))
        if is_dirty:
            self._status_dirty.setText("● Unsaved Changes")
            self._status_dirty.setStyleSheet(
                f"color: {DIRTY_COLOR}; font-weight: bold;")
        else:
            self._status_dirty.setText("● Saved")
            self._status_dirty.setStyleSheet(
                f"color: {CLEAN_COLOR}; font-weight: bold;")

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
