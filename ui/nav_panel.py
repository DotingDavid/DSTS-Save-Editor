"""Left navigation panel — clean sidebar with slot selector, navigation, tools, summary."""

import os
from datetime import datetime

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QFrame, QComboBox, QSizePolicy,
                              QFileDialog)
from PyQt6.QtCore import pyqtSignal, Qt

from ui.style import (ACCENT, ACCENT_DIM, TEXT_PRIMARY, TEXT_SECONDARY,
                       TEXT_VALUE, BG_PANEL, BG_INPUT, BG_HOVER, BORDER,
                       STAT_FARM, STAT_BLUE)
from save_data import find_save_directory, find_all_save_directories, list_save_slots


# ── Shared styled helpers ──

def _section_header(text):
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color: rgba(0,191,255,0.5); font-size: 9px; font-weight: bold; "
        f"letter-spacing: 3px; padding: 10px 0 3px 14px; background: transparent;")
    return lbl


def _separator():
    sep = QFrame()
    sep.setFixedHeight(1)
    sep.setStyleSheet(f"background-color: {BORDER}; border: none; margin: 2px 10px;")
    return sep


class _NavButton(QPushButton):
    """Slim navigation button with active highlight."""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setFixedHeight(32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._apply_style()
        self.toggled.connect(lambda: self._apply_style())

    def _apply_style(self):
        if self.isChecked():
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgba(0, 191, 255, 0.08);
                    color: {ACCENT};
                    border: none;
                    border-left: 2px solid {ACCENT};
                    text-align: left;
                    padding-left: 14px;
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
                    border-left: 2px solid transparent;
                    text-align: left;
                    padding-left: 14px;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background-color: rgba(255,255,255,0.03);
                    color: {TEXT_PRIMARY};
                }}
            """)


class _ToolButton(QPushButton):
    """Slim tool button."""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {TEXT_SECONDARY};
                border: none;
                text-align: left;
                padding-left: 16px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: rgba(255,255,255,0.03);
                color: {TEXT_PRIMARY};
            }}
        """)


