"""Icon cache for Digimon portraits.

Loads 256x256 PNGs from data/icons/ and caches scaled QPixmaps.
"""

import logging
import os
from PyQt6.QtGui import QColor, QPixmap, QPixmapCache
from PyQt6.QtCore import QSize, Qt

logger = logging.getLogger(__name__)

from app_paths import get_icon_dir

_ICON_DIR = get_icon_dir()

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
        # Check mod overlay for modded icons first
        from save_data import _mod_overlay
        if _mod_overlay and _mod_overlay.is_active and name_or_id in _mod_overlay.icon_paths:
            cache_key = f"mod_{name_or_id}_{size}"
            pm = QPixmapCache.find(cache_key)
            if pm and not pm.isNull():
                return pm
            pm = QPixmap(_mod_overlay.icon_paths[name_or_id])
            if not pm.isNull():
                pm = pm.scaled(QSize(size, size),
                               transformMode=Qt.TransformationMode.SmoothTransformation)
                QPixmapCache.insert(cache_key, pm)
                return pm
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
        logger.debug("Icon not found for '%s' (slug: %s)", name, slug)
        pm = QPixmap(size, size)
        pm.fill(QColor(0, 0, 0, 0))
    else:
        pm = pm.scaled(QSize(size, size),
                       transformMode=Qt.TransformationMode.SmoothTransformation)

    QPixmapCache.insert(cache_key, pm)
    return pm
