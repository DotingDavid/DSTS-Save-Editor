"""Save file data access layer.

Reads and writes structured data from decrypted save files using
the field definitions in save_layout.py. All reads/writes operate
on an in-memory bytearray — call save() to write back to disk.
"""

import os
import glob
import logging
import shutil
import struct
import random
import sqlite3
import base64
import json
import subprocess
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

import save_crypto
from save_layout import (DIGI, REGIONS, AGENT, PERSONALITY_NAMES,
                         SCAN_TABLE_OFFSET, SCAN_TABLE_STRIDE,
                         SCAN_TABLE_REAL_START,
                         AGENT_BASE_OFFSET, AGENT_SKILL_OFFSET,
                         AGENT_SKILL_STRIDE)
from app_paths import get_db_path

VERSION = "1.0.0"

# ── Mod overlay ──────────────────────────────────────────────────────
_mod_overlay = None


def set_mod_overlay(overlay):
    """Set the global mod overlay. Called once on startup after detection."""
    global _mod_overlay, _species_cache
    _mod_overlay = overlay
    _species_cache = None  # force rebuild with modded species


# ── Save UID system ──────────────────────────────────────────────────
# Shared namespace for deterministic UUID generation. MUST be identical
# in both ANAMNESIS SE and ANAMNESIS Companion.
ANAMNESIS_NAMESPACE = uuid.UUID('f47ac10b-58cc-4372-a567-0e02b2c3d479')
SAVE_UID_OFFSET = 0x904       # offset in decrypted save data
SAVE_UID_MAGIC = b'ANAMNESIS|' # magic bytes to detect existing signature
AUTOSAVE_SLOT = '0000'        # never write UID to autosave — read only


def generate_save_uid(steam_id: str, slot_number: str) -> str:
    """Generate a deterministic UUID for a save slot.

    Same inputs → same output, every time, in any language.
    Both ANAMNESIS SE and ANAMNESIS Companion use this exact function
    with the same ANAMNESIS_NAMESPACE to produce identical UUIDs.
    """
    return str(uuid.uuid5(ANAMNESIS_NAMESPACE, f"{steam_id}:{slot_number}"))


def read_save_uid(data: bytes) -> str | None:
    """Read the ANAMNESIS UID from decrypted save data. Returns None if not stamped."""
    sig = data[SAVE_UID_OFFSET:SAVE_UID_OFFSET + 80]
    if sig.startswith(SAVE_UID_MAGIC):
        parts = sig.split(b'\x00')[0].decode('ascii', errors='replace').split('|')
        if len(parts) >= 2:
            return parts[1]  # the UUID
    # Backward compat: old format was ANSE|version|uuid
    if sig.startswith(b'ANSE|'):
        parts = sig.split(b'\x00')[0].decode('ascii', errors='replace').split('|')
        if len(parts) >= 3:
            return parts[2]
    return None


def write_save_uid(data: bytearray, uid: str):
    """Write the ANAMNESIS signature into decrypted save data at 0x904."""
    sig = f"ANAMNESIS|{uid}".encode('ascii')
    for i, b in enumerate(sig):
        data[SAVE_UID_OFFSET + i] = b
    # Null-terminate
    data[SAVE_UID_OFFSET + len(sig)] = 0


def unsign_save(path: str):
    """Remove the ANAMNESIS signature from a save file.

    Zeroes out the signature region at 0x904, restoring it to the
    state the game originally had (all zeros in the padding region).
    """
    with open(path, 'rb') as f:
        raw = f.read()
    data = bytearray(save_crypto.decrypt(raw))

    # Check if there's actually a signature
    if not read_save_uid(data):
        return False

    # Zero out the signature region
    for i in range(80):
        data[SAVE_UID_OFFSET + i] = 0

    encrypted = save_crypto.encrypt(bytes(data))
    with open(path, 'wb') as f:
        f.write(encrypted)
    logger.info("Unsigned save: %s", path)
    return True


def restore_pre_signature_backup(save_dir: str, slot_str: str) -> bool:
    """Restore a pre-signature backup for a specific slot.

    Copies the original unsigned save from pre_signature_backups/ back
    to the save directory, overwriting the current (signed) version.
    """
    pre_sig_dir = os.path.join(save_dir, 'pre_signature_backups')
    backup_path = os.path.join(pre_sig_dir, f"{slot_str}.bin")
    dest_path = os.path.join(save_dir, f"{slot_str}.bin")

    if not os.path.exists(backup_path):
        return False

    shutil.copy2(backup_path, dest_path)
    logger.info("Restored pre-signature backup for slot %s", slot_str)
    return True


def _extract_steam_id_and_slot(path: str) -> tuple[str | None, str | None]:
    """Extract steam_id and slot number from a save file path.

    Expected path: .../savedata/{steam_id}/{slot}.bin
    """
    path = os.path.normpath(path)
    basename = os.path.basename(path)
    slot = basename.replace('.bin', '') if basename.endswith('.bin') else None
    parent = os.path.basename(os.path.dirname(path))
    steam_id = parent if parent.isdigit() else None
    return steam_id, slot


def stamp_save_uid(path: str) -> str | None:
    """Stamp a save file with a deterministic UID if it doesn't have one.

    Rules:
    - Slot 0000 (autosave): NEVER write, read only
    - Slots 0001+: write UUID on first encounter
    Returns the UID (existing or newly written), or None if autosave.
    """
    steam_id, slot = _extract_steam_id_and_slot(path)
    if not steam_id or not slot:
        return None

    with open(path, 'rb') as f:
        raw = f.read()
    data = bytearray(save_crypto.decrypt(raw))

    # Check existing
    existing = read_save_uid(data)
    if existing:
        return existing

    # Never write to autosave
    if slot == AUTOSAVE_SLOT:
        return None

    # Back up the original unsigned save before writing the signature.
    # Separate from the regular auto-backup folder — this is a one-time
    # "pre-signature" backup so users can restore if they're uncomfortable
    # with their save being signed.
    pre_sig_dir = os.path.join(os.path.dirname(path), 'pre_signature_backups')
    os.makedirs(pre_sig_dir, exist_ok=True)
    backup_path = os.path.join(pre_sig_dir, os.path.basename(path))
    if not os.path.exists(backup_path):
        shutil.copy2(path, backup_path)
        logger.info("Pre-signature backup: %s", backup_path)

    # Generate and write
    uid = generate_save_uid(steam_id, slot)
    write_save_uid(data, uid)
    encrypted = save_crypto.encrypt(bytes(data))
    with open(path, 'wb') as f:
        f.write(encrypted)
    logger.info("Stamped save UID for slot %s: %s", slot, uid)
    return uid


def _consent_path(save_dir: str) -> str:
    """Path to the stamp consent file."""
    return os.path.join(save_dir, 'stamp_consent.json')


def get_stamp_consent(save_dir: str) -> bool | None:
    """Check stamp consent state.

    Returns True (consented), False (declined), or None (never asked).
    """
    path = _consent_path(save_dir)
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        return data.get("consented")
    except Exception:
        return None


def set_stamp_consent(save_dir: str, consented: bool):
    """Record the user's stamp consent decision."""
    path = _consent_path(save_dir)
    with open(path, 'w') as f:
        json.dump({"consented": consented}, f)


