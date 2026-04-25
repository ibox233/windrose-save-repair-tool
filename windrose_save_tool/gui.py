from __future__ import annotations

"""Tkinter GUI for scanning and repairing Windrose save folders.

The GUI is intentionally thin: it gathers user choices, displays inspection
results, and forwards all repair logic to `core.py`.
"""

import tkinter as tk
import tkinter.ttk as ttk
from pathlib import Path
from tkinter import filedialog, messagebox

from .core import (
    DISPLAY_LEVEL_MAX,
    ProgressionSummary,
    RepairOptions,
    classify_summary,
    describe_summary,
    discover_players_dirs,
    display_level_from_reward_level,
    get_lang,
    get_lang_preference,
    has_suspicious_progression,
    inspect_save_data,
    list_save_dirs,
    make_backup,
    normalize_custom_stat_points,
    normalize_custom_talent_points,
    normalize_custom_total_exp,
    normalize_target_reward_level,
    refresh_auto_lang,
    repair_save,
    set_lang,
)

ROOT_BG = "#1e1e1e"
PANEL_BG = "#252526"
INPUT_BG = "#3c3c3c"
INPUT_BORDER = "#4f4f52"
BUTTON_BG = "#0e639c"
BUTTON_HOVER = "#1177bb"
BUTTON_ALT_BG = "#3a3d41"
BUTTON_ALT_HOVER = "#4a4f55"
BUTTON_DANGER_BG = "#a1260d"
BUTTON_DANGER_HOVER = "#c13c1d"
LANG_BG = "#2f6b45"
LANG_HOVER = "#3f8558"
TEXT = "#f3f3f3"
TEXT_MUTED = "#c8c8c8"
TEXT_DIM = "#9da0a8"
TABLE_BG = "#1f1f1f"
TABLE_HEAD_BG = "#2a2d2e"
TABLE_HEAD_FG = "#d7e3ff"
TABLE_OK = "#d8f4ff"
TABLE_WARN = "#ffbf69"
TABLE_UNKNOWN = "#9ea6b3"
TABLE_SELECT = "#094771"
BORDER = "#3f3f46"
STATUS_BG = "#181818"

FONT = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI Semibold", 10)
FONT_SMALL = ("Segoe UI", 9)
FONT_CODE = ("Consolas", 10)
FONT_CODE_BOLD = ("Consolas", 10, "bold")

LANGUAGE_OPTIONS = ("auto", "zh", "en")
VALUE_MODE_OPTIONS = ("vanilla", "custom")
MAX_TARGET_LEVEL = DISPLAY_LEVEL_MAX
APP_AUTHOR = "Ice Box Studio"
APP_CONTACT = "764884112@qq.com or ibox2333@gmail.com"

LANGUAGE_MENU_LABELS = {
    "auto": {"zh": "跟随系统", "en": "System"},
    "zh": {"zh": "中文", "en": "中文"},
    "en": {"zh": "English", "en": "English"},
}

