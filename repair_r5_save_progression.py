#!/usr/bin/env python3
from __future__ import annotations

"""Console-oriented launcher for the repair CLI.

This script is mainly useful during development or manual debugging. The
packaged GUI executable uses `windrose_save_repair_tool.py` instead.
"""

import sys
import traceback
from pathlib import Path


def get_runtime_dir() -> Path:
    """Return the directory used for logs in source and frozen modes."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


RUNTIME_DIR = get_runtime_dir()
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from windrose_save_tool.cli import main


def report_startup_error(exc: Exception) -> None:
    """Write a crash log and show a message box when startup fails."""
    log_path = RUNTIME_DIR / "WindroseSaveRepairTool-error.log"
    message = "".join(traceback.format_exception(exc))
    log_path.write_text(message, encoding="utf-8", newline="\n")

    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Windrose Save Repair Tool",
            "程序启动失败。\n\n"
            "错误日志已写入:\n"
            f"{log_path}\n\n"
            "The tool failed to start.\n\n"
            "A crash log was written to:\n"
            f"{log_path}",
        )
        root.destroy()
    except Exception:
        pass


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        report_startup_error(exc)
        raise SystemExit(1)
