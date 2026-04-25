from __future__ import annotations

"""Command-line entry points for inspecting and repairing Windrose saves."""

import argparse
import sys
from pathlib import Path

from .core import (
    DISPLAY_LEVEL_MAX,
    DISPLAY_LEVEL_MIN,
    RepairOptions,
    bi,
    classify_summary,
    describe_summary,
    display_level_from_reward_level,
    inspect_save_data,
    list_save_dirs,
    make_backup,
    normalize_custom_stat_points,
    normalize_custom_talent_points,
    normalize_custom_total_exp,
    normalize_target_reward_level,
    repair_save,
    resolve_players_dir,
)
from .gui import launch_gui


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser shared by the console tool and helper scripts."""
    parser = argparse.ArgumentParser(
        description=bi(
            "Windrose 存档成长修复工具",
            "Windrose save progression repair tool",
        )
    )
    parser.add_argument(
        "--players-dir",
        type=Path,
        default=None,
        help=bi("Players 目录；不传则自动查找", "Players directory; auto-detect if omitted"),
    )
    parser.add_argument(
        "--save-id",
        default=None,
        help=bi("指定存档目录名；不传则扫描全部", "Specific save ID; scan all if omitted"),
    )
    parser.add_argument(
        "--mode",
        choices=["inspect", "repair-vanilla-reset"],
        default="inspect",
        help=bi(
            "inspect 只检查；repair-vanilla-reset 修复为原版兼容状态",
            "inspect only scans; repair-vanilla-reset repairs to a vanilla-compatible state",
        ),
    )
    parser.add_argument("--gui", action="store_true", help=bi("启动图形界面", "Launch GUI"))
    parser.add_argument("--backup", action="store_true", help=bi("修复前备份整个存档目录", "Backup the save before repairing"))
    parser.add_argument(
        "--target-level",
        type=int,
        default=None,
        help=bi(
            f"将存档恢复到指定原版等级（{DISPLAY_LEVEL_MIN}-{DISPLAY_LEVEL_MAX}）",
            f"Restore the save to a specific in-game vanilla level ({DISPLAY_LEVEL_MIN}-{DISPLAY_LEVEL_MAX})",
        ),
    )
    parser.add_argument(
        "--custom-total-exp",
        type=int,
        default=None,
        help=bi(
            "自定义写入的总经验；留空则按官方默认值",
            "Custom total XP to write; leave empty to use the vanilla default",
        ),
    )
    parser.add_argument(
        "--custom-stat-points",
        type=int,
        default=None,
        help=bi(
            "自定义写入的属性点；留空则按官方默认值",
            "Custom stat points to write; leave empty to use the vanilla default",
        ),
    )
    parser.add_argument(
        "--custom-talent-points",
        type=int,
        default=None,
        help=bi(
            "自定义写入的天赋点；留空则按官方默认值",
            "Custom talent points to write; leave empty to use the vanilla default",
        ),
    )
    parser.add_argument("--no-zero-nodes", action="store_true", help=bi("修复时不清零 NodeLevel", "Do not zero NodeLevel"))
    parser.add_argument(
        "--no-fix-reward-level",
        action="store_true",
        help=bi("修复时不调整 RewardLevel", "Do not adjust RewardLevel"),
    )
    parser.add_argument(
        "--no-fix-total-exp",
        action="store_true",
        help=bi("修复时不调整 TotalExp", "Do not adjust TotalExp"),
    )
    parser.add_argument(
        "--no-fix-stat-points",
        action="store_true",
        help=bi("修复时不调整属性点", "Do not adjust stat points"),
    )
    parser.add_argument(
        "--no-fix-talent-points",
        action="store_true",
        help=bi("修复时不调整天赋点", "Do not adjust talent points"),
    )
    return parser


def build_repair_options(args: argparse.Namespace) -> RepairOptions:
    """Map parsed CLI flags onto the core RepairOptions dataclass."""
    return RepairOptions(
        backup=args.backup,
        zero_nodes=not args.no_zero_nodes,
        fix_reward_level=not args.no_fix_reward_level,
        fix_total_exp=not args.no_fix_total_exp,
        fix_stat_points=not args.no_fix_stat_points,
        fix_talent_points=not args.no_fix_talent_points,
        target_reward_level=args.target_level,
        custom_total_exp=args.custom_total_exp,
        custom_stat_points=args.custom_stat_points,
        custom_talent_points=args.custom_talent_points,
    )


def run_cli(args: argparse.Namespace) -> int:
    """Execute the requested CLI mode against one save or a whole Players folder."""
    players_dir = resolve_players_dir(args.players_dir)
    save_dirs = list_save_dirs(players_dir, args.save_id)
    if not save_dirs:
        raise ValueError(bi("没有找到可处理的存档目录。", "No save directories found."))

    if args.target_level is not None:
        normalize_target_reward_level(args.target_level)
    normalize_custom_total_exp(args.custom_total_exp)
    normalize_custom_stat_points(args.custom_stat_points)
    normalize_custom_talent_points(args.custom_talent_points)

    repair_options = build_repair_options(args)
    for save_dir in save_dirs:
        if not save_dir.is_dir():
            print(f"{save_dir.name}: {bi('目录不存在，已跳过。', 'Directory not found, skipped.')}")
            continue

        if args.mode == "repair-vanilla-reset" and repair_options.backup:
            backup_dir = make_backup(save_dir)
            print(f"{save_dir.name}: {bi('已备份到', 'Backed up to')} {backup_dir}")

        if args.mode == "inspect":
            summary = inspect_save_data(save_dir)
            status, message = classify_summary(summary)
            print(describe_summary(summary, save_dir.name))
            print(f"  {bi('状态', 'Status')}: {status}")
            print(f"  {bi('诊断', 'Diagnosis')}: {message}")
            continue

        result = repair_save(save_dir, repair_options)
        before_level = display_level_from_reward_level(result.before.reward_level)
        after_level = display_level_from_reward_level(result.after.reward_level)
        print(f"{save_dir.name}:")
        print(
            f"  {bi('修复前', 'Before')}: "
            f"level={before_level} exp={result.before.total_exp} "
            f"stat={result.before.stat_points} talent={result.before.talent_points}"
        )
        print(
            f"  {bi('修复后', 'After')}: "
            f"level={after_level} exp={result.after.total_exp} "
            f"stat={result.after.stat_points} talent={result.after.talent_points}"
        )
        print(f"  {bi('清零节点数', 'Zeroed node count')}: {result.node_levels_zeroed}")
        print(f"  {bi('已写入存档。', 'Save updated.')}")

    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Launch the GUI when no arguments are supplied."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.gui or len(sys.argv) == 1:
        initial_players_dir = resolve_players_dir(args.players_dir) if args.players_dir else None
        return launch_gui(initial_players_dir)
    return run_cli(args)
