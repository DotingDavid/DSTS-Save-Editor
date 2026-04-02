"""Save File Manager — card-based visual interface.

Shows save slots as graphical cards with player name, money, date previews,
signature status, party icons, and per-slot backup management.
"""

import os
import shutil
from datetime import datetime, date, timedelta

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QScrollArea, QGridLayout,
                              QMessageBox, QComboBox, QDialog, QFileDialog,
                              QFrame, QMenu, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QPixmap, QPainter

from ui.style import (ACCENT, ACCENT_DIM, TEXT_PRIMARY, TEXT_SECONDARY,
                       TEXT_VALUE, BORDER, BORDER_BRIGHT, BG_INPUT, BG_PANEL,
                       BG_HOVER, BG_HEADER, STAT_FARM, STAT_BLUE,
                       DIRTY_COLOR, CLEAN_COLOR)
from save_data import (find_save_directory, list_save_slots, peek_save_info,
                        get_digimon_name)
from ui.icon_cache import get_icon
from save_crypto import SAVE_FILE_SIZE

CARD_COLS = 3
PARTY_ICON_SIZE = 28


# ── Helpers ──────────────────────────────────────────────────────────

def _fmt_size(b):
    if b >= 1024 * 1024:
        return f"{b / 1024 / 1024:.1f} MB"
    return f"{b / 1024:.0f} KB"


def _fmt_money(val):
    return f"\u00a5 {val:,}"


def _friendly_date(ts):
    """Returns (headline, detail) for two-line date display.

    headline: 'Today', 'Yesterday', 'Monday', 'March 24, 2026', etc.
    detail:   'Mar 31, 2026 · 2:32 PM'
    """
    dt = datetime.fromtimestamp(ts)
    today = date.today()
    diff = (today - dt.date()).days
    time_str = dt.strftime('%I:%M %p').lstrip('0')
    date_full = dt.strftime('%b %d, %Y')
    if diff == 0:
        headline = "Today"
    elif diff == 1:
        headline = "Yesterday"
    elif diff < 7:
        headline = dt.strftime('%A')
    else:
        headline = dt.strftime('%B %d, %Y')
    detail = f"{date_full}  \u00b7  {time_str}"
    return headline, detail


def _friendly_date_single(ts):
    """Single-line friendly date for dialogs/backup lists."""
    dt = datetime.fromtimestamp(ts)
    today = date.today()
    diff = (today - dt.date()).days
    time_str = dt.strftime('%I:%M %p').lstrip('0')
    date_full = dt.strftime('%b %d, %Y')
    if diff == 0:
        return f"Today {time_str}"
    elif diff == 1:
        return f"Yesterday {time_str}"
    elif diff < 7:
        return f"{dt.strftime('%A')} {time_str}  \u00b7  {date_full}"
    return f"{date_full}  \u00b7  {time_str}"


# ── Backup Dialog ────────────────────────────────────────────────────

