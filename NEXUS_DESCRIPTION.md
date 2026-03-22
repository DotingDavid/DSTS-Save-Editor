# ANAMNESIS SE — Save Editor for Digimon Story: Time Stranger

The first and only save editor for DSTS. View and edit your Digimon, stats, scans, money, and more — all through a clean dark-themed GUI with full Digimon portrait icons.

Built by reverse-engineering the game's encrypted save file format from scratch. Part of the ANAMNESIS project.

---

## Features

**Digimon Editing**
- View your full roster — party, box, and farm — with accurate counts matching the game
- Edit blue, white, and farm stats (capped at 9999 per layer)
- Edit level, EXP, talent, bond, personality, current HP/SP
- Reset evolution counter for unlimited blue stat gains from evolution
- Change species (resets growth stats, keeps blue/farm/bond/equipment)
- Edit attachment skills (4 slots) and equipment (2 slots)
- Set nicknames

**Roster Tools**
- PKHeX-style icon grid with all 475 Digimon portraits
- Clone any Digimon to an empty box slot
- Create new Digimon from scratch (pick species, level, personality)
- Export/import individual Digimon as .digi files (share with friends)
- Search, sort by name/level/stage/personality, filter by party/box/farm

**Scan Table**
- View and edit scan percentages for all species
- Batch set: set all scans to 100% or 200% with one click

**Agent / Player Data**
- Edit money and Tamer Points
- View and unlock agent skill trees (Valor, Philanthropy, Amicability, Wisdom, Loyalty)

**Batch Operations**
- Set bond to 100% on all Digimon
- Set talent on all Digimon
- Set blue stats on all Digimon
- Reset all evolution counters

**File Management**
- Multi-account support (auto-detects all Steam save directories)
- Backup, copy, swap, export, and import save slots
- Automatic backup before every save (keeps 2 most recent per slot)
- Save As to a new file
- Game-running detection with warning

---

## Installation

1. Download `ANAMNESIS_SE.exe` from the Files tab
2. Place it anywhere — no installation needed
3. Run it. Your save directory is auto-detected from Steam.

**Note:** Windows SmartScreen or your browser may flag the download because the executable is unsigned. This is a false positive common to all PyInstaller-built applications. The source code is available for review.

---

## Important Disclaimers

**Back up your saves.** The editor creates automatic backups before every save, but you should also keep your own manual backups of important save files. Backups are stored in `{your save directory}/backups/`.

**This is the first save editor for this game.** The save file format was reverse-engineered through binary analysis and save-diffing — there is no official documentation. While every editable field has been verified through testing, there may be edge cases or value combinations that cause the game to behave unexpectedly.

**Stay within reasonable values.** The game displays stats up to 9999 — the editor enforces this cap. Setting values to extreme numbers (e.g., 9999 in every stat on a level 1 Digimon) may work, but the game was not designed for it. If something crashes, restore from a backup and try more moderate values.

**Do not edit saves while the game is running on that slot.** The game's autosave will overwrite your edits. The editor warns you if the game process is detected, but close the game or use a different save slot to be safe.

**Fields we do NOT modify:** The editor only writes to fields that have been verified safe through save-diff analysis. It does not touch game state, quest progress, dialogue history, encounter data, or any unverified byte ranges.

---

## Known Limitations

- The story partner (Aegiochusmon) is stored at a special offset and is not currently editable
- Party slot positions (battle vs reserve) are not distinguished — the editor shows which Digimon are in your party but not which specific slot they occupy
- The editor cannot add Digimon beyond the game's box limit (999)
- Some Digimon caught under specific conditions may have unusual data that the editor displays as "Unknown"

---

## How It Works

The game encrypts save files with AES-128-ECB using a fixed key. The editor decrypts the file, parses the binary roster structure, and presents it through a graphical interface. When you save, it encrypts and writes back.

The roster parser reads the game's own flags to determine which Digimon are in your party, box, and farm — no heuristic deduplication or guesswork. It matches the game's exact displayed counts.

---

## Source Code

The full source code is available on GitHub. Link in the Posts tab.

---

## Credits

Developed by DotingDavid
Part of the ANAMNESIS project for Digimon Story: Time Stranger

Save file structure reverse-engineered through binary analysis, memory inspection, and save-diff techniques using the ANAMNESIS Companion overlay tool.
