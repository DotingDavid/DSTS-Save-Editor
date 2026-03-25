"""Save File Manager — integrated panel for managing save slots and backups.

Embedded in the main window as a view, not a popup dialog.
"""

import os
import shutil
from datetime import datetime

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QTableWidget, QTableWidgetItem,
                              QHeaderView, QAbstractItemView, QMessageBox,
                              QSplitter, QComboBox, QDialog, QFileDialog,
                              QFrame)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from ui.style import (ACCENT, ACCENT_DIM, TEXT_PRIMARY, TEXT_SECONDARY,
                       TEXT_VALUE, BORDER, BG_INPUT, BG_PANEL, BG_HOVER,
                       STAT_FARM, STAT_BLUE, DIRTY_COLOR, CLEAN_COLOR)
from save_data import find_save_directory, list_save_slots
from save_crypto import SAVE_FILE_SIZE


def _fmt_size(b):
    return f"{b / 1024 / 1024:.1f} MB" if b > 1024*1024 else f"{b / 1024:.0f} KB"


def _fmt_date(ts):
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d  %H:%M")


def _sep():
    s = QFrame()
    s.setFixedHeight(1)
    s.setStyleSheet(f"background: {BORDER}; border: none;")
    return s


def _action_btn(text, color=None, danger=False):
    btn = QPushButton(text)
    btn.setFixedHeight(28)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    if danger:
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {TEXT_SECONDARY};
                border: 1px solid {BORDER}; border-radius: 3px;
                padding: 0 12px; font-size: 11px;
            }}
            QPushButton:hover {{
                background: #3E2723; color: #EF5350; border-color: #EF5350;
            }}
        """)
    elif color:
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba({color}, 0.15); color: rgb({color});
                border: 1px solid rgba({color}, 0.4); border-radius: 3px;
                padding: 0 12px; font-size: 11px; font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: rgba({color}, 0.25);
                border-color: rgb({color});
            }}
        """)
    else:
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {TEXT_SECONDARY};
                border: 1px solid {BORDER}; border-radius: 3px;
                padding: 0 12px; font-size: 11px;
            }}
            QPushButton:hover {{
                background: {BG_HOVER}; color: {TEXT_PRIMARY};
                border-color: rgba(255,255,255,0.2);
            }}
        """)
    return btn


class FileManagerPanel(QWidget):
    """Integrated save file manager panel."""

    file_load_requested = pyqtSignal(str)  # request to load a file in the editor

    def __init__(self, parent=None):
        super().__init__(parent)
        self._save_dir = find_save_directory()
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # ── Header ──
        header = QLabel("Save File Manager")
        header.setStyleSheet(
            f"color: {ACCENT}; font-size: 18px; font-weight: bold; "
            f"background: transparent;")
        layout.addWidget(header)

        if self._save_dir:
            path_lbl = QLabel(self._save_dir)
            path_lbl.setStyleSheet(
                f"color: {TEXT_SECONDARY}; font-size: 10px; background: transparent;")
            layout.addWidget(path_lbl)

        # ── Splitter: Slots (top) / Backups (bottom) ──
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setStyleSheet("QSplitter::handle { background: transparent; height: 6px; }")

        # ═══ SAVE SLOTS SECTION ═══
        slots_panel = QWidget()
        slots_panel.setStyleSheet("background: transparent;")
        slots_layout = QVBoxLayout(slots_panel)
        slots_layout.setContentsMargins(0, 0, 0, 0)
        slots_layout.setSpacing(6)

        slots_header = QLabel("SAVE SLOTS")
        slots_header.setStyleSheet(
            f"color: rgba(0,191,255,0.5); font-size: 9px; font-weight: bold; "
            f"letter-spacing: 3px; background: transparent;")
        slots_layout.addWidget(slots_header)

        self._slots_table = QTableWidget()
        self._slots_table.setColumnCount(4)
        self._slots_table.setHorizontalHeaderLabels(
            ["Slot", "Last Modified", "Size", "Backups"])
        self._slots_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch)
        self._slots_table.setColumnWidth(0, 60)
        self._slots_table.setColumnWidth(2, 70)
        self._slots_table.setColumnWidth(3, 70)
        self._slots_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self._slots_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        self._slots_table.verticalHeader().setVisible(False)
        self._slots_table.verticalHeader().setDefaultSectionSize(24)
        self._slots_table.setAlternatingRowColors(True)
        slots_layout.addWidget(self._slots_table)

        # Slot buttons
        s_btns = QHBoxLayout()
        s_btns.setSpacing(4)

        btn = _action_btn("Backup", "0, 191, 255")
        btn.clicked.connect(self._backup_slot)
        s_btns.addWidget(btn)

        btn = _action_btn("Copy To...")
        btn.clicked.connect(self._copy_slot)
        s_btns.addWidget(btn)

        btn = _action_btn("Swap...")
        btn.clicked.connect(self._swap_slots)
        s_btns.addWidget(btn)

        btn = _action_btn("Export...")
        btn.clicked.connect(self._export_save)
        s_btns.addWidget(btn)

        btn = _action_btn("Import...", "129, 199, 132")
        btn.clicked.connect(self._import_save)
        s_btns.addWidget(btn)

        btn = _action_btn("Load in Editor", "0, 191, 255")
        btn.clicked.connect(self._load_in_editor)
        s_btns.addWidget(btn)

        s_btns.addStretch()
        slots_layout.addLayout(s_btns)

        splitter.addWidget(slots_panel)

        # ═══ BACKUPS SECTION ═══
        backups_panel = QWidget()
        backups_panel.setStyleSheet("background: transparent;")
        backups_layout = QVBoxLayout(backups_panel)
        backups_layout.setContentsMargins(0, 0, 0, 0)
        backups_layout.setSpacing(6)

        bak_header_row = QHBoxLayout()
        bak_header = QLabel("BACKUPS")
        bak_header.setStyleSheet(
            f"color: rgba(0,191,255,0.5); font-size: 9px; font-weight: bold; "
            f"letter-spacing: 3px; background: transparent;")
        bak_header_row.addWidget(bak_header)
        bak_header_row.addStretch()
        self._bak_summary = QLabel("")
        self._bak_summary.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 9px; background: transparent;")
        bak_header_row.addWidget(self._bak_summary)
        backups_layout.addLayout(bak_header_row)

        self._backups_table = QTableWidget()
        self._backups_table.setColumnCount(3)
        self._backups_table.setHorizontalHeaderLabels(
            ["Backup File", "Date", "Size"])
        self._backups_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self._backups_table.setColumnWidth(1, 140)
        self._backups_table.setColumnWidth(2, 70)
        self._backups_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self._backups_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        self._backups_table.verticalHeader().setVisible(False)
        self._backups_table.verticalHeader().setDefaultSectionSize(24)
        self._backups_table.setAlternatingRowColors(True)
        backups_layout.addWidget(self._backups_table)

        # Backup buttons
        b_btns = QHBoxLayout()
        b_btns.setSpacing(4)

        btn = _action_btn("Restore", "129, 199, 132")
        btn.clicked.connect(self._restore_backup)
        b_btns.addWidget(btn)

        btn = _action_btn("Delete", danger=True)
        btn.clicked.connect(self._delete_backup)
        b_btns.addWidget(btn)

        btn = _action_btn("Delete All", danger=True)
        btn.clicked.connect(self._delete_all_backups)
        b_btns.addWidget(btn)

        b_btns.addStretch()

        btn = _action_btn("Refresh")
        btn.clicked.connect(self._refresh)
        b_btns.addWidget(btn)

        backups_layout.addLayout(b_btns)

        splitter.addWidget(backups_panel)
        splitter.setSizes([300, 200])

        layout.addWidget(splitter)

        # ═══ SIGNATURE SECTION ═══
        sig_row = QHBoxLayout()
        sig_row.setSpacing(6)

        sig_header = QLabel("SIGNATURE")
        sig_header.setStyleSheet(
            f"color: rgba(0,191,255,0.5); font-size: 9px; font-weight: bold; "
            f"letter-spacing: 3px; background: transparent;")
        sig_row.addWidget(sig_header)
        sig_row.addStretch()

        btn = _action_btn("Restore Pre-Signature Backup", "129, 199, 132")
        btn.setToolTip("Restore this save to its original state from before ANAMNESIS was used. Undoes all edits.")
        btn.clicked.connect(self._restore_pre_signature)
        sig_row.addWidget(btn)

        btn = _action_btn("Unsign Selected Save", danger=True)
        btn.setToolTip("Remove the ANAMNESIS signature from this save. Your edits are kept, only the signature is removed.")
        btn.clicked.connect(self._unsign_save)
        sig_row.addWidget(btn)

        btn = _action_btn("Unsign All Saves", danger=True)
        btn.setToolTip("Remove ANAMNESIS signatures from ALL saves and reset consent. The consent dialog will appear on next launch.")
        btn.clicked.connect(self._unsign_all)
        sig_row.addWidget(btn)

        layout.addLayout(sig_row)

    # ── Data ──

    def _refresh(self):
        self._load_slots()
        self._load_backups()

    def _load_slots(self):
        self._slots_table.setRowCount(0)
        if not self._save_dir:
            return
        slots = list_save_slots(self._save_dir)
        backup_dir = os.path.join(self._save_dir, 'backups')
        self._slots_table.setRowCount(len(slots))

        for row, (num, path, mtime) in enumerate(slots):
            item = QTableWidgetItem(f"{num:04d}")
            item.setData(Qt.ItemDataRole.UserRole, path)
            item.setData(Qt.ItemDataRole.UserRole + 1, num)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._slots_table.setItem(row, 0, item)

            d = QTableWidgetItem(_fmt_date(mtime))
            d.setFlags(d.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._slots_table.setItem(row, 1, d)

            s = QTableWidgetItem(_fmt_size(os.path.getsize(path)))
            s.setFlags(s.flags() & ~Qt.ItemFlag.ItemIsEditable)
            s.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._slots_table.setItem(row, 2, s)

            # Count backups for this slot
            bak_count = 0
            basename = os.path.basename(path)
            if os.path.isdir(backup_dir):
                bak_count = sum(1 for f in os.listdir(backup_dir) if f.startswith(basename))
            b = QTableWidgetItem(str(bak_count) if bak_count else "")
            b.setFlags(b.flags() & ~Qt.ItemFlag.ItemIsEditable)
            b.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if bak_count:
                b.setForeground(QColor(STAT_FARM))
            self._slots_table.setItem(row, 3, b)

    def _load_backups(self):
        self._backups_table.setRowCount(0)
        backup_dir = os.path.join(self._save_dir or "", 'backups')
        if not os.path.isdir(backup_dir):
            self._bak_summary.setText("No backups")
            return
        files = []
        for f in os.listdir(backup_dir):
            if f.endswith('.bak'):
                p = os.path.join(backup_dir, f)
                files.append((f, p, os.path.getmtime(p), os.path.getsize(p)))
        files.sort(key=lambda x: x[2], reverse=True)
        self._backups_table.setRowCount(len(files))

        for row, (name, path, mtime, size) in enumerate(files):
            n = QTableWidgetItem(name)
            n.setData(Qt.ItemDataRole.UserRole, path)
            n.setFlags(n.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._backups_table.setItem(row, 0, n)

            d = QTableWidgetItem(_fmt_date(mtime))
            d.setFlags(d.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._backups_table.setItem(row, 1, d)

            s = QTableWidgetItem(_fmt_size(size))
            s.setFlags(s.flags() & ~Qt.ItemFlag.ItemIsEditable)
            s.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._backups_table.setItem(row, 2, s)

        total = sum(f[3] for f in files)
        self._bak_summary.setText(f"{len(files)} files  ·  {_fmt_size(total)}")

    # ── Helpers ──

    def _selected_slot(self):
        rows = self._slots_table.selectionModel().selectedRows()
        if not rows:
            return None, None
        item = self._slots_table.item(rows[0].row(), 0)
        return item.data(Qt.ItemDataRole.UserRole), item.data(Qt.ItemDataRole.UserRole + 1)

    def _selected_backup(self):
        rows = self._backups_table.selectionModel().selectedRows()
        if not rows:
            return None, None
        item = self._backups_table.item(rows[0].row(), 0)
        return item.data(Qt.ItemDataRole.UserRole), item.text()

    def _make_backup(self, path):
        backup_dir = os.path.join(self._save_dir, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        dest = os.path.join(backup_dir, f"{os.path.basename(path)}.{ts}.bak")
        shutil.copy2(path, dest)
        return dest

    # ── Slot Actions ──

    def _backup_slot(self):
        path, num = self._selected_slot()
        if not path:
            return
        try:
            self._make_backup(path)
            from ui.toast import show_toast
            show_toast(self.window(), f"Backed up slot {num:04d}", "success")
            self._refresh()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _load_in_editor(self):
        path, num = self._selected_slot()
        if path:
            self.file_load_requested.emit(path)

    def _copy_slot(self):
        src, src_num = self._selected_slot()
        if not src:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Copy Slot {src_num:04d}")
        dlg.setMinimumWidth(280)
        dl = QVBoxLayout(dlg)
        dl.addWidget(QLabel(f"Copy slot {src_num:04d} to:"))
        combo = QComboBox()
        for i in range(20):
            p = os.path.join(self._save_dir, f"{i:04d}.bin")
            combo.addItem(f"Slot {i:04d}" + (" (exists)" if os.path.exists(p) else " (empty)"), i)
        dl.addWidget(combo)
        btns = QHBoxLayout()
        btns.addStretch()
        ok = QPushButton("Copy")
        ok.clicked.connect(dlg.accept)
        btns.addWidget(ok)
        btns.addWidget(QPushButton("Cancel", clicked=dlg.reject))
        dl.addLayout(btns)
        if dlg.exec():
            tgt_num = combo.currentData()
            tgt = os.path.join(self._save_dir, f"{tgt_num:04d}.bin")
            try:
                if os.path.exists(tgt):
                    self._make_backup(tgt)
                shutil.copy2(src, tgt)
                from ui.toast import show_toast
                show_toast(self.window(), f"Copied {src_num:04d} → {tgt_num:04d}", "success")
                self._refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _swap_slots(self):
        src, src_num = self._selected_slot()
        if not src:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Swap Slot {src_num:04d}")
        dlg.setMinimumWidth(280)
        dl = QVBoxLayout(dlg)
        dl.addWidget(QLabel(f"Swap slot {src_num:04d} with:"))
        combo = QComboBox()
        for num, path, mtime in list_save_slots(self._save_dir):
            if num != src_num:
                combo.addItem(f"Slot {num:04d}  —  {_fmt_date(mtime)}", num)
        dl.addWidget(combo)
        btns = QHBoxLayout()
        btns.addStretch()
        ok = QPushButton("Swap")
        ok.clicked.connect(dlg.accept)
        btns.addWidget(ok)
        btns.addWidget(QPushButton("Cancel", clicked=dlg.reject))
        dl.addLayout(btns)
        if dlg.exec():
            tgt_num = combo.currentData()
            tgt = os.path.join(self._save_dir, f"{tgt_num:04d}.bin")
            try:
                tmp = src + ".swap"
                shutil.copy2(src, tmp)
                shutil.copy2(tgt, src)
                shutil.move(tmp, tgt)
                from ui.toast import show_toast
                show_toast(self.window(), f"Swapped {src_num:04d} ↔ {tgt_num:04d}", "success")
                self._refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _export_save(self):
        src, num = self._selected_slot()
        if not src:
            return
        dest, _ = QFileDialog.getSaveFileName(
            self, "Export Save", f"DSTS_Slot{num:04d}.bin",
            "Save Files (*.bin);;All Files (*)")
        if dest:
            try:
                shutil.copy2(src, dest)
                from ui.toast import show_toast
                show_toast(self.window(), f"Exported slot {num:04d}", "success")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _import_save(self):
        src, _ = QFileDialog.getOpenFileName(
            self, "Import Save File", "",
            "Save Files (*.bin);;All Files (*)")
        if not src:
            return
        if os.path.getsize(src) != SAVE_FILE_SIZE:
            QMessageBox.critical(self, "Invalid File",
                                  "File size doesn't match a DSTS save file.")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Import Save")
        dlg.setMinimumWidth(280)
        dl = QVBoxLayout(dlg)
        dl.addWidget(QLabel("Import into which slot?"))
        combo = QComboBox()
        for i in range(20):
            p = os.path.join(self._save_dir, f"{i:04d}.bin")
            combo.addItem(f"Slot {i:04d}" + (" (exists)" if os.path.exists(p) else " (empty)"), i)
        dl.addWidget(combo)
        btns = QHBoxLayout()
        btns.addStretch()
        ok = QPushButton("Import")
        ok.clicked.connect(dlg.accept)
        btns.addWidget(ok)
        btns.addWidget(QPushButton("Cancel", clicked=dlg.reject))
        dl.addLayout(btns)
        if dlg.exec():
            tgt_num = combo.currentData()
            tgt = os.path.join(self._save_dir, f"{tgt_num:04d}.bin")
            try:
                if os.path.exists(tgt):
                    self._make_backup(tgt)
                shutil.copy2(src, tgt)
                from ui.toast import show_toast
                show_toast(self.window(), f"Imported to slot {tgt_num:04d}", "success")
                self._refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    # ── Backup Actions ──

    def _restore_backup(self):
        path, name = self._selected_backup()
        if not path:
            return
        original = name.split('.')[0] + '.bin'
        reply = QMessageBox.question(
            self, "Restore", f"Restore {name} to {original}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                shutil.copy2(path, os.path.join(self._save_dir, original))
                from ui.toast import show_toast
                show_toast(self.window(), f"Restored {original}", "success")
                self._refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _delete_backup(self):
        path, name = self._selected_backup()
        if not path:
            return
        reply = QMessageBox.question(
            self, "Delete", f"Delete {name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                os.remove(path)
                self._refresh()
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
            self, "Delete All",
            f"Delete all {len(files)} backups? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            failed = 0
            for f in files:
                try:
                    os.remove(os.path.join(backup_dir, f))
                except Exception:
                    failed += 1
            if failed:
                QMessageBox.warning(
                    self, "Partial Failure",
                    f"Failed to delete {failed} of {len(files)} backups.")
            self._refresh()

    # ── Signature Actions ──

    def _restore_pre_signature(self):
        path, num = self._selected_slot()
        if not path:
            return
        slot_str = f"{num:04d}"
        pre_sig_dir = os.path.join(self._save_dir, 'pre_signature_backups')
        backup_path = os.path.join(pre_sig_dir, f"{slot_str}.bin")
        if not os.path.exists(backup_path):
            QMessageBox.information(
                self, "No Backup",
                f"No pre-signature backup exists for slot {slot_str}.\n\n"
                "This save was either never signed by ANAMNESIS, or the "
                "backup was already restored/deleted.")
            return
        reply = QMessageBox.question(
            self, "Restore Pre-Signature Backup",
            f"Restore slot {slot_str} to its original state from before "
            f"ANAMNESIS first signed it?\n\n"
            f"This will undo ALL changes made by ANAMNESIS SE — your save "
            f"will be exactly as it was before you ever used this tool.\n\n"
            f"Any edits you made (stats, skills, levels, etc.) will be lost.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            from save_data import restore_pre_signature_backup
            restore_pre_signature_backup(self._save_dir, slot_str)
            from ui.toast import show_toast
            show_toast(self.window(), f"Restored pre-signature backup for slot {slot_str}", "success")
            self._refresh()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _unsign_save(self):
        path, num = self._selected_slot()
        if not path:
            return
        slot_str = f"{num:04d}"
        if slot_str == '0000':
            QMessageBox.information(
                self, "Autosave",
                "The autosave (slot 0000) cannot be unsigned directly.\n\n"
                "It inherits the signature from whichever slot you load in-game. "
                "Unsign the source slot instead.")
            return
        reply = QMessageBox.question(
            self, "Unsign Save",
            f"Remove the ANAMNESIS signature from slot {slot_str}?\n\n"
            f"This only removes the signature — your edits and Digimon "
            f"data are NOT affected. The save will look like it was never "
            f"touched by ANAMNESIS.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            from save_data import unsign_save
            if unsign_save(path):
                from ui.toast import show_toast
                show_toast(self.window(), f"Unsigned slot {slot_str}", "success")
            else:
                QMessageBox.information(self, "Not Signed",
                    f"Slot {slot_str} doesn't have an ANAMNESIS signature.")
            self._refresh()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _unsign_all(self):
        if not self._save_dir:
            return
        reply = QMessageBox.question(
            self, "Unsign All Saves",
            "Remove the ANAMNESIS signature from ALL save files?\n\n"
            "This will:\n"
            "  - Remove signatures from every save slot\n"
            "  - Reset the consent preference\n"
            "  - The consent dialog will appear on next launch\n\n"
            "Your edits and Digimon data are NOT affected.\n"
            "Only the signatures are removed.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            from save_data import unsign_save, list_save_slots, _consent_path
            count = 0
            for _, path, _ in list_save_slots(self._save_dir):
                if unsign_save(path):
                    count += 1
            # Delete the consent file so dialog shows again
            consent_path = _consent_path(self._save_dir)
            if os.path.exists(consent_path):
                os.remove(consent_path)
            from ui.toast import show_toast
            show_toast(self.window(),
                       f"Unsigned {count} saves. Consent reset.", "success")
            self._refresh()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