STRINGS: dict[str, dict[str, str]] = {
    "title": {"zh": "Windrose 存档修复工具", "en": "Windrose Save Repair Tool"},
    "players_dir": {"zh": "Players 目录", "en": "Players Directory"},
    "browse": {"zh": "浏览...", "en": "Browse..."},
    "rediscover": {"zh": "重新发现", "en": "Rediscover"},
    "scan": {"zh": "扫描存档", "en": "Scan Saves"},
    "target_level": {"zh": "目标原版等级", "en": "Target Vanilla Level"},
    "target_level_auto": {"zh": "自动", "en": "Auto"},
    "target_level_hint": {
        "zh": "自动 = 保持当前游戏内等级并限制在原版上限；也可手动选择 1-15。",
        "en": "Auto keeps the current in-game level capped to vanilla; you can also choose 1-15.",
    },
    "value_mode": {"zh": "写入数值", "en": "Write Values"},
    "value_mode_vanilla": {"zh": "官方默认", "en": "Vanilla Default"},
    "value_mode_custom": {"zh": "自定义", "en": "Custom"},
    "value_mode_hint": {
        "zh": "自定义模式下，留空的项目仍按官方默认值写入。",
        "en": "In custom mode, empty fields still fall back to the vanilla default values.",
    },
    "custom_total_exp": {"zh": "自定义总经验", "en": "Custom Total XP"},
    "custom_stat_points": {"zh": "自定义属性点", "en": "Custom Stat Points"},
    "custom_talent_points": {"zh": "自定义天赋点", "en": "Custom Talent Points"},
    "custom_value_hint": {"zh": "留空则按官方默认值", "en": "Leave empty for vanilla default"},
    "backup": {"zh": "修复前备份", "en": "Backup before repair"},
    "fix_reward": {"zh": "修正等级", "en": "Fix level"},
    "fix_exp": {"zh": "修正总经验", "en": "Fix total XP"},
    "fix_stat": {"zh": "恢复属性点", "en": "Restore stat points"},
    "fix_talent": {"zh": "恢复天赋点", "en": "Restore talent points"},
    "zero_nodes": {"zh": "重置技能节点", "en": "Reset skill nodes"},
    "repair_selected": {"zh": "修复所选", "en": "Repair Selected"},
    "repair_all": {"zh": "修复全部可疑存档", "en": "Repair All Suspicious"},
    "show_details": {"zh": "查看详情", "en": "Show Details"},
    "ready": {"zh": "就绪", "en": "Ready"},
    "status_scanned": {"zh": "已扫描 {count} 个存档", "en": "Scanned {count} saves"},
    "status_processed": {"zh": "已处理 {count} 个存档", "en": "Processed {count} saves"},
    "status_rediscovered": {"zh": "已刷新存档目录", "en": "Save directories refreshed"},
    "status_language_changed": {"zh": "界面语言已更新", "en": "Interface language updated"},
    "status_language_auto_changed": {
        "zh": "已按系统语言自动切换",
        "en": "Interface updated from system language",
    },
    "status_processing": {"zh": "正在处理 {count} 个存档", "en": "Processing {count} saves"},
    "status_no_suspicious": {"zh": "没有可修复的可疑存档", "en": "No suspicious saves to repair"},
    "notice": {"zh": "提示", "en": "Notice"},
    "error": {"zh": "错误", "en": "Error"},
    "done": {"zh": "完成", "en": "Done"},
    "repair_fail": {"zh": "修复失败", "en": "Repair Failed"},
    "save_details": {"zh": "存档详情", "en": "Save Details"},
    "select_dir": {"zh": "选择 Players 目录", "en": "Select Players Directory"},
    "err_no_dir": {"zh": "请先选择 Players 目录。", "en": "Please select a Players directory first."},
    "err_dir_miss": {"zh": "目录不存在", "en": "Directory not found"},
    "err_no_sel": {"zh": "请先选择一个存档。", "en": "Please select a save first."},
    "err_no_rep": {"zh": "请先选择要修复的存档。", "en": "Please select saves to repair."},
    "err_no_suspicious": {"zh": "没有发现可修复的可疑存档。", "en": "No suspicious saves found."},
    "done_msg": {"zh": "已处理 {count} 个存档。", "en": "Processed {count} saves."},
    "details_player_key": {"zh": "玩家键", "en": "Player Key"},
    "details_value_size": {"zh": "数据大小", "en": "Value Size"},
    "details_bytes": {"zh": "{count} 字节", "en": "{count} bytes"},
    "details_diagnosis": {"zh": "诊断", "en": "Diagnosis"},
    "lang_button_auto": {"zh": "跟随系统", "en": "System"},
    "col_save_id": {"zh": "存档 ID", "en": "Save ID"},
    "col_status": {"zh": "状态", "en": "Status"},
    "col_reward": {"zh": "等级", "en": "Level"},
    "col_exp": {"zh": "总经验", "en": "Total XP"},
    "col_stat": {"zh": "可用属性点", "en": "Free Stat"},
    "col_talent": {"zh": "可用天赋点", "en": "Free Talent"},
    "col_spent_stat": {"zh": "已加属性点", "en": "Spent Stat"},
    "col_spent_talent": {"zh": "已加天赋点", "en": "Spent Talent"},
    "col_message": {"zh": "诊断", "en": "Diagnosis"},
    "author_info": {
        "zh": f"作者: {APP_AUTHOR}  |  联系方式: {APP_CONTACT}",
        "en": f"By {APP_AUTHOR}  |  Contact: {APP_CONTACT}",
    },
}

TABLE_COLUMNS = ("save_id", "status", "reward", "exp", "stat", "talent", "spent_stat", "spent_talent", "message")
TABLE_WIDTHS = {
    "save_id": 250,
    "status": 90,
    "reward": 75,
    "exp": 100,
    "stat": 90,
    "talent": 90,
    "spent_stat": 95,
    "spent_talent": 95,
    "message": 555,
}


def t(key: str) -> str:
    lang = get_lang()
    return STRINGS.get(key, {}).get(lang, STRINGS.get(key, {}).get("en", key))


def language_button_label() -> str:
    preference = get_lang_preference()
    if preference == "auto":
        return t("lang_button_auto")
    if preference == "zh":
        return "中文"
    return "EN"


def language_menu_label(code: str) -> str:
    lang = get_lang()
    return LANGUAGE_MENU_LABELS[code][lang]


def value_mode_label(code: str) -> str:
    return t(f"value_mode_{code}")