def stamp_all_saves(save_dir: str) -> dict[str, str]:
    """Stamp all unstamped save files in a directory. Skip slot 0000.

    Call on first launch with game closed. Returns {slot: uid} mapping.
    """
    results = {}
    slots = list_save_slots(save_dir)
    for slot_num, path, _ in slots:
        slot_str = f"{slot_num:04d}"
        if slot_str == AUTOSAVE_SLOT:
            # Read only for autosave
            try:
                with open(path, 'rb') as f:
                    raw = f.read()
                data = save_crypto.decrypt(raw)
                uid = read_save_uid(data)
                if uid:
                    results[slot_str] = uid
            except Exception:
                pass
            continue
        try:
            uid = stamp_save_uid(path)
            if uid:
                results[slot_str] = uid
        except Exception as e:
            logger.warning("Failed to stamp slot %s: %s", slot_str, e)
    return results


# ── Database lookups ────────────────────────────────────────────────

_db_conn = None


def _get_db():
    global _db_conn
    if _db_conn is None:
        _db_conn = sqlite3.connect(get_db_path())
        _db_conn.row_factory = sqlite3.Row
    return _db_conn


def close_db():
    """Close the database connection. Call on app exit."""
    global _db_conn
    if _db_conn is not None:
        _db_conn.close()
        _db_conn = None


import re as _re

_tamer_skill_cache = None


def get_tamer_skill_catalog():
    """Return cached list of all 208 tamer skills with DB metadata.

    Each entry: {id, name_jp, description, cost, tree_group, boost_value}
    Descriptions have template markers resolved with boost_value.
    """
    global _tamer_skill_cache
    if _tamer_skill_cache is not None:
        return _tamer_skill_cache

    db = _get_db()
    rows = db.execute("""
        SELECT t.id, t.description, t.cost, t.tree_group, t.boost_value,
               n.name AS name_jp, t.name_en,
               t.grid_position, t.prerequisite, t.prerequisite2,
               t.effect_type_id, t.digimon_req, t.tp_cost
        FROM tamer_skills t
        LEFT JOIN tamer_skill_names n ON CAST(t.id AS TEXT) = n.key
        ORDER BY t.id
    """).fetchall()

    catalog = []
    for r in rows:
        desc = r["description"] or ""
        bv = r["boost_value"] or 0
        # Resolve template markers {d0}, {d1}, ... {d6} with int(boost_value)
        desc = _re.sub(r'\{d\d\}', str(int(bv)), desc)
        desc = desc.replace('\n', ' ')
        catalog.append({
            'id': r["id"],
            'name_jp': r["name_jp"] or '',
            'description': desc,
            'cost': r["cost"] or 0,
            'tree_group': r["tree_group"],
            'boost_value': bv,
            'grid_position': r["grid_position"] or '',
            'prerequisite': r["prerequisite"] or 0,
            'prerequisite2': r["prerequisite2"] or 0,
            'effect_type_id': r["effect_type_id"] or 0,
            'digimon_req': r["digimon_req"] or 0,
            'tp_cost': r["tp_cost"] or 0,
            'name_en': r["name_en"] or '',
        })

    _tamer_skill_cache = catalog
    return catalog


def get_digimon_name(db_id):
    """Look up Digimon species name by database ID."""
    # Check mod overlay first
    if _mod_overlay and _mod_overlay.is_active and db_id in _mod_overlay.new_digimon:
        return _mod_overlay.new_digimon[db_id].get("name", f"Modded #{db_id}")
    row = _get_db().execute(
        "SELECT name FROM digimon WHERE id = ?", (db_id,)
    ).fetchone()
    if row:
        return row["name"]
    logger.warning("Unknown Digimon ID: %d", db_id)
    return f"Unknown({db_id})"


def get_digimon_info(db_id):
    """Look up Digimon name, stage, attribute, type by database ID."""
    if _mod_overlay and _mod_overlay.is_active and db_id in _mod_overlay.new_digimon:
        info = _mod_overlay.new_digimon[db_id]
        return {"name": info.get("name", f"Modded #{db_id}"),
                "stage": info.get("stage", ""),
                "attribute": info.get("attribute", ""),
                "type": info.get("type", "")}
    row = _get_db().execute(
        "SELECT name, stage, attribute, type FROM digimon WHERE id = ?", (db_id,)
    ).fetchone()
    if row:
        return dict(row)
    return None


def get_growth_type(db_id):
    """Look up growth_type for a Digimon species."""
    row = _get_db().execute(
        "SELECT growth_type FROM digimon WHERE id = ?", (db_id,)
    ).fetchone()
    return row["growth_type"] if row else 1


def get_exp_curve(db_id):
    """Look up the EXP curve for a species. Returns curve_id (1-4)."""
    row = _get_db().execute(
        "SELECT exp_curve FROM digimon WHERE id = ?", (db_id,)
    ).fetchone()
    return row["exp_curve"] if row and row["exp_curve"] else 1


def get_exp_for_level(level, curve_id=None, db_id=None):
    """Look up the total EXP required for a given level.

    Pass db_id to auto-detect the species' curve, or curve_id to specify
    explicitly. If neither is given, defaults to curve 4 (safest).
    """
    if curve_id is None:
        curve_id = get_exp_curve(db_id) if db_id else 4
    row = _get_db().execute(
        "SELECT total_exp FROM experience_curves WHERE curve_id = ? AND level = ?",
        (curve_id, level)
    ).fetchone()
    return row["total_exp"] if row else 0


def get_growth_stats(growth_type, level):
    """Look up cumulative white stat growth at a given level.

    The growth_curves table stores per-level increments, so we sum
    all rows from level 1 through the target level.

    Returns [hp, sp, atk, def, int, spi, spd] — the total growth
    from leveling, NOT including personality bonuses.
    """
    row = _get_db().execute(
        "SELECT SUM(hp), SUM(sp), SUM(atk), SUM(def_), SUM(int_), "
        "SUM(spi), SUM(spd) FROM growth_curves "
        "WHERE curve_id = ? AND level <= ?",
        (growth_type, level)
    ).fetchone()
    if row and row[0] is not None:
        return [row[0], row[1], row[2], row[3], row[4], row[5], row[6]]
    return [0] * 7


def get_base_stats(db_id):
    """Look up base stats (level 1) for a Digimon."""
    if _mod_overlay and _mod_overlay.is_active and db_id in _mod_overlay.new_stats:
        return list(_mod_overlay.new_stats[db_id])
    row = _get_db().execute(
        "SELECT hp, sp, atk, def_, int_, spi, spd FROM stats_base WHERE digimon_id = ?",
        (db_id,)
    ).fetchone()
    if row:
        return list(row)
    logger.warning("No base stats for Digimon ID: %d", db_id)
    return [0] * 7


_species_cache = None

def get_all_digimon_species():
    """Return sorted list of (db_id, name, stage, attribute, type) for all Digimon."""
    global _species_cache
    if _species_cache is not None:
        return _species_cache
    db = _get_db()
    _species_cache = []
    for row in db.execute(
            "SELECT id, name, stage, attribute, type FROM digimon ORDER BY name"):
        _species_cache.append(
            (row["id"], row["name"], row["stage"] or "",
             row["attribute"] or "", row["type"] or ""))
    # Append modded species
    if _mod_overlay and _mod_overlay.is_active:
        existing_ids = {s[0] for s in _species_cache}
        for db_id, info in _mod_overlay.new_digimon.items():
            if db_id not in existing_ids:
                _species_cache.append(
                    (db_id, info.get("name", f"Modded #{db_id}"),
                     info.get("stage", ""), info.get("attribute", ""),
                     info.get("type", "")))
        _species_cache.sort(key=lambda s: s[1].lower())
    return _species_cache


