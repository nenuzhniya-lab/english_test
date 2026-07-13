"""Одноразовые идемпотентные миграции пользовательских JSON-данных.

Запуск на старте (bot.py → run_migrations) ДО загрузки репозиториями. Применённые
отмечаются в файле-маркере (settings.migrations_state_file) и повторно не идут.

m001: CEFR (A1..C1) → 3 уровня сложности (settings.json + stats.json).
m002: stats.json из кумулятивного в разбитый по дням.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable, Optional

from models.difficulty import WORD_CEFR_TO_DIFFICULTY, Difficulty

logger = logging.getLogger(__name__)

_DIFFICULTY_VALUES = {d.value for d in Difficulty}


def _rewrite(path: Path, transform: Callable[[dict[str, Any]], dict[str, Any]]) -> None:
    if not path.exists():
        return
    raw = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps(transform(raw), ensure_ascii=False, indent=2), encoding="utf-8")


# ─────────────────────────── m001: CEFR → Difficulty ───────────────────────────
M001_ID = "m001_cefr_to_difficulty"


def _to_difficulty(level: Optional[str]) -> Optional[str]:
    """CEFR-код или уже-сложность → код сложности. None → None."""
    if level is None:
        return None
    if level in _DIFFICULTY_VALUES:
        return level
    mapped = WORD_CEFR_TO_DIFFICULTY.get(level)
    return mapped.value if mapped else Difficulty.HARD.value


def m001_settings(data: dict[str, Any]) -> dict[str, Any]:
    """{uid: {..., level: CEFR}} → {uid: {..., level: Difficulty}}."""
    for user in data.values():
        if isinstance(user, dict) and "level" in user:
            user["level"] = _to_difficulty(user["level"])
    return data


def m001_stats(data: dict[str, Any]) -> dict[str, Any]:
    """{uid: {CEFR: {c,t}}} → {uid: {Difficulty: {c,t}}} со слиянием счётчиков."""
    result: dict[str, Any] = {}
    for uid, levels in data.items():
        if not isinstance(levels, dict):
            result[uid] = levels
            continue
        merged: dict[str, Any] = {}
        for lvl, ct in levels.items():
            key = _to_difficulty(lvl) or lvl
            acc = merged.setdefault(key, {"c": 0, "t": 0})
            acc["c"] += (ct or {}).get("c", 0)
            acc["t"] += (ct or {}).get("t", 0)
        result[uid] = merged
    return result


def _apply_m001(settings: Any) -> None:
    _rewrite(Path(settings.settings_file), m001_settings)
    _rewrite(Path(settings.stats_file), m001_stats)


# ─────────────────────────── m002: stats по дням ───────────────────────────
M002_ID = "m002_stats_windowed"
_ANCIENT_DAY = "0"


def _is_cumulative(level_dict: dict[str, Any]) -> bool:
    """Старый формат: у уровня прямо ключи c/t (int), а не дни."""
    return "c" in level_dict and isinstance(level_dict.get("c"), int)


def m002_stats(data: dict[str, Any]) -> dict[str, Any]:
    """{uid: {level: {c,t}}} → {uid: {level: {day: {c,t}}}} (старое под день '0')."""
    for user in data.values():
        if not isinstance(user, dict):
            continue
        for level, entry in list(user.items()):
            if isinstance(entry, dict) and _is_cumulative(entry):
                user[level] = {_ANCIENT_DAY: {"c": entry.get("c", 0), "t": entry.get("t", 0)}}
    return data


def _apply_m002(settings: Any) -> None:
    _rewrite(Path(settings.stats_file), m002_stats)


# ─────────────────────────── runner ───────────────────────────
# (id, apply) по порядку. Новую миграцию добавляем в конец.
_MIGRATIONS = [(M001_ID, _apply_m001), (M002_ID, _apply_m002)]


def _load_applied(path: Path) -> list[str]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        applied = data.get("applied", [])
        return applied if isinstance(applied, list) else []
    except (json.JSONDecodeError, OSError):
        logger.warning("Не удалось прочитать состояние миграций %s — считаю пустым", path)
        return []


def _save_applied(path: Path, applied: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"applied": applied}, ensure_ascii=False, indent=2), encoding="utf-8")


def run_migrations(settings: Any) -> None:
    """Применяет непроведённые миграции. Вызывать ДО build_container()."""
    state_path = Path(settings.migrations_state_file)
    applied = _load_applied(state_path)
    for mid, apply in _MIGRATIONS:
        if mid in applied:
            continue
        try:
            apply(settings)
        except Exception:
            logger.exception("Миграция %s упала — пропускаю (данные не тронуты)", mid)
            continue
        applied.append(mid)
        _save_applied(state_path, applied)
        logger.info("✅ Применена миграция %s", mid)