def configure_styles(root: tk.Misc) -> None:
    """Apply the VS Code-inspired dark theme used by the desktop tool."""
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(".", background=ROOT_BG, foreground=TEXT, fieldbackground=INPUT_BG, font=FONT)

    style.configure(
        "TCombobox",
        background=INPUT_BG,
        fieldbackground=INPUT_BG,
        foreground=TEXT,
        bordercolor=INPUT_BORDER,
        lightcolor=INPUT_BORDER,
        darkcolor=INPUT_BORDER,
        arrowcolor=TEXT_MUTED,
        insertcolor=TEXT,
        padding=5,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", INPUT_BG)],
        selectbackground=[("readonly", INPUT_BG)],
        selectforeground=[("readonly", TEXT)],
    )

    style.configure(
        "Treeview",
        background=TABLE_BG,
        fieldbackground=TABLE_BG,
        foreground=TEXT,
        borderwidth=0,
        relief="flat",
        rowheight=34,
        font=FONT_CODE,
    )
    style.map("Treeview", background=[("selected", TABLE_SELECT)], foreground=[("selected", "#ffffff")])

    style.configure(
        "Treeview.Heading",
        background=TABLE_HEAD_BG,
        foreground=TABLE_HEAD_FG,
        borderwidth=0,
        relief="flat",
        padding=(6, 5),
        font=FONT_CODE_BOLD,
        anchor="center",
    )
    style.map("Treeview.Heading", background=[("active", TABLE_HEAD_BG)])

    style.configure(
        "Vertical.TScrollbar",
        background=PANEL_BG,
        troughcolor=TABLE_BG,
        bordercolor=TABLE_BG,
        arrowcolor=TEXT_MUTED,
        darkcolor=PANEL_BG,
        lightcolor=PANEL_BG,
    )


def make_button(
    parent: tk.Widget,
    text: str,
    command,
    *,
    bg: str,
    hover: str,
    fg: str = TEXT,
    padx: int = 18,
) -> tk.Label:
    """Create a lightweight clickable label styled as a button."""
    widget = tk.Label(
        parent,
        text=text,
        bg=bg,
        fg=fg,
        font=FONT,
        cursor="hand2",
        padx=padx,
        pady=7,
        relief="flat",
    )
    widget.bind("<Enter>", lambda _event: widget.configure(bg=hover))
    widget.bind("<Leave>", lambda _event: widget.configure(bg=bg))
    widget.bind("<Button-1>", lambda _event: command())
    return widget


def make_entry(parent: tk.Widget, variable: tk.StringVar, *, width: int = 12) -> tk.Entry:
    """Create a text entry that matches the custom dark theme."""
    return tk.Entry(
        parent,
        textvariable=variable,
        bg=INPUT_BG,
        fg=TEXT,
        insertbackground=TEXT,
        disabledbackground="#2a2a2a",
        disabledforeground=TEXT_DIM,
        highlightbackground=INPUT_BORDER,
        highlightcolor=BUTTON_BG,
        highlightthickness=1,
        relief="flat",
        font=FONT,
        width=width,
    )


def launch_gui(initial_players_dir: Path | None = None) -> int:
    """Start the desktop UI and return its exit code."""
    return WindroseSaveRepairApp(initial_players_dir).run()


