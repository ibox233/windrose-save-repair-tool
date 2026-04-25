# -*- mode: python ; coding: utf-8 -*-
import fnmatch
import os
from pathlib import Path

from PyInstaller.building.datastruct import TOC
from PyInstaller.utils.hooks import collect_all


SYSTEM32 = Path(os.environ["WINDIR"]) / "System32"
# Force the packaged app to use the current Windows VC++ runtime instead of
# bundling an arbitrary DLL discovered elsewhere on PATH.
RUNTIME_OVERRIDES = {
    "msvcp140.dll": SYSTEM32 / "MSVCP140.dll",
    "vcruntime140.dll": SYSTEM32 / "VCRUNTIME140.dll",
    "vcruntime140_1.dll": SYSTEM32 / "VCRUNTIME140_1.dll",
}
RUNTIME_EXCLUDE_PATTERNS = (
    "api-ms-win-crt-*.dll",
    "ucrtbase.dll",
    *RUNTIME_OVERRIDES.keys(),
)


def patch_runtime_binaries(entries):
    """Filter runtime DLLs and replace them with the known-good System32 copies."""
    kept = []
    for entry in entries:
        name = Path(entry[0]).name.lower()
        if any(fnmatch.fnmatch(name, pattern) for pattern in RUNTIME_EXCLUDE_PATTERNS):
            continue
        kept.append(entry)

    for _, source in RUNTIME_OVERRIDES.items():
        if not source.is_file():
            raise FileNotFoundError(f"Required runtime DLL not found: {source}")
        kept.append((source.name, str(source), "BINARY"))

    return TOC(kept)

datas = []
binaries = []
hiddenimports = []

tmp = collect_all('rocksdict')
datas += tmp[0]; binaries += tmp[1]; hiddenimports += tmp[2]
# Bundle the runtime icon asset used by the Tk window in source and frozen mode.
datas += [('H:\\Tools\\Unreal Engine\\FModel\\Output\\Exports\\R5\\windrose_save_tool\\logo.png', '.')]

a = Analysis(
    ['H:\\Tools\\Unreal Engine\\FModel\\Output\\Exports\\R5\\windrose_save_tool\\windrose_save_repair_tool.py'],
    pathex=['H:\\Tools\\Unreal Engine\\FModel\\Output\\Exports\\R5\\windrose_save_tool'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
a.binaries = patch_runtime_binaries(a.binaries)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='WindroseSaveRepairTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='H:\\Tools\\Unreal Engine\\FModel\\Output\\Exports\\R5\\windrose_save_tool\\logo.ico',
)
