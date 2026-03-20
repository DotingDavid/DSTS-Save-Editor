"""Main application window for the ANAMNESIS SE.

Left nav panel + center content area (stacked views).
"""

import os
import struct
import logging

from PyQt6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                              QToolBar, QStatusBar, QLabel, QStackedWidget,
                              QMessageBox, QFileDialog, QPushButton, QSizePolicy)
from PyQt6.QtCore import Qt, QSize, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QIcon

from save_data import SaveFile, is_game_running
from save_layout import SCAN_TABLE_OFFSET, SCAN_TABLE_STRIDE
from app_paths import get_app_icon_path
from ui.style import (GLOBAL_STYLESHEET, BG_PANEL, BG_INPUT, BG_HEADER,
                       BORDER, ACCENT, TEXT_SECONDARY, TEXT_DISABLED,
                       DIRTY_COLOR, CLEAN_COLOR)
from ui.nav_panel import NavPanel
from ui.digimon_editor import DigimonEditor
from ui.roster_grid import RosterGrid
from ui.scan_editor import ScanEditor
from ui.agent_editor import AgentEditor
from ui.batch_ops import BatchOpsDialog
from ui.file_manager import FileManagerPanel
from ui.toast import show_toast
from ui.pixel_bg import PixelDissolveBG

logger = logging.getLogger(__name__)


class ProcessChecker(QThread):
    """Background thread to check if the game is running."""
    result = pyqtSignal(bool)

    def run(self):
        self.result.emit(is_game_running())


STAT_KEY_TO_INDEX = {"hp": 0, "sp": 1, "atk": 2, "def": 3, "int": 4, "spi": 5, "spd": 6}


