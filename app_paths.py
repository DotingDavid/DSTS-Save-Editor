"""Path resolution for both dev mode and PyInstaller frozen exe."""

import os
import sys


def get_data_dir():
    """Return the path to the data/ directory."""
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, 'data')


def get_icon_dir():
    """Return the path to the data/icons/ directory."""
    return os.path.join(get_data_dir(), 'icons')


def get_db_path():
    """Return the path to anamnesis.db."""
    return os.path.join(get_data_dir(), 'anamnesis.db')


def get_app_icon_path():
    """Return the path to the app icon."""
    return os.path.join(get_data_dir(), 'app_icon.ico')
