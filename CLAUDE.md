# ANAMNESIS Save Editor — Digimon Story: Time Stranger

## Project Overview
Standalone PyQt6 save file editor for Digimon Story: Time Stranger.
First save editor for this game — no other tool exists.
**Branded as ANAMNESIS Save Editor** — shares name/aesthetic with the ANAMNESIS Companion App but is a separate standalone tool.

- **Location:** `C:\Users\apham\DigimonSaveEditor\`
- **Repo:** TBD (will be created on GitHub)
- **Companion project:** ANAMNESIS (`C:\Users\apham\DigimonCompanion\`) — overlay app that discovered the save file structure
- **Framework:** PyQt6 (same as ANAMNESIS for consistency)
- **Python:** 3.11+

## Critical Rules

### Commit Early and Frequently
- **Commit after every meaningful change** — new feature, bug fix, refactor, even partial progress
- Never let more than 30 minutes of work go uncommitted
- Use descriptive commit messages that explain WHY, not just what
- Tag releases (v0.1.0, v0.2.0, etc.) at each milestone

### Always Back Up Before Writing
- The `SaveFile.save()` method MUST create a timestamped backup before overwriting
- Never write to the original save without a backup existing
- Backup directory: `{save_dir}/backups/` (inside the game's save folder)

### Don't Break the Game
- Only modify fields we have verified through save-diff analysis
- Never write to unknown/unverified byte ranges
- Validate all values before writing (e.g., personality 1-16, level 1-99)
- The save file is AES-128-ECB encrypted — must encrypt after modification

## Architecture

### File Structure
```
DigimonSaveEditor/
├── CLAUDE.md              # This file — project rules and context
├── save_editor.py         # Main app entry point + PyQt6 UI
├── save_crypto.py         # AES-128-ECB encrypt/decrypt
├── save_data.py           # Save file model — reads/writes structured data
├── save_layout.py         # Complete save file structure (from ANAMNESIS)
├── data/
│   ├── anamnesis.db       # Digimon database (names, stats, skills, items)
│   └── icons/             # 475 Digimon portrait PNGs (256x256)
└── .gitignore
```

### Key Modules
- **`save_crypto.py`** — AES key: `33393632373736373534353535383833`, ECB mode, fixed 3,098,176-byte files
- **`save_data.py`** — `SaveFile` class wraps decrypted bytearray, provides typed read/write for all known fields, handles roster parsing with dedup
- **`save_layout.py`** — Single source of truth for every mapped byte in the save file. 30 regions, 75 Digimon struct fields. Imported from ANAMNESIS.

### Save File Structure (Summary)
- **Total size:** 3,098,176 bytes (encrypted), same decrypted
- **Encryption:** AES-128-ECB with fixed key
- **ANSE watermark:** 0x000904-0x001000 (1,788 bytes safe padding — game never touches, confirmed 3 resave cycles). Format: `ANSE|version|uuid`
- **Digimon roster:** Party+box at 0x001000 (stride 0x150), farm at 0x053000 (stride 0x158)
- **Scan table:** 583 entries at 0x05C100, stride 4 (Int16 digi_id + Int16 scan_pct)
- **Agent info:** At 0x0FDE80 — rank, money, TP, skill counts
- **Discovery table:** At 0x078000 — 432 flag/id pairs
- **Per-Digimon padding:** +0x20 to +0x5F (64 bytes zeros per Digimon, potential UUID storage — NOT YET TESTED)

### Digimon Compact Struct (0x150 bytes, relative to name start)
| Offset | Size | Field |
|--------|------|-------|
| -0x04 | u32 | db_id (species) |
| +0x00 | str | Name/nickname (32 bytes) |
| +0x60 | i32 | Level |
| +0x64 | i32 | Total EXP |
| +0x6C | i32 | Current HP |
| +0x70 | i32 | Current SP |
| +0x74 | 7×i32 | White stats (growth + personality) |
| +0x90 | 7×i32 | Farm training stats (stored ×10) |
| +0xAC | 7×i32 | Blue stats (evolution bonuses) |
| +0xC8 | u8 | Evo blue stat grant counter |
| +0xEE | u8 | Personality ID (1-16) |
| +0x100 | i32 | Talent (stored ×1000) |
| +0x108 | 5×u32 | Evolution history (previous form IDs) |
| +0x120 | 4×(u16+u16) | Attachment skills |
| +0x130 | 2×u16 | Equipment slots |
| +0x13C | f32 | Bond (stored ×100) |
| +0x148 | u32 | Creation hash (box/party) |
| +0x150 | u32 | Creation hash (farm — +0x148 is slot index) |

### Verified Formulas
- **Blue stat gain (evo):** `floor(white_growth / 10)` — requires bond > 0%, tracked by +0xC8 counter
- **Blue stat gain (Load Enhancement):** `5% fodder growth + 50% fodder blue` — unlimited, no counter
- **Stat display:** `floor(stat × (1 + agent_boost% + perfection%)) + loyalty_flat + equipment`

## Editable Fields (Verified Safe)
These fields have been verified through save-diffs and can be safely modified:
- Blue stats (+0xAC-0xC4) — 7 stat values
- Personality (+0xEE) — 1-16
- Bond (+0x13C) — float, stored ×100
- Talent (+0x100) — stored ×1000
- Level (+0x60) — 1-99
- Evo counter (+0xC8) — 0-255 (reset to 0 for unlimited blue gains)
- Scan percentages (scan table) — 0-200 per Digimon
- Money (agent base + 0x58)
- Tamer Points (agent base + 0x60)

## UI Design Goals
- Clean, dark theme matching ANAMNESIS aesthetic
- Left panel: save slot selector + Digimon roster list with icons
- Right panel: selected Digimon detail editor with all editable fields
- Toolbar: load, save, undo, backup status
- Status bar: shows backup path after save, dirty indicator

## Dependencies
- PyQt6
- pycryptodome (for AES)
- sqlite3 (stdlib)
