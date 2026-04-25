from __future__ import annotations

"""Core save inspection and repair logic for Windrose save folders.

The game stores each save as a RocksDB directory. The tool works directly on
that database, reads the raw player progression blob from the `R5BLPlayer`
column family, locates a small set of BSON int32 fields by name, and then
patches only those values in place.
"""

import ctypes
import gc
import locale
import os
import re
import shutil
import struct
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# rocksdict is imported lazily inside functions to avoid interfering
# with tkinter when bundled as a frozen executable.


GAME_DIR_CANDIDATES = ("Windrose", "R5")
SUPPORTED_LANGS = {"auto", "zh", "en"}
SAVE_ID_PATTERN = re.compile(r"^[0-9A-F]{32}$")
DISPLAY_LEVEL_MIN = 1
UINT32_MAX = 0xFFFFFFFF

# Vanilla progression data indexed by the internal reward level.
# The UI shows level 1-15, while the stored RewardLevel is zero-based.
VANILLA_LEVELS = [
    {"Exp": 0, "TalentPointsReward": 0, "StatPointsReward": 0},
    {"Exp": 600, "TalentPointsReward": 0, "StatPointsReward": 4},
    {"Exp": 1200, "TalentPointsReward": 2, "StatPointsReward": 4},
    {"Exp": 1800, "TalentPointsReward": 2, "StatPointsReward": 4},
    {"Exp": 2400, "TalentPointsReward": 1, "StatPointsReward": 4},
    {"Exp": 3200, "TalentPointsReward": 1, "StatPointsReward": 3},
    {"Exp": 4000, "TalentPointsReward": 1, "StatPointsReward": 3},
    {"Exp": 4800, "TalentPointsReward": 1, "StatPointsReward": 3},
    {"Exp": 5600, "TalentPointsReward": 1, "StatPointsReward": 3},
    {"Exp": 6400, "TalentPointsReward": 0, "StatPointsReward": 3},
    {"Exp": 7400, "TalentPointsReward": 1, "StatPointsReward": 3},
    {"Exp": 8400, "TalentPointsReward": 0, "StatPointsReward": 3},
    {"Exp": 9400, "TalentPointsReward": 1, "StatPointsReward": 3},
    {"Exp": 10400, "TalentPointsReward": 0, "StatPointsReward": 3},
    {"Exp": 11400, "TalentPointsReward": 1, "StatPointsReward": 2},
]

DEFAULT_NODE_MAX_LEVELS = [60, 60, 60, 60, 60, 60, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3]
DISPLAY_LEVEL_MAX = len(VANILLA_LEVELS)


@dataclass
class ProgressionOffsets:
    reward_level: int | None
    total_exp: int | None
    progression_points: list[int]
    node_levels: list[int]


@dataclass
class ProgressionSummary:
    save_id: str
    reward_level: int | None
    total_exp: int | None
    stat_points: int | None
    talent_points: int | None
    spent_stat_points: int | None
    spent_talent_points: int | None
    node_level_count: int
    player_key: bytes
    value_size: int


@dataclass
class RepairOptions:
    backup: bool = False
    zero_nodes: bool = True
    fix_reward_level: bool = True
    fix_total_exp: bool = True
    fix_stat_points: bool = True
    fix_talent_points: bool = True
    target_reward_level: int | str | None = None
    custom_total_exp: int | str | None = None
    custom_stat_points: int | str | None = None
    custom_talent_points: int | str | None = None


@dataclass
class RepairTargets:
    reward_level: int
    total_exp: int
    stat_points: int
    talent_points: int


@dataclass
class RepairResult:
    before: ProgressionSummary
    after: ProgressionSummary
    node_levels_zeroed: int
    wrote_changes: bool


_LANG_PREFERENCE = "auto"
_DETECTED_LANG = "en"


def _normalize_language(value: str | None) -> str | None:
    if not value:
        return None
    lowered = value.strip().lower().replace("_", "-")
    if lowered.startswith("zh"):
        return "zh"
    if lowered.startswith("en"):
        return "en"
    return None


