#!/usr/bin/env python3
"""Entry point for the packaged GUI executable.

The frozen build skips argparse entirely and launches the desktop UI directly.
If startup fails, the script writes a crash log next to the executable and
shows a message box so end users still get a readable error.
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path


def get_runtime_dir() -> Path:
    """Return the folder that should receive logs and runtime-relative files."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


RUNTIME_DIR = get_runtime_dir()
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def report_startup_error(exc: Exception) -> None:
    """Persist startup failures to disk and surface them to GUI users."""
    log_path = RUNTIME_DIR / "WindroseSaveRepairTool-error.log"
    message = "".join(traceback.format_exception(exc))
    try:
        log_path.write_text(message, encoding="utf-8", newline="\n")
    except Exception:
        pass

    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Windrose Save Repair Tool",
            f"程序启动失败 / The tool failed to start.\n\n{exc}\n\nLog: {log_path}",
        )
        root.destroy()
    except Exception:
        pass


if __name__ == "__main__":
    try:
        from windrose_save_tool.gui import launch_gui

        raise SystemExit(launch_gui())
    except SystemExit:
        raise
    except Exception as exc:
        report_startup_error(exc)
        raise SystemExit(1)
