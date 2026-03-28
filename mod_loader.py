"""Detect and load Reloaded-II mod data for DSTS.

Adapted from ANAMNESIS Companion's mod_loader.py for the save editor.
Scans the user's Reloaded-II installation for enabled content mods,
parses their CSV/MBE files, and produces overlay dicts that can be
merged into save_data.py's runtime lookups.

Never modifies anamnesis.db on disk — all changes are in-memory overlays.
"""

import csv
import json
import logging
import os
import re

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────

RELEVANT_SHEETS = {
    "evolution_condition", "evolution_to", "chronodevolution",
    "digimon_status_data",
    "battle_skill_list", "skill_mode_change",
    "Sheet1",
}

STAGE_MAP = {
    0: "???", 1: "In-Training I", 2: "In-Training II", 3: "Rookie",
    4: "Champion", 5: "Ultimate", 6: "Mega", 7: "Mega+", 8: "Armor",
    9: "Golden Armor", 10: "Human Hybrid", 11: "Beast Hybrid",
    12: "Fusion Hybrid", 13: "Transcendent Hybrid",
}

ATTR_MAP = {
    0: "Vaccine", 1: "Data", 2: "Virus", 3: "Free",
    4: "Variable", 5: "Unknown",
}

RES_VAL_MAP = {0: 1.0, 1: 1.5, 2: 2.0, 3: 0.5, 4: 0.0}
RES_COL_ELEMENTS = [
    (7, "Null"), (8, "Fire"), (9, "Water"), (10, "Ice"), (11, "Plant"),
    (12, "Wind"), (13, "Electricity"), (14, "Earth"), (15, "Steel"),
    (16, "Light"), (17, "Dark"),
]


# ── Data classes ─────────────────────────────────────────────────────────

class ModInfo:
    """Metadata about a single content mod."""
    __slots__ = ('mod_id', 'name', 'version', 'path', 'csv_files')

    def __init__(self, mod_id, name, version, path, csv_files):
        self.mod_id = mod_id
        self.name = name
        self.version = version
        self.path = path
        self.csv_files = csv_files

    def __repr__(self):
        return f"ModInfo({self.mod_id!r}, csvs={len(self.csv_files)})"


class ModOverlay:
    """Merged mod data ready to be applied to runtime lookups."""

    def __init__(self):
        self.evo_additions = []
        self.evo_replacements = {}
        self.devo_additions = []
        self.devo_replacements = {}
        self.cond_overrides = {}

        self.new_digimon = {}
        self.new_stats = {}
        self.new_resistances = {}

        self.icon_paths = {}

        self.name_overrides = {}

        self.personalities = {}
        self.special_skills = {}
        self.profiles = {}
        self.digimon_types = {}
        self.skill_names = {}

        self.mod_names = []
        self.mod_count = 0
        self.is_active = False


# ── Reloaded-II Discovery ────────────────────────────────────────────────

def find_reloaded_ii():
    """Find the Reloaded-II installation directory."""
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, "Reloaded-II"),
        os.path.join(home, "Desktop", "Reloaded-II"),
        r"C:\Reloaded-II",
    ]

    # Check near the game install (derive from save directory path)
    try:
        from save_data import find_save_directory
        save_dir = find_save_directory()
        if save_dir:
            # Walk up from .../gamedata/savedata/{steam_id} to game root
            game_root = save_dir
            for _ in range(3):
                game_root = os.path.dirname(game_root)
            if os.path.isdir(game_root):
                candidates.insert(0, os.path.join(
                    os.path.dirname(game_root), "Reloaded-II"))
    except Exception:
        pass

    for path in candidates:
        app_config = os.path.join(path, "Apps", "Digimon Story Time Stranger",
                                  "AppConfig.json")
        if os.path.isfile(app_config):
            return path

    return None


