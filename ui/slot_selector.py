"""Save slot selector panel.

Displays available save slots and lets the user choose one to load.
"""

import os
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                              QComboBox, QPushButton, QLabel, QFileDialog)
from PyQt6.QtCore import pyqtSignal

from save_data import find_save_directory, list_save_slots
from ui.style import TEXT_SECONDARY, ACCENT


class SlotSelector(QWidget):
    """Save slot picker with auto-detection of game save directory."""

    file_selected = pyqtSignal(str)  # emits file path

    def __init__(self, parent=None):
        super().__init__(parent)
        self._save_dir = find_save_directory()
        self._slots = []
        self._build_ui()
        self._populate_slots()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 4)
        layout.setSpacing(4)

        header = QLabel("Save Slot")
        header.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 13px;")
        layout.addWidget(header)

        self._combo = QComboBox()
        self._combo.setMaxVisibleItems(16)
        layout.addWidget(self._combo)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)
        self._load_btn = QPushButton("Load")
        self._load_btn.clicked.connect(self._on_load)
        btn_row.addWidget(self._load_btn)

        self._open_btn = QPushButton("Open File...")
        self._open_btn.clicked.connect(self._on_open_file)
        btn_row.addWidget(self._open_btn)
        layout.addLayout(btn_row)

        self._path_label = QLabel("")
        self._path_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 10px;")
        self._path_label.setWordWrap(True)
        layout.addWidget(self._path_label)

        if self._save_dir:
            self._path_label.setText(self._save_dir)
        else:
            self._path_label.setText("Save directory not found — use Open File...")

        self.setMaximumHeight(140)

    def _populate_slots(self):
        self._combo.clear()
        if not self._save_dir:
            return
        self._slots = list_save_slots(self._save_dir)
        for slot_num, path, mtime in self._slots:
            dt = datetime.fromtimestamp(mtime).strftime("%b %d, %H:%M")
            self._combo.addItem(f"Slot {slot_num:04d}  —  {dt}", path)

    def _on_load(self):
        idx = self._combo.currentIndex()
        if idx >= 0:
            path = self._combo.itemData(idx)
            if path and os.path.isfile(path):
                self.file_selected.emit(path)

    def _on_open_file(self):
        start_dir = self._save_dir or ""
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Save File", start_dir, "Save Files (*.bin);;All Files (*)")
        if path:
            self.file_selected.emit(path)