def detect_system_language() -> str:
    candidates: list[str | None] = []

    if os.name == "nt":
        try:
            lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            candidates.append(locale.windows_locale.get(lang_id))
        except Exception:
            pass

    for env_name in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        candidates.append(os.environ.get(env_name))

    try:
        lang_code, _ = locale.getlocale()
        candidates.append(lang_code)
    except Exception:
        pass

    for candidate in candidates:
        normalized = _normalize_language(candidate)
        if normalized is not None:
            return normalized

    return "en"


def refresh_auto_lang() -> str:
    global _DETECTED_LANG
    _DETECTED_LANG = detect_system_language()
    return _DETECTED_LANG


refresh_auto_lang()


def get_lang_preference() -> str:
    return _LANG_PREFERENCE


def get_lang() -> str:
    return _DETECTED_LANG if _LANG_PREFERENCE == "auto" else _LANG_PREFERENCE


def set_lang(lang: str) -> str:
    global _LANG_PREFERENCE

    normalized = (lang or "auto").strip().lower()
    if normalized not in SUPPORTED_LANGS:
        raise ValueError(f"Unsupported language: {lang}")

    _LANG_PREFERENCE = normalized
    if normalized == "auto":
        return refresh_auto_lang()
    return normalized


def bi(zh: str, en: str) -> str:
    return zh if get_lang() == "zh" else en


def normalize_save_id(save_id: str) -> str:
    normalized = (save_id or "").strip().upper()
    if not SAVE_ID_PATTERN.fullmatch(normalized):
        raise ValueError(
            bi(
                "存档 ID 必须是 32 位十六进制字符串。",
                "Save ID must be a 32-character hexadecimal string.",
            )
        )
    return normalized


def normalize_target_reward_level(value: int | str | None) -> int | None:
    if value is None:
        return None

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        raw_value: object = stripped
    else:
        raw_value = value

    try:
        display_level = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            bi(
                f"目标等级必须是 {DISPLAY_LEVEL_MIN} 到 {DISPLAY_LEVEL_MAX} 之间的整数。",
                f"Target level must be an integer between {DISPLAY_LEVEL_MIN} and {DISPLAY_LEVEL_MAX}.",
            )
        ) from exc

    if display_level < DISPLAY_LEVEL_MIN or display_level > DISPLAY_LEVEL_MAX:
        raise ValueError(
            bi(
                f"目标等级必须是 {DISPLAY_LEVEL_MIN} 到 {DISPLAY_LEVEL_MAX} 之间的整数。",
                f"Target level must be an integer between {DISPLAY_LEVEL_MIN} and {DISPLAY_LEVEL_MAX}.",
            )
        )

    return display_level - 1


def display_level_from_reward_level(reward_level: int | None) -> int | None:
    if reward_level is None:
        return None
    return reward_level + 1


def normalize_optional_u32(value: int | str | None, label_zh: str, label_en: str) -> int | None:
    if value is None:
        return None

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        raw_value: object = stripped
    else:
        raw_value = value

    try:
        normalized = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            bi(
                f"{label_zh}\u5fc5\u987b\u662f 0 \u5230 {UINT32_MAX} \u4e4b\u95f4\u7684\u6574\u6570\u3002",
                f"{label_en} must be an integer between 0 and {UINT32_MAX}.",
            )
        ) from exc

    if normalized < 0 or normalized > UINT32_MAX:
        raise ValueError(
            bi(
                f"{label_zh}\u5fc5\u987b\u662f 0 \u5230 {UINT32_MAX} \u4e4b\u95f4\u7684\u6574\u6570\u3002",
                f"{label_en} must be an integer between 0 and {UINT32_MAX}.",
            )
        )

    return normalized


def normalize_custom_total_exp(value: int | str | None) -> int | None:
    return normalize_optional_u32(value, "\u81ea\u5b9a\u4e49\u603b\u7ecf\u9a8c", "Custom total XP")


def normalize_custom_stat_points(value: int | str | None) -> int | None:
    return normalize_optional_u32(value, "\u81ea\u5b9a\u4e49\u5c5e\u6027\u70b9", "Custom stat points")


