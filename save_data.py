"""Save file data access layer.

Reads and writes structured data from decrypted save files using
the field definitions in save_layout.py. All reads/writes operate
on an in-memory bytearray — call save() to write back to disk.
"""

import os
import glob
import shutil
import struct
import random
import sqlite3
import base64
import json
import subprocess
from datetime import datetime

import save_crypto
from save_layout import DIGI, REGIONS, AGENT, PERSONALITY_NAMES
from app_paths import get_db_path


# ── Database lookups ────────────────────────────────────────────────

_db_conn = None


def _get_db():
    global _db_conn
    if _db_conn is None:
        _db_conn = sqlite3.connect(get_db_path())
        _db_conn.row_factory = sqlite3.Row
    return _db_conn


def get_digimon_name(db_id):
    """Look up Digimon species name by database ID."""
    row = _get_db().execute(
        "SELECT name FROM digimon WHERE id = ?", (db_id,)
    ).fetchone()
    return row["name"] if row else f"Unknown({db_id})"


def get_digimon_info(db_id):
    """Look up Digimon name, stage, attribute, type by database ID."""
    row = _get_db().execute(
        "SELECT name, stage, attribute, type FROM digimon WHERE id = ?", (db_id,)
    ).fetchone()
    if row:
        return dict(row)
    return None


def get_base_stats(db_id):
    """Look up base stats (level 1) for a Digimon."""
    row = _get_db().execute(
        "SELECT hp, sp, atk, def_, int_, spi, spd FROM stats_base WHERE digimon_id = ?",
        (db_id,)
    ).fetchone()
    return list(row) if row else [0] * 7


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
    except Exception:
        return False


def get_item_name(item_id):
    """Look up item name by ID."""
    row = _get_db().execute(
        "SELECT name FROM item_names WHERE item_id = ?", (str(item_id),)
    ).fetchone()
    return row["name"] if row and row["name"] else f"Item #{item_id}"


# ── Save file discovery ────────────────────────────────────────────

def find_save_directory():
    """Find the game's save directory. Returns path or None."""
    steam_base = os.path.join(
        os.environ.get('ProgramFiles(x86)', ''),
        'Steam', 'steamapps', 'common',
        'Digimon Story Time Stranger', 'gamedata', 'savedata'
    )
    if os.path.isdir(steam_base):
        # Find the Steam user ID subdirectory
        subdirs = [d for d in os.listdir(steam_base)
                   if os.path.isdir(os.path.join(steam_base, d)) and d.isdigit()]
        if subdirs:
            return os.path.join(steam_base, subdirs[0])
    return None


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


# ── Save file model ────────────────────────────────────────────────

