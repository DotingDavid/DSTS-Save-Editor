"""Backup manager dialog — view, restore, and delete save backups."""

import os
from datetime import datetime

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QTableWidget, QTableWidgetItem,
                              QHeaderView, QAbstractItemView, QMessageBox)
from PyQt6.QtCore import Qt

from ui.style import ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, BORDER, CLEAN_COLOR


class BackupManager(QDialog):
    """Dialog to manage save file backups."""

    def __init__(self, save_path, parent=None):
        super().__init__(parent)
        self._save_path = save_path
        self._backup_dir = os.path.join(os.path.dirname(save_path), 'backups')
        self._restored = False
        self.setWindowTitle("Backup Manager")
        self.setMinimumSize(550, 400)
        self._build_ui()
        self._load_backups()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        header = QLabel("Save File Backups")
        header.setStyleSheet(
            f"color: {ACCENT}; font-size: 14px; font-weight: bold;")
        layout.addWidget(header)

        path_label = QLabel(f"Backup folder: {self._backup_dir}")
        path_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 10px;")
        path_label.setWordWrap(True)
        layout.addWidget(path_label)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels(["File", "Date", "Size"])
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self._table.setColumnWidth(1, 160)
        self._table.setColumnWidth(2, 80)
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        self._table.verticalHeader().setVisible(False)
        layout.addWidget(self._table)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._restore_btn = QPushButton("Restore Selected")
        self._restore_btn.clicked.connect(self._on_restore)
        self._restore_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #1B5E20;
                color: #81C784;
                border: 1px solid #388E3C;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #2E7D32;
            }}
        """)
        btn_row.addWidget(self._restore_btn)

        self._delete_btn = QPushButton("Delete Selected")
        self._delete_btn.clicked.connect(self._on_delete)
        btn_row.addWidget(self._delete_btn)

        btn_row.addStretch()

        self._close_btn = QPushButton("Close")
        self._close_btn.clicked.connect(self.accept)
        btn_row.addWidget(self._close_btn)

        layout.addLayout(btn_row)

        # Info
        self._info = QLabel("")
        self._info.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 10px;")
        layout.addWidget(self._info)

    def _load_backups(self):
        self._table.setRowCount(0)
        if not os.path.isdir(self._backup_dir):
            self._info.setText("No backups folder found.")
            return

        files = []
        for f in os.listdir(self._backup_dir):
            if f.endswith('.bak'):
                path = os.path.join(self._backup_dir, f)
                mtime = os.path.getmtime(path)
                size = os.path.getsize(path)
                files.append((f, path, mtime, size))

        files.sort(key=lambda x: x[2], reverse=True)

        self._table.setRowCount(len(files))
        for row, (name, path, mtime, size) in enumerate(files):
            name_item = QTableWidgetItem(name)
            name_item.setData(Qt.ItemDataRole.UserRole, path)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 0, name_item)

            dt = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            date_item = QTableWidgetItem(dt)
            date_item.setFlags(date_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 1, date_item)

            size_mb = f"{size / 1024 / 1024:.1f} MB"
            size_item = QTableWidgetItem(size_mb)
            size_item.setFlags(size_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight |
                                       Qt.AlignmentFlag.AlignVCenter)
            self._table.setItem(row, 2, size_item)

        self._info.setText(f"{len(files)} backup(s) found")

    def _get_selected_path(self):
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return None
        item = self._table.item(rows[0].row(), 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _on_restore(self):
        path = self._get_selected_path()
        if not path:
            QMessageBox.information(self, "No Selection", "Select a backup to restore.")
            return

        name = os.path.basename(path)
        reply = QMessageBox.question(
            self, "Restore Backup",
            f"Restore {name}?\n\nThis will overwrite the current save file.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return

        import shutil
        try:
            # Figure out which save file this backup belongs to
            # Backup name format: NNNN.bin.YYYYMMDD_HHMMSS.bak
            original_name = name.split('.')[0] + '.bin'
            original_path = os.path.join(os.path.dirname(self._backup_dir), original_name)
            shutil.copy2(path, original_path)
            self._restored = True
            QMessageBox.information(
                self, "Restored",
                f"Restored {name} to {original_name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Restore failed: {e}")

    def _on_delete(self):
        path = self._get_selected_path()
        if not path:
            return
        name = os.path.basename(path)
        reply = QMessageBox.question(
            self, "Delete Backup",
            f"Delete {name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                os.remove(path)
                self._load_backups()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Delete failed: {e}")

    @property
    def restored(self):
        return self._restored