class BackupDialog(QDialog):
    """Modal dialog showing backups for a single save slot."""

    action_taken = pyqtSignal()  # emitted when a restore or delete happens

    def __init__(self, slot_num, backups, save_dir, parent=None):
        super().__init__(parent)
        self._slot_num = slot_num
        self._backups = backups
        self._save_dir = save_dir
        self._changed = False
        self.setWindowTitle(f"Backups \u2014 Slot {slot_num:04d}")
        self.setMinimumWidth(420)
        self.setStyleSheet(f"""
            QDialog {{ background: #0C0C14; color: {TEXT_PRIMARY}; }}
            QLabel {{ color: {TEXT_PRIMARY}; }}
        """)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        header = QLabel(
            f"{len(self._backups)} backup"
            f"{'s' if len(self._backups) != 1 else ''} "
            f"for slot {self._slot_num:04d}")
        header.setStyleSheet(
            f"color: {ACCENT}; font-size: 13px; font-weight: bold;")
        layout.addWidget(header)

        for i, (bname, bpath, bmtime, bsize) in enumerate(self._backups):
            row = QFrame()
            bg = '#151525' if i % 2 == 0 else 'transparent'
            row.setStyleSheet(
                f"QFrame {{ background: {bg}; border: none; "
                "border-radius: 4px; }}")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(10, 6, 10, 6)
            rl.setSpacing(12)

            date_lbl = QLabel(_friendly_date_single(bmtime))
            date_lbl.setStyleSheet(
                f"color: {TEXT_VALUE}; font-size: 11px; "
                "background: transparent;")
            rl.addWidget(date_lbl)

            size_lbl = QLabel(_fmt_size(bsize))
            size_lbl.setStyleSheet(
                f"color: {TEXT_SECONDARY}; font-size: 11px; "
                "background: transparent;")
            rl.addWidget(size_lbl)

            rl.addStretch()

            restore_btn = QPushButton("Restore")
            restore_btn.setFixedHeight(24)
            restore_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            restore_btn.setStyleSheet(f"""
                QPushButton {{
                    background: rgba(129,199,132,0.1); color: #81C784;
                    border: 1px solid rgba(129,199,132,0.3);
                    border-radius: 3px; font-size: 10px;
                    padding: 0 12px;
                }}
                QPushButton:hover {{
                    background: rgba(129,199,132,0.2);
                    border-color: #81C784;
                }}
            """)
            restore_btn.clicked.connect(
                lambda _, p=bpath, n=bname: self._restore(p, n))
            rl.addWidget(restore_btn)

            del_btn = QPushButton("Delete")
            del_btn.setFixedHeight(24)
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {TEXT_SECONDARY};
                    border: 1px solid {BORDER}; border-radius: 3px;
                    font-size: 10px; padding: 0 10px;
                }}
                QPushButton:hover {{
                    background: #3E2723; color: #EF5350;
                    border-color: #EF5350;
                }}
            """)
            del_btn.clicked.connect(
                lambda _, p=bpath, n=bname: self._delete(p, n))
            rl.addWidget(del_btn)

            layout.addWidget(row)

        layout.addStretch()

        # Close button
        close_row = QHBoxLayout()
        close_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setFixedHeight(28)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: {BG_INPUT}; color: {TEXT_PRIMARY};
                border: 1px solid {BORDER}; border-radius: 4px;
                padding: 0 20px; font-size: 11px;
            }}
            QPushButton:hover {{ border-color: {ACCENT}; color: {ACCENT}; }}
        """)
        close_btn.clicked.connect(self.accept)
        close_row.addWidget(close_btn)
        layout.addLayout(close_row)

    def _restore(self, path, name):
        original = name.split('.')[0] + '.bin'
        reply = QMessageBox.question(
            self, "Restore", f"Restore backup to {original}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                shutil.copy2(
                    path, os.path.join(self._save_dir, original))
                from ui.toast import show_toast
                show_toast(
                    self.window(), f"Restored {original}", "success")
                self._changed = True
                self.accept()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _delete(self, path, name):
        reply = QMessageBox.question(
            self, "Delete", f"Delete this backup?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                os.remove(path)
                self._changed = True
                self.accept()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Delete failed: {e}")


# ── Save Slot Card ───────────────────────────────────────────────────

class SaveSlotCard(QFrame):
    """Visual card for a single save slot with party icons and backup access."""

    load_requested = pyqtSignal(str)  # path

    def __init__(self, slot_num, path, mtime, size, backups,
                 preview, on_action=None, parent=None):
        super().__init__(parent)
        self._slot_num = slot_num
        self._path = path
        self._mtime = mtime
        self._size = size
        self._backups = backups       # list of (name, path, mtime, size)
        self._preview = preview or {}
        self._on_action = on_action
        self._is_loaded = False

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self._apply_style()
        self._build()

    def _apply_style(self):
        if self._is_loaded:
            self.setStyleSheet(f"""
                SaveSlotCard {{
                    background: rgba(0, 191, 255, 0.06);
                    border: 2px solid {ACCENT};
                    border-radius: 8px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                SaveSlotCard {{
                    background: #1A1A2E;
                    border: 1px solid rgba(255,255,255,0.06);
                    border-radius: 8px;
                }}
                SaveSlotCard:hover {{
                    border-color: rgba(0, 191, 255, 0.4);
                    background: #1E1E37;
                }}
            """)

    def set_loaded(self, loaded):
        self._is_loaded = loaded
        self._apply_style()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 10)
        layout.setSpacing(6)

        # ── Row 1: Slot badge + Name + Menu ──
        top = QHBoxLayout()
        top.setSpacing(10)

        is_auto = (self._slot_num == 0)
        badge_rgb = "255, 140, 0" if is_auto else "0, 191, 255"
        badge = QLabel(f"{self._slot_num:02d}")
        badge.setFixedSize(36, 28)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(f"""
            background: rgba({badge_rgb}, 0.15);
            color: rgb({badge_rgb});
            font-size: 13px; font-weight: bold;
            border-radius: 6px;
            border: 1px solid rgba({badge_rgb}, 0.3);
        """)
        top.addWidget(badge)

        if is_auto:
            auto_lbl = QLabel("AUTO")
            auto_lbl.setStyleSheet(
                "color: rgba(255,140,0,0.6); font-size: 8px; "
                "font-weight: bold; letter-spacing: 1px; "
                "background: transparent;")
            top.addWidget(auto_lbl)

        name = self._preview.get('name', '')
        if name:
            name_lbl = QLabel(name)
            name_lbl.setStyleSheet(
                f"color: {TEXT_VALUE}; font-size: 14px; font-weight: bold; "
                "background: transparent;")
            top.addWidget(name_lbl)

        top.addStretch()

        menu_btn = QPushButton("Menu")
        menu_btn.setFixedHeight(22)
        menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        menu_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255,255,255,0.05); color: {TEXT_SECONDARY};
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 3px; font-size: 9px;
                padding: 0 8px;
            }}
            QPushButton:hover {{
                background: rgba(255,255,255,0.1); color: {TEXT_PRIMARY};
                border-color: rgba(255,255,255,0.25);
            }}
        """)
        menu_btn.clicked.connect(lambda: self._show_menu(menu_btn))
        top.addWidget(menu_btn)

        layout.addLayout(top)

        # ── Row 2: Day headline ──
        headline, detail = _friendly_date(self._mtime)
        day_lbl = QLabel(headline)
        day_lbl.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 12px; font-weight: bold; "
            "background: transparent;")
        layout.addWidget(day_lbl)

        # ── Row 3: Date · Time ──
        meta = QLabel(detail)
        meta.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 10px; "
            "background: transparent;")
        layout.addWidget(meta)

        # ── Row 3: Money + Backup indicator ──
        row3 = QHBoxLayout()
        row3.setSpacing(0)

        money = self._preview.get('money', 0)
        if money > 0:
            m_lbl = QLabel(_fmt_money(money))
            m_lbl.setStyleSheet(
                f"color: {TEXT_SECONDARY}; font-size: 10px; "
                "background: transparent;")
            row3.addWidget(m_lbl)

        row3.addStretch()

        if self._backups:
            count = len(self._backups)
            s = "s" if count != 1 else ""
            bak_btn = QPushButton(f"\u25cf {count} backup{s}")
            bak_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            bak_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {STAT_FARM};
                    border: none; font-size: 10px; font-weight: bold;
                    padding: 0;
                }}
                QPushButton:hover {{ color: #A5D6A7; }}
            """)
            bak_btn.clicked.connect(self._open_backup_dialog)
            row3.addWidget(bak_btn)

        layout.addLayout(row3)

        # ── Row 4: Party icons ──
        party = self._preview.get('party', [])
        if party:
            party_row = QHBoxLayout()
            party_row.setSpacing(3)
            for slot in party:
                icon_lbl = QLabel()
                icon_lbl.setFixedSize(PARTY_ICON_SIZE, PARTY_ICON_SIZE)
                icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                if slot['db_id'] > 0:
                    species = get_digimon_name(slot['db_id'])
                    pm = get_icon(species, PARTY_ICON_SIZE)
                    icon_lbl.setPixmap(pm)
                    tip = slot['nickname'] or species
                    if slot['nickname'] and slot['nickname'] != species:
                        tip = f"{slot['nickname']} ({species})"
                    icon_lbl.setToolTip(tip)
                    icon_lbl.setStyleSheet(
                        "border: 1px solid rgba(0,191,255,0.3); "
                        "border-radius: 4px; "
                        "background: rgba(12,12,20,200);")
                else:
                    icon_lbl.setStyleSheet(
                        "border: 1px solid rgba(255,255,255,0.04); "
                        "border-radius: 4px; "
                        "background: rgba(12,12,20,80);")
                party_row.addWidget(icon_lbl)
            party_row.addStretch()
            layout.addLayout(party_row)

        # ── Row 5: Save ID ──
        uid = self._preview.get('uid')
        if uid:
            uid_lbl = QLabel(f"Save ID: {uid}")
            uid_lbl.setStyleSheet(
                "color: rgba(136,136,170,0.5); font-size: 8px; "
                "background: transparent;")
            uid_lbl.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse)
            layout.addWidget(uid_lbl)

        # ── Row 6: Load button ──
        layout.addSpacing(2)
        load_btn = QPushButton("Load in Editor")
        load_btn.setFixedHeight(28)
        load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        load_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(0, 191, 255, 0.1);
                color: {ACCENT};
                border: 1px solid rgba(0, 191, 255, 0.3);
                border-radius: 4px;
                font-size: 11px; font-weight: bold;
            }}
            QPushButton:hover {{
                background: rgba(0, 191, 255, 0.2);
                border-color: {ACCENT};
            }}
        """)
        load_btn.clicked.connect(lambda: self.load_requested.emit(self._path))
        layout.addWidget(load_btn)

    def _open_backup_dialog(self):
        self._fire("open_backups")

    def _show_menu(self, btn):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background: #1A1A2E; color: {TEXT_PRIMARY};
                border: 1px solid {BORDER}; padding: 4px;
                border-radius: 4px;
            }}
            QMenu::item {{
                padding: 6px 20px 6px 12px;
                border-radius: 3px;
            }}
            QMenu::item:selected {{
                background: {BG_HOVER}; color: {ACCENT};
            }}
            QMenu::separator {{
                height: 1px; background: {BORDER};
                margin: 3px 8px;
            }}
        """)

        menu.addAction("Create Backup", lambda: self._fire("backup"))
        menu.addSeparator()
        menu.addAction("Copy To...", lambda: self._fire("copy"))
        menu.addAction("Swap With...", lambda: self._fire("swap"))
        menu.addSeparator()
        menu.addAction("Export...", lambda: self._fire("export"))
        menu.addSeparator()

        menu.addAction(
            "Create Signature", lambda: self._fire("sign"))
        if self._preview.get('uid'):
            menu.addAction(
                "Remove Signature", lambda: self._fire("unsign"))

        menu.exec(btn.mapToGlobal(btn.rect().bottomLeft()))

    def _fire(self, action, *extra):
        if self._on_action:
            self._on_action(action, self._path, self._slot_num, *extra)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.load_requested.emit(self._path)
        super().mouseDoubleClickEvent(event)