def normalize_custom_talent_points(value: int | str | None) -> int | None:
    return normalize_optional_u32(value, "\u81ea\u5b9a\u4e49\u5929\u8d4b\u70b9", "Custom talent points")


def get_default_save_roots() -> list[Path]:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        return []

    base = Path(local_app_data)
    roots: list[Path] = []
    for game_dir in GAME_DIR_CANDIDATES:
        candidate = base / game_dir / "Saved" / "SaveProfiles"
        if candidate.is_dir():
            roots.append(candidate)
    return roots


def discover_players_dirs() -> list[Path]:
    results: list[Path] = []
    for save_root in get_default_save_roots():
        for profile_dir in sorted(save_root.iterdir()):
            if not profile_dir.is_dir():
                continue
            rocksdb_root = profile_dir / "RocksDB"
            if not rocksdb_root.is_dir():
                continue
            for version_dir in sorted(rocksdb_root.iterdir()):
                players_dir = version_dir / "Players"
                if players_dir.is_dir():
                    results.append(players_dir)
    results.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return results


def resolve_players_dir(players_dir: Path | None) -> Path:
    if players_dir is not None:
        resolved = players_dir.resolve()
        if not resolved.is_dir():
            raise ValueError(
                bi(
                    f"Players 目录不存在: {resolved}",
                    f"Players directory not found: {resolved}",
                )
            )
        return resolved

    candidates = discover_players_dirs()
    if not candidates:
        raise ValueError(
            bi(
                "未能自动找到 Windrose 存档目录，请手动选择 Players 目录。",
                "Could not auto-detect the Windrose save directory. Please choose the Players folder manually.",
            )
        )
    return candidates[0]


def list_save_dirs(players_dir: Path, save_id: str | None = None) -> list[Path]:
    if save_id:
        return [players_dir / save_id]
    return sorted(path for path in players_dir.iterdir() if path.is_dir())


def list_column_families(db_path: Path) -> list[str]:
    from rocksdict import Rdict

    return Rdict.list_cf(str(db_path), _make_db_options())


def _make_db_options(*, create_if_missing: bool = False) -> "Options":
    """Build RocksDB options that keep reads/writes deterministic for save data.

    The tool intentionally disables compression so a rewritten DB keeps a simple
    layout and avoids introducing storage settings different from the source
    save.
    """
    from rocksdict import DBCompressionType, Options

    options = Options(raw_mode=True)
    options.set_compression_type(DBCompressionType.none())
    options.set_bottommost_compression_type(DBCompressionType.none())
    try:
        options.set_blob_compression_type(DBCompressionType.none())
    except Exception:
        pass
    if create_if_missing:
        options.create_if_missing(True)
        options.create_missing_column_families(True)
    return options


def open_db(db_path: Path, read_only: bool) -> "Rdict":
    """Open a save directory as a raw RocksDB database."""
    from rocksdict import AccessType, Rdict

    column_families = list_column_families(db_path)
    cf_options = {name: _make_db_options() for name in column_families if name != "default"}
    kwargs: dict[str, object] = {
        "options": _make_db_options(),
        "column_families": cf_options,
    }
    if read_only:
        kwargs["access_type"] = AccessType.read_only()
    return Rdict(str(db_path), **kwargs)


def _rename_dir_with_retry(source: Path, target: Path, retries: int = 20, delay: float = 0.1) -> None:
    last_error: Exception | None = None
    for _ in range(retries):
        try:
            source.rename(target)
            return
        except PermissionError as exc:
            last_error = exc
            time.sleep(delay)
    if last_error is not None:
        raise last_error


def _remove_tree_with_retry(path: Path, retries: int = 20, delay: float = 0.1) -> None:
    last_error: Exception | None = None
    for _ in range(retries):
        try:
            shutil.rmtree(path)
            return
        except PermissionError as exc:
            last_error = exc
            time.sleep(delay)
    if last_error is not None:
        raise last_error


