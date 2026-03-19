"""Scan percentage table editor.

Shows all 583 Digimon species with their scan percentages.
Supports inline editing, search filtering, and batch operations.
"""

import struct
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QLineEdit, QTableWidget,
                              QTableWidgetItem, QHeaderView, QAbstractItemView,
                              QSpinBox, QStyledItemDelegate, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from ui.style import (ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_VALUE,
                       BG_PANEL, BG_INPUT, BORDER, STAT_FARM, DIRTY_COLOR)
from ui.icon_cache import get_icon
from save_layout import SCAN_TABLE_OFFSET, SCAN_TABLE_STRIDE


class ScanSpinDelegate(QStyledItemDelegate):
    """Inline spinbox editor for scan percentage column."""

    def createEditor(self, parent, option, index):
        spin = QSpinBox(parent)
        spin.setRange(0, 200)
        spin.setSuffix("%")
        return spin

    def setEditorData(self, editor, index):
        val = index.data(Qt.ItemDataRole.EditRole)
        if val is not None:
            editor.setValue(int(val))

    def setModelData(self, editor, model, index):
        model.setData(index, editor.value(), Qt.ItemDataRole.EditRole)


class ScanEditor(QWidget):
    """Scan percentage table with search and batch operations."""

    data_changed = pyqtSignal()  # emitted when any scan value changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self._save_file = None
        self._scan_entries = []  # list of (table_index, digi_id, scan_pct)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Header
        header = QLabel("Scan Percentage Table")
        header.setStyleSheet(
            f"color: {ACCENT}; font-size: 14px; font-weight: bold;")
        layout.addWidget(header)

        # Toolbar row
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search Digimon...")
        self._search.textChanged.connect(self._filter_table)
        toolbar.addWidget(self._search, 1)

        btn_100 = QPushButton("Set All 100%")
        btn_100.clicked.connect(lambda: self._set_all(100))
        toolbar.addWidget(btn_100)

        btn_200 = QPushButton("Set All 200%")
        btn_200.clicked.connect(lambda: self._set_all(200))
        toolbar.addWidget(btn_200)

        btn_clear = QPushButton("Clear All")
        btn_clear.clicked.connect(lambda: self._set_all(0))
        toolbar.addWidget(btn_clear)

        layout.addLayout(toolbar)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["", "Name", "ID", "Scan %"])
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch)
        self._table.setColumnWidth(0, 32)
        self._table.setColumnWidth(2, 50)
        self._table.setColumnWidth(3, 80)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setDefaultSectionSize(28)
        self._table.verticalHeader().setVisible(False)
        self._table.setItemDelegateForColumn(3, ScanSpinDelegate(self))
        self._table.cellChanged.connect(self._on_cell_changed)
        layout.addWidget(self._table)

        # Summary
        self._summary = QLabel("")
        self._summary.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        layout.addWidget(self._summary)

    def set_save_file(self, save_file):
        """Load scan data from a SaveFile."""
        self._save_file = save_file
        self._load_scan_data()

    def _load_scan_data(self):
        if not self._save_file:
            return

        from save_data import get_digimon_name, _get_db
        db = _get_db()
        id_to_name = {}
        for row in db.execute("SELECT id, name FROM digimon"):
            id_to_name[row["id"]] = row["name"]

        self._scan_entries = []
        d = self._save_file._data

        for i in range(583):
            off = SCAN_TABLE_OFFSET + i * SCAN_TABLE_STRIDE
            digi_id = struct.unpack('<h', d[off:off + 2])[0]
            scan_pct = struct.unpack('<h', d[off + 2:off + 4])[0]
            if digi_id > 0:
                name = id_to_name.get(digi_id, f"Unknown({digi_id})")
                self._scan_entries.append((i, digi_id, name, scan_pct))

        self._populate_table()

    def _populate_table(self):
        self._table.blockSignals(True)
        self._table.setRowCount(len(self._scan_entries))

        scanned = 0
        for row, (idx, digi_id, name, pct) in enumerate(self._scan_entries):
            # Icon
            icon_item = QTableWidgetItem()
            icon_item.setIcon(get_icon(name, 24).toImage()
                              if False else get_icon(name, 24))
            # Actually QTableWidgetItem doesn't take QPixmap as icon easily
            # Just use text for now
            icon_item.setText("")
            icon_item.setFlags(icon_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 0, icon_item)

            # Name
            name_item = QTableWidgetItem(name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 1, name_item)

            # ID
            id_item = QTableWidgetItem(str(digi_id))
            id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 2, id_item)

            # Scan %
            pct_item = QTableWidgetItem()
            pct_item.setData(Qt.ItemDataRole.EditRole, pct)
            pct_item.setData(Qt.ItemDataRole.DisplayRole, f"{pct}%")
            pct_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if pct >= 200:
                pct_item.setForeground(QColor(STAT_FARM))
            elif pct >= 100:
                pct_item.setForeground(QColor(ACCENT))
            elif pct > 0:
                pct_item.setForeground(QColor(TEXT_VALUE))
            self._table.setItem(row, 3, pct_item)

            if pct > 0:
                scanned += 1

        self._table.blockSignals(False)
        self._summary.setText(
            f"{len(self._scan_entries)} species  |  "
            f"{scanned} scanned  |  "
            f"{sum(1 for _, _, _, p in self._scan_entries if p >= 100)} at 100%+")

    def _on_cell_changed(self, row, col):
        if col != 3 or not self._save_file:
            return
        item = self._table.item(row, col)
        if not item:
            return
        new_pct = item.data(Qt.ItemDataRole.EditRole)
        if new_pct is None:
            return
        new_pct = int(new_pct)

        idx, digi_id, name, old_pct = self._scan_entries[row]
        if new_pct != old_pct:
            # Write to save data
            off = SCAN_TABLE_OFFSET + idx * SCAN_TABLE_STRIDE + 2
            struct.pack_into('<h', self._save_file._data, off, new_pct)
            self._save_file._mark_dirty()
            self._scan_entries[row] = (idx, digi_id, name, new_pct)

            # Update display
            item.setData(Qt.ItemDataRole.DisplayRole, f"{new_pct}%")
            if new_pct >= 200:
                item.setForeground(QColor(STAT_FARM))
            elif new_pct >= 100:
                item.setForeground(QColor(ACCENT))
            elif new_pct > 0:
                item.setForeground(QColor(TEXT_VALUE))
            else:
                item.setForeground(QColor(TEXT_SECONDARY))

            self.data_changed.emit()

    def _filter_table(self, text):
        text = text.lower()
        for row in range(self._table.rowCount()):
            name_item = self._table.item(row, 1)
            if name_item:
                visible = text in name_item.text().lower() if text else True
                self._table.setRowHidden(row, not visible)

    def _set_all(self, value):
        if not self._save_file:
            return
        label = {0: "Clear", 100: "100%", 200: "200%"}.get(value, str(value))
        reply = QMessageBox.question(
            self, f"Set All to {label}",
            f"Set all {len(self._scan_entries)} scan entries to {value}%?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._table.blockSignals(True)
        for row, (idx, digi_id, name, _) in enumerate(self._scan_entries):
            off = SCAN_TABLE_OFFSET + idx * SCAN_TABLE_STRIDE + 2
            struct.pack_into('<h', self._save_file._data, off, value)
            self._scan_entries[row] = (idx, digi_id, name, value)

            item = self._table.item(row, 3)
            if item:
                item.setData(Qt.ItemDataRole.EditRole, value)
                item.setData(Qt.ItemDataRole.DisplayRole, f"{value}%")

        self._save_file._mark_dirty()
        self._table.blockSignals(False)
        self._populate_table()
        self.data_changed.emit()