class WindroseSaveRepairApp:
    """Desktop application wrapper around save discovery, inspection, and repair."""
    def __init__(self, initial_players_dir: Path | None = None) -> None:
        refresh_auto_lang()
        self.root = tk.Tk()
        self.root.configure(bg=ROOT_BG)
        self.root.title(t("title"))
        self.root.geometry("1320x800")
        self.root.minsize(1160, 680)

        self._logo_image: tk.PhotoImage | None = None
        self._apply_app_icon()
        configure_styles(self.root)

        self.discovered = self._discover_paths()
        initial = str(initial_players_dir) if initial_players_dir else (self.discovered[0] if self.discovered else "")

        self.players_dir_var = tk.StringVar(value=initial)
        self.status_var = tk.StringVar(value=t("ready"))
        self.backup_var = tk.BooleanVar(value=True)
        self.fix_reward_var = tk.BooleanVar(value=True)
        self.fix_exp_var = tk.BooleanVar(value=True)
        self.fix_stat_var = tk.BooleanVar(value=True)
        self.fix_talent_var = tk.BooleanVar(value=True)
        self.zero_nodes_var = tk.BooleanVar(value=True)
        self.target_level_var = tk.StringVar()
        self.value_mode_var = tk.StringVar()
        self.custom_total_exp_var = tk.StringVar()
        self.custom_stat_points_var = tk.StringVar()
        self.custom_talent_points_var = tk.StringVar()
        self._target_level_choice: int | None = None
        self._value_mode_choice = "vanilla"

        self._last_auto_lang = get_lang()
        self._save_details: dict[str, ProgressionSummary | None] = {}
        self._refs: dict[str, tk.Widget] = {}
        self._option_refs: dict[str, tk.Checkbutton] = {}
        self._custom_label_refs: dict[str, tk.Label] = {}
        self._custom_entry_refs: dict[str, tk.Entry] = {}

        self._build()
        self._refresh_text()
        self._toggle_custom_inputs()
        self._start_auto_language_watch()

        if self.players_dir_var.get():
            self.root.after(120, lambda: self.refresh_save_list(show_errors=False))

    def _runtime_root(self) -> Path:
        return Path(__file__).resolve().parent.parent

    def _apply_app_icon(self) -> None:
        logo_path = self._runtime_root() / "logo.png"
        if not logo_path.is_file():
            return
        try:
            self._logo_image = tk.PhotoImage(file=str(logo_path))
            self.root.iconphoto(True, self._logo_image)
        except Exception:
            self._logo_image = None

    def _discover_paths(self) -> list[str]:
        return [str(path) for path in discover_players_dirs()]

    def _build(self) -> None:
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(2, weight=1)

        self._build_topbar()
        self._build_option_bar()
        self._build_table_area()
        self._build_action_bar()
        self._build_status_bar()

    def _build_topbar(self) -> None:
        bar = tk.Frame(self.root, bg=PANEL_BG, padx=14, pady=10)
        bar.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 6))
        bar.grid_columnconfigure(1, weight=1)

        label = tk.Label(bar, bg=PANEL_BG, fg=TEXT, font=FONT_BOLD)
        label.grid(row=0, column=0, sticky="w", padx=(0, 12))
        self._refs["players_dir"] = label

        combo = ttk.Combobox(bar, textvariable=self.players_dir_var, values=self.discovered)
        combo.grid(row=0, column=1, sticky="ew", ipady=2)
        self._refs["combo"] = combo

        buttons = tk.Frame(bar, bg=PANEL_BG)
        buttons.grid(row=0, column=2, sticky="e", padx=(12, 0))

        self._refs["button_browse"] = make_button(buttons, t("browse"), self.browse_dir, bg=BUTTON_BG, hover=BUTTON_HOVER)
        self._refs["button_browse"].pack(side="left", padx=(0, 8))

        self._refs["button_rediscover"] = make_button(
            buttons,
            t("rediscover"),
            self.rediscover,
            bg=BUTTON_ALT_BG,
            hover=BUTTON_ALT_HOVER,
        )
        self._refs["button_rediscover"].pack(side="left", padx=(0, 8))

        self._refs["button_scan"] = make_button(
            buttons,
            t("scan"),
            lambda: self.refresh_save_list(show_errors=True),
            bg=BUTTON_BG,
            hover=BUTTON_HOVER,
        )
        self._refs["button_scan"].pack(side="left", padx=(0, 8))

        self.lang_button = tk.Menubutton(
            buttons,
            text=language_button_label(),
            bg=LANG_BG,
            fg=TEXT,
            activebackground=LANG_HOVER,
            activeforeground=TEXT,
            relief="flat",
            font=FONT_BOLD,
            padx=14,
            pady=7,
            cursor="hand2",
            indicatoron=False,
            direction="below",
        )
        self.lang_button.pack(side="left")
        self._refs["lang_button"] = self.lang_button
        self._rebuild_language_menu()

    def _build_option_bar(self) -> None:
        panel = tk.Frame(self.root, bg=PANEL_BG, padx=18, pady=14)
        panel.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 6))
        panel.grid_columnconfigure(4, weight=1)

        target_label = tk.Label(panel, bg=PANEL_BG, fg=TEXT, font=FONT_BOLD)
        target_label.grid(row=0, column=0, sticky="w", padx=(0, 8))
        self._refs["target_level_label"] = target_label

        target_combo = ttk.Combobox(panel, textvariable=self.target_level_var, state="readonly", width=16)
        target_combo.grid(row=0, column=1, sticky="w", padx=(0, 18), ipady=2)
        target_combo.bind("<<ComboboxSelected>>", lambda _event: self._sync_target_level_choice())
        self._refs["target_level_combo"] = target_combo

        value_mode_label_widget = tk.Label(panel, bg=PANEL_BG, fg=TEXT, font=FONT_BOLD)
        value_mode_label_widget.grid(row=0, column=2, sticky="w", padx=(0, 8))
        self._refs["value_mode_label"] = value_mode_label_widget

        value_mode_combo = ttk.Combobox(panel, textvariable=self.value_mode_var, state="readonly", width=18)
        value_mode_combo.grid(row=0, column=3, sticky="w", padx=(0, 18), ipady=2)
        value_mode_combo.bind("<<ComboboxSelected>>", lambda _event: self._sync_value_mode_choice())
        self._refs["value_mode_combo"] = value_mode_combo

        options = tk.Frame(panel, bg=PANEL_BG)
        options.grid(row=0, column=4, sticky="w")

        # These toggles map directly to fields in RepairOptions.
        checks = [
            ("backup", self.backup_var),
            ("fix_reward", self.fix_reward_var),
            ("fix_exp", self.fix_exp_var),
            ("fix_stat", self.fix_stat_var),
            ("fix_talent", self.fix_talent_var),
            ("zero_nodes", self.zero_nodes_var),
        ]
        for index, (key, variable) in enumerate(checks):
            widget = tk.Checkbutton(
                options,
                text=t(key),
                variable=variable,
                bg=PANEL_BG,
                fg=TEXT,
                activebackground=PANEL_BG,
                activeforeground=TEXT,
                selectcolor=INPUT_BG,
                relief="flat",
                highlightthickness=0,
                font=FONT,
                padx=4,
                pady=6,
                anchor="w",
            )
            widget.grid(row=index // 3, column=index % 3, sticky="w", padx=(0, 18))
            self._option_refs[key] = widget

        target_hint = tk.Label(panel, bg=PANEL_BG, fg=TEXT_DIM, font=FONT_SMALL, anchor="w")
        target_hint.grid(row=1, column=0, columnspan=5, sticky="w", pady=(6, 0))
        self._refs["target_level_hint"] = target_hint

        value_hint = tk.Label(panel, bg=PANEL_BG, fg=TEXT_DIM, font=FONT_SMALL, anchor="w")
        value_hint.grid(row=2, column=0, columnspan=5, sticky="w", pady=(4, 0))
        self._refs["value_mode_hint"] = value_hint

        custom_wrap = tk.Frame(panel, bg=PANEL_BG)
        custom_wrap.grid(row=3, column=0, columnspan=5, sticky="ew", pady=(10, 0))
        custom_wrap.grid_columnconfigure(1, weight=1)
        custom_wrap.grid_columnconfigure(3, weight=1)
        custom_wrap.grid_columnconfigure(5, weight=1)

        total_label = tk.Label(custom_wrap, bg=PANEL_BG, fg=TEXT, font=FONT)
        total_label.grid(row=0, column=0, sticky="w", padx=(0, 8))
        self._custom_label_refs["custom_total_exp"] = total_label

        total_entry = make_entry(custom_wrap, self.custom_total_exp_var, width=14)
        total_entry.grid(row=0, column=1, sticky="ew", padx=(0, 18), ipady=4)
        self._custom_entry_refs["custom_total_exp"] = total_entry

        stat_label = tk.Label(custom_wrap, bg=PANEL_BG, fg=TEXT, font=FONT)
        stat_label.grid(row=0, column=2, sticky="w", padx=(0, 8))
        self._custom_label_refs["custom_stat_points"] = stat_label

        stat_entry = make_entry(custom_wrap, self.custom_stat_points_var, width=12)
        stat_entry.grid(row=0, column=3, sticky="ew", padx=(0, 18), ipady=4)
        self._custom_entry_refs["custom_stat_points"] = stat_entry

        talent_label = tk.Label(custom_wrap, bg=PANEL_BG, fg=TEXT, font=FONT)
        talent_label.grid(row=0, column=4, sticky="w", padx=(0, 8))
        self._custom_label_refs["custom_talent_points"] = talent_label

        talent_entry = make_entry(custom_wrap, self.custom_talent_points_var, width=12)
        talent_entry.grid(row=0, column=5, sticky="ew", ipady=4)
        self._custom_entry_refs["custom_talent_points"] = talent_entry

        custom_hint = tk.Label(custom_wrap, bg=PANEL_BG, fg=TEXT_DIM, font=FONT_SMALL, anchor="w")
        custom_hint.grid(row=1, column=0, columnspan=6, sticky="w", pady=(6, 0))
        self._refs["custom_value_hint"] = custom_hint

    def _build_table_area(self) -> None:
        wrap = tk.Frame(self.root, bg=TABLE_BG, highlightbackground=BORDER, highlightthickness=1)
        wrap.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 6))
        wrap.grid_rowconfigure(0, weight=1)
        wrap.grid_columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(wrap, columns=TABLE_COLUMNS, show="headings", selectmode="extended")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<Double-1>", lambda _event: self.show_details())

        scroll = ttk.Scrollbar(wrap, orient="vertical", command=self.tree.yview, style="Vertical.TScrollbar")
        scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scroll.set)

        self.tree.tag_configure("ok", foreground=TABLE_OK)
        self.tree.tag_configure("suspicious", foreground=TABLE_WARN)
        self.tree.tag_configure("unknown", foreground=TABLE_UNKNOWN)

        self._apply_tree_headings()

    def _build_action_bar(self) -> None:
        bar = tk.Frame(self.root, bg=ROOT_BG, padx=8, pady=4)
        bar.grid(row=3, column=0, sticky="ew")
        bar.grid_columnconfigure(1, weight=1)

        actions = tk.Frame(bar, bg=ROOT_BG)
        actions.grid(row=0, column=0, sticky="w")

        self._refs["repair_selected"] = make_button(
            actions,
            t("repair_selected"),
            self.repair_selected,
            bg=BUTTON_BG,
            hover=BUTTON_HOVER,
            padx=34,
        )
        self._refs["repair_selected"].pack(side="left", padx=(0, 8))

        self._refs["repair_all"] = make_button(
            actions,
            t("repair_all"),
            self.repair_all_suspicious,
            bg=BUTTON_DANGER_BG,
            hover=BUTTON_DANGER_HOVER,
            padx=28,
        )
        self._refs["repair_all"].pack(side="left", padx=(0, 8))

        self._refs["show_details"] = make_button(
            actions,
            t("show_details"),
            self.show_details,
            bg=BUTTON_ALT_BG,
            hover=BUTTON_ALT_HOVER,
            padx=28,
        )
        self._refs["show_details"].pack(side="left")

        info = tk.Label(
            bar,
            bg=ROOT_BG,
            fg=TEXT_DIM,
            font=FONT_SMALL,
            anchor="e",
            justify="right",
        )
        info.grid(row=0, column=1, sticky="e")
        self._refs["author_info"] = info

    def _build_status_bar(self) -> None:
        status = tk.Label(
            self.root,
            textvariable=self.status_var,
            bg=STATUS_BG,
            fg=TEXT_DIM,
            anchor="w",
            font=FONT_SMALL,
            padx=12,
            pady=6,
        )
        status.grid(row=4, column=0, sticky="ew", padx=8, pady=(0, 8))
        self._refs["statusbar"] = status

    def _apply_tree_headings(self) -> None:
        labels = {
            "save_id": t("col_save_id"),
            "status": t("col_status"),
            "reward": t("col_reward"),
            "exp": t("col_exp"),
            "stat": t("col_stat"),
            "talent": t("col_talent"),
            "spent_stat": t("col_spent_stat"),
            "spent_talent": t("col_spent_talent"),
            "message": t("col_message"),
        }
        for column in TABLE_COLUMNS:
            anchor = "w" if column == "message" else "center"
            self.tree.heading(column, text=labels[column], anchor="center")
            self.tree.column(
                column,
                width=TABLE_WIDTHS[column],
                minwidth=TABLE_WIDTHS[column],
                anchor=anchor,
                stretch=False,
            )

    def _rebuild_language_menu(self) -> None:
        menu = tk.Menu(
            self.lang_button,
            tearoff=False,
            bg=PANEL_BG,
            fg=TEXT,
            activebackground=TABLE_SELECT,
            activeforeground=TEXT,
        )
        for code in LANGUAGE_OPTIONS:
            menu.add_command(label=language_menu_label(code), command=lambda value=code: self._set_language_preference(value))
        self.lang_button.configure(menu=menu)

    def _auto_target_level_label(self) -> str:
        return t("target_level_auto")

    def _target_level_values(self) -> list[str]:
        return [self._auto_target_level_label(), *[str(level) for level in range(1, MAX_TARGET_LEVEL + 1)]]

    def _set_target_level_choice(self, value: int | None) -> None:
        self._target_level_choice = value
        if value is None:
            self.target_level_var.set(self._auto_target_level_label())
        else:
            self.target_level_var.set(str(value))

    def _sync_target_level_choice(self) -> None:
        raw = self.target_level_var.get().strip()
        if not raw or raw == self._auto_target_level_label():
            self._target_level_choice = None
            self.target_level_var.set(self._auto_target_level_label())
            return
        normalize_target_reward_level(raw)
        self._target_level_choice = int(raw)
        self.target_level_var.set(str(self._target_level_choice))

    def _value_mode_values(self) -> list[str]:
        return [value_mode_label(code) for code in VALUE_MODE_OPTIONS]

    def _set_value_mode_choice(self, value: str) -> None:
        self._value_mode_choice = value if value in VALUE_MODE_OPTIONS else "vanilla"
        self.value_mode_var.set(value_mode_label(self._value_mode_choice))
        self._toggle_custom_inputs()

    def _sync_value_mode_choice(self) -> None:
        raw = self.value_mode_var.get().strip()
        mapping = {value_mode_label(code): code for code in VALUE_MODE_OPTIONS}
        self._set_value_mode_choice(mapping.get(raw, "vanilla"))

    def _toggle_custom_inputs(self) -> None:
        """Enable custom value fields only when the user selects custom mode."""
        is_custom = self._value_mode_choice == "custom"
        state = "normal" if is_custom else "disabled"
        label_color = TEXT if is_custom else TEXT_DIM
        for widget in self._custom_entry_refs.values():
            widget.configure(state=state)
        for widget in self._custom_label_refs.values():
            widget.configure(fg=label_color)

    def _set_status(self, text: str | None = None) -> None:
        self.status_var.set(text or t("ready"))

    def _set_language_preference(self, code: str) -> None:
        set_lang(code)
        self._last_auto_lang = get_lang()
        self._refresh_text()
        self.refresh_save_list(show_errors=False)
        self._set_status(t("status_language_changed"))

    def _refresh_text(self) -> None:
        self.root.title(t("title"))
        self._refs["players_dir"].configure(text=t("players_dir"))
        self._refs["button_browse"].configure(text=t("browse"))
        self._refs["button_rediscover"].configure(text=t("rediscover"))
        self._refs["button_scan"].configure(text=t("scan"))
        self._refs["target_level_label"].configure(text=t("target_level"))
        self._refs["value_mode_label"].configure(text=t("value_mode"))
        self._refs["target_level_hint"].configure(text=t("target_level_hint"))
        self._refs["value_mode_hint"].configure(text=t("value_mode_hint"))
        self._refs["custom_value_hint"].configure(text=t("custom_value_hint"))
        self._refs["repair_selected"].configure(text=t("repair_selected"))
        self._refs["repair_all"].configure(text=t("repair_all"))
        self._refs["show_details"].configure(text=t("show_details"))
        self._refs["author_info"].configure(text=t("author_info"))
        self._custom_label_refs["custom_total_exp"].configure(text=t("custom_total_exp"))
        self._custom_label_refs["custom_stat_points"].configure(text=t("custom_stat_points"))
        self._custom_label_refs["custom_talent_points"].configure(text=t("custom_talent_points"))
        for key, widget in self._option_refs.items():
            widget.configure(text=t(key))
        self._refs["combo"].configure(values=self.discovered)
        self._refs["target_level_combo"].configure(values=self._target_level_values())
        self._refs["value_mode_combo"].configure(values=self._value_mode_values())
        self._set_target_level_choice(self._target_level_choice)
        self._set_value_mode_choice(self._value_mode_choice)
        self.lang_button.configure(text=language_button_label())
        self._rebuild_language_menu()
        self._apply_tree_headings()
        self._set_status()

    def _start_auto_language_watch(self) -> None:
        self._poll_auto_language()

    def _poll_auto_language(self) -> None:
        if get_lang_preference() == "auto":
            current = refresh_auto_lang()
            if current != self._last_auto_lang:
                self._last_auto_lang = current
                self._refresh_text()
                self.refresh_save_list(show_errors=False)
                self._set_status(t("status_language_auto_changed"))
        else:
            self._last_auto_lang = get_lang()
        self.root.after(3000, self._poll_auto_language)

    def _make_options(self) -> RepairOptions:
        """Translate the current UI state into core repair options."""
        custom_total_exp = None
        custom_stat_points = None
        custom_talent_points = None
        if self._value_mode_choice == "custom":
            custom_total_exp = normalize_custom_total_exp(self.custom_total_exp_var.get())
            custom_stat_points = normalize_custom_stat_points(self.custom_stat_points_var.get())
            custom_talent_points = normalize_custom_talent_points(self.custom_talent_points_var.get())

        return RepairOptions(
            backup=self.backup_var.get(),
            zero_nodes=self.zero_nodes_var.get(),
            fix_reward_level=self.fix_reward_var.get(),
            fix_total_exp=self.fix_exp_var.get(),
            fix_stat_points=self.fix_stat_var.get(),
            fix_talent_points=self.fix_talent_var.get(),
            target_reward_level=self._target_level_choice,
            custom_total_exp=custom_total_exp,
            custom_stat_points=custom_stat_points,
            custom_talent_points=custom_talent_points,
        )

    def _ensure_current_dir_in_choices(self, path: str) -> None:
        if path and path not in self.discovered:
            self.discovered = [path, *self.discovered]
            self._refs["combo"].configure(values=self.discovered)

    def get_players_dir(self) -> Path:
        raw = self.players_dir_var.get().strip()
        if not raw:
            raise ValueError(t("err_no_dir"))
        path = Path(raw).resolve()
        if not path.is_dir():
            raise ValueError(f"{t('err_dir_miss')}: {path}")
        return path

    def browse_dir(self) -> None:
        selected = filedialog.askdirectory(title=t("select_dir"))
        if selected:
            self.players_dir_var.set(selected)
            self._ensure_current_dir_in_choices(selected)
            self.refresh_save_list(show_errors=True)

    def rediscover(self) -> None:
        current = self.players_dir_var.get().strip()
        self.discovered = self._discover_paths()
        if current and current not in self.discovered:
            self.discovered.insert(0, current)
        self._refs["combo"].configure(values=self.discovered)
        if not current and self.discovered:
            self.players_dir_var.set(self.discovered[0])
        self._set_status(t("status_rediscovered"))

    def refresh_save_list(self, *, show_errors: bool) -> None:
        """Rescan the selected Players directory and repopulate the table."""
        try:
            players_dir = self.get_players_dir()
        except ValueError as exc:
            self._save_details.clear()
            for item in self.tree.get_children():
                self.tree.delete(item)
            self._set_status(str(exc))
            if show_errors:
                messagebox.showerror(t("error"), str(exc))
            return

        self._ensure_current_dir_in_choices(str(players_dir))

        for item in self.tree.get_children():
            self.tree.delete(item)
        self._save_details.clear()

        save_dirs = list_save_dirs(players_dir, None)
        for save_dir in save_dirs:
            summary = inspect_save_data(save_dir)
            self._save_details[save_dir.name] = summary
            status, message = classify_summary(summary)
            tag = "unknown" if summary is None else ("suspicious" if has_suspicious_progression(summary) else "ok")
            self.tree.insert(
                "",
                "end",
                values=(
                    save_dir.name,
                    status,
                    display_level_from_reward_level(summary.reward_level) if summary else "-",
                    summary.total_exp if summary else "-",
                    summary.stat_points if summary else "-",
                    summary.talent_points if summary else "-",
                    summary.spent_stat_points if summary and summary.spent_stat_points is not None else "-",
                    summary.spent_talent_points if summary and summary.spent_talent_points is not None else "-",
                    message,
                ),
                tags=(tag,),
            )

        self._set_status(t("status_scanned").format(count=len(save_dirs)))

    def repair_targets(self, save_ids: list[str]) -> None:
        """Repair one or more selected saves using the current UI options."""
        if not save_ids:
            messagebox.showwarning(t("notice"), t("err_no_rep"))
            return

        try:
            players_dir = self.get_players_dir()
            options = self._make_options()
        except ValueError as exc:
            messagebox.showerror(t("error"), str(exc))
            return

        self._set_status(t("status_processing").format(count=len(save_ids)))

        for save_id in save_ids:
            save_dir = players_dir / save_id
            try:
                if options.backup:
                    make_backup(save_dir)
                repair_save(save_dir, options)
            except Exception as exc:
                self._set_status(t("repair_fail"))
                messagebox.showerror(t("repair_fail"), f"{save_id}\n{exc}")
                return

        self.refresh_save_list(show_errors=False)
        self._set_status(t("status_processed").format(count=len(save_ids)))
        messagebox.showinfo(t("done"), t("done_msg").format(count=len(save_ids)))

    def repair_selected(self) -> None:
        selected = [str(self.tree.item(item, "values")[0]) for item in self.tree.selection()]
        self.repair_targets(selected)

    def repair_all_suspicious(self) -> None:
        selected: list[str] = []
        for item in self.tree.get_children():
            save_id = str(self.tree.item(item, "values")[0])
            if has_suspicious_progression(self._save_details.get(save_id)):
                selected.append(save_id)

        if not selected:
            self._set_status(t("status_no_suspicious"))
            messagebox.showinfo(t("notice"), t("err_no_suspicious"))
            return

        self.repair_targets(selected)

    def _format_details(self, save_id: str, summary: ProgressionSummary | None) -> str:
        if summary is None:
            return describe_summary(summary, save_id)

        status, diagnosis = classify_summary(summary)
        player_key = summary.player_key.decode("utf-8", errors="ignore")
        lines = [
            f"{t('col_save_id')}: {summary.save_id}",
            f"{t('col_status')}: {status}",
            f"{t('col_reward')}: {display_level_from_reward_level(summary.reward_level)}",
            f"{t('col_exp')}: {summary.total_exp}",
            f"{t('col_stat')}: {summary.stat_points}",
            f"{t('col_talent')}: {summary.talent_points}",
            f"{t('col_spent_stat')}: {summary.spent_stat_points}",
            f"{t('col_spent_talent')}: {summary.spent_talent_points}",
            f"{t('details_player_key')}: {player_key}",
            f"{t('details_value_size')}: {t('details_bytes').format(count=summary.value_size)}",
            f"{t('details_diagnosis')}: {diagnosis}",
        ]
        return "\n".join(lines)

    def show_details(self) -> None:
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning(t("notice"), t("err_no_sel"))
            return
        save_id = str(self.tree.item(selection[0], "values")[0])
        summary = self._save_details.get(save_id)
        messagebox.showinfo(t("save_details"), self._format_details(save_id, summary))

    def run(self) -> int:
        self.root.mainloop()
        return 0
