# ANAMNESIS SE — Save Editor for Digimon Story: Time Stranger

The first and only save editor for DSTS. Edit your Digimon, stats, skills, inventory, scans, agent skills, and more through a polished dark-themed GUI with all 475 Digimon portraits and game-accurate icons.

Built by reverse-engineering the game's encrypted save file format from scratch. Part of the ANAMNESIS project.

---

## Features

**Digimon Editing**
- View your full roster with accurate party, box, and farm counts matching the game
- Edit stats across all layers: growth (white), farm training, and blue (evolution) stats
- Edit level — EXP, growth stats, and HP/SP update automatically to match the species curve
- Edit talent, bond, personality, and personality skill (40 skills with English names)
- HP/SP health bars with click-to-heal
- Change species, set nicknames
- Edit attachment skills (4 slots) and equipment (2 slots)
- Food preference, talent accumulator, and evolution counter visible and editable

**Single-Page Editor**
- Everything on one screen. Identity and skills side by side on top, full-width stat bars with editable values below.

**Roster Tools**
- PKHeX-style icon grid with all 475 Digimon portraits
- Box displayed in reverse order matching the game
- Clone any Digimon to an empty box slot
- Create new Digimon from scratch — pick species, level, personality. Growth stats, HP/SP, talent, bond, EXP, and UUID are all set correctly
- Export/import individual Digimon as .digi files
- Search, sort by name/level/stage/personality, filter by party/box/farm

**Visual Agent Skill Tree**
- Full visual skill tree matching the in-game layout with extracted game icons
- 5 category tabs: Valor, Philanthropy, Amicability, Wisdom, Loyalty
- All 208 agent skills individually viewable — hover for details (description, AP cost, prerequisites)
- Click any skill to buy or refund it individually
- Prerequisite enforcement in both directions — can't buy without prerequisites, can't refund if a dependent skill is purchased
- Buy auto-grants Anomaly Points if you don't have enough
- Refund returns the exact AP cost to your available pool
- Unlock All / Refund All per category or globally
- Edit player name, money, available AP, and spent AP directly

**Inventory Editor**
- Browse all items by category: Recovery, Stat Boost, Evolution Items, Gems, Attachment Skills, Crafting, Farm, Equipment, Quest Items
- Attachment skill discs organized by element (Fire, Water, Ice, Electric, Plant, Wind, Earth, Steel, Light, Dark, Neutral, Support)
- Add new items, edit quantities, remove items
- Icon grid with item portraits

**Scan Table**
- View and edit scan percentages for all species
- Batch set: set all scans to 100% or 200% with one click

**Batch Operations**
- Set bond to 100% on all Digimon
- Set talent on all Digimon
- Set blue stats on all Digimon
- Reset all evolution counters

**File Management**
- Card-based save slot display with player name, money, party icons, save date, and signature status
- Multi-account support (auto-detects Steam save directories, or browse manually)
- Per-slot backup management with timestamps
- Automatic backup before every save (keeps 2 most recent per slot, aborts save if backup fails)
- Game-running detection with warning
- Optional save signatures for cross-tool identification with ANAMNESIS Companion

**Mod Support**
- Automatically detects Reloaded-II content mods
- Overlays modded Digimon names, stats, and skills without modifying the base database

---

## Installation

1. Download the zip from the Files tab and extract it
2. Run `ANAMNESIS_SE.exe`. No installation needed.
3. Your save directory is auto-detected from Steam.
4. If auto-detection fails, use the Browse button to select your save folder.

**Note:** Windows SmartScreen or your browser may flag the download because the executable is unsigned. This is a false positive common to all PyInstaller-built applications.

---

## Disclaimer

**Use at your own risk.** This tool modifies your save files. While extensive testing has been done, it is possible to corrupt a save file. The author is not responsible for any lost progress or damaged save data.

**Always have backups.** The editor creates automatic backups, but you should also keep your own manual copies of important saves before making significant changes.

**This is the first save editor for this game.** The save file format was reverse-engineered through binary analysis and save-diffing. There is no official documentation. While every editable field has been verified through testing, there may be edge cases that cause unexpected behavior. If something goes wrong, restore from a backup and try more moderate values.

---

## Backup System

The editor has a multi-layered backup system to protect your save files:

**Automatic Backups.** A backup is created before every save, stored in a `backups` folder next to your saves. The editor keeps the 2 most recent backups per slot to avoid filling your disk. If the backup fails for any reason, the save is aborted — your original file is never overwritten without a successful backup.

**File Manager.** The built-in File Manager lets you manage backups per save slot, view timestamps, and restore at any time.

---

## Important Notes

**Close the game before editing.** The game's autosave will overwrite your edits if it's running. The editor warns you if it detects the game process.

**Stay within reasonable values.** The game displays stats up to 9999, and the editor enforces this cap. Setting extreme values on low-level Digimon may cause unexpected behavior in-game.

**Level changes are smart.** When you change a Digimon's level, the editor automatically sets the correct EXP for that species' experience curve and adjusts growth stats to match.

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
