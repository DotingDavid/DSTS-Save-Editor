"""Icon cache for Digimon portraits.

Loads 256x256 PNGs from data/icons/ and caches scaled QPixmaps.
"""

import os
from PyQt6.QtGui import QPixmap, QPixmapCache
from PyQt6.QtCore import QSize, Qt

_ICON_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'icons')

# Increase cache limit for 475 icons at multiple sizes
QPixmapCache.setCacheLimit(200 * 1024)  # 200MB


def name_to_slug(name):
    """Convert a Digimon name to its icon filename slug."""
    slug = name.lower()
    slug = slug.replace('+', '-plus-')
    slug = slug.replace(' ', '-')
    slug = slug.replace(':', '-')
    slug = slug.replace('(', '-')
    slug = slug.replace(')', '')
    while '--' in slug:
        slug = slug.replace('--', '-')
    slug = slug.strip('-')
    return slug


def get_icon(name_or_id, size=64):
    """Get a QPixmap for a Digimon, scaled to size x size.

    Args:
        name_or_id: Species name (str) or database ID (int)
        size: Pixel size (square)
    Returns:
        QPixmap (may be null if icon not found)
    """
    if isinstance(name_or_id, int):
        from save_data import get_digimon_name
        name = get_digimon_name(name_or_id)
    else:
        name = name_or_id

    slug = name_to_slug(name)
    cache_key = f"digi_{slug}_{size}"

    pm = QPixmapCache.find(cache_key)
    if pm and not pm.isNull():
        return pm

    path = os.path.join(_ICON_DIR, f"{slug}.png")
    pm = QPixmap(path)
    if pm.isNull():
        # Fallback: empty pixmap
        pm = QPixmap(size, size)
        pm.fill()
    else:
        pm = pm.scaled(QSize(size, size),
                       transformMode=Qt.TransformationMode.SmoothTransformation)

    QPixmapCache.insert(cache_key, pm)
    return pm
