"""Species chooser dialog — searchable list of all 475 Digimon."""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
                              QTableWidget, QTableWidgetItem, QHeaderView,
                              QAbstractItemView, QPushButton, QLabel)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from ui.style import ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, BORDER
from ui.icon_cache import get_icon
from save_data import get_all_digimon_species


class SpeciesChooserDialog(QDialog):
    """Dialog to pick a Digimon species from all 475."""

    def __init__(self, current_species="", parent=None):
        super().__init__(parent)
        self._selected_id = None
        self._selected_name = None
        self._species = get_all_digimon_species()
        self.setWindowTitle("Choose Species")
        self.setMinimumSize(500, 600)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #0C0C14;
                color: #A0A0B0;
            }}
            QLineEdit {{
                background-color: #1A1A2E;
                color: #E0E0E0;
                border: 1px solid {BORDER};
                border-radius: 3px;
                padding: 4px 8px;
            }}
            QTableWidget {{
                background-color: #0C0C14;
                alternate-background-color: #12121E;
                color: #E0E0E0;
                gridline-color: {BORDER};
                border: 1px solid {BORDER};
            }}
            QTableWidget::item:selected {{
                background-color: rgba(0,191,255,0.2);
            }}
            QHeaderView::section {{
                background-color: #1A1A2E;
                color: #A0A0B0;
                border: 1px solid {BORDER};
                padding: 3px;
            }}
            QLabel {{ color: #A0A0B0; }}
            QPushButton {{
                background-color: #1A1A2E;
                color: #E0E0E0;
                border: 1px solid {BORDER};
                border-radius: 4px;
                padding: 6px 16px;
            }}
            QPushButton:hover {{
                border-color: {ACCENT};
                color: {ACCENT};
            }}
        """)
        self._build_ui()
        self._populate()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        header = QLabel("Change Species")
        header.setStyleSheet(
            f"color: {ACCENT}; font-size: 14px; font-weight: bold;")
        layout.addWidget(header)

        warn = QLabel(
            "This will reset growth (white) stats to 0.\n"
            "Blue stats, farm stats, bond, talent, equipment are kept.")
        warn.setStyleSheet(f"color: #FF8A65; font-size: 11px;")
        warn.setWordWrap(True)
        layout.addWidget(warn)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search by name...")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._filter)
        layout.addWidget(self._search)

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
        self._table.doubleClicked.connect(self._on_double_click)
        layout.addWidget(self._table)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._ok_btn = QPushButton("Select")
        self._ok_btn.clicked.connect(self._on_ok)
        self._ok_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #1B5E20;
                color: #81C784;
                border: 1px solid #388E3C;
                border-radius: 4px;
                padding: 6px 20px;
                font-weight: bold;
            }}
        """)
        btn_row.addWidget(self._ok_btn)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def _populate(self):
        self._table.setRowCount(len(self._species))
        for row, (db_id, name, stage, attr, dtype) in enumerate(self._species):
            # Icon
            icon_item = QTableWidgetItem()
            pm = get_icon(name, 24)
            if not pm.isNull():
                icon_item.setIcon(QIcon(pm))
            icon_item.setFlags(icon_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 0, icon_item)

            # Name
            name_item = QTableWidgetItem(name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            name_item.setData(Qt.ItemDataRole.UserRole, db_id)
            self._table.setItem(row, 1, name_item)

            # Stage
            stage_item = QTableWidgetItem(stage)
            stage_item.setFlags(stage_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 2, stage_item)

            # Attribute
            attr_item = QTableWidgetItem(attr)
            attr_item.setFlags(attr_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 3, attr_item)

            # ID
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

    def _on_ok(self):
        rows = self._table.selectionModel().selectedRows()
        if rows:
            name_item = self._table.item(rows[0].row(), 1)
            if name_item:
                self._selected_id = name_item.data(Qt.ItemDataRole.UserRole)
                self._selected_name = name_item.text()
                self.accept()

    def _on_double_click(self, index):
        self._on_ok()

    @property
    def selected_id(self):
        return self._selected_id

    @property
    def selected_name(self):
        return self._selected_name
