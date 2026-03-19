"""Save file manager — view, copy, backup, restore, and manage all save slots.

Works independently of loading a save into the editor.
"""

import os
import shutil
from datetime import datetime

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QTableWidget, QTableWidgetItem,
                              QHeaderView, QAbstractItemView, QMessageBox,
                              QTabWidget, QWidget, QComboBox, QFrame)
from PyQt6.QtCore import Qt

from ui.style import (ACCENT, ACCENT_DIM, TEXT_PRIMARY, TEXT_SECONDARY,
                       TEXT_VALUE, BORDER, BG_INPUT, BG_PANEL, BG_HOVER,
                       STAT_FARM, STAT_BLUE, DIRTY_COLOR)
from save_data import find_save_directory, list_save_slots


def _format_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / 1024 / 1024:.1f} MB"


def _format_date(mtime):
    return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d  %H:%M:%S")


class SaveFileManager(QDialog):
    """Full save file manager with slots and backups tabs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._save_dir = find_save_directory()
        self._restored = False
        self.setWindowTitle("Save File Manager")
        self.setMinimumSize(650, 500)
        self._build_ui()
        self._refresh_all()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        header = QLabel("Save File Manager")
        header.setStyleSheet(
            f"color: {ACCENT}; font-size: 16px; font-weight: bold;")
        layout.addWidget(header)

        if self._save_dir:
            path_lbl = QLabel(self._save_dir)
            path_lbl.setStyleSheet(
                f"color: {TEXT_SECONDARY}; font-size: 10px;")
            path_lbl.setWordWrap(True)
            layout.addWidget(path_lbl)
        else:
            warn = QLabel("Save directory not found!")
            warn.setStyleSheet(f"color: {DIRTY_COLOR}; font-size: 12px;")
            layout.addWidget(warn)

        # Tabs
        self._tabs = QTabWidget()

        # ── Slots Tab ──
        slots_widget = QWidget()
        slots_layout = QVBoxLayout(slots_widget)
        slots_layout.setSpacing(6)

        self._slots_table = QTableWidget()
        self._slots_table.setColumnCount(4)
        self._slots_table.setHorizontalHeaderLabels(
            ["Slot", "Last Modified", "Size", "Status"])
        self._slots_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch)
        self._slots_table.setColumnWidth(0, 70)
        self._slots_table.setColumnWidth(2, 80)
        self._slots_table.setColumnWidth(3, 100)
        self._slots_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self._slots_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        self._slots_table.verticalHeader().setVisible(False)
        self._slots_table.verticalHeader().setDefaultSectionSize(26)
        self._slots_table.setAlternatingRowColors(True)
        slots_layout.addWidget(self._slots_table)

        # Slot action buttons
        slot_btns = QHBoxLayout()
        slot_btns.setSpacing(6)

        self._backup_slot_btn = QPushButton("Backup Selected")
        self._backup_slot_btn.setStyleSheet(self._green_btn_style())
        self._backup_slot_btn.clicked.connect(self._backup_slot)
        slot_btns.addWidget(self._backup_slot_btn)

        self._copy_slot_btn = QPushButton("Copy To...")
        self._copy_slot_btn.clicked.connect(self._copy_slot)
        slot_btns.addWidget(self._copy_slot_btn)

        self._swap_slot_btn = QPushButton("Swap With...")
        self._swap_slot_btn.clicked.connect(self._swap_slots)
        slot_btns.addWidget(self._swap_slot_btn)

        self._export_save_btn = QPushButton("Export Save...")
        self._export_save_btn.clicked.connect(self._export_save)
        slot_btns.addWidget(self._export_save_btn)

        self._import_save_btn = QPushButton("Import Save...")
        self._import_save_btn.clicked.connect(self._import_save)
        slot_btns.addWidget(self._import_save_btn)

        slot_btns.addStretch()

        self._refresh_btn = QPushButton("Refresh")
        self._refresh_btn.clicked.connect(self._refresh_all)
        slot_btns.addWidget(self._refresh_btn)

        slots_layout.addLayout(slot_btns)
        self._tabs.addTab(slots_widget, "Save Slots")

        # ── Backups Tab ──
        backups_widget = QWidget()
        backups_layout = QVBoxLayout(backups_widget)
        backups_layout.setSpacing(6)

        self._backups_table = QTableWidget()
        self._backups_table.setColumnCount(3)
        self._backups_table.setHorizontalHeaderLabels(
            ["File", "Date", "Size"])
        self._backups_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self._backups_table.setColumnWidth(1, 160)
        self._backups_table.setColumnWidth(2, 80)
        self._backups_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self._backups_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        self._backups_table.verticalHeader().setVisible(False)
        self._backups_table.verticalHeader().setDefaultSectionSize(26)
        self._backups_table.setAlternatingRowColors(True)
        backups_layout.addWidget(self._backups_table)

        # Backup action buttons
        bak_btns = QHBoxLayout()
        bak_btns.setSpacing(6)

        self._restore_btn = QPushButton("Restore Selected")
        self._restore_btn.setStyleSheet(self._green_btn_style())
        self._restore_btn.clicked.connect(self._restore_backup)
        bak_btns.addWidget(self._restore_btn)

        self._delete_bak_btn = QPushButton("Delete Selected")
        self._delete_bak_btn.setStyleSheet(f"""
            QPushButton:hover {{
                background-color: #3E2723;
                color: #EF5350;
                border-color: #EF5350;
            }}
        """)
        self._delete_bak_btn.clicked.connect(self._delete_backup)
        bak_btns.addWidget(self._delete_bak_btn)

        self._delete_all_btn = QPushButton("Delete All Backups")
        self._delete_all_btn.setStyleSheet(self._delete_bak_btn.styleSheet())
        self._delete_all_btn.clicked.connect(self._delete_all_backups)
        bak_btns.addWidget(self._delete_all_btn)

        bak_btns.addStretch()
        backups_layout.addLayout(bak_btns)

        self._tabs.addTab(backups_widget, "Backups")
        layout.addWidget(self._tabs)

        # Summary + Close
        self._summary = QLabel("")
        self._summary.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 10px;")
        layout.addWidget(self._summary)

        close_row = QHBoxLayout()
        close_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_row.addWidget(close_btn)
        layout.addLayout(close_row)

    def _green_btn_style(self):
        return f"""
            QPushButton {{
                background-color: #1B5E20;
                color: #81C784;
                border: 1px solid #388E3C;
                border-radius: 4px;
                padding: 5px 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #2E7D32;
            }}
        """

    # ── Data loading ──

    def _refresh_all(self):
        self._load_slots()
        self._load_backups()

    def _load_slots(self):
        self._slots_table.setRowCount(0)
        if not self._save_dir:
            return

        slots = list_save_slots(self._save_dir)
        self._slots_table.setRowCount(len(slots))

        for row, (slot_num, path, mtime) in enumerate(slots):
            # Slot number
            slot_item = QTableWidgetItem(f"{slot_num:04d}")
            slot_item.setData(Qt.ItemDataRole.UserRole, path)
            slot_item.setData(Qt.ItemDataRole.UserRole + 1, slot_num)
            slot_item.setFlags(slot_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            slot_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._slots_table.setItem(row, 0, slot_item)

            # Modified date
            date_item = QTableWidgetItem(_format_date(mtime))
            date_item.setFlags(date_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._slots_table.setItem(row, 1, date_item)

            # Size
            size = os.path.getsize(path)
            size_item = QTableWidgetItem(_format_size(size))
            size_item.setFlags(size_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight |
                                       Qt.AlignmentFlag.AlignVCenter)
            self._slots_table.setItem(row, 2, size_item)

            # Status — check if backup exists
            backup_dir = os.path.join(self._save_dir, 'backups')
            basename = os.path.basename(path)
            has_backup = False
            if os.path.isdir(backup_dir):
                has_backup = any(f.startswith(basename) for f in os.listdir(backup_dir))
            status = "Backed up" if has_backup else ""
            status_item = QTableWidgetItem(status)
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if has_backup:
                status_item.setForeground(
                    __import__('PyQt6.QtGui', fromlist=['QColor']).QColor(STAT_FARM))
            self._slots_table.setItem(row, 3, status_item)

        self._summary.setText(f"{len(slots)} save slots found")

    def _load_backups(self):
        self._backups_table.setRowCount(0)
        backup_dir = os.path.join(self._save_dir or "", 'backups')
        if not os.path.isdir(backup_dir):
            return

        files = []
        for f in os.listdir(backup_dir):
            if f.endswith('.bak'):
                path = os.path.join(backup_dir, f)
                files.append((f, path, os.path.getmtime(path),
                              os.path.getsize(path)))

        files.sort(key=lambda x: x[2], reverse=True)
        self._backups_table.setRowCount(len(files))

        for row, (name, path, mtime, size) in enumerate(files):
            name_item = QTableWidgetItem(name)
            name_item.setData(Qt.ItemDataRole.UserRole, path)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._backups_table.setItem(row, 0, name_item)

            date_item = QTableWidgetItem(_format_date(mtime))
            date_item.setFlags(date_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._backups_table.setItem(row, 1, date_item)

            size_item = QTableWidgetItem(_format_size(size))
            size_item.setFlags(size_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight |
                                       Qt.AlignmentFlag.AlignVCenter)
            self._backups_table.setItem(row, 2, size_item)

        total_size = sum(f[3] for f in files)
        self._summary.setText(
            f"{len(files)} backup(s)  —  {_format_size(total_size)} total")

    # ── Slot actions ──

    def _get_selected_slot(self):
        rows = self._slots_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(self, "No Selection",
                                    "Select a save slot first.")
            return None, None
        item = self._slots_table.item(rows[0].row(), 0)
        path = item.data(Qt.ItemDataRole.UserRole)
        slot_num = item.data(Qt.ItemDataRole.UserRole + 1)
        return path, slot_num

    def _backup_slot(self):
        path, slot_num = self._get_selected_slot()
        if not path:
            return
        backup_dir = os.path.join(self._save_dir, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        basename = os.path.basename(path)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(backup_dir, f"{basename}.{ts}.bak")
        try:
            shutil.copy2(path, backup_path)
            QMessageBox.information(
                self, "Backup Created",
                f"Slot {slot_num:04d} backed up to:\n{os.path.basename(backup_path)}")
            self._refresh_all()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Backup failed: {e}")

    def _copy_slot(self):
        src_path, src_num = self._get_selected_slot()
        if not src_path:
            return

        # Build list of target slots (0-19)
        dlg = QDialog(self)
        dlg.setWindowTitle("Copy To Slot")
        dlg.setMinimumWidth(300)
        dlg_layout = QVBoxLayout(dlg)
        dlg_layout.addWidget(QLabel(f"Copy slot {src_num:04d} to:"))

        target_combo = QComboBox()
        for i in range(20):
            target_path = os.path.join(self._save_dir, f"{i:04d}.bin")
            exists = os.path.exists(target_path)
            label = f"Slot {i:04d}" + (" (exists)" if exists else " (empty)")
            target_combo.addItem(label, i)
        dlg_layout.addWidget(target_combo)

        warn = QLabel("This will overwrite the target slot!")
        warn.setStyleSheet(f"color: {DIRTY_COLOR}; font-size: 11px;")
        dlg_layout.addWidget(warn)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ok_btn = QPushButton("Copy")
        ok_btn.setStyleSheet(self._green_btn_style())
        ok_btn.clicked.connect(dlg.accept)
        btn_row.addWidget(ok_btn)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dlg.reject)
        btn_row.addWidget(cancel_btn)
        dlg_layout.addLayout(btn_row)

        if dlg.exec():
            target_num = target_combo.currentData()
            target_path = os.path.join(self._save_dir, f"{target_num:04d}.bin")
            try:
                # Backup target if it exists
                if os.path.exists(target_path):
                    backup_dir = os.path.join(self._save_dir, 'backups')
                    os.makedirs(backup_dir, exist_ok=True)
                    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                    shutil.copy2(target_path, os.path.join(
                        backup_dir, f"{target_num:04d}.bin.{ts}.bak"))

                shutil.copy2(src_path, target_path)
                QMessageBox.information(
                    self, "Copied",
                    f"Slot {src_num:04d} copied to slot {target_num:04d}")
                self._refresh_all()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Copy failed: {e}")

    def _swap_slots(self):
        src_path, src_num = self._get_selected_slot()
        if not src_path:
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Swap Slots")
        dlg.setMinimumWidth(300)
        dlg_layout = QVBoxLayout(dlg)
        dlg_layout.addWidget(QLabel(f"Swap slot {src_num:04d} with:"))

        target_combo = QComboBox()
        slots = list_save_slots(self._save_dir)
        for slot_num, path, mtime in slots:
            if slot_num != src_num:
                dt = datetime.fromtimestamp(mtime).strftime("%b %d, %H:%M")
                target_combo.addItem(f"Slot {slot_num:04d}  —  {dt}", slot_num)
        dlg_layout.addWidget(target_combo)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ok_btn = QPushButton("Swap")
        ok_btn.setStyleSheet(self._green_btn_style())
        ok_btn.clicked.connect(dlg.accept)
        btn_row.addWidget(ok_btn)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dlg.reject)
        btn_row.addWidget(cancel_btn)
        dlg_layout.addLayout(btn_row)

        if dlg.exec():
            target_num = target_combo.currentData()
            target_path = os.path.join(self._save_dir, f"{target_num:04d}.bin")
            try:
                tmp = src_path + ".tmp_swap"
                shutil.copy2(src_path, tmp)
                shutil.copy2(target_path, src_path)
                shutil.move(tmp, target_path)
                QMessageBox.information(
                    self, "Swapped",
                    f"Slot {src_num:04d} ↔ Slot {target_num:04d}")
                self._refresh_all()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Swap failed: {e}")

    def _export_save(self):
        """Export a save slot to a user-chosen location for sharing."""
        src_path, src_num = self._get_selected_slot()
        if not src_path:
            return
        from PyQt6.QtWidgets import QFileDialog
        default_name = f"DSTS_Slot{src_num:04d}.bin"
        dest, _ = QFileDialog.getSaveFileName(
            self, "Export Save File", default_name,
            "Save Files (*.bin);;All Files (*)")
        if dest:
            try:
                shutil.copy2(src_path, dest)
                QMessageBox.information(
                    self, "Exported",
                    f"Slot {src_num:04d} exported to:\n{dest}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Export failed: {e}")

    def _import_save(self):
        """Import a save file from an external location into a slot."""
        from PyQt6.QtWidgets import QFileDialog
        src, _ = QFileDialog.getOpenFileName(
            self, "Import Save File", "",
            "Save Files (*.bin);;All Files (*)")
        if not src:
            return

        # Verify file size
        size = os.path.getsize(src)
        from save_crypto import SAVE_FILE_SIZE
        if size != SAVE_FILE_SIZE:
            QMessageBox.critical(
                self, "Invalid File",
                f"File size is {_format_size(size)}, expected "
                f"{_format_size(SAVE_FILE_SIZE)}.\n\n"
                "This doesn't appear to be a valid DSTS save file.")
            return

        # Choose target slot
        dlg = QDialog(self)
        dlg.setWindowTitle("Import to Slot")
        dlg.setMinimumWidth(300)
        dlg_layout = QVBoxLayout(dlg)
        dlg_layout.addWidget(QLabel(f"Import into which slot?"))

        target_combo = QComboBox()
        for i in range(20):
            target_path = os.path.join(self._save_dir, f"{i:04d}.bin")
            exists = os.path.exists(target_path)
            label = f"Slot {i:04d}" + (" (exists — will backup first)" if exists else " (empty)")
            target_combo.addItem(label, i)
        dlg_layout.addWidget(target_combo)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ok_btn = QPushButton("Import")
        ok_btn.setStyleSheet(self._green_btn_style())
        ok_btn.clicked.connect(dlg.accept)
        btn_row.addWidget(ok_btn)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dlg.reject)
        btn_row.addWidget(cancel_btn)
        dlg_layout.addLayout(btn_row)

        if dlg.exec():
            target_num = target_combo.currentData()
            target_path = os.path.join(self._save_dir, f"{target_num:04d}.bin")
            try:
                # Backup existing slot if it exists
                if os.path.exists(target_path):
                    backup_dir = os.path.join(self._save_dir, 'backups')
                    os.makedirs(backup_dir, exist_ok=True)
                    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                    shutil.copy2(target_path, os.path.join(
                        backup_dir, f"{target_num:04d}.bin.{ts}.bak"))

                shutil.copy2(src, target_path)
                QMessageBox.information(
                    self, "Imported",
                    f"Save file imported to slot {target_num:04d}")
                self._refresh_all()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Import failed: {e}")

    # ── Backup actions ──

    def _get_selected_backup(self):
        rows = self._backups_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(self, "No Selection",
                                    "Select a backup first.")
            return None, None
        item = self._backups_table.item(rows[0].row(), 0)
        path = item.data(Qt.ItemDataRole.UserRole)
        name = item.text()
        return path, name

    def _restore_backup(self):
        path, name = self._get_selected_backup()
        if not path:
            return
        # Parse original slot from backup name (NNNN.bin.timestamp.bak)
        original_name = name.split('.')[0] + '.bin'
        original_path = os.path.join(self._save_dir, original_name)

        reply = QMessageBox.question(
            self, "Restore Backup",
            f"Restore {name}?\n\n"
            f"This will overwrite {original_name}.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            shutil.copy2(path, original_path)
            self._restored = True
            QMessageBox.information(
                self, "Restored",
                f"Restored to {original_name}")
            self._refresh_all()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Restore failed: {e}")

    def _delete_backup(self):
        path, name = self._get_selected_backup()
        if not path:
            return
        reply = QMessageBox.question(
            self, "Delete Backup",
            f"Delete {name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                os.remove(path)
                self._refresh_all()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Delete failed: {e}")

    def _delete_all_backups(self):
        backup_dir = os.path.join(self._save_dir or "", 'backups')
        if not os.path.isdir(backup_dir):
            return
        files = [f for f in os.listdir(backup_dir) if f.endswith('.bak')]
        if not files:
            return
        reply = QMessageBox.question(
            self, "Delete All Backups",
            f"Delete all {len(files)} backup files?\n\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            for f in files:
                try:
                    os.remove(os.path.join(backup_dir, f))
                except Exception:
                    pass
            self._refresh_all()

    @property
    def restored(self):
        return self._restored