class NavPanel(QWidget):
    """Clean left sidebar with save slot, navigation, tools, and summary."""

    view_requested = pyqtSignal(str)
    file_selected = pyqtSignal(str)
    batch_requested = pyqtSignal()
    backup_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._buttons = {}
        self._all_accounts = find_all_save_directories()
        self._save_dir = find_save_directory()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(0)

        # ── Save Slot (compact) ──
        slot_section = QWidget()
        slot_section.setStyleSheet("background: transparent;")
        slot_layout = QVBoxLayout(slot_section)
        slot_layout.setContentsMargins(10, 0, 10, 6)
        slot_layout.setSpacing(4)

        # Account label + selector (always shown)
        acct_label = QLabel("ACCOUNT")
        acct_label.setStyleSheet(
            f"color: rgba(0,191,255,0.5); font-size: 8px; font-weight: bold; "
            f"letter-spacing: 2px; background: transparent;")
        slot_layout.addWidget(acct_label)

        self._account_combo = QComboBox()
        self._account_combo.setFixedHeight(26)
        if self._all_accounts:
            for steam_id, path, player_name in self._all_accounts:
                slots = list_save_slots(path)
                label = f"{player_name}  ({len(slots)} saves)"
                self._account_combo.addItem(label, path)
            for i, (_, path, _) in enumerate(self._all_accounts):
                if path == self._save_dir:
                    self._account_combo.setCurrentIndex(i)
                    break
        else:
            self._account_combo.addItem("No saves found")
        self._account_combo.currentIndexChanged.connect(self._on_account_changed)
        slot_layout.addWidget(self._account_combo)

        # Save slot selector
        slot_label = QLabel("SAVE SLOT")
        slot_label.setStyleSheet(
            f"color: rgba(0,191,255,0.5); font-size: 8px; font-weight: bold; "
            f"letter-spacing: 2px; background: transparent; padding-top: 2px;")
        slot_layout.addWidget(slot_label)

        self._combo = QComboBox()
        self._combo.setMaxVisibleItems(16)
        self._combo.setFixedHeight(28)
        self._populate_slots()
        slot_layout.addWidget(self._combo)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)

        load_btn = QPushButton("Load")
        load_btn.setFixedHeight(26)
        load_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(0, 191, 255, 0.12);
                color: {ACCENT};
                border: 1px solid rgba(0, 191, 255, 0.3);
                border-radius: 3px;
                font-size: 11px;
                font-weight: bold;
                padding: 0 12px;
            }}
            QPushButton:hover {{
                background-color: rgba(0, 191, 255, 0.2);
                border-color: {ACCENT};
            }}
        """)
        load_btn.clicked.connect(self._on_load)
        btn_row.addWidget(load_btn)

        open_btn = QPushButton("Open File...")
        open_btn.setFixedHeight(26)
        open_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {TEXT_SECONDARY};
                border: 1px solid {BORDER};
                border-radius: 3px;
                font-size: 10px;
                padding: 0 8px;
            }}
            QPushButton:hover {{
                color: {TEXT_PRIMARY};
                border-color: rgba(255,255,255,0.2);
            }}
        """)
        open_btn.clicked.connect(self._on_open_file)
        btn_row.addWidget(open_btn)
        slot_layout.addLayout(btn_row)

        layout.addWidget(slot_section)
        layout.addWidget(_separator())

        # ── Views ──
        layout.addWidget(_section_header("VIEWS"))

        nav_items = [
            ("grid", "Roster Grid"),
            ("digimon", "Digimon Editor"),
            ("scan", "Scan Table"),
            ("agent", "Agent / Player"),
            ("files", "File Manager"),
        ]
        for key, label in nav_items:
            btn = _NavButton(label)
            btn.clicked.connect(lambda checked, k=key: self._on_nav_clicked(k))
            self._buttons[key] = btn
            layout.addWidget(btn)

        layout.addWidget(_separator())

        # ── Tools ──
        layout.addWidget(_section_header("TOOLS"))

        batch_btn = _ToolButton("Batch Operations...")
        batch_btn.clicked.connect(self.batch_requested.emit)
        layout.addWidget(batch_btn)

        layout.addWidget(_separator())

        # ── Summary ──
        layout.addWidget(_section_header("SUMMARY"))

        summary = QWidget()
        summary.setStyleSheet("background: transparent;")
        s_layout = QVBoxLayout(summary)
        s_layout.setContentsMargins(14, 2, 14, 4)
        s_layout.setSpacing(1)

        self._stat_labels = {}
        stats = [
            ("total", "Digimon", TEXT_VALUE),
            ("party", "Party", ACCENT),
            ("box", "Box", ACCENT_DIM),
            ("farm", "Farm", STAT_FARM),
            ("scanned", "Scanned", TEXT_SECONDARY),
            ("scan_100", "100%+", STAT_BLUE),
        ]
        for key, label, val_color in stats:
            row = QHBoxLayout()
            row.setSpacing(0)
            name_lbl = QLabel(label)
            name_lbl.setStyleSheet(
                f"color: {TEXT_SECONDARY}; font-size: 10px; background: transparent;")
            row.addWidget(name_lbl)
            row.addStretch()
            val_lbl = QLabel("—")
            val_lbl.setStyleSheet(
                f"color: {val_color}; font-size: 10px; font-weight: bold; "
                f"background: transparent;")
            self._stat_labels[key] = val_lbl
            row.addWidget(val_lbl)
            s_layout.addLayout(row)

        layout.addWidget(summary)
        layout.addStretch()

        # ── Version footer ──
        ver = QLabel("ANAMNESIS Save Editor v0.2.0")
        ver.setStyleSheet(
            f"color: rgba(136,136,170,0.4); font-size: 8px; "
            f"background: transparent; padding: 6px;")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(ver)

        # Default
        self._buttons["grid"].setChecked(True)

    def _populate_slots(self):
        self._combo.clear()
        if not self._save_dir:
            self._combo.addItem("No saves found")
            return
        slots = list_save_slots(self._save_dir)
        for slot_num, path, mtime in slots:
            dt = datetime.fromtimestamp(mtime).strftime("%b %d, %H:%M")
            self._combo.addItem(f"Slot {slot_num:04d}  —  {dt}", path)

    def _on_account_changed(self, idx):
        """Switch to a different Steam account's saves."""
        if hasattr(self, '_account_combo') and idx >= 0:
            path = self._account_combo.itemData(idx)
            if path:
                self._save_dir = path
                self._populate_slots()

    def _on_load(self):
        idx = self._combo.currentIndex()
        if idx >= 0:
            path = self._combo.itemData(idx)
            if path and os.path.isfile(path):
                self.file_selected.emit(path)

    def _on_open_file(self):
        start_dir = self._save_dir or ""
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Save File", start_dir,
            "Save Files (*.bin);;All Files (*)")
        if path:
            self.file_selected.emit(path)

    def _on_nav_clicked(self, key):
        for k, btn in self._buttons.items():
            btn.setChecked(k == key)
        self.view_requested.emit(key)

    def set_active_view(self, key):
        for k, btn in self._buttons.items():
            btn.setChecked(k == key)

    def update_summary(self, roster, scan_count=0, scan_100=0):
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