def read_app_config(reloaded_path):
    """Read EnabledMods and SortedMods from AppConfig.json."""
    config_path = os.path.join(reloaded_path, "Apps",
                               "Digimon Story Time Stranger", "AppConfig.json")
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        enabled = set(config.get("EnabledMods", []))
        sorted_mods = list(config.get("SortedMods", []))
        return enabled, sorted_mods
    except Exception as e:
        logger.warning("Failed to read AppConfig: %s", e)
        return set(), []


def get_content_mods(reloaded_path, enabled, sorted_mods):
    """Enumerate enabled content mods that have dsts-loader data."""
    mods_dir = os.path.join(reloaded_path, "Mods")
    result = []

    for mod_id in sorted_mods:
        if mod_id not in enabled:
            continue
        mod_path = os.path.join(mods_dir, mod_id)
        loader_dir = os.path.join(mod_path, "dsts-loader")
        if not os.path.isdir(loader_dir):
            continue

        name = mod_id
        version = "?"
        config_path = os.path.join(mod_path, "ModConfig.json")
        if os.path.isfile(config_path):
            try:
                with open(config_path, 'r') as f:
                    mc = json.load(f)
                name = mc.get("ModName", mod_id)
                version = mc.get("ModVersion", "?")
            except Exception:
                pass

        csv_files = _discover_mod_csvs(loader_dir)
        if csv_files:
            result.append(ModInfo(mod_id, name, version, loader_dir, csv_files))

    return result


# ── CSV Discovery & Parsing ──────────────────────────────────────────────

def _discover_mod_csvs(loader_dir):
    """Walk dsts-loader/ and find relevant CSVs."""
    results = []
    for root, dirs, files in os.walk(loader_dir):
        for fname in files:
            if not fname.lower().endswith('.csv'):
                continue

            full_path = os.path.join(root, fname)
            rel_path = os.path.relpath(full_path, loader_dir)

            is_append = fname.lower().endswith('.ap.csv')

            base = fname
            if is_append:
                base = base[:-7]
            else:
                base = base[:-4]
            sheet_name = re.sub(r'^[0-9]+_', '', base)

            parent = os.path.basename(root)
            mbe_context = parent.replace('.mbe', '')

            results.append((rel_path, sheet_name, is_append, mbe_context, full_path))

    return results


_CSV_TYPE_PARSERS = {
    'int32': lambda v: int(v) if v else 0,
    'int16': lambda v: int(v) if v else 0,
    'int8':  lambda v: int(v) if v else 0,
    'float': lambda v: float(v) if v else 0.0,
    'string': lambda v: v,
    'string2': lambda v: v,
    'string3': lambda v: v,
    'bool': lambda v: v.lower() == 'true' if v else False,
    'empty': lambda v: None,
}


def parse_mod_csv(csv_path):
    """Parse a mod CSV into a list of row dicts keyed as col_0, col_1, etc."""
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)

            col_types = []
            for h in header:
                parts = h.strip().split()
                ctype = parts[0].lower() if parts else 'empty'
                if ctype in ('int', 'int32'):
                    ctype = 'int32'
                elif ctype == 'short':
                    ctype = 'int16'
                elif ctype == 'byte':
                    ctype = 'int8'
                col_types.append(ctype)

            rows = []
            for row_data in reader:
                row = {}
                for i, val in enumerate(row_data):
                    if i >= len(col_types):
                        break
                    parser = _CSV_TYPE_PARSERS.get(col_types[i], lambda v: v)
                    try:
                        row[f"col_{i}"] = parser(val)
                    except (ValueError, TypeError):
                        row[f"col_{i}"] = None
                rows.append(row)

            return col_types, rows
    except Exception as e:
        logger.warning("Failed to parse CSV %s: %s", csv_path, e)
        return [], []


# ── Mod Data Merger ──────────────────────────────────────────────────────

