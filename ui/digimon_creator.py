"""Digimon Creator dialog — create a new Digimon from scratch."""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
                              QTableWidget, QTableWidgetItem, QHeaderView,
                              QAbstractItemView, QPushButton, QLabel,
                              QSpinBox, QComboBox, QFormLayout)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from ui.style import ACCENT, TEXT_SECONDARY, BORDER
from ui.icon_cache import get_icon
from save_data import get_all_digimon_species
from save_layout import PERSONALITY_NAMES


class DigimonCreatorDialog(QDialog):
    """Dialog to create a new Digimon — pick species, level, personality."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_id = None
        self._level = 1
        self._personality_id = 1
        self._species = get_all_digimon_species()
        self.setWindowTitle("Create New Digimon")
        self.setMinimumSize(520, 650)
        self._build_ui()
        self._populate()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        header = QLabel("Create New Digimon")
        header.setStyleSheet(
            f"color: {ACCENT}; font-size: 14px; font-weight: bold;")
        layout.addWidget(header)

        desc = QLabel("Select a species, set level and personality. "
                       "The Digimon will be added to your Box with base stats.")
        desc.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Search
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search by name...")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._filter)
        layout.addWidget(self._search)

        # Species table
        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(
            ["", "Name", "Stage", "Attribute", "ID"])
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch)
        self._table.setColumnWidth(0, 32)
        self._table.setColumnWidth(2, 100)
        self._table.setColumnWidth(3, 80)
        self._table.setColumnWidth(4, 45)
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        self._table.verticalHeader().setDefaultSectionSize(28)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        self._table.doubleClicked.connect(self._on_create)
        layout.addWidget(self._table)

        # Options row
        opts = QFormLayout()
        opts.setSpacing(6)

        self._level_spin = QSpinBox()
        self._level_spin.setRange(1, 99)
        self._level_spin.setValue(1)
        opts.addRow("Level:", self._level_spin)

        self._pers_combo = QComboBox()
        for pid, pname in sorted(PERSONALITY_NAMES.items()):
            self._pers_combo.addItem(pname, pid)
        opts.addRow("Personality:", self._pers_combo)

        layout.addLayout(opts)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._create_btn = QPushButton("Create")
        self._create_btn.clicked.connect(self._on_create)
        self._create_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #1B5E20;
                color: #81C784;
                border: 1px solid #388E3C;
                border-radius: 4px;
                padding: 6px 20px;
                font-weight: bold;
            }}
        """)
        btn_row.addWidget(self._create_btn)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def _populate(self):
        self._table.setRowCount(len(self._species))
        for row, (db_id, name, stage, attr, dtype) in enumerate(self._species):
            icon_item = QTableWidgetItem()
            pm = get_icon(name, 24)
            if not pm.isNull():
                icon_item.setIcon(QIcon(pm))
            icon_item.setFlags(icon_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 0, icon_item)

            name_item = QTableWidgetItem(name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            name_item.setData(Qt.ItemDataRole.UserRole, db_id)
            self._table.setItem(row, 1, name_item)

            stage_item = QTableWidgetItem(stage)
            stage_item.setFlags(stage_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 2, stage_item)

            attr_item = QTableWidgetItem(attr)
            attr_item.setFlags(attr_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 3, attr_item)

            id_item = QTableWidgetItem(str(db_id))
            id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 4, id_item)

    def _filter(self, text):
        text = text.lower().strip()
        for row in range(self._table.rowCount()):
            name_item = self._table.item(row, 1)
            visible = not text or (name_item and text in name_item.text().lower())
            self._table.setRowHidden(row, not visible)

    def _on_create(self):
        rows = self._table.selectionModel().selectedRows()
        if rows:
            name_item = self._table.item(rows[0].row(), 1)
            if name_item:
                self._selected_id = name_item.data(Qt.ItemDataRole.UserRole)
                self._level = self._level_spin.value()
                idx = self._pers_combo.currentIndex()
                self._personality_id = self._pers_combo.itemData(idx)
                self.accept()

    @property
    def selected_id(self):
        return self._selected_id

    @property
    def level(self):
        return self._level

    @property
    def personality_id(self):
        return self._personality_id
