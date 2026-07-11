"""Прогон миграций данных на старте.

Хранит список применённых миграций в файле-маркере и применяет только новые.
Порядок в _MIGRATIONS = порядок применения.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from migrations import m001_cefr_to_difficulty

logger = logging.getLogger(__name__)

# Список миграций по порядку. Новую добавляем в конец.
_MIGRATIONS = [m001_cefr_to_difficulty]


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


def run_migrations(settings) -> None:
    """Применяет непроведённые миграции. Вызывать ДО build_container()."""
    state_path = Path(settings.migrations_state_file)
    applied = _load_applied(state_path)
    for migration in _MIGRATIONS:
        if migration.MIGRATION_ID in applied:
            continue
        try:
            migration.apply(settings)
        except Exception:
            logger.exception("Миграция %s упала — пропускаю (данные не тронуты)", migration.MIGRATION_ID)
            continue
        applied.append(migration.MIGRATION_ID)
        _save_applied(state_path, applied)
        logger.info("✅ Применена миграция %s", migration.MIGRATION_ID)