# ── File Manager Panel ───────────────────────────────────────────────

class FileManagerPanel(QWidget):
    """Card-based save file manager panel."""

    file_load_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._save_dir = find_save_directory()
        self._cards = []
        self._loaded_path = None
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
            "background: transparent;")
        layout.addWidget(header)

        if self._save_dir:
            path_lbl = QLabel(self._save_dir)
            path_lbl.setStyleSheet(
                f"color: {TEXT_SECONDARY}; font-size: 10px; "
                "background: transparent;")
            path_lbl.setWordWrap(True)
            layout.addWidget(path_lbl)

        # ── Card grid scroll area ──
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }")
        layout.addWidget(self._scroll, 1)

        # Initial empty container
        self._grid_container = QWidget()
        self._grid_container.setStyleSheet("background: transparent;")
        QVBoxLayout(self._grid_container)
        self._scroll.setWidget(self._grid_container)

        # ── Toolbar ──
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        import_btn = QPushButton("Import Save...")
        import_btn.setFixedHeight(28)
        import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        import_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(129, 199, 132, 0.1);
                color: #81C784;
                border: 1px solid rgba(129, 199, 132, 0.3);
                border-radius: 4px;
                padding: 0 14px; font-size: 11px; font-weight: bold;
            }}
            QPushButton:hover {{
                background: rgba(129, 199, 132, 0.2);
                border-color: #81C784;
            }}
        """)
        import_btn.clicked.connect(self._import_save)
        toolbar.addWidget(import_btn)

        toolbar.addStretch()

        unsign_all_btn = QPushButton("Unsign All Saves")
        unsign_all_btn.setFixedHeight(28)
        unsign_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        unsign_all_btn.setToolTip(
            "Remove ANAMNESIS signatures from ALL saves and reset consent")
        unsign_all_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {TEXT_SECONDARY};
                border: 1px solid {BORDER}; border-radius: 4px;
                padding: 0 10px; font-size: 10px;
            }}
            QPushButton:hover {{
                background: #3E2723; color: #EF5350;
                border-color: #EF5350;
            }}
        """)
        unsign_all_btn.clicked.connect(self._unsign_all)
        toolbar.addWidget(unsign_all_btn)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setFixedHeight(28)
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {TEXT_SECONDARY};
                border: 1px solid {BORDER}; border-radius: 4px;
                padding: 0 12px; font-size: 11px;
            }}
            QPushButton:hover {{
                color: {TEXT_PRIMARY};
                border-color: rgba(255,255,255,0.2);
            }}
        """)
        refresh_btn.clicked.connect(self._refresh)
        toolbar.addWidget(refresh_btn)

        layout.addLayout(toolbar)

    # ── Data loading ─────────────────────────────────────────────────

    def _refresh(self):
        self._build_cards()

    def set_loaded_path(self, path):
        """Highlight the card for the currently loaded save."""
        self._loaded_path = path
        for card in self._cards:
            card.set_loaded(card._path == path)

    def _build_cards(self):
        """Rebuild the save slot card grid."""
        self._cards.clear()

        old = self._scroll.widget()
        if old:
            old.deleteLater()

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 8, 0)
        main_layout.setSpacing(0)

        if not self._save_dir:
            empty = QLabel(
                "No save directory found.\n"
                "Use the nav panel to browse for saves.")
            empty.setStyleSheet(
                f"color: {TEXT_SECONDARY}; font-size: 12px; "
                "background: transparent; padding: 40px;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            main_layout.addWidget(empty)
            main_layout.addStretch()
            self._scroll.setWidget(container)
            return

        slots = list_save_slots(self._save_dir)
        backup_dir = os.path.join(self._save_dir, 'backups')

        # Gather per-slot backup files
        all_backups = {}
        if os.path.isdir(backup_dir):
            for f in os.listdir(backup_dir):
                if f.endswith('.bak'):
                    p = os.path.join(backup_dir, f)
                    base = f.split('.')[0] + '.bin'
                    all_backups.setdefault(base, []).append(
                        (f, p, os.path.getmtime(p), os.path.getsize(p)))
            for base in all_backups:
                all_backups[base].sort(key=lambda x: x[2], reverse=True)

        slot_data = []
        for num, path, mtime in slots:
            size = os.path.getsize(path)
            basename = os.path.basename(path)
            backups = all_backups.get(basename, [])
            preview = peek_save_info(path)
            slot_data.append((num, path, mtime, size, backups, preview))

        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setContentsMargins(0, 0, 0, 0)
        for c in range(CARD_COLS):
            grid.setColumnStretch(c, 1)

        for i, (num, path, mtime, size, backups, preview) in enumerate(slot_data):
            card = SaveSlotCard(
                num, path, mtime, size, backups, preview,
                on_action=self._handle_card_action)
            card.load_requested.connect(self.file_load_requested.emit)
            if self._loaded_path and path == self._loaded_path:
                card.set_loaded(True)
            grid.addWidget(card, i // CARD_COLS, i % CARD_COLS)
            self._cards.append(card)

        wrapper = QWidget()
        wrapper.setLayout(grid)
        wrapper.setStyleSheet("background: transparent;")
        main_layout.addWidget(wrapper)
        main_layout.addStretch()

        self._scroll.setWidget(container)

    # ── Card actions ─────────────────────────────────────────────────

    def _handle_card_action(self, action, path, slot_num, *extra):
        if action == "backup":
            self._backup_slot(path, slot_num)
        elif action == "copy":
            self._copy_slot(path, slot_num)
        elif action == "swap":
            self._swap_slot(path, slot_num)
        elif action == "export":
            self._export_save(path, slot_num)
        elif action == "unsign":
            self._unsign_single(path, slot_num)
        elif action == "sign":
            self._sign_single(path, slot_num)
        elif action == "open_backups":
            self._open_backup_dialog(path, slot_num)

    def _make_backup(self, path):
        backup_dir = os.path.join(self._save_dir, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        dest = os.path.join(
            backup_dir, f"{os.path.basename(path)}.{ts}.bak")
        shutil.copy2(path, dest)
        return dest

    def _backup_slot(self, path, slot_num):
        try:
            self._make_backup(path)
            from ui.toast import show_toast
            show_toast(
                self.window(), f"Backed up slot {slot_num:04d}", "success")
            self._refresh()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _copy_slot(self, src_path, src_num):
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Copy Slot {src_num:04d}")
        dlg.setMinimumWidth(280)
        dl = QVBoxLayout(dlg)
        dl.addWidget(QLabel(f"Copy slot {src_num:04d} to:"))
        combo = QComboBox()
        for i in range(20):
            p = os.path.join(self._save_dir, f"{i:04d}.bin")
            exists = " (exists)" if os.path.exists(p) else " (empty)"
            combo.addItem(f"Slot {i:04d}{exists}", i)
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
                shutil.copy2(src_path, tgt)
                from ui.toast import show_toast
                show_toast(
                    self.window(),
                    f"Copied {src_num:04d} \u2192 {tgt_num:04d}", "success")
                self._refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _swap_slot(self, src_path, src_num):
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Swap Slot {src_num:04d}")
        dlg.setMinimumWidth(280)
        dl = QVBoxLayout(dlg)
        dl.addWidget(QLabel(f"Swap slot {src_num:04d} with:"))
        combo = QComboBox()
        for num, path, mtime in list_save_slots(self._save_dir):
            if num != src_num:
                combo.addItem(
                    f"Slot {num:04d}  \u2014  {_friendly_date_single(mtime)}", num)
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
                tmp = src_path + ".swap"
                shutil.copy2(src_path, tmp)
                shutil.copy2(tgt, src_path)
                shutil.move(tmp, tgt)
                from ui.toast import show_toast
                show_toast(
                    self.window(),
                    f"Swapped {src_num:04d} \u2194 {tgt_num:04d}", "success")
                self._refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _export_save(self, src_path, slot_num):
        dest, _ = QFileDialog.getSaveFileName(
            self, "Export Save", f"DSTS_Slot{slot_num:04d}.bin",
            "Save Files (*.bin);;All Files (*)")
        if dest:
            try:
                shutil.copy2(src_path, dest)
                from ui.toast import show_toast
                show_toast(
                    self.window(), f"Exported slot {slot_num:04d}", "success")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _import_save(self):
        src, _ = QFileDialog.getOpenFileName(
            self, "Import Save File", "",
            "Save Files (*.bin);;All Files (*)")
        if not src:
            return
        if os.path.getsize(src) != SAVE_FILE_SIZE:
            QMessageBox.critical(
                self, "Invalid File",
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
            exists = " (exists)" if os.path.exists(p) else " (empty)"
            combo.addItem(f"Slot {i:04d}{exists}", i)
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
                show_toast(
                    self.window(),
                    f"Imported to slot {tgt_num:04d}", "success")
                self._refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    # ── Backup dialog ────────────────────────────────────────────────

    def _open_backup_dialog(self, path, slot_num):
        basename = os.path.basename(path)
        backup_dir = os.path.join(self._save_dir, 'backups')
        backups = []
        if os.path.isdir(backup_dir):
            for f in os.listdir(backup_dir):
                if f.startswith(basename) and f.endswith('.bak'):
                    p = os.path.join(backup_dir, f)
                    backups.append(
                        (f, p, os.path.getmtime(p), os.path.getsize(p)))
            backups.sort(key=lambda x: x[2], reverse=True)

        if not backups:
            QMessageBox.information(
                self, "No Backups",
                f"No backups found for slot {slot_num:04d}.")
            return

        dlg = BackupDialog(slot_num, backups, self._save_dir, self)
        dlg.exec()
        if dlg._changed:
            self._refresh()

    # ── Signature actions ────────────────────────────────────────────

    def _sign_single(self, path, slot_num):
        slot_str = f"{slot_num:04d}"
        if slot_str == '0000':
            QMessageBox.information(
                self, "Autosave",
                "The autosave (0000) cannot be signed directly.")
            return
        reply = QMessageBox.question(
            self, "Create Signature",
            f"Create an ANAMNESIS signature for slot {slot_str}?\n\n"
            "A pre-signature backup will be saved automatically.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            from save_data import stamp_save_uid, unsign_save
            unsign_save(path)  # clear existing so stamp_save_uid writes fresh
            uid = stamp_save_uid(path)
            if uid:
                from ui.toast import show_toast
                show_toast(
                    self.window(),
                    f"Signed slot {slot_str}: {uid[:8]}...", "success")
            else:
                QMessageBox.information(
                    self, "Could Not Sign",
                    f"Could not determine Steam ID for slot {slot_str}.")
            self._refresh()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _unsign_single(self, path, slot_num):
        slot_str = f"{slot_num:04d}"
        if slot_str == '0000':
            QMessageBox.information(
                self, "Autosave",
                "The autosave (0000) cannot be unsigned directly.")
            return
        reply = QMessageBox.question(
            self, "Remove Signature",
            f"Remove ANAMNESIS signature from slot {slot_str}?\n"
            "Your edits are NOT affected.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            from save_data import unsign_save
            if unsign_save(path):
                from ui.toast import show_toast
                show_toast(
                    self.window(), f"Unsigned slot {slot_str}", "success")
            else:
                QMessageBox.information(
                    self, "Not Signed",
                    f"Slot {slot_str} has no ANAMNESIS signature.")
            self._refresh()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _unsign_all(self):
        if not self._save_dir:
            return
        reply = QMessageBox.question(
            self, "Unsign All",
            "Remove ANAMNESIS signatures from ALL saves?\n"
            "Consent will be reset.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            from save_data import unsign_save, list_save_slots, _consent_path
            count = 0
            for _, path, _ in list_save_slots(self._save_dir):
                if unsign_save(path):
                    count += 1
            consent_path = _consent_path(self._save_dir)
            if os.path.exists(consent_path):
                os.remove(consent_path)
            from ui.toast import show_toast
            show_toast(
                self.window(),
                f"Unsigned {count} saves. Consent reset.", "success")
            self._refresh()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
