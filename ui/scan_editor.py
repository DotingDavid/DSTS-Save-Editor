"""Scan percentage table editor — icon grid view.

Shows scanned Digimon as a grid of icons with percentage overlays.
Click to edit, with search and batch operations.
"""

import struct
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QLineEdit, QScrollArea,
                              QGridLayout, QSpinBox, QMessageBox, QDialog,
                              QFormLayout, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QPixmap, QPainter, QFont

from ui.style import (ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_VALUE,
                       BG_PANEL, BG_INPUT, BORDER, STAT_FARM, ACCENT_DIM)
from ui.icon_cache import get_icon
from save_layout import SCAN_TABLE_OFFSET, SCAN_TABLE_STRIDE

GRID_COLS = 10
ICON_SIZE = 48


class ScanSlot(QWidget):
    """Single scan entry — icon with percentage overlay."""

    clicked = pyqtSignal(int)  # emits row index

    def __init__(self, row, name, pct, parent=None):
        super().__init__(parent)
        self._row = row
        self._name = name
        self._pct = pct
        self.setFixedSize(ICON_SIZE + 16, ICON_SIZE + 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"{name}\n{pct}%")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 0)
        layout.setSpacing(0)

        self._icon = QLabel()
        self._icon.setFixedSize(ICON_SIZE, ICON_SIZE)
        self._icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pm = get_icon(self._name, ICON_SIZE)
        if self._pct == 0:
            # Dim the icon for unscanned
            dark = QPixmap(pm.size())
            dark.fill(QColor(0, 0, 0, 0))
            p = QPainter(dark)
            p.setOpacity(0.25)
            p.drawPixmap(0, 0, pm)
            p.end()
            self._icon.setPixmap(dark)
        else:
            self._icon.setPixmap(pm)

        border_color = self._get_border_color()
        self._icon.setStyleSheet(
            f"border: 2px solid {border_color}; border-radius: 4px; "
            f"background: rgba(12,12,20,200);")
        layout.addWidget(self._icon, alignment=Qt.AlignmentFlag.AlignCenter)

        self._pct_label = QLabel(f"{self._pct}%" if self._pct > 0 else "—")
        color = self._get_text_color()
        self._pct_label.setStyleSheet(
            f"color: {color}; font-size: 9px; font-weight: bold; "
            f"background: transparent; border: none;")
        self._pct_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._pct_label)

    def _get_border_color(self):
        if self._pct >= 200:
            return STAT_FARM
        elif self._pct >= 100:
            return ACCENT
        elif self._pct > 0:
            return BORDER
        return "rgba(255,255,255,0.05)"

    def _get_text_color(self):
        if self._pct >= 200:
            return STAT_FARM
        elif self._pct >= 100:
            return ACCENT
        elif self._pct > 0:
            return TEXT_VALUE
        return TEXT_SECONDARY

    def update_pct(self, pct):
        self._pct = pct
        self.setToolTip(f"{self._name}\n{pct}%")
        self._pct_label.setText(f"{pct}%" if pct > 0 else "—")
        color = self._get_text_color()
        self._pct_label.setStyleSheet(
            f"color: {color}; font-size: 9px; font-weight: bold; "
            f"background: transparent; border: none;")
        border = self._get_border_color()
        self._icon.setStyleSheet(
            f"border: 2px solid {border}; border-radius: 4px; "
            f"background: rgba(12,12,20,200);")
        # Update icon opacity
        pm = get_icon(self._name, ICON_SIZE)
        if pct == 0:
            dark = QPixmap(pm.size())
            dark.fill(QColor(0, 0, 0, 0))
            p = QPainter(dark)
            p.setOpacity(0.25)
            p.drawPixmap(0, 0, pm)
            p.end()
            self._icon.setPixmap(dark)
        else:
            self._icon.setPixmap(pm)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._row)
        super().mousePressEvent(event)