def build_overlay(content_mods):
    """Process all content mods and build a ModOverlay."""
    overlay = ModOverlay()
    if not content_mods:
        return overlay

    accumulated = {}

    for mod in content_mods:
        overlay.mod_names.append(mod.name)
        for rel_path, sheet_name, is_append, mbe_context, full_path in mod.csv_files:
            _, rows = parse_mod_csv(full_path)
            if not rows:
                continue

            key = (mbe_context, sheet_name)
            if is_append:
                accumulated.setdefault(key, []).extend(rows)
            else:
                accumulated[key] = list(rows)

    overlay.mod_count = len(content_mods)
    overlay.is_active = True

    _build_evolution_overlay(accumulated, overlay)
    _build_digimon_overlay(accumulated, overlay)
    _build_name_overlay(accumulated, overlay)

    # Resolve English names for new Digimon
    for did, info in overlay.new_digimon.items():
        internal = info.get("internal", "")
        if internal in overlay.name_overrides:
            info["name"] = overlay.name_overrides[internal]
        elif internal:
            # Strip char_ prefix, title-case
            name = internal.replace("char_", "").replace("_", " ").title()
            info["name"] = name
        else:
            info["name"] = f"Modded #{did}"

        # Add type from overlay if available
        info["type"] = overlay.digimon_types.get(did, "")

    return overlay


def _build_evolution_overlay(accumulated, overlay):
    """Extract evolution data from accumulated CSV rows."""
    for key, rows in accumulated.items():
        mbe_ctx, sheet = key
        if sheet != "evolution_to":
            continue
        if "evolution" not in mbe_ctx:
            continue
        for r in rows:
            src = r.get("col_1", 0)
            tgt = r.get("col_3", 0)
            if src and tgt and tgt > 0 and tgt != -1:
                overlay.evo_additions.append((src, tgt))

    for key, rows in accumulated.items():
        mbe_ctx, sheet = key
        if sheet != "chronodevolution":
            continue
        for r in rows:
            did = r.get("col_0", 0)
            if not did:
                continue
            for ci in range(2, 8):
                tgt = r.get(f"col_{ci}", 0)
                if tgt and tgt > 0 and tgt != -1:
                    overlay.devo_additions.append((did, tgt))

    for key, rows in accumulated.items():
        mbe_ctx, sheet = key
        if sheet != "evolution_condition":
            continue
        for r in rows:
            did = r.get("col_0", 0)
            if not did:
                continue
            overlay.cond_overrides[did] = {
                "agent_rank": r.get("col_2", 0) or 0,
                "talent": r.get("col_11", 0) or 0,
                "hp": r.get("col_4", 0) or 0,
                "sp": r.get("col_5", 0) or 0,
                "atk": r.get("col_6", 0) or 0,
                "def_": r.get("col_7", 0) or 0,
                "int_": r.get("col_8", 0) or 0,
                "spi": r.get("col_9", 0) or 0,
                "spd": r.get("col_10", 0) or 0,
                "item_id": r.get("col_15", 0) or 0,
                "jogress1_id": r.get("col_19", 0) or 0,
                "jogress2_id": r.get("col_20", 0) or 0,
            }


def _build_digimon_overlay(accumulated, overlay):
    """Extract new Digimon data from accumulated CSV rows."""
    for key, rows in accumulated.items():
        mbe_ctx, sheet = key
        if sheet != "digimon_status_data":
            continue
        for r in rows:
            did = r.get("col_0", 0)
            if not did or did <= 0:
                continue

            internal = r.get("col_2", "")
            stage_id = r.get("col_4", 0) or 0
            attr_id = r.get("col_6", 0) or 0

            stage = STAGE_MAP.get(stage_id, f"Unknown({stage_id})")
            attr = ATTR_MAP.get(attr_id, f"Unknown({attr_id})")

            base_stats = [r.get(f"col_{i}", 0) or 0 for i in range(64, 71)]

            overlay.new_digimon[did] = {
                "id": did,
                "internal": internal,
                "stage": stage,
                "stage_id": stage_id,
                "attribute": attr,
                "attribute_id": attr_id,
            }
            overlay.new_stats[did] = base_stats

            pers_id = r.get("col_61", 0) or 0
            if pers_id:
                overlay.personalities[did] = pers_id

            skill1 = r.get("col_72", 0) or 0
            skill2 = r.get("col_126", 0) or 0
            if skill1:
                overlay.special_skills[did] = (skill1, skill2 if skill2 else 0)

            res = {}
            for col_i, element in RES_COL_ELEMENTS:
                raw = r.get(f"col_{col_i}", 0) or 0
                mult = RES_VAL_MAP.get(raw, 1.0)
                if mult != 1.0:
                    res[element] = mult
            if res:
                overlay.new_resistances[did] = res