class MainWindow(QMainWindow):
    """Primary application window."""

    def __init__(self):
        super().__init__()
        self._save_file = None
        self._roster = []
        self._current_entry = None

        self.setWindowTitle("ANAMNESIS SE")
        self.resize(1280, 800)
        self.setMinimumSize(1024, 700)

        # No custom icon yet — user will provide one later
        self.setStyleSheet(GLOBAL_STYLESHEET)
        self._build_toolbar()
        self._build_panels()
        self._build_statusbar()

        # Game process detection timer
        self._game_running = False
        self._process_timer = QTimer()
        self._process_timer.timeout.connect(self._check_game_process)
        self._process_timer.start(5000)

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
        ver = QLabel("  ANAMNESIS SE v0.3.0  ")
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

        # Pixel dissolve background (spans entire window)
        self._pixel_bg = PixelDissolveBG(central)
        self._pixel_bg.setGeometry(0, 0, 1280, 800)
        self._pixel_bg.lower()  # behind all other widgets

        # Left nav panel — semi-transparent so pixel BG shows through
        self._nav = NavPanel()
        self._nav.setFixedWidth(220)
        self._nav.setStyleSheet(
            f"background-color: rgba(18, 18, 32, 200); border-right: 1px solid {BORDER};")
        self._nav.file_selected.connect(self._load_file)
        self._nav.view_requested.connect(self._switch_view)
        self._nav.batch_requested.connect(self._on_batch_ops)
        self._nav.backup_requested.connect(self._on_backup_manager)
        main_layout.addWidget(self._nav)

        # Center content (stacked views) — transparent so pixel BG shows
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background: transparent;")

        self._editor = DigimonEditor()
        self._editor.field_changed.connect(self._on_field_changed)
        self._editor.back_requested.connect(lambda: self._switch_view("grid"))
        self._editor.export_requested.connect(
            lambda: self._on_export(self._current_entry) if self._current_entry else None)
        self._editor.import_requested.connect(self._on_import)
        self._stack.addWidget(self._editor)  # 0: digimon

        self._grid = RosterGrid()
        self._grid.digimon_selected.connect(self._on_grid_selected)
        self._grid.clone_requested.connect(self._on_clone)
        self._grid.export_requested.connect(self._on_export)
        self._grid.create_requested.connect(self._on_create_digimon)
        self._stack.addWidget(self._grid)  # 1: grid

        self._scan_editor = ScanEditor()
        self._scan_editor.data_changed.connect(self._update_dirty_indicator)
        self._stack.addWidget(self._scan_editor)  # 2: scan

        self._agent_editor = AgentEditor()
        self._agent_editor.data_changed.connect(self._update_dirty_indicator)
        self._stack.addWidget(self._agent_editor)  # 3: agent

        self._file_manager = FileManagerPanel()
        self._file_manager.file_load_requested.connect(self._load_file)
        self._stack.addWidget(self._file_manager)  # 4: files

        main_layout.addWidget(self._stack, 1)

    def _build_statusbar(self):
        sb = QStatusBar()
        self.setStatusBar(sb)

        self._status_file = QLabel("No file loaded")
        sb.addWidget(self._status_file, 1)

        self._game_warning = QLabel("")
        self._game_warning.setStyleSheet(
            "color: #EF5350; font-weight: bold; font-size: 11px;")
        self._game_warning.hide()
        sb.addPermanentWidget(self._game_warning)

        self._status_dirty = QLabel("")
        self._status_dirty.setStyleSheet(f"color: {CLEAN_COLOR}; font-weight: bold;")
        sb.addPermanentWidget(self._status_dirty)

        self._status_count = QLabel("")
        sb.addPermanentWidget(self._status_count)

    # ── View switching ──

    def _switch_view(self, name):
        # File manager always accessible; others need a save loaded
        if not self._save_file and name not in ("digimon", "files"):
            show_toast(self, "Load a save file first", "warning")
            self._nav.set_active_view("digimon")
            return
        view_map = {"digimon": 0, "grid": 1, "scan": 2, "agent": 3, "files": 4}
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

            show_toast(self, f"Loaded {len(self._roster)} Digimon from {basename}", "info")
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
            show_toast(self, "Saved with backup", "success")
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
        self._file_manager._refresh()
        self._switch_view("files")

    def _on_batch_ops(self):
        if not self._save_file or not self._roster:
            show_toast(self, "Load a save file first", "warning")
            return
        dlg = BatchOpsDialog(self._save_file, self._roster, self)
        dlg.exec()
        if dlg.changes_made:
            self._update_dirty_indicator()

    # ── Create / Clone / Export / Import ──

    def _on_create_digimon(self):
        if not self._save_file:
            return
        from ui.digimon_creator import DigimonCreatorDialog
        dlg = DigimonCreatorDialog(self)
        if dlg.exec() and dlg.selected_id:
            try:
                self._save_file.create_digimon(
                    dlg.selected_id, dlg.level, dlg.personality_id)
                self._roster = self._save_file.read_roster()
                self._grid.set_roster(self._roster)
                self._update_dirty_indicator()
                from save_data import get_digimon_name
                name = get_digimon_name(dlg.selected_id)
                show_toast(self, f"Created {name} Lv{dlg.level}", "success")
            except Exception as e:
                QMessageBox.critical(self, "Create Error", str(e))

    def _on_clone(self, entry):
        if not self._save_file:
            return
        name = entry.get("nickname") or entry["species"]
        reply = QMessageBox.question(
            self, "Clone Digimon",
            f"Clone {name} (Lv{entry['level']})?\n\n"
            "The clone will be placed in the box with a new creation hash.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            new_off = self._save_file.clone_digimon(entry["_offset"])
            self._roster = self._save_file.read_roster()
            self._grid.set_roster(self._roster)
            self._update_dirty_indicator()
            show_toast(self, f"Cloned {name} to box", "success")
        except Exception as e:
            QMessageBox.critical(self, "Clone Error", str(e))

    def _on_export(self, entry):
        if not self._save_file or not entry:
            return
        try:
            import json
            data = self._save_file.export_digimon(entry["_offset"])
            name = entry.get("nickname") or entry["species"]
            default_name = f"{name}_Lv{entry['level']}.digi"
            path, _ = QFileDialog.getSaveFileName(
                self, "Export Digimon", default_name,
                "Digimon Files (*.digi);;All Files (*)")
            if path:
                with open(path, 'w') as f:
                    json.dump(data, f, indent=2)
                show_toast(self, f"Exported {name}", "success")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))

    def _on_import(self):
        if not self._save_file:
            show_toast(self, "Load a save file first", "warning")
            return
        try:
            import json
            path, _ = QFileDialog.getOpenFileName(
                self, "Import Digimon", "",
                "Digimon Files (*.digi);;All Files (*)")
            if not path:
                return
            with open(path, 'r') as f:
                data = json.load(f)
            species = data.get("species", "Unknown")
            reply = QMessageBox.question(
                self, "Import Digimon",
                f"Import {species} (Lv{data.get('level', '?')})?\n\n"
                "It will be placed in the box with a new creation hash.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return
            self._save_file.import_digimon(data)
            self._roster = self._save_file.read_roster()
            self._grid.set_roster(self._roster)
            self._update_dirty_indicator()
            show_toast(self, f"Imported {species}", "success")
        except Exception as e:
            QMessageBox.critical(self, "Import Error", str(e))

    # ── Game process detection ──

    def _check_game_process(self):
        checker = ProcessChecker()
        checker.result.connect(self._on_process_check)
        checker.start()
        self._checker = checker  # prevent GC

    def _on_process_check(self, running):
        self._game_running = running
        if running:
            self._game_warning.setText("GAME RUNNING")
            self._game_warning.show()
        else:
            self._game_warning.hide()

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
        elif field == "species_change":
            self._save_file.change_species(offset, value)
            # Reload roster and refresh
            self._roster = self._save_file.read_roster()
            self._grid.set_roster(self._roster)
            # Find and re-select the changed entry
            for e in self._roster:
                if e["_offset"] == offset:
                    self._current_entry = e
                    self._editor.set_entry(e)
                    break
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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_pixel_bg'):
            self._pixel_bg.setGeometry(self.centralWidget().rect())

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