class ScanEditor(QWidget):
    """Scan percentage editor with icon grid."""

    data_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._save_file = None
        self._scan_entries = []
        self._slots = []
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

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search Digimon...")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._on_toolbar_changed)
        toolbar.addWidget(self._search, 1)

        from PyQt6.QtWidgets import QComboBox
        sort_label = QLabel("Sort:")
        sort_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        toolbar.addWidget(sort_label)
        self._sort_combo = QComboBox()
        self._sort_combo.addItems(["Scan % ↓", "Scan % ↑", "Name", "ID"])
        self._sort_combo.setFixedWidth(100)
        self._sort_combo.currentIndexChanged.connect(self._on_toolbar_changed)
        toolbar.addWidget(self._sort_combo)

        filter_label = QLabel("Show:")
        filter_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        toolbar.addWidget(filter_label)
        self._filter_combo = QComboBox()
        self._filter_combo.addItems(["All", "Scanned", "Not Scanned", "100%+", "Under 100%"])
        self._filter_combo.setFixedWidth(110)
        self._filter_combo.currentIndexChanged.connect(self._on_toolbar_changed)
        toolbar.addWidget(self._filter_combo)

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

        # Scrollable grid
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        layout.addWidget(self._scroll)

        self._container = QWidget()
        self._grid_layout = QVBoxLayout(self._container)
        self._grid_layout.setContentsMargins(4, 4, 4, 4)
        self._grid_layout.setSpacing(4)
        self._grid_layout.addStretch()
        self._scroll.setWidget(self._container)

        # Summary
        self._summary = QLabel("")
        self._summary.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        layout.addWidget(self._summary)

    def set_save_file(self, save_file):
        self._save_file = save_file
        self._load_scan_data()

    def _load_scan_data(self):
        if not self._save_file:
            return

        from save_data import _get_db
        db = _get_db()
        id_to_name = {}
        for row in db.execute("SELECT id, name FROM digimon"):
            id_to_name[row["id"]] = row["name"]

        self._scan_entries = []
        d = self._save_file._data

        _REAL_START = 130
        for i in range(_REAL_START, 583):
            off = SCAN_TABLE_OFFSET + i * SCAN_TABLE_STRIDE
            digi_id = struct.unpack('<H', d[off:off + 2])[0]
            scan_pct = struct.unpack('<H', d[off + 2:off + 4])[0]
            if digi_id > 0 and digi_id in id_to_name:
                scan_pct = min(scan_pct, 200)
                self._scan_entries.append(
                    (i, digi_id, id_to_name[digi_id], scan_pct))

        self._rebuild_grid()

    def _on_toolbar_changed(self, *_):
        self._rebuild_grid()

    def _rebuild_grid(self):
        self._slots.clear()
        # Clear existing
        while self._grid_layout.count() > 0:
            item = self._grid_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
            elif item.layout():
                sub = item.layout()
                while sub.count() > 0:
                    si = sub.takeAt(0)
                    sw = si.widget()
                    if sw:
                        sw.deleteLater()

        # Apply search filter
        search = self._search.text().lower().strip()
        entries = []
        for row, (idx, digi_id, name, pct) in enumerate(self._scan_entries):
            if search and search not in name.lower():
                continue
            entries.append((row, idx, digi_id, name, pct))

        # Apply show filter
        show_idx = self._filter_combo.currentIndex()
        if show_idx == 1:  # Scanned
            entries = [e for e in entries if e[4] > 0]
        elif show_idx == 2:  # Not Scanned
            entries = [e for e in entries if e[4] == 0]
        elif show_idx == 3:  # 100%+
            entries = [e for e in entries if e[4] >= 100]
        elif show_idx == 4:  # Under 100%
            entries = [e for e in entries if e[4] < 100]

        # Apply sort
        sort_idx = self._sort_combo.currentIndex()
        if sort_idx == 0:  # Scan % desc (default)
            entries.sort(key=lambda e: e[4], reverse=True)
        elif sort_idx == 1:  # Scan % asc
            entries.sort(key=lambda e: e[4])
        elif sort_idx == 2:  # Name
            entries.sort(key=lambda e: e[3].lower())
        elif sort_idx == 3:  # ID
            entries.sort(key=lambda e: e[2])

        scanned_count = sum(1 for _, _, _, p in self._scan_entries if p > 0)
        full_count = sum(1 for _, _, _, p in self._scan_entries if p >= 100)

        if entries:
            count_lbl = QLabel(f"Showing {len(entries)}")
            count_lbl.setStyleSheet(
                f"color: {TEXT_SECONDARY}; font-size: 10px; "
                f"background: transparent;")
            self._grid_layout.addWidget(count_lbl)
            self._add_grid_section(entries)

        self._grid_layout.addStretch()

        self._summary.setText(
            f"{len(self._scan_entries)} species  |  "
            f"{scanned_count} scanned  |  {full_count} at 100%+")

    def _add_grid_section(self, entries):
        grid = QGridLayout()
        grid.setSpacing(2)
        for i, (row, idx, digi_id, name, pct) in enumerate(entries):
            r = i // GRID_COLS
            c = i % GRID_COLS
            slot = ScanSlot(row, name, pct)
            slot.clicked.connect(self._on_slot_clicked)
            grid.addWidget(slot, r, c)
            self._slots.append(slot)

        wrapper = QWidget()
        wrapper.setLayout(grid)
        self._grid_layout.addWidget(wrapper)

    def _on_slot_clicked(self, row):
        if row < 0 or row >= len(self._scan_entries):
            return
        idx, digi_id, name, old_pct = self._scan_entries[row]

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Edit Scan — {name}")
        dlg.setFixedWidth(280)
        dlg.setStyleSheet(f"""
            QDialog {{ background: #0C0C14; color: #E0E0E0; }}
            QLabel {{ color: #A0A0B0; }}
            QSpinBox {{
                background: #1A1A2E; color: #E0E0E0;
                border: 1px solid {BORDER}; border-radius: 3px;
                padding: 4px; font-size: 14px;
            }}
            QPushButton {{
                background: #1A1A2E; color: #E0E0E0;
                border: 1px solid {BORDER}; border-radius: 4px;
                padding: 6px 16px;
            }}
            QPushButton:hover {{ border-color: {ACCENT}; color: {ACCENT}; }}
        """)
        dl = QVBoxLayout(dlg)

        # Icon + name
        top = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(get_icon(name, 48))
        icon.setFixedSize(52, 52)
        top.addWidget(icon)
        n = QLabel(name)
        n.setStyleSheet(f"color: {TEXT_VALUE}; font-size: 14px; font-weight: bold;")
        top.addWidget(n)
        top.addStretch()
        dl.addLayout(top)

        spin = QSpinBox()
        spin.setRange(0, 200)
        spin.setValue(old_pct)
        spin.setSuffix("%")
        spin.setFixedHeight(32)
        dl.addWidget(spin)

        # Quick buttons
        qrow = QHBoxLayout()
        for val, label in [(0, "0%"), (100, "100%"), (200, "200%")]:
            b = QPushButton(label)
            b.clicked.connect(lambda _, v=val: spin.setValue(v))
            qrow.addWidget(b)
        dl.addLayout(qrow)

        # OK/Cancel
        brow = QHBoxLayout()
        brow.addStretch()
        ok = QPushButton("Save")
        ok.setStyleSheet(f"""
            QPushButton {{
                background: #1B5E20; color: #81C784;
                border: 1px solid #388E3C; border-radius: 4px;
                padding: 6px 20px; font-weight: bold;
            }}
        """)
        ok.clicked.connect(dlg.accept)
        brow.addWidget(ok)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(dlg.reject)
        brow.addWidget(cancel)
        dl.addLayout(brow)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_pct = spin.value()
            if new_pct != old_pct:
                off = SCAN_TABLE_OFFSET + idx * SCAN_TABLE_STRIDE + 2
                struct.pack_into('<h', self._save_file._data, off, new_pct)
                self._save_file._mark_dirty()
                self._scan_entries[row] = (idx, digi_id, name, new_pct)
                # Update the slot widget if it still exists
                for s in self._slots:
                    if s._row == row:
                        s.update_pct(new_pct)
                        break
                self.data_changed.emit()
                self._update_summary()

    def _update_summary(self):
        scanned_count = sum(1 for _, _, _, p in self._scan_entries if p > 0)
        full_count = sum(1 for _, _, _, p in self._scan_entries if p >= 100)
        self._summary.setText(
            f"{len(self._scan_entries)} species  |  "
            f"{scanned_count} scanned  |  {full_count} at 100%+")

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

        for row, (idx, digi_id, name, _) in enumerate(self._scan_entries):
            off = SCAN_TABLE_OFFSET + idx * SCAN_TABLE_STRIDE + 2
            struct.pack_into('<h', self._save_file._data, off, value)
            self._scan_entries[row] = (idx, digi_id, name, value)

        self._save_file._mark_dirty()
        self._rebuild_grid()
        self.data_changed.emit()