def _build_name_overlay(accumulated, overlay):
    """Extract name mappings, profiles, types, and skill names."""
    for key, rows in accumulated.items():
        mbe_ctx, sheet = key
        if sheet != "Sheet1":
            continue
        for r in rows:
            col0 = r.get("col_0", "")
            col1 = r.get("col_1", "")
            if not col0 or not col1:
                continue

            if "char_name" in mbe_ctx:
                overlay.name_overrides[col0] = col1
            elif "digimon_profile" in mbe_ctx:
                overlay.profiles[col0] = col1
            elif "belong" in mbe_ctx:
                try:
                    did = int(col0)
                    overlay.digimon_types[did] = col1
                except (ValueError, TypeError):
                    pass
            elif "skill_name" in mbe_ctx:
                overlay.skill_names[col0] = col1


# ── Icon Discovery ───────────────────────────────────────────────────────

def _discover_mod_icons(content_mods, overlay):
    """Find DDS icon files in mods and convert to PNG for display."""
    try:
        from PIL import Image
    except ImportError:
        return

    # Store converted icons next to save files
    try:
        from save_data import find_save_directory
        save_dir = find_save_directory()
        if not save_dir:
            return
        icon_cache = os.path.join(os.path.dirname(save_dir), "mod_icon_cache")
    except Exception:
        return

    os.makedirs(icon_cache, exist_ok=True)

    for mod in content_mods:
        for root, dirs, files in os.walk(mod.path):
            for fname in files:
                if not fname.lower().endswith('.dds'):
                    continue
                if not fname.lower().startswith('ui_chara_icon_'):
                    continue

                try:
                    did_str = fname[len('ui_chara_icon_'):-4]
                    did = int(did_str)
                except (ValueError, IndexError):
                    continue

                dds_path = os.path.join(root, fname)
                png_path = os.path.join(icon_cache, f"{did}.png")
                if not os.path.exists(png_path):
                    try:
                        img = Image.open(dds_path)
                        img = img.resize((256, 256), Image.LANCZOS)
                        img.save(png_path, "PNG")
                        logger.info("Converted mod icon: %s", fname)
                    except Exception as e:
                        logger.debug("Failed to convert icon %s: %s", fname, e)
                        continue

                overlay.icon_paths[did] = png_path


# ── Main Detection Entry Point ───────────────────────────────────────────

def detect_mods():
    """Full mod detection pipeline. Returns a ModOverlay (may be empty)."""
    reloaded_path = find_reloaded_ii()
    if not reloaded_path:
        logger.debug("Mod detection: Reloaded-II not found")
        return ModOverlay()

    logger.info("Mod detection: Reloaded-II at %s", reloaded_path)

    enabled, sorted_mods = read_app_config(reloaded_path)
    if not enabled:
        logger.info("Mod detection: no enabled mods")
        return ModOverlay()

    content_mods = get_content_mods(reloaded_path, enabled, sorted_mods)
    if not content_mods:
        logger.info("Mod detection: no content mods with data CSVs")
        return ModOverlay()

    logger.info("Mod detection: found %d content mods: %s",
                len(content_mods),
                ", ".join(m.name for m in content_mods))

    overlay = build_overlay(content_mods)
    _discover_mod_icons(content_mods, overlay)

    logger.info("Mod overlay: %d new Digimon, %d name overrides, %d icons, "
                "%d evo additions, %d skill names",
                len(overlay.new_digimon), len(overlay.name_overrides),
                len(overlay.icon_paths), len(overlay.evo_additions),
                len(overlay.skill_names))

    return overlay