def rewrite_db_without_compression(db_path: Path) -> None:
    """Clone a DB into a fresh uncompressed directory and swap it in place.

    This helper is not part of the normal repair flow, but it is useful for the
    ownership-rebinding test script when a DB needs to be rewritten cleanly.
    """
    from rocksdict import Rdict

    column_families = list_column_families(db_path)
    temp_dir = db_path.with_name(f"{db_path.name}.rewrite_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}")
    backup_dir = db_path.with_name(f"{db_path.name}.rewrite_backup_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}")

    source_db = open_db(db_path, read_only=True)
    try:
        target_db = Rdict(
            str(temp_dir),
            options=_make_db_options(create_if_missing=True),
            column_families={name: _make_db_options() for name in column_families if name != "default"},
        )
        try:
            for cf_name in column_families:
                source_cf = source_db if cf_name == "default" else source_db.get_column_family(cf_name)
                target_cf = target_db if cf_name == "default" else target_db.get_column_family(cf_name)
                for key, value in source_cf.items():
                    target_cf[key] = value
                del source_cf
                del target_cf
            target_db.flush()
        finally:
            target_db.close()
            del target_db
    finally:
        source_db.close()
        del source_db

    gc.collect()
    time.sleep(0.2)

    _rename_dir_with_retry(db_path, backup_dir)
    try:
        _rename_dir_with_retry(temp_dir, db_path)
    except Exception:
        _rename_dir_with_retry(backup_dir, db_path)
        raise

    _remove_tree_with_retry(backup_dir)


def read_u32(data: bytes, offset: int) -> int:
    return struct.unpack("<I", data[offset : offset + 4])[0]


def write_u32(data: bytearray, offset: int, value: int) -> None:
    data[offset : offset + 4] = struct.pack("<I", value)


def find_bson_int32_offsets(data: bytes, field_name: bytes) -> list[int]:
    """Locate BSON int32 field payloads by field name inside the raw blob.

    The save data is not decoded into a full document tree. Instead we search
    for the BSON type marker plus field name and return the offset of the 4-byte
    integer payload that follows it.
    """
    offsets: list[int] = []
    pattern = b"\x10" + field_name + b"\x00"
    start = 0
    while True:
        index = data.find(pattern, start)
        if index < 0:
            return offsets
        value_offset = index + len(pattern)
        if value_offset + 4 <= len(data):
            offsets.append(value_offset)
        start = index + 1


def collect_offsets(data: bytes) -> ProgressionOffsets:
    """Gather the specific progression fields that the repair tool knows how to fix."""
    reward_offsets = find_bson_int32_offsets(data, b"RewardLevel")
    total_exp_offsets = find_bson_int32_offsets(data, b"TotalExp")
    progression_points = find_bson_int32_offsets(data, b"ProgressionPoints")
    node_levels = find_bson_int32_offsets(data, b"NodeLevel")
    return ProgressionOffsets(
        reward_level=reward_offsets[0] if reward_offsets else None,
        total_exp=total_exp_offsets[0] if total_exp_offsets else None,
        progression_points=progression_points,
        node_levels=node_levels,
    )


def restore_default_node_caps(data: bytearray) -> None:
    """Restore the default MaxNodeLevel values after a skill-node reset."""
    max_node_offsets = find_bson_int32_offsets(bytes(data), b"MaxNodeLevel")
    for offset, default_value in zip(max_node_offsets, DEFAULT_NODE_MAX_LEVELS):
        write_u32(data, offset, default_value)


