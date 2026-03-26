# ANAMNESIS SE — Save Editor

Save editor for **Digimon Story: Time Stranger**. Part of the [ANAMNESIS project](https://www.nexusmods.com/digimonstorytimestranger/mods/).

## Download

Get the latest release from [GitHub Releases](https://github.com/DotingDavid/DSTS-Save-Editor/releases) or [Nexus Mods](https://www.nexusmods.com/digimonstorytimestranger/mods/).

No installation required. Run `ANAMNESIS_SE.exe` and it auto-detects your save directory.

## What It Does

- **Edit Digimon:** Stats, level, EXP, talent, bond, personality, personality skill, skills, equipment, nicknames
- **Roster management:** Clone, create, export/import Digimon. PKHeX-style icon grid.
- **Scan table:** View and batch-edit scan percentages
- **Agent data:** Money, Tamer Points, agent skill tree unlocks
- **File management:** Backup, copy, swap, export/import save slots
- **Smart level changes:** EXP and growth stats auto-update per species' experience curve
- **Save identification:** Deterministic UUID system shared with ANAMNESIS Companion

## Technical Details

- **Encryption:** AES-128-ECB with fixed key, 3,098,176 byte files
- **Roster parsing:** Uses the game's own active_flag and compacting array structure
- **Per-species EXP curves:** 4 curves mapped by evolution stage (3 exceptions)
- **Talent accumulator:** Hidden ABI equivalent at +0xFC, confirmed via save-diff
- **Personality skills:** 40 skills with English names, stored at +0xF8
- **Save UID:** Deterministic `uuid5` written to unused padding at 0x904

## Building from Source

```
pip install PyQt6 pycryptodome
python save_editor.py
```

To build the standalone exe:
```
pip install pyinstaller
pyinstaller ANAMNESIS_SaveEditor.spec
```

## Running Tests

```
python -m unittest tests.test_exp_and_growth -v
```

## License

This project is not yet licensed. Contact the author for usage terms.

## Credits

Developed by DotingDavid

Save file structure reverse-engineered through binary analysis, memory inspection, and save-diff techniques using the ANAMNESIS Companion overlay tool.
