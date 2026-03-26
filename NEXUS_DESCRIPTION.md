# ANAMNESIS SE — Save Editor for Digimon Story: Time Stranger

The first and only save editor for DSTS. View and edit your Digimon, stats, skills, scans, money, and more through a clean dark-themed GUI with all 475 Digimon portrait icons.

Built by reverse-engineering the game's encrypted save file format from scratch. Part of the ANAMNESIS project.

---

## Features

**Digimon Editing**
- View your full roster with accurate party, box, and farm counts matching the game
- Edit stats: growth (white), farm, and blue stats (capped at 9999)
- Edit level (EXP and growth stats update automatically to match)
- Edit talent, bond, personality, and personality skill (40 skills with English names)
- HP/SP health bars with click-to-heal
- Change species, set nicknames
- Edit attachment skills (4 slots) and equipment (2 slots)
- Talent accumulator and evolution counter visible and editable

**Single-Page Editor**
- Everything on one screen. No tabs. Identity and skills side by side on top, full-width stat bars with editable values below.

**Roster Tools**
- PKHeX-style icon grid with all 475 Digimon portraits
- Box displayed in reverse order matching the game
- Clone any Digimon to an empty box slot
- Create new Digimon from scratch (pick species, level, personality)
- Export/import individual Digimon as .digi files
- Search, sort by name/level/stage/personality, filter by party/box/farm

**Scan Table**
- View and edit scan percentages for all species
- Batch set: set all scans to 100% or 200% with one click

**Agent / Player Data**
- Edit money and Tamer Points
- Unlock agent skill trees (Valor, Philanthropy, Amicability, Wisdom, Loyalty)

**Batch Operations**
- Set bond to 100% on all Digimon
- Set talent on all Digimon
- Set blue stats on all Digimon
- Reset all evolution counters

**File Management**
- Multi-account support (auto-detects Steam save directories, or browse manually)
- Backup, copy, swap, export, and import save slots
- Automatic backup before every save (keeps 2 most recent per slot)
- Game-running detection with warning

**Save Identification System**
- Works with ANAMNESIS Companion for per-save collection tracking
- Consent dialog on first launch with automatic pre-signature backups
- Unsign individual saves or all saves from File Manager
- Full revert to pre-ANAMNESIS state available at any time

---

## Installation

1. Download `ANAMNESIS_SE.exe` from the Files tab
2. Place it anywhere. No installation needed.
3. Run it. Your save directory is auto-detected from Steam.
4. If auto-detection fails, use the Browse button to select your save folder.

**Note:** Windows SmartScreen or your browser may flag the download because the executable is unsigned. This is a false positive common to all PyInstaller-built applications.

---

## Important Information

**Automatic Backups.** The editor creates a backup before every save, stored in a `backups` folder next to your saves. You can also restore pre-signature backups from the File Manager.

**This is the first save editor for this game.** The save format was reverse-engineered through binary analysis and save-diffing. While every editable field has been verified through testing, stay within reasonable values. The game displays stats up to 9999, and the editor enforces this cap.

**Close the game before editing.** The game's autosave will overwrite your edits if it's running. The editor warns you if it detects the game process.

**Level changes are smart.** When you change a Digimon's level, the editor automatically sets the correct EXP for that species' experience curve and adjusts growth stats to match. No more negative EXP displays.

**What we don't touch.** The editor only modifies verified fields. It does not change quest progress, dialogue history, encounter data, or any unverified byte ranges.

---

## Known Limitations

- The story partner (Aegiochusmon) is not currently editable
- Party slot positions (battle vs reserve) are not distinguished
- The editor cannot add Digimon beyond the game's box limit (999)

---

## How It Works

The game encrypts save files with AES-128-ECB. The editor decrypts the file, parses the binary roster structure using the game's own flags (active_flag, party_flag, compacting arrays), and presents it through a graphical interface. When you save, it encrypts and writes back.

The roster parser matches the game's exact displayed counts. No heuristic deduplication or guesswork.

---

## Credits

Developed by DotingDavid
Part of the ANAMNESIS project for Digimon Story: Time Stranger

Save file structure reverse-engineered through binary analysis, memory inspection, and save-diff techniques.