def is_game_running():
    """Check if the game process is currently running."""
    try:
        output = subprocess.check_output(
            ['tasklist', '/FI', 'IMAGENAME eq Digimon Story Time Stranger.exe',
             '/NH'],
            creationflags=0x08000000,  # CREATE_NO_WINDOW
            timeout=3
        ).decode('ascii', errors='replace')
        return 'Digimon' in output
    except Exception as e:
        logger.warning("Game process check failed: %s", e)
        return False


def get_item_name(item_id):
    """Look up item name by ID. Falls back to skill_names for skill disc IDs."""
    db = _get_db()
    row = db.execute(
        "SELECT name FROM item_names WHERE item_id = ?", (str(item_id),)
    ).fetchone()
    if row and row["name"]:
        return row["name"]
    # Skill disc IDs (30000+) map to skill_names
    if item_id >= 30000:
        row = db.execute(
            "SELECT name FROM skill_names WHERE skill_id = ?", (item_id,)
        ).fetchone()
        if row and row["name"]:
            return row["name"]
    return f"Item #{item_id}"


# ── Save file discovery ────────────────────────────────────────────

def find_save_directory():
    """Find the game's save directory. Returns path or None.

    If multiple Steam accounts exist, returns the most recently modified one.
    Use find_all_save_directories() to get all of them.
    """
    dirs = find_all_save_directories()
    if not dirs:
        return None
    if len(dirs) == 1:
        return dirs[0][1]
    # Return the one with the most recent save file
    best = None
    best_mtime = 0
    for steam_id, path, _ in dirs:
        slots = list_save_slots(path)
        if slots:
            latest = max(s[2] for s in slots)
            if latest > best_mtime:
                best_mtime = latest
                best = path
    return best or dirs[0][1]


def find_all_save_directories():
    """Find all Steam user save directories.

    Returns list of (steam_id, path, player_name) tuples.
    player_name is read from the most recent save's header.
    """
    steam_base = os.path.join(
        os.environ.get('ProgramFiles(x86)', ''),
        'Steam', 'steamapps', 'common',
        'Digimon Story Time Stranger', 'gamedata', 'savedata'
    )
    results = []
    if os.path.isdir(steam_base):
        subdirs = sorted(
            [d for d in os.listdir(steam_base)
             if os.path.isdir(os.path.join(steam_base, d)) and d.isdigit()])
        for d in subdirs:
            path = os.path.join(steam_base, d)
            player_name = _read_player_name(path)
            results.append((d, path, player_name))
    return results


def _read_player_name(save_dir):
    """Read the player name from the most recent save file's header."""
    slots = list_save_slots(save_dir)
    if not slots:
        return "Unknown"
    # Use most recent slot
    _, best_path, _ = max(slots, key=lambda s: s[2])
    try:
        with open(best_path, 'rb') as f:
            raw = f.read()
        data = save_crypto.decrypt(raw)
        # Header is plaintext CSV, player name is field 4 (0-indexed)
        header = data[:200].split(b'\x00')[0].decode('ascii', errors='replace')
        parts = [p.strip() for p in header.split(',')]
        if len(parts) > 4:
            return parts[4].strip()
    except Exception as e:
        logger.debug("Failed to read player name from %s: %s", save_dir, e)
    return "Unknown"


def list_save_slots(save_dir):
    """List available save slots. Returns [(slot_num, file_path, mtime), ...]."""
    if not save_dir or not os.path.isdir(save_dir):
        return []
    slots = []
    for f in sorted(glob.glob(os.path.join(save_dir, '????.bin'))):
        basename = os.path.basename(f)
        if basename.startswith('slot_') or basename == 'sysdata_dx11.bin':
            continue
        try:
            slot_num = int(basename.replace('.bin', ''))
            mtime = os.path.getmtime(f)
            slots.append((slot_num, f, mtime))
        except (ValueError, OSError):
            continue
    return slots


def peek_save_info(path):
    """Quickly read player name, money, and signature status from an encrypted save.

    Used by the file manager to show previews on save slot cards.
    Returns dict with 'name', 'money', 'signed', or None on error.
    """
    try:
        with open(path, 'rb') as f:
            raw = f.read()
        if len(raw) != save_crypto.SAVE_FILE_SIZE:
            return None
        data = save_crypto.decrypt(raw)
        name_bytes = data[0x0FDE90:0x0FDE90 + 32]
        name = name_bytes.split(b'\x00')[0].decode('ascii', errors='replace').strip()
        money = struct.unpack_from('<I', data, AGENT_BASE_OFFSET + 0x058)[0]
        uid = read_save_uid(data)
        # Find stride base in party/box region (same logic as _find_stride_base)
        party = []
        pb_base = None
        for off in range(0x001000, 0x001000 + 0x150 * 20, 4):
            did = struct.unpack_from('<I', data, off)[0]
            if not (1 <= did <= 10000):
                continue
            noff = off + 4
            if noff + 0x64 > len(data):
                continue
            ne = data.find(b'\x00', noff, noff + 32)
            if ne <= noff:
                continue
            lv = struct.unpack_from('<i', data, noff + 0x60)[0]
            if 1 <= lv <= 99:
                pb_base = 0x001000 + ((off - 0x001000) % 0x150)
                break
        # Party = positions 2-7 (first 2 are sentinels)
        if pb_base is not None:
            for i in range(2, 8):
                off = pb_base + i * 0x150
                did = struct.unpack_from('<I', data, off)[0]
                nick = ''
                if 1 <= did <= 10000:
                    nb = data[off + 4:off + 36]
                    nick = nb.split(b'\x00')[0].decode(
                        'ascii', errors='replace').strip()
                else:
                    did = 0
                party.append({'db_id': did, 'nickname': nick})
        else:
            party = [{'db_id': 0, 'nickname': ''} for _ in range(6)]
        return {
            'name': name if name else '???',
            'money': money,
            'uid': uid,
            'party': party,
        }
    except Exception:
        return None


# ── Save file model ────────────────────────────────────────────────

