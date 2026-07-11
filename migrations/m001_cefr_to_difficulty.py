"""m001: CEFR-уровни (A1..C1) → 3 уровня сложности (EASY/MEDIUM/HARD).

Затрагивает:
  • settings.json — поле `level` каждого пользователя (A1→EASY, A2→MEDIUM, B1/B2→HARD).
  • stats.json    — ключи уровней сливаются в сложности, счётчики c/t суммируются.

srs.json НЕ трогаем — там word_id, уровни не хранятся.

Идемпотентна: уже мигрированные значения (EASY/MEDIUM/HARD) остаются без изменений,
поэтому повторный прогон безопасен даже без файла-маркера.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from models.difficulty import WORD_CEFR_TO_DIFFICULTY, Difficulty

MIGRATION_ID = "m001_cefr_to_difficulty"

logger = logging.getLogger(__name__)

_DIFFICULTY_VALUES = {d.value for d in Difficulty}


def _to_difficulty(level: str | None) -> str | None:
    """CEFR-код или уже-сложность → код сложности. None → None."""
    if level is None:
        return None
    if level in _DIFFICULTY_VALUES:
        return level  # уже мигрировано
    mapped = WORD_CEFR_TO_DIFFICULTY.get(level)
    return mapped.value if mapped else Difficulty.HARD.value


def migrate_settings(data: dict) -> dict:
    """{uid: {..., level: CEFR}} → {uid: {..., level: Difficulty}}."""
    for user in data.values():
        if isinstance(user, dict) and "level" in user:
            user["level"] = _to_difficulty(user["level"])
    return data


def migrate_stats(data: dict) -> dict:
    """{uid: {CEFR: {c,t}}} → {uid: {Difficulty: {c,t}}} со слиянием счётчиков."""
    result: dict = {}
    for uid, levels in data.items():
        if not isinstance(levels, dict):
            result[uid] = levels
            continue
        merged: dict = {}
        for lvl, ct in levels.items():
            key = _to_difficulty(lvl) or lvl
            acc = merged.setdefault(key, {"c": 0, "t": 0})
            acc["c"] += (ct or {}).get("c", 0)
            acc["t"] += (ct or {}).get("t", 0)
        result[uid] = merged
    return result


def _rewrite(path: Path, transform) -> None:
    if not path.exists():
        return
    raw = json.loads(path.read_text(encoding="utf-8"))
    migrated = transform(raw)
    path.write_text(json.dumps(migrated, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("m001: обновлён %s", path.name)


def apply(settings) -> None:
    _rewrite(Path(settings.settings_file), migrate_settings)
    _rewrite(Path(settings.stats_file), migrate_stats)