class SaveFile:
    """Represents a loaded save file with read/write access to all fields."""

    def __init__(self, path):
        self.path = path
        with open(path, 'rb') as f:
            raw = f.read()
        self._data = bytearray(save_crypto.decrypt(raw))
        self._dirty = False

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

    # ── Roster parsing ──

    def read_roster(self):
        """Read all Digimon entries from the save file.

        Returns list of dicts with all parsed fields.
        """
        results = []
        d = self._data
        stat_names = ['hp', 'sp', 'atk', 'def', 'int', 'spi', 'spd']

        # Pre-build lookup of all valid Digimon IDs (avoids per-offset DB queries)
        db = _get_db()
        id_to_info = {}
        for row in db.execute("SELECT id, name, stage, attribute, type FROM digimon"):
            id_to_info[row["id"]] = dict(row)
        base_stats_cache = {}
        for row in db.execute("SELECT digimon_id, hp, sp, atk, def_, int_, spi, spd FROM stats_base"):
            base_stats_cache[row["digimon_id"]] = [row["hp"], row["sp"], row["atk"],
                                                     row["def_"], row["int_"],
                                                     row["spi"], row["spd"]]

        # Scan only known roster regions at correct strides
        # Party+box: db_id at 0x001024, stride 0x150 (36-byte header in region)
        # Farm:      db_id at 0x053074, stride 0x158 (116-byte header in region)
        # Name field is always db_id + 4
        scan_offsets = []
        for db_off in range(0x001024, 0x053000, 0x150):
            scan_offsets.append((db_off + 4, "party_box"))
        for db_off in range(0x053074, 0x05C000, 0x158):
            scan_offsets.append((db_off + 4, "farm"))

        for offset, region in scan_offsets:
            db_id = struct.unpack('<I', d[offset - 4:offset])[0]
            info = id_to_info.get(db_id)
            if not info:
                continue

            name_end = d.find(b'\x00', offset, offset + 32)
            if name_end <= offset:
                continue
            try:
                entry_name = d[offset:name_end].decode('ascii')
            except (UnicodeDecodeError, ValueError):
                continue
            if not entry_name or len(entry_name) < 2:
                continue

            lv = struct.unpack('<i', d[offset + 0x60:offset + 0x64])[0]
            if not (1 <= lv <= 99):
                continue

            pers_id = d[offset + 0xEE]
            if pers_id < 1 or pers_id > 16:
                continue

            # Read all stat layers
            white = [struct.unpack('<i', d[offset + 0x74 + i * 4:offset + 0x78 + i * 4])[0] for i in range(7)]
            farm = [struct.unpack('<i', d[offset + 0x90 + i * 4:offset + 0x94 + i * 4])[0] // 10 for i in range(7)]
            blue = [struct.unpack('<i', d[offset + 0xAC + i * 4:offset + 0xB0 + i * 4])[0] for i in range(7)]
            base = base_stats_cache.get(db_id, [0] * 7)
            total = [base[i] + white[i] + farm[i] + blue[i] for i in range(7)]

            # Additional fields
            talent_raw = struct.unpack('<i', d[offset + 0x100:offset + 0x104])[0]
            talent = talent_raw // 1000 if talent_raw > 0 else 0
            bond_raw = struct.unpack('<f', d[offset + 0x13C:offset + 0x140])[0]
            bond = round(bond_raw) // 100 if bond_raw > 0 else 0

            # Creation hash — box/party at +0x148, farm at +0x150
            creation_hash = struct.unpack('<I', d[offset + 0x148:offset + 0x14C])[0]
            if creation_hash < 0x100 and offset + 0x154 <= len(d):
                farm_hash = struct.unpack('<I', d[offset + 0x150:offset + 0x154])[0]
                if farm_hash > 0x100:
                    creation_hash = farm_hash

            exp = struct.unpack('<I', d[offset + 0x64:offset + 0x68])[0]
            cur_hp = struct.unpack('<i', d[offset + 0x6C:offset + 0x70])[0]
            cur_sp = struct.unpack('<i', d[offset + 0x70:offset + 0x74])[0]
            evo_fwd = d[offset + 0xC8]
            total_transforms = struct.unpack('<I', d[offset + 0x138:offset + 0x13C])[0]
            equip_1 = struct.unpack('<h', d[offset + 0x130:offset + 0x132])[0]
            equip_2 = struct.unpack('<h', d[offset + 0x132:offset + 0x134])[0]

            # Attachment skills (4 slots, each u16 skill + u16 padding)
            attach_skills = []
            for slot in range(4):
                sid = struct.unpack('<H', d[offset + 0x120 + slot * 4:offset + 0x122 + slot * 4])[0]
                attach_skills.append(sid)

            nickname = entry_name if entry_name != info["name"] else None

            # Determine location (party vs box vs farm)
            if region == "farm":
                location = "farm"
            else:
                active_flag = struct.unpack('<I', d[offset + 0x11C:offset + 0x120])[0]
                location = "party" if active_flag == 1 else "box"

            # Evolution history
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

            entry = {
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
                "evo_fwd_count": evo_fwd,
                "total_transforms": total_transforms,
                "creation_hash": creation_hash,
                "exp": exp,
                "cur_hp": cur_hp,
                "cur_sp": cur_sp,
                "equip_1": equip_1,
                "equip_2": equip_2,
                "attach_skills": attach_skills,
                "location": location,
                "evo_history": evo_history,
            }
            results.append(entry)

        # Dedup by (creation_hash, species) — only merge true duplicates,
        # not different Digimon that happen to share a hash
        seen = {}
        deduped = []
        for entry in results:
            h = entry["creation_hash"]
            key = (h, entry["db_id"])
            if h and h > 0x10:
                if key in seen:
                    prev = seen[key]
                    prev_total = sum(prev["total"].values())
                    cur_total = sum(entry["total"].values())
                    if cur_total > prev_total:
                        deduped[deduped.index(prev)] = entry
                        seen[key] = entry
                else:
                    seen[key] = entry
                    deduped.append(entry)
            else:
                deduped.append(entry)

        return deduped

    # ── Field writers ──

    def write_blue_stat(self, entry_offset, stat_index, value):
        """Write a blue stat value. stat_index: 0=HP, 1=SP, 2=ATK, etc."""
        offset = entry_offset + 0xAC + stat_index * 4
        self.write_i32(offset, value)

    def write_personality(self, entry_offset, pers_id):
        """Write personality ID (1-16)."""
        self._data[entry_offset + 0xEE] = pers_id & 0xFF
        # Also update the packed personality at +0xEC
        struct.pack_into('<I', self._data, entry_offset + 0xEC, pers_id << 16)
        self._mark_dirty()

    def write_bond(self, entry_offset, bond_percent):
        """Write bond percentage (0-100)."""
        bond_raw = float(bond_percent * 100)
        self.write_f32(entry_offset + 0x13C, bond_raw)

    def write_talent(self, entry_offset, talent):
        """Write talent value (0-200)."""
        self.write_i32(entry_offset + 0x100, talent * 1000)

    def write_level(self, entry_offset, level):
        """Write level (1-99)."""
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
        """Find the first empty slot in the box region. Returns offset or None."""
        d = self._data
        # Box empty region: 0x009000-0x053000, stride 0x150
        for offset in range(0x009004, 0x053000, 0x150):
            # Check if db_id is 0 and name field is null
            db_id = struct.unpack('<I', d[offset - 4:offset])[0]
            if db_id == 0:
                # Verify name is empty too
                if d[offset:offset + 4] == b'\x00\x00\x00\x00':
                    return offset
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
            "format_version": 1,
            "editor_version": "0.1.0",
            "species": get_digimon_name(db_id),
            "db_id": db_id,
            "display_name": display_name,
            "level": struct.unpack('<i', d[entry_offset + 0x60:entry_offset + 0x64])[0],
            "personality_id": d[entry_offset + 0xEE],
            "personality": PERSONALITY_NAMES.get(d[entry_offset + 0xEE], "?"),
            "talent": struct.unpack('<i', d[entry_offset + 0x100:entry_offset + 0x104])[0] // 1000,
            "evo_fwd_count": d[entry_offset + 0xC8],
            "raw_hex": raw_b64,
        }

    def import_digimon(self, digi_data):
        """Import a Digimon from an exported dict. Returns new offset or raises."""
        dest = self.find_empty_slot()
        if dest is None:
            raise RuntimeError("No empty roster slots available")

        raw = base64.b64decode(digi_data["raw_hex"])
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

    # ── Save to disk ──

    def save(self, backup=True):
        """Encrypt and write back to disk. Creates a timestamped backup first."""
        if backup:
            backup_dir = os.path.join(os.path.dirname(self.path), 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            basename = os.path.basename(self.path)
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = os.path.join(backup_dir, f"{basename}.{ts}.bak")
            shutil.copy2(self.path, backup_path)

        encrypted = save_crypto.encrypt(bytes(self._data))
        with open(self.path, 'wb') as f:
            f.write(encrypted)
        self._dirty = False