def summarize_progression(save_id: str, player_key: bytes, data: bytes) -> ProgressionSummary:
    """Read the current progression numbers from the raw player blob.

    The first six NodeLevel entries are treated as stat nodes and the remaining
    entries are treated as talent nodes, matching the current save layout used
    by the repair UI.
    """
    offsets = collect_offsets(data)
    points = [read_u32(data, offset) for offset in offsets.progression_points]
    node_values = [read_u32(data, offset) for offset in offsets.node_levels]
    spent_stat_points = None
    spent_talent_points = None
    if node_values:
        stat_node_values = node_values[:6]
        talent_node_values = node_values[6:]
        spent_stat_points = sum(stat_node_values)
        spent_talent_points = sum(talent_node_values)
    return ProgressionSummary(
        save_id=save_id,
        reward_level=read_u32(data, offsets.reward_level) if offsets.reward_level is not None else None,
        total_exp=read_u32(data, offsets.total_exp) if offsets.total_exp is not None else None,
        stat_points=points[0] if len(points) >= 1 else None,
        talent_points=points[1] if len(points) >= 2 else None,
        spent_stat_points=spent_stat_points,
        spent_talent_points=spent_talent_points,
        node_level_count=len(offsets.node_levels),
        player_key=player_key,
        value_size=len(data),
    )


def vanilla_totals_for_reward_level(reward_level: int) -> tuple[int, int]:
    clamped = max(0, min(reward_level, len(VANILLA_LEVELS) - 1))
    stat_points = sum(level["StatPointsReward"] for level in VANILLA_LEVELS[: clamped + 1])
    talent_points = sum(level["TalentPointsReward"] for level in VANILLA_LEVELS[: clamped + 1])
    return stat_points, talent_points


def vanilla_exp_for_reward_level(reward_level: int) -> int:
    clamped = max(0, min(reward_level, len(VANILLA_LEVELS) - 1))
    return int(VANILLA_LEVELS[clamped]["Exp"])


def vanilla_exp_range_for_reward_level(reward_level: int) -> tuple[int, int]:
    clamped = max(0, min(reward_level, len(VANILLA_LEVELS) - 1))
    lower = int(VANILLA_LEVELS[clamped]["Exp"])
    if clamped >= len(VANILLA_LEVELS) - 1:
        return lower, lower
    upper = int(VANILLA_LEVELS[clamped + 1]["Exp"]) - 1
    return lower, upper