class SaveFile:
    """Represents a loaded save file with read/write access to all fields."""

    def __init__(self, path):
        self.path = path
        with open(path, 'rb') as f:
            raw = f.read()
        self._data = bytearray(save_crypto.decrypt(raw))
        self._dirty = False
        # Read existing UID only — stamping requires user consent first
        self._uid = read_save_uid(self._data)

    @property
    def uid(self):
        return self._uid

    @property
    def dirty(self):
        return self._dirty

    def _mark_dirty(self):
        self._dirty = True

    # ── Raw read/write helpers ──

    def read_u8(self, offset):
        return self._data[offset]

    def read_i16(self, offset):
        return struct.unpack('<h', self._data[offset:offset + 2])[0]

    def read_u16(self, offset):
        return struct.unpack('<H', self._data[offset:offset + 2])[0]

    def read_i32(self, offset):
        return struct.unpack('<i', self._data[offset:offset + 4])[0]

    def read_u32(self, offset):
        return struct.unpack('<I', self._data[offset:offset + 4])[0]

    def read_f32(self, offset):
        return struct.unpack('<f', self._data[offset:offset + 4])[0]

    def read_f64(self, offset):
        return struct.unpack('<d', self._data[offset:offset + 8])[0]

    def read_str(self, offset, max_len=32):
        end = self._data.find(b'\x00', offset, offset + max_len)
        if end == -1:
            logger.warning("No null terminator in string at offset 0x%X (max_len=%d)", offset, max_len)
            end = offset + max_len
        return self._data[offset:end].decode('ascii', errors='replace')

    def write_u8(self, offset, value):
        self._data[offset] = value & 0xFF
        self._mark_dirty()

    def write_i32(self, offset, value):
        struct.pack_into('<i', self._data, offset, value)
        self._mark_dirty()

    def write_u32(self, offset, value):
        struct.pack_into('<I', self._data, offset, value)
        self._mark_dirty()

    def write_f32(self, offset, value):
        struct.pack_into('<f', self._data, offset, value)
        self._mark_dirty()

    # ── Stride detection (shared by read_roster and find_empty_slot) ──

    def _find_stride_base(self, region_start, region_end, stride, valid_ids):
        """Find the first valid Digimon in a region and derive stride base."""
        d = self._data
        for off in range(region_start, min(region_start + stride * 20, region_end), 4):
            db_id = struct.unpack('<I', d[off:off + 4])[0]
            if db_id not in valid_ids:
                continue
            name_off = off + 4
            if name_off + 0x64 > len(d):
                continue
            name_end = d.find(b'\x00', name_off, name_off + 32)
            if name_end <= name_off:
                continue
            lv = struct.unpack('<i', d[name_off + 0x60:name_off + 0x64])[0]
            if 1 <= lv <= 99:
                base = region_start + ((off - region_start) % stride)
                return base
        return None

    # ── Roster parsing ──

    def read_roster(self):
        """Read all Digimon entries from the save file.

        The game uses compacting arrays — active entries are contiguous
        from the start of each region, with active_flag=1. When a Digimon
        is removed, the game shifts remaining entries up to fill the gap
        and marks the tail as active_flag=0. No deduplication needed.

        Party/box layout:
          - First 6 entries = party slots (party_flag=1 means occupied)
          - Entry 7+ = box (read until active_flag=0)
        Farm layout:
          - All entries contiguous (read until active_flag=0)
        """
        d = self._data
        stat_names = ['hp', 'sp', 'atk', 'def', 'int', 'spi', 'spd']

        # Pre-build lookup of all valid Digimon IDs
        db = _get_db()
        id_to_info = {}
        for row in db.execute("SELECT id, name, stage, attribute, type FROM digimon"):
            id_to_info[row["id"]] = dict(row)
        base_stats_cache = {}
        for row in db.execute("SELECT digimon_id, hp, sp, atk, def_, int_, spi, spd FROM stats_base"):
            base_stats_cache[row["digimon_id"]] = [row["hp"], row["sp"], row["atk"],
                                                     row["def_"], row["int_"],
                                                     row["spi"], row["spd"]]

        # Inject modded species so they appear in the roster
        if _mod_overlay and _mod_overlay.is_active:
            for db_id, info in _mod_overlay.new_digimon.items():
                if db_id not in id_to_info:
                    id_to_info[db_id] = {
                        "id": db_id, "name": info.get("name", f"Modded #{db_id}"),
                        "stage": info.get("stage", ""),
                        "attribute": info.get("attribute", ""),
                        "type": info.get("type", "")}
            for db_id, stats in _mod_overlay.new_stats.items():
                if db_id not in base_stats_cache:
                    base_stats_cache[db_id] = stats

        party_entries = []
        box_entries = []

        # ── Party/box region ──
        # Layout: 2 sentinel/header slots + 6 party slots + box entries.
        # The first 8 stride positions are party territory — any valid
        # Digimon within those positions is a party member.
        # Position 8 onwards is the box (read until first active=0).
        # The game displays the box in reverse (newest first), so we
        # reverse box_entries before returning.
        PARTY_SLOTS = 8  # 2 sentinels + 6 party members
        pb_base = self._find_stride_base(0x001000, 0x009000, 0x150, id_to_info)
        if pb_base is not None:
            for slot, db_off in enumerate(range(pb_base, 0x053000, 0x150)):
                name_off = db_off + 4
                active = struct.unpack('<I', d[name_off + 0x140:name_off + 0x144])[0]

                if slot < PARTY_SLOTS:
                    entry = self._parse_entry(d, name_off, "party_box",
                                              id_to_info, base_stats_cache, stat_names)
                    if entry is not None:
                        entry["location"] = "party"
                        party_entries.append(entry)
                elif active == 1:
                    entry = self._parse_entry(d, name_off, "party_box",
                                              id_to_info, base_stats_cache, stat_names)
                    if entry is not None:
                        entry["location"] = "box"
                        box_entries.append(entry)
                else:
                    # First active=0 entry is the box list head (newest entry).
                    # Include it, then stop — everything after is stale.
                    entry = self._parse_entry(d, name_off, "party_box",
                                              id_to_info, base_stats_cache, stat_names)
                    if entry is not None:
                        entry["location"] = "box"
                        box_entries.append(entry)
                    break

        # Reverse box to match game display order (newest first)
        box_entries.reverse()

        # ── Farm region ──
        # Farm has empty pre-allocated slots at the start (active=0, db_id=0),
        # then a sentinel (active=1, db_id=0), then real entries (active=1),
        # then tail (active=0). Only break on active=0 AFTER seeing real data.
        farm_entries = []
        fm_base = self._find_stride_base(0x053000, 0x055000, 0x158, id_to_info)
        if fm_base is not None:
            found_active = False
            for db_off in range(fm_base, 0x05C000, 0x158):
                name_off = db_off + 4
                db_id = struct.unpack('<I', d[db_off:db_off + 4])[0]
                active = struct.unpack('<I', d[name_off + 0x140:name_off + 0x144])[0]

                if active == 1 and db_id > 0 and db_id in id_to_info:
                    found_active = True
                    entry = self._parse_entry(d, name_off, "farm",
                                              id_to_info, base_stats_cache, stat_names)
                    if entry is not None:
                        farm_entries.append(entry)
                elif found_active and active == 0:
                    break  # tail reached after real entries

        return party_entries + box_entries + farm_entries

    def _parse_entry(self, d, offset, region, id_to_info, base_stats_cache, stat_names):
        """Parse a single Digimon entry. Returns dict or None if invalid."""
        db_id = struct.unpack('<I', d[offset - 4:offset])[0]
        info = id_to_info.get(db_id)
        if not info:
            # Fallback for unrecognized species (modded save without mods)
            name_end = d.find(b'\x00', offset, offset + 32)
            if name_end > offset:
                try:
                    fallback_name = d[offset:name_end].decode('ascii')
                    if len(fallback_name) >= 2:
                        info = {"id": db_id, "name": fallback_name,
                                "stage": "", "attribute": "", "type": ""}
                except (UnicodeDecodeError, ValueError):
                    pass
            if not info:
                return None

        name_end = d.find(b'\x00', offset, offset + 32)
        if name_end <= offset:
            return None
        try:
            entry_name = d[offset:name_end].decode('ascii')
        except (UnicodeDecodeError, ValueError):
            return None
        if not entry_name or len(entry_name) < 2:
            return None

        lv = struct.unpack('<i', d[offset + 0x60:offset + 0x64])[0]
        if not (1 <= lv <= 99):
            return None

        pers_id = d[offset + 0xEE]
        if pers_id < 1 or pers_id > 16:
            return None

        # Stat layers
        white = [struct.unpack('<i', d[offset + 0x74 + i * 4:offset + 0x78 + i * 4])[0] for i in range(7)]
        farm = [struct.unpack('<i', d[offset + 0x90 + i * 4:offset + 0x94 + i * 4])[0] // 10 for i in range(7)]
        blue = [struct.unpack('<i', d[offset + 0xAC + i * 4:offset + 0xB0 + i * 4])[0] for i in range(7)]
        base = base_stats_cache.get(db_id, [0] * 7)
        total = [base[i] + white[i] + farm[i] + blue[i] for i in range(7)]

        talent_raw = struct.unpack('<i', d[offset + 0x100:offset + 0x104])[0]
        talent = talent_raw // 1000 if talent_raw > 0 else 0
        bond_raw = struct.unpack('<f', d[offset + 0x13C:offset + 0x140])[0]
        bond = round(bond_raw) // 100 if bond_raw > 0 else 0

        # Creation hash — differs by region
        if region == "farm":
            farm_hash = struct.unpack('<I', d[offset + 0x150:offset + 0x154])[0]
            if farm_hash < 0x100:
                # Hash not populated — verify entry is real via training/bond data
                training_status = struct.unpack('<I', d[offset + 0xD8:offset + 0xDC])[0]
                if training_status == 0 and bond_raw == 0:
                    return None  # truly empty — no hash, no training, no bond
            creation_hash = farm_hash
        else:
            creation_hash = struct.unpack('<I', d[offset + 0x148:offset + 0x14C])[0]

        # Evolution history — stored most-recent-first, reverse for display
        evo_history = []
        for x in (0x108, 0x10C, 0x110, 0x114, 0x118):
            prev_id = struct.unpack('<I', d[offset + x:offset + x + 4])[0]
            if prev_id > 0:
                prev_info = id_to_info.get(prev_id)
                if prev_info:
                    evo_history.append(prev_info["name"])
                else:
                    break
            else:
                break
        evo_history.reverse()  # oldest first for chronological display

        nickname = entry_name if entry_name != info["name"] else None

        return {
            "_offset": offset,
            "db_id": db_id,
            "species": info["name"],
            "nickname": nickname,
            "display_name": entry_name,
            "stage": info.get("stage", ""),
            "attribute": info.get("attribute", ""),
            "type": info.get("type", ""),
            "level": lv,
            "personality_id": pers_id,
            "personality": PERSONALITY_NAMES.get(pers_id, f"?({pers_id})"),
            "talent": talent,
            "bond": bond,
            "base": dict(zip(stat_names, base)),
            "white": dict(zip(stat_names, white)),
            "farm": dict(zip(stat_names, farm)),
            "blue": dict(zip(stat_names, blue)),
            "total": dict(zip(stat_names, total)),
            "evo_fwd_count": d[offset + 0xC8],
            "total_transforms": struct.unpack('<I', d[offset + 0x138:offset + 0x13C])[0],
            "creation_hash": creation_hash,
            "pers_skill_id": struct.unpack('<I', d[offset + 0xF8:offset + 0xFC])[0],
            "food_pref": d[offset + 0xCE],
            "exp": struct.unpack('<I', d[offset + 0x64:offset + 0x68])[0],
            "cur_hp": struct.unpack('<i', d[offset + 0x6C:offset + 0x70])[0],
            "cur_sp": struct.unpack('<i', d[offset + 0x70:offset + 0x74])[0],
            "equip_1": struct.unpack('<h', d[offset + 0x130:offset + 0x132])[0],
            "equip_2": struct.unpack('<h', d[offset + 0x132:offset + 0x134])[0],
            "attach_skills": [struct.unpack('<H', d[offset + 0x120 + s * 4:offset + 0x122 + s * 4])[0] for s in range(4)],
            "talent_acc": struct.unpack('<I', d[offset + 0xFC:offset + 0x100])[0],
            "location": region if region == "farm" else "box",
            "evo_history": evo_history,
            "farm_slot": struct.unpack('<I', d[offset + 0x148:offset + 0x14C])[0] if region == "farm" else None,
            "training_timer": struct.unpack('<d', d[offset + 0xD0:offset + 0xD8])[0] if region == "farm" else 0.0,
            "training_status": struct.unpack('<I', d[offset + 0xD8:offset + 0xDC])[0] if region == "farm" else 0,
            "training_set_id": struct.unpack('<I', d[offset + 0xE8:offset + 0xEC])[0] if region == "farm" else 0,
        }

    # ── Field writers ──

    def write_blue_stat(self, entry_offset, stat_index, value):
        """Write a blue stat value. stat_index: 0=HP, 1=SP, 2=ATK, etc."""
        offset = entry_offset + 0xAC + stat_index * 4
        self.write_i32(offset, value)

    def write_personality(self, entry_offset, pers_id):
        """Write personality ID (1-16)."""
        if not (1 <= pers_id <= 16):
            raise ValueError(f"Personality ID must be 1-16, got {pers_id}")
        self._data[entry_offset + 0xEE] = pers_id & 0xFF
        # Also update the packed personality at +0xEC
        struct.pack_into('<I', self._data, entry_offset + 0xEC, pers_id << 16)
        self._mark_dirty()

    def write_bond(self, entry_offset, bond_percent):
        """Write bond percentage (0-100)."""
        if not (0 <= bond_percent <= 100):
            raise ValueError(f"Bond must be 0-100, got {bond_percent}")
        bond_raw = float(bond_percent * 100)
        self.write_f32(entry_offset + 0x13C, bond_raw)

    def write_talent(self, entry_offset, talent):
        """Write talent value (0-200)."""
        if not (0 <= talent <= 200):
            raise ValueError(f"Talent must be 0-200, got {talent}")
        self.write_i32(entry_offset + 0x100, talent * 1000)

    def write_level(self, entry_offset, level):
        """Write level (1-99)."""
        if not (1 <= level <= 99):
            raise ValueError(f"Level must be 1-99, got {level}")
        self.write_i32(entry_offset + 0x60, level)

    def write_nickname(self, entry_offset, name):
        """Write a nickname (up to 30 chars ASCII). Pads with null bytes."""
        name_bytes = name.encode('ascii', errors='replace')[:30]
        # Clear the full 32-byte name field
        for i in range(32):
            self._data[entry_offset + i] = 0
        # Write the new name
        for i, b in enumerate(name_bytes):
            self._data[entry_offset + i] = b
        self._mark_dirty()

    def write_talent_acc(self, entry_offset, value):
        """Write the hidden talent accumulator* at +0xFC."""
        self.write_u32(entry_offset + 0xFC, value)

    def write_pers_skill(self, entry_offset, skill_id):
        """Write personality skill ID at +0xF8."""
        self.write_u32(entry_offset + 0xF8, skill_id)

    def write_food_pref(self, entry_offset, value):
        """Write food preference at +0xCE (0-5)."""
        if not (0 <= value <= 5):
            raise ValueError(f"Food preference must be 0-5, got {value}")
        self.write_u8(entry_offset + 0xCE, value)

    def write_white_stat(self, entry_offset, stat_index, value):
        """Write a white (growth) stat. stat_index: 0=HP, 1=SP, 2=ATK, etc."""
        offset = entry_offset + 0x74 + stat_index * 4
        self.write_i32(offset, value)

    def write_farm_stat(self, entry_offset, stat_index, value):
        """Write a farm training stat (stored x10). stat_index: 0=HP..."""
        offset = entry_offset + 0x90 + stat_index * 4
        self.write_i32(offset, value * 10)

    def write_exp(self, entry_offset, exp):
        """Write total EXP."""
        self.write_i32(entry_offset + 0x64, exp)

    def write_cur_hp(self, entry_offset, hp):
        """Write current HP."""
        self.write_i32(entry_offset + 0x6C, hp)

    def write_cur_sp(self, entry_offset, sp):
        """Write current SP."""
        self.write_i32(entry_offset + 0x70, sp)

    def write_evo_counter(self, entry_offset, count):
        """Write the evolution blue stat grant counter at +0xC8."""
        if not (0 <= count <= 100):
            raise ValueError(f"Evo counter must be 0-100, got {count}")
        self.write_u8(entry_offset + 0xC8, count)

    def write_attach_skill(self, entry_offset, slot_index, skill_id):
        """Write an attachment skill ID (slot 0-3)."""
        offset = entry_offset + 0x120 + slot_index * 4
        struct.pack_into('<H', self._data, offset, skill_id & 0xFFFF)
        self._mark_dirty()

    def write_equipment(self, entry_offset, slot_index, item_id):
        """Write an equipment item ID (slot 0-1)."""
        offset = entry_offset + 0x130 + slot_index * 2
        struct.pack_into('<H', self._data, offset, item_id & 0xFFFF)
        self._mark_dirty()

    # ── Species change ──

    def change_species(self, entry_offset, new_db_id):
        """Change a Digimon's species. Resets white stats, keeps blue/farm/bond."""
        name = get_digimon_name(new_db_id)
        # Write db_id at -0x04
        struct.pack_into('<I', self._data, entry_offset - 4, new_db_id)
        # Write db_id_copy at +0x104
        struct.pack_into('<I', self._data, entry_offset + 0x104, new_db_id)
        # Write new species name
        self.write_nickname(entry_offset, name)
        # Zero white stats (growth is species-dependent)
        for i in range(7):
            struct.pack_into('<i', self._data, entry_offset + 0x74 + i * 4, 0)
        # Reset current HP/SP to new base stats
        base = get_base_stats(new_db_id)
        struct.pack_into('<i', self._data, entry_offset + 0x6C, base[0])  # HP
        struct.pack_into('<i', self._data, entry_offset + 0x70, base[1])  # SP
        self._mark_dirty()

    # ── Clone ──

    def find_empty_slot(self):
        """Find the first empty box slot at the correct stride alignment.

        Uses the same dynamic base detection as read_roster to ensure
        the new entry will be found on the next scan.
        """
        d = self._data
        db = _get_db()
        valid_ids = set()
        for row in db.execute("SELECT id FROM digimon"):
            valid_ids.add(row["id"])

        pb_base = self._find_stride_base(0x001000, 0x009000, 0x150, valid_ids)

        if pb_base is None:
            return None  # stride detection failed — refuse to guess

        # Scan stride-aligned slots starting after party (skip first ~8)
        # Look for an empty slot (db_id == 0)
        for db_off in range(pb_base + 8 * 0x150, 0x053000, 0x150):
            name_off = db_off + 4
            db_id = struct.unpack('<I', d[db_off:db_off + 4])[0]
            if db_id == 0 and d[name_off:name_off + 4] == b'\x00\x00\x00\x00':
                return name_off  # return name offset (consistent with struct layout)
        return None

    def clone_digimon(self, source_offset):
        """Clone a Digimon to an empty box slot. Returns new offset or raises."""
        dest = self.find_empty_slot()
        if dest is None:
            raise RuntimeError("No empty roster slots available")

        # Copy 0x154 bytes (db_id at -4 through +0x14F)
        src_start = source_offset - 4
        dst_start = dest - 4
        length = 0x154
        self._data[dst_start:dst_start + length] = self._data[src_start:src_start + length]

        # New creation hash
        new_hash = random.randint(0x1000, 0xFFFFFFFF)
        struct.pack_into('<I', self._data, dest + 0x148, new_hash)

        # Unique talent accumulator — increment source by 1 for uniqueness*
        src_acc = struct.unpack('<I', self._data[source_offset + 0xFC:source_offset + 0x100])[0]
        struct.pack_into('<I', self._data, dest + 0xFC, src_acc + 1)

        # Reset evo counter
        self._data[dest + 0xC8] = 0

        # Put in box (not party)
        struct.pack_into('<I', self._data, dest + 0x11C, 0)

        # Set active flag
        struct.pack_into('<I', self._data, dest + 0x140, 1)

        # Clear next pointer (end of list)
        struct.pack_into('<I', self._data, dest + 0x14C, 0)

        self._mark_dirty()
        return dest

    # ── Create from scratch ──

    def create_digimon(self, db_id, level=1, personality_id=1):
        """Create a brand new Digimon in an empty box slot. Returns offset."""
        dest = self.find_empty_slot()
        if dest is None:
            raise RuntimeError("No empty roster slots available")

        info = get_digimon_info(db_id)
        if not info:
            raise ValueError(f"Unknown Digimon ID: {db_id}")
        base_stats = get_base_stats(db_id)
        growth_type = get_growth_type(db_id)
        growth = get_growth_stats(growth_type, level)

        # Clear the full struct area (db_id at -4 through +0x14F)
        for i in range(0x154):
            self._data[dest - 4 + i] = 0

        # db_id
        struct.pack_into('<I', self._data, dest - 4, db_id)
        # db_id copy
        struct.pack_into('<I', self._data, dest + 0x104, db_id)
        # Name
        self.write_nickname(dest, info["name"])
        # Level
        struct.pack_into('<i', self._data, dest + 0x60, level)
        # Personality
        self._data[dest + 0xEE] = personality_id & 0xFF
        struct.pack_into('<I', self._data, dest + 0xEC, personality_id << 16)
        # White stats (growth from leveling — 7 stats at +0x74)
        stat_names = ['hp', 'sp', 'atk', 'def', 'int', 'spi', 'spd']
        for i, val in enumerate(growth):
            struct.pack_into('<i', self._data, dest + 0x74 + i * 4, val)
        # Current HP/SP = base + growth
        struct.pack_into('<i', self._data, dest + 0x6C, base_stats[0] + growth[0])
        struct.pack_into('<i', self._data, dest + 0x70, base_stats[1] + growth[1])
        # Talent (reasonable starting value: 50, stored ×1000)
        struct.pack_into('<i', self._data, dest + 0x100, 50 * 1000)
        # Bond (100% = 10000 stored as float ×100)
        struct.pack_into('<f', self._data, dest + 0x13C, 100.0)
        # Creation hash
        new_hash = random.randint(0x1000, 0xFFFFFFFF)
        struct.pack_into('<I', self._data, dest + 0x148, new_hash)
        # Talent accumulator — find max for this species and add 1 for uniqueness
        roster = self.read_roster()
        max_acc = 0
        for e in roster:
            if e["db_id"] == db_id:
                max_acc = max(max_acc, e.get("talent_acc", 0))
        struct.pack_into('<I', self._data, dest + 0xFC, max_acc + 1)
        # EXP for level — use this species' actual curve
        exp = get_exp_for_level(level, db_id=db_id)
        struct.pack_into('<I', self._data, dest + 0x64, exp)
        # Box (not party)
        struct.pack_into('<I', self._data, dest + 0x11C, 0)
        # Active
        struct.pack_into('<I', self._data, dest + 0x140, 1)

        self._mark_dirty()
        return dest

    # ── Export/Import ──

    def export_digimon(self, entry_offset):
        """Export a Digimon as a JSON-serializable dict."""
        d = self._data
        raw = d[entry_offset - 4:entry_offset + 0x150]
        raw_b64 = base64.b64encode(bytes(raw)).decode('ascii')

        db_id = struct.unpack('<I', d[entry_offset - 4:entry_offset])[0]
        name_end = d.find(b'\x00', entry_offset, entry_offset + 32)
        display_name = d[entry_offset:name_end].decode('ascii', errors='replace')

        return {
            "format_version": 2,
            "editor_version": VERSION,
            "species": get_digimon_name(db_id),
            "db_id": db_id,
            "display_name": display_name,
            "level": struct.unpack('<i', d[entry_offset + 0x60:entry_offset + 0x64])[0],
            "personality_id": d[entry_offset + 0xEE],
            "personality": PERSONALITY_NAMES.get(d[entry_offset + 0xEE], "?"),
            "talent": struct.unpack('<i', d[entry_offset + 0x100:entry_offset + 0x104])[0] // 1000,
            "evo_fwd_count": d[entry_offset + 0xC8],
            "raw_b64": raw_b64,
        }

    def import_digimon(self, digi_data):
        """Import a Digimon from an exported dict. Returns new offset or raises."""
        dest = self.find_empty_slot()
        if dest is None:
            raise RuntimeError("No empty roster slots available")

        # Accept both format_version 1 ("raw_hex") and 2 ("raw_b64")
        raw_key = "raw_b64" if "raw_b64" in digi_data else "raw_hex"
        raw = base64.b64decode(digi_data[raw_key])
        if len(raw) != 0x154:
            raise ValueError(f"Invalid raw data size: {len(raw)} (expected {0x154})")

        # Verify db_id matches
        raw_db_id = struct.unpack('<I', raw[0:4])[0]
        if raw_db_id != digi_data.get("db_id"):
            raise ValueError("db_id mismatch between raw data and metadata")

        # Verify species exists
        info = get_digimon_info(raw_db_id)
        if not info:
            raise ValueError(f"Unknown Digimon ID: {raw_db_id}")

        # Write to empty slot
        dst_start = dest - 4
        self._data[dst_start:dst_start + 0x154] = raw

        # New creation hash
        new_hash = random.randint(0x1000, 0xFFFFFFFF)
        struct.pack_into('<I', self._data, dest + 0x148, new_hash)

        # Reset evo counter
        self._data[dest + 0xC8] = 0

        # Box, not party
        struct.pack_into('<I', self._data, dest + 0x11C, 0)
        struct.pack_into('<I', self._data, dest + 0x140, 1)
        struct.pack_into('<I', self._data, dest + 0x14C, 0)

        self._mark_dirty()
        return dest

    # ── Scan table access ──

    def read_scan_entry(self, table_index):
        """Read a scan table entry. Returns (digi_id, scan_pct)."""
        off = SCAN_TABLE_OFFSET + table_index * SCAN_TABLE_STRIDE
        digi_id = struct.unpack('<H', self._data[off:off + 2])[0]
        scan_pct = struct.unpack('<H', self._data[off + 2:off + 4])[0]
        return digi_id, scan_pct

    def write_scan_pct(self, table_index, pct):
        """Write a scan percentage (0-200) at the given table index."""
        off = SCAN_TABLE_OFFSET + table_index * SCAN_TABLE_STRIDE + 2
        struct.pack_into('<H', self._data, off, pct)
        self._mark_dirty()

    def scan_summary(self):
        """Return (scanned_count, full_count) for the scan table."""
        db = _get_db()
        valid_ids = set()
        for row in db.execute("SELECT id FROM digimon"):
            valid_ids.add(row["id"])
        if _mod_overlay and _mod_overlay.is_active:
            valid_ids.update(_mod_overlay.new_digimon.keys())
        scan_count = 0
        scan_100 = 0
        for i in range(SCAN_TABLE_REAL_START, 583):
            digi_id, pct = self.read_scan_entry(i)
            if digi_id > 0 and digi_id in valid_ids and 0 < pct <= 200:
                scan_count += 1
                if pct >= 100:
                    scan_100 += 1
        return scan_count, scan_100

    # ── Inventory access ──

    def read_inventory(self):
        """Read all inventory slots. Returns list of dicts for occupied slots.

        Each dict: {slot_index, item_id, quantity, flags, flags2, timestamp, name}
        """
        from save_layout import INVENTORY_OFFSET, INVENTORY_STRIDE, INVENTORY_SLOTS
        d = self._data
        items = []
        for i in range(INVENTORY_SLOTS):
            off = INVENTORY_OFFSET + i * INVENTORY_STRIDE
            if off + INVENTORY_STRIDE > len(d):
                break
            item_id = struct.unpack_from('<I', d, off + 4)[0]
            if item_id == 0:
                continue
            items.append({
                'slot_index': struct.unpack_from('<I', d, off)[0],
                'item_id': item_id,
                'quantity': struct.unpack_from('<I', d, off + 8)[0],
                'flags': struct.unpack_from('<I', d, off + 12)[0],
                'flags2': struct.unpack_from('<I', d, off + 16)[0],
                'timestamp': struct.unpack_from('<I', d, off + 20)[0],
                '_inv_offset': off,
                'name': get_item_name(item_id),
            })
        return items

    def write_item_quantity(self, inv_offset, quantity):
        """Write quantity for an existing inventory slot."""
        if quantity < 0 or quantity > 999:
            raise ValueError(f"Quantity must be 0-999, got {quantity}")
        struct.pack_into('<I', self._data, inv_offset + 8, quantity)
        if quantity >= 1 and self._data[inv_offset + 20] == 0:
            self._data[inv_offset + 20] = 1
        # Heal ALL invalid markers so the game reads the full inventory
        self._heal_valid_markers()
        self._mark_dirty()

    def _heal_valid_markers(self):
        """Ensure every inventory slot with an item has valid_marker byte0=1.

        The game reads inventory sequentially and stops at the first slot
        where byte0=0. Any item with byte0=0 would act as a premature
        stop point, hiding everything after it. This fixes all of them.
        """
        from save_layout import INVENTORY_OFFSET, INVENTORY_STRIDE, INVENTORY_SLOTS
        d = self._data
        fixed = 0
        for i in range(INVENTORY_SLOTS):
            off = INVENTORY_OFFSET + i * INVENTORY_STRIDE
            if off + INVENTORY_STRIDE > len(d):
                break
            item_id = struct.unpack_from('<I', d, off + 4)[0]
            if item_id > 0 and d[off + 20] == 0:
                d[off + 20] = 1
                fixed += 1
        if fixed > 0:
            self._mark_dirty()
            logger.info("Healed %d inventory valid markers", fixed)

    def add_item(self, item_id, quantity=1):
        """Add a new item to the first empty inventory slot.

        If the item already exists, adds to its quantity instead.
        Also heals any invalid markers on prior slots so the game
        reads the full inventory.
        Returns the inventory offset of the slot, or None if inventory full.
        """
        from save_layout import INVENTORY_OFFSET, INVENTORY_STRIDE, INVENTORY_SLOTS
        d = self._data

        # First check if item already in inventory
        for i in range(INVENTORY_SLOTS):
            off = INVENTORY_OFFSET + i * INVENTORY_STRIDE
            if off + INVENTORY_STRIDE > len(d):
                break
            existing_id = struct.unpack_from('<I', d, off + 4)[0]
            if existing_id == item_id:
                # Item exists — add to quantity
                old_qty = struct.unpack_from('<I', d, off + 8)[0]
                new_qty = min(old_qty + quantity, 999)
                struct.pack_into('<I', self._data, off + 8, new_qty)
                if d[off + 20] == 0:
                    d[off + 20] = 1
                self._heal_valid_markers()
                self._mark_dirty()
                return off
            if existing_id == 0:
                # Empty slot — write new item here
                struct.pack_into('<I', self._data, off + 4, item_id)
                struct.pack_into('<I', self._data, off + 8, min(quantity, 999))
                struct.pack_into('<I', self._data, off + 12, 0)  # equipped
                struct.pack_into('<I', self._data, off + 16, 0)  # card_flag
                struct.pack_into('<I', self._data, off + 20, 1)  # valid_marker
                self._heal_valid_markers()
                self._mark_dirty()
                return off

    def remove_item(self, inv_offset):
        """Remove an item from inventory by zeroing its slot."""
        struct.pack_into('<I', self._data, inv_offset + 4, 0)   # item_id
        struct.pack_into('<I', self._data, inv_offset + 8, 0)   # quantity
        struct.pack_into('<I', self._data, inv_offset + 12, 0)  # equipped
        struct.pack_into('<I', self._data, inv_offset + 16, 0)  # card_flag
        # Leave valid_marker as-is (byte0=1) so it doesn't become a
        # premature sentinel that would hide items after it
        self._mark_dirty()

    # ── Agent data access ──

    def read_agent_u32(self, relative_offset):
        """Read a uint32 at AGENT_BASE_OFFSET + relative_offset."""
        off = AGENT_BASE_OFFSET + relative_offset
        return struct.unpack('<I', self._data[off:off + 4])[0]

    def write_player_name(self, name):
        """Write player name to agent struct (+0x10) and header CSV."""
        name_bytes = name.encode('ascii', errors='replace')[:30]
        # Write to agent struct at absolute 0x0FDE90 (agent_base + 0x10)
        off = AGENT_BASE_OFFSET + 0x10
        for i in range(32):
            self._data[off + i] = 0
        for i, b in enumerate(name_bytes):
            self._data[off + i] = b
        # Update header CSV (plaintext, field index 4)
        header_end = self._data.find(b'\x00')
        if header_end > 0:
            header = self._data[:header_end].decode('ascii', errors='replace')
            fields = header.split(',')
            if len(fields) > 4:
                fields[4] = f' {name} '
                new_header = ','.join(fields).encode('ascii', errors='replace')
                # Pad or truncate to same length
                if len(new_header) <= header_end:
                    for i in range(header_end):
                        self._data[i] = 0
                    for i, b in enumerate(new_header):
                        self._data[i] = b
        self._mark_dirty()

    def write_agent_u32(self, relative_offset, value):
        """Write a uint32 at AGENT_BASE_OFFSET + relative_offset."""
        off = AGENT_BASE_OFFSET + relative_offset
        struct.pack_into('<I', self._data, off, value)
        self._mark_dirty()

    def read_agent_skill(self, skill_index):
        """Read agent skill record. Returns (tree_group, category, purchased, visible)."""
        off = AGENT_BASE_OFFSET + AGENT_SKILL_OFFSET + skill_index * AGENT_SKILL_STRIDE
        tree_group = struct.unpack('<I', self._data[off:off + 4])[0]
        category = struct.unpack('<I', self._data[off + 4:off + 8])[0]
        purchased = self._data[off + 8]
        visible = self._data[off + 9]
        return tree_group, category, purchased, visible

    def write_agent_skill_flags(self, skill_index, purchased, visible, unknown=None):
        """Write purchased, visible, and optionally unknown flags for an agent skill."""
        off = AGENT_BASE_OFFSET + AGENT_SKILL_OFFSET + skill_index * AGENT_SKILL_STRIDE
        self._data[off + 8] = purchased
        self._data[off + 9] = visible
        if unknown is not None:
            self._data[off + 10] = unknown
        self._mark_dirty()

    # Category ID → count offset (relative to agent base)
    _CAT_COUNT_OFFSETS = {1: 0x068, 2: 0x06C, 3: 0x070, 4: 0x074, 5: 0x080}

    def buy_agent_skill(self, skill_index):
        """Buy a skill: set flags, subtract TP cost, increment category count.

        Returns True on success, False if insufficient TP or already purchased.
        """
        _, cat, purchased, _ = self.read_agent_skill(skill_index)
        if purchased:
            return False
        catalog = get_tamer_skill_catalog()
        cost = catalog[skill_index]['tp_cost']
        tp_avail = self.read_agent_u32(0x05C)
        if tp_avail < cost:
            return False
        # Set all three flags to match natural purchased state
        self.write_agent_skill_flags(skill_index, 1, 1, 1)
        self.write_agent_u32(0x05C, tp_avail - cost)
        # Increment category count
        if cat in self._CAT_COUNT_OFFSETS:
            old = self.read_agent_u32(self._CAT_COUNT_OFFSETS[cat])
            self.write_agent_u32(self._CAT_COUNT_OFFSETS[cat], old + 1)
        return True

    def refund_agent_skill(self, skill_index):
        """Refund a skill: clear purchased flag, return TP cost, decrement category count.

        Leaves visible and unknown flags untouched so the skill stays in the game tree.
        Returns True on success, False if not purchased.
        """
        off = AGENT_BASE_OFFSET + AGENT_SKILL_OFFSET + skill_index * AGENT_SKILL_STRIDE
        cat = struct.unpack('<I', self._data[off + 4:off + 8])[0]
        purchased = self._data[off + 8]
        if not purchased:
            return False
        catalog = get_tamer_skill_catalog()
        cost = catalog[skill_index]['tp_cost']
        # Only clear purchased — leave visible and unknown as-is
        self._data[off + 8] = 0
        self._mark_dirty()
        # Return TP
        tp_avail = self.read_agent_u32(0x05C)
        self.write_agent_u32(0x05C, tp_avail + cost)
        # Decrement category count
        if cat in self._CAT_COUNT_OFFSETS:
            old = self.read_agent_u32(self._CAT_COUNT_OFFSETS[cat])
            if old > 0:
                self.write_agent_u32(self._CAT_COUNT_OFFSETS[cat], old - 1)
        return True

    # ── Save to disk ──

    def _fix_duplicate_talent_acc(self):
        """Ensure no two Digimon of the same species share a talent accumulator*.

        The game requires unique (db_id, talent_acc) pairs. When duplicates
        exist (e.g., from cloning or creating multiple of the same species),
        auto-increment the accumulator on duplicates by +1 each.
        """
        roster = self.read_roster()
        by_species = {}
        for entry in roster:
            by_species.setdefault(entry["db_id"], []).append(entry)

        for db_id, entries in by_species.items():
            if len(entries) < 2:
                continue
            seen = set()
            for entry in entries:
                acc = entry["talent_acc"]
                if acc in seen:
                    while acc in seen:
                        acc += 1
                    self.write_talent_acc(entry["_offset"], acc)
                    logger.info("Fixed duplicate talent_acc for %s at 0x%X: set to %d",
                                entry["species"], entry["_offset"], acc)
                seen.add(acc)

    def save(self, backup=True, max_backups=2):
        """Encrypt and write back to disk. Creates a timestamped backup first.

        Keeps only the most recent max_backups auto-generated backups per slot
        to avoid filling the disk.
        """
        # Fix duplicate game ticks before writing
        self._fix_duplicate_talent_acc()

        if backup and os.path.exists(self.path):
            backup_dir = os.path.join(os.path.dirname(self.path), 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            basename = os.path.basename(self.path)
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = os.path.join(backup_dir, f"{basename}.{ts}.bak")
            shutil.copy2(self.path, backup_path)

            # Prune old auto-backups for this slot, keep only the newest
            existing = sorted(
                [f for f in os.listdir(backup_dir)
                 if f.startswith(basename) and f.endswith('.bak')],
                reverse=True)  # newest first
            for old in existing[max_backups:]:
                try:
                    os.remove(os.path.join(backup_dir, old))
                except Exception:
                    pass

        encrypted = save_crypto.encrypt(bytes(self._data))
        with open(self.path, 'wb') as f:
            f.write(encrypted)
        self._dirty = False
