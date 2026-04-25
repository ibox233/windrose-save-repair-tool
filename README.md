# Windrose Save Repair Tool

Windrose Save Repair Tool is a desktop utility for repairing Windrose / R5 saves that fail to load after using level-modifying mods.

The project is written in Python, uses Tkinter for the GUI, and reads the game's save folders directly through RocksDB via `rocksdict`.

## What The Tool Repairs

The tool focuses on broken progression values inside a save:

- reward level
- total XP
- free stat points
- free talent points
- skill node levels

Its goal is to bring those values back into a vanilla-compatible state so the save can load again.

## How The Repair Works

At a high level the tool does this:

1. Open the selected save directory as a RocksDB database.
2. Read the main player blob from the `R5BLPlayer` column family.
3. Locate a small set of BSON `int32` fields by field name inside the raw bytes.
4. Compare the current values against the built-in vanilla progression table.
5. Compute repair targets from either:
   - the vanilla table, or
   - optional custom values provided in the UI / CLI
6. Patch only those numeric fields in the raw blob.
7. Optionally reset purchased skill nodes and restore their default caps.
8. Write the patched bytes back to the same RocksDB key.

The tool does not rebuild the whole save from scratch. It edits only the supported progression fields.

## Repository Layout

- `windrose_save_tool/core.py`: save inspection and repair logic
- `windrose_save_tool/gui.py`: Tkinter desktop UI
- `windrose_save_tool/cli.py`: CLI wrapper around the same repair logic
- `windrose_save_repair_tool.py`: GUI executable entry point
- `repair_r5_save_progression.py`: console-oriented launcher
- `WindroseSaveRepairTool.spec`: PyInstaller build definition
- `build_windrose_save_repair_exe.ps1`: convenience build script
- `inspect_r5_rocksdb.py`: read-only low-level inspection helper
- `rebind_windrose_save_owner.py`: experimental ownership-rebinding helper

## Dependencies

Runtime dependency:

- `rocksdict`

Standard-library components used heavily:

- `tkinter`
- `argparse`
- `pathlib`
- `struct`
- `shutil`

Build dependency:

- `PyInstaller`

## Run From Source

```powershell
python -m pip install rocksdict
python .\repair_r5_save_progression.py --gui
```

Or launch the package entry directly:

```powershell
python .\windrose_save_repair_tool.py
```

## Build The EXE

Using the provided PowerShell helper:

```powershell
.\build_windrose_save_repair_exe.ps1
```

Or directly with PyInstaller:

```powershell
python -m pip install pyinstaller rocksdict
python -m PyInstaller --noconfirm .\WindroseSaveRepairTool.spec
```

The packaged executable is written to:

```text
dist\WindroseSaveRepairTool.exe
```

## Notes

- Backups are intentionally created outside the live `Players` folder.
- The tool is aimed at progression-data recovery, not every possible kind of corrupted save.
- Helper scripts in this repository are included for research and debugging. The main end-user workflow is the GUI executable.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