def make_backup(save_dir: Path) -> Path:
    """Create a full directory backup outside the live Players folder.

    Backups are stored next to `Players` so the game does not try to scan them
    as additional saves during startup.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_root = save_dir.parent.parent / "_WindroseSaveTool_Backups"
    backup_root.mkdir(parents=True, exist_ok=True)
    backup_dir = backup_root / f"{save_dir.name}_{timestamp}"
    shutil.copytree(save_dir, backup_dir)
    return backup_dir


def copy_target_dir(save_dir: Path, output_dir: Path) -> Path:
    if output_dir.exists():
        raise ValueError(
            bi(
                f"输出目录已存在: {output_dir}",
                f"Output directory already exists: {output_dir}",
            )
        )
    shutil.copytree(save_dir, output_dir)
    return output_dir


def read_primary_player_id(save_dir: Path) -> str:
    db = open_db(save_dir, read_only=True)
    try:
        _, player_key, _ = get_player_entry(db)
        return normalize_save_id(player_key.decode("ascii", errors="ignore"))
    finally:
        db.close()


def rebind_save_to_player_id(save_dir: Path, target_save_id: str) -> Path:
    target_id = normalize_save_id(target_save_id)
    current_id = read_primary_player_id(save_dir)
    if target_id == current_id and save_dir.name == target_id:
        return save_dir

    target_dir = save_dir.parent / target_id
    if target_dir.exists() and target_dir.resolve() != save_dir.resolve():
        raise ValueError(
            bi(
                f"目标存档 ID 已存在: {target_dir}。请先移走现有存档。",
                f"Target save ID already exists: {target_dir}. Move the existing save first.",
            )
        )

    current_bytes = current_id.encode("ascii")
    target_bytes = target_id.encode("ascii")
    column_families = list_column_families(save_dir)
    db = open_db(save_dir, read_only=False)
    try:
        for cf_name in column_families:
            cf = db if cf_name == "default" else db.get_column_family(cf_name)
            updates: list[tuple[bytes | str | int, bytes | str | int, bytes]] = []
            deletes: list[bytes | str | int] = []

            for key, value in list(cf.items()):
                key_bytes = key if isinstance(key, bytes) else str(key).encode("utf-8", errors="ignore")
                new_key = key
                if current_bytes in key_bytes:
                    replaced_key = key_bytes.replace(current_bytes, target_bytes)
                    if replaced_key != key_bytes:
                        new_key = replaced_key if isinstance(key, bytes) else replaced_key.decode("utf-8", errors="ignore")

                new_value = value
                if isinstance(value, bytes) and current_bytes in value:
                    new_value = value.replace(current_bytes, target_bytes)

                if new_key != key or new_value != value:
                    updates.append((key, new_key, new_value))
                    if new_key != key:
                        deletes.append(key)

            for _, new_key, new_value in updates:
                cf[new_key] = new_value
            for old_key in deletes:
                del cf[old_key]
    finally:
        db.close()

    if save_dir.name != target_id:
        save_dir.rename(target_dir)
        return target_dir
    return save_dir


def get_player_entry(db: "Rdict") -> tuple["Rdict", bytes, bytes]:
    cf = db.get_column_family("R5BLPlayer")
    keys = list(cf.keys())
    if not keys:
        raise ValueError(bi("R5BLPlayer 列族为空。", "R5BLPlayer column family is empty."))
    key = keys[0]
    return cf, key, cf[key]


def inspect_save_data(save_dir: Path) -> ProgressionSummary | None:
    """Read and summarize the main player progression entry for one save."""
    try:
        column_families = list_column_families(save_dir)
    except Exception:
        return None

    if "R5BLPlayer" not in column_families:
        return None

    try:
        db = open_db(save_dir, read_only=True)
    except Exception:
        return None

    try:
        try:
            _, player_key, data = get_player_entry(db)
        except ValueError:
            return None
        return summarize_progression(save_dir.name, player_key, data)
    finally:
        db.close()


def summarize_issues(summary: ProgressionSummary | None) -> list[str]:
    """Compare a save summary against vanilla limits and consistency rules."""
    if summary is None:
        return [bi("没有玩家成长数据。", "No player progression data.")]

    issues: list[str] = []
    max_reward = len(VANILLA_LEVELS) - 1

    if summary.reward_level is None or summary.total_exp is None:
        issues.append(bi("缺少关键成长字段。", "Missing key progression fields."))
    else:
        if summary.reward_level > max_reward:
            issues.append(bi("等级超出原版上限。", "Reward level exceeds vanilla limits."))
        if summary.total_exp > VANILLA_LEVELS[-1]["Exp"]:
            issues.append(bi("总经验超出原版上限。", "Total XP exceeds vanilla limits."))
        if 0 <= summary.reward_level <= max_reward:
            lower, upper = vanilla_exp_range_for_reward_level(summary.reward_level)
            if summary.total_exp < lower or summary.total_exp > upper:
                issues.append(bi("经验值与等级不匹配。", "XP and reward level do not match."))

    if summary.reward_level is not None and 0 <= summary.reward_level <= max_reward:
        vanilla_stat_points, vanilla_talent_points = vanilla_totals_for_reward_level(summary.reward_level)
        if summary.stat_points is not None and summary.stat_points > vanilla_stat_points:
            issues.append(bi("属性点超出原版上限。", "Stat points exceed vanilla limits."))
        if summary.talent_points is not None and summary.talent_points > vanilla_talent_points:
            issues.append(bi("天赋点超出原版上限。", "Talent points exceed vanilla limits."))

    return issues


def has_suspicious_progression(summary: ProgressionSummary | None) -> bool:
    if summary is None:
        return False
    return bool(summarize_issues(summary))


def classify_summary(summary: ProgressionSummary | None) -> tuple[str, str]:
    if summary is None:
        return bi("未知", "Unknown"), bi("没有玩家成长数据。", "No player progression data.")

    issues = summarize_issues(summary)
    if not issues:
        return bi("正常", "OK"), bi("未发现明显越界值。", "No obvious out-of-range values.")
    return bi("可疑", "Suspicious"), " | ".join(issues)


def describe_summary(summary: ProgressionSummary | None, save_id: str) -> str:
    if summary is None:
        return f"{save_id}: {bi('没有玩家成长数据。', 'No player progression data.')}"

    try:
        player_key = summary.player_key.decode("utf-8", errors="ignore")
    except Exception:
        player_key = "<decode failed>"

    return (
        f"{summary.save_id}: "
        f"key={player_key} "
        f"level={display_level_from_reward_level(summary.reward_level)} "
        f"total_exp={summary.total_exp} "
        f"stat_points={summary.stat_points} "
        f"talent_points={summary.talent_points} "
        f"spent_stat_points={summary.spent_stat_points} "
        f"spent_talent_points={summary.spent_talent_points} "
        f"node_levels={summary.node_level_count} "
        f"bytes={summary.value_size}"
    )


def resolve_repair_targets(before: ProgressionSummary, options: RepairOptions) -> RepairTargets:
    """Compute the values that will be written back during repair.

    The default path is to restore values from the vanilla progression table.
    Optional custom values from the UI/CLI can then selectively override XP,
    stat points, or talent points.
    """
    original_reward = before.reward_level if before.reward_level is not None else 0
    validated_target_level = normalize_target_reward_level(options.target_reward_level)
    if validated_target_level is None:
        target_reward = min(original_reward, len(VANILLA_LEVELS) - 1)
    else:
        target_reward = validated_target_level

    target_exp = vanilla_exp_for_reward_level(target_reward)
    target_stat_points, target_talent_points = vanilla_totals_for_reward_level(target_reward)

    custom_total_exp = normalize_custom_total_exp(options.custom_total_exp)
    custom_stat_points = normalize_custom_stat_points(options.custom_stat_points)
    custom_talent_points = normalize_custom_talent_points(options.custom_talent_points)

    if custom_total_exp is not None:
        target_exp = custom_total_exp
    if custom_stat_points is not None:
        target_stat_points = custom_stat_points
    if custom_talent_points is not None:
        target_talent_points = custom_talent_points

    return RepairTargets(
        reward_level=target_reward,
        total_exp=target_exp,
        stat_points=target_stat_points,
        talent_points=target_talent_points,
    )


def repair_save(save_dir: Path, options: RepairOptions) -> RepairResult:
    """Patch the main player progression blob in place.

    This function does not rebuild the full save. It edits a copy of the raw
    value from `R5BLPlayer`, writes only the known progression integers, and
    then stores the patched bytes back under the same key.
    """
    db = open_db(save_dir, read_only=False)
    try:
        cf, player_key, original_data = get_player_entry(db)
        offsets = collect_offsets(original_data)
        before = summarize_progression(save_dir.name, player_key, original_data)

        if offsets.reward_level is None or offsets.total_exp is None or len(offsets.progression_points) < 2:
            raise ValueError(
                bi(
                    "未找到完整的成长数据块，无法自动修复。",
                    "Could not find a complete progression block to repair.",
                )
            )

        # Work on a mutable copy so every repair step is explicit and limited to
        # the few fields we intentionally support.
        patched = bytearray(original_data)
        targets = resolve_repair_targets(before, options)

        if options.fix_reward_level:
            write_u32(patched, offsets.reward_level, targets.reward_level)
        if options.fix_total_exp:
            write_u32(patched, offsets.total_exp, targets.total_exp)
        if options.fix_stat_points:
            write_u32(patched, offsets.progression_points[0], targets.stat_points)
        if options.fix_talent_points:
            write_u32(patched, offsets.progression_points[1], targets.talent_points)

        zeroed_count = 0
        if options.zero_nodes:
            # Reset all purchased node levels, then restore the default caps so
            # the game accepts future point allocation again.
            for offset in offsets.node_levels:
                write_u32(patched, offset, 0)
            restore_default_node_caps(patched)
            zeroed_count = len(offsets.node_levels)

        after = summarize_progression(save_dir.name, player_key, bytes(patched))
        cf[player_key] = bytes(patched)

        return RepairResult(
            before=before,
            after=after,
            node_levels_zeroed=zeroed_count,
            wrote_changes=True,
        )
    finally:
        db.close()
