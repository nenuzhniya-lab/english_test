from __future__ import annotations

import datetime

from models.difficulty import DIFFICULTY_ORDER
from repositories.base import AbstractStatsRepository

# Ступени сложности слов по возрастанию (для адаптива).
# Крайние переходы (EASY↓, HARD↑) — no-op: индекс за границей не сдвигается.
WORD_LEVELS = [d.value for d in DIFFICULTY_ORDER]

_THRESH_UP = 85     # ≥ этого % → предложить уровень выше
_THRESH_DOWN = 45   # ≤ этого % → предложить уровень ниже
_MIN_ANSWERS = 8    # минимум ответов на уровне (в окне), чтобы советовать
WINDOW_DAYS = 7     # окно точности: последние N дней


class StatsService:
    """Точность по уровням за скользящее окно (7 дней) + совет сменить сложность."""

    def __init__(self, repo: AbstractStatsRepository):
        self._repo = repo

    @staticmethod
    def _since() -> int:
        today = datetime.date.today().toordinal()
        return today - (WINDOW_DAYS - 1)

    @staticmethod
    def _today() -> int:
        return datetime.date.today().toordinal()

    async def record(self, user_id: int, level: str | None, correct: bool) -> None:
        if level in WORD_LEVELS:
            await self._repo.add(user_id, level, 1 if correct else 0, 1, self._today())

    async def reset(self, user_id: int, level: str | None) -> None:
        if level in WORD_LEVELS:
            await self._repo.reset(user_id, level)

    async def accuracy_by_level(self, user_id: int) -> list[tuple[str, int, int]]:
        """Точность по уровням за последние 7 дней: [(код_сложности, верно, всего), ...].

        Только уровни, где были ответы в окне.
        """
        since = self._since()
        result: list[tuple[str, int, int]] = []
        for level in WORD_LEVELS:
            correct, total = await self._repo.window(user_id, level, since)
            if total:
                result.append((level, correct, total))
        return result

    async def suggestion(self, user_id: int, level: str | None) -> tuple[str, str, int] | None:
        """(direction, target_level, accuracy%) по окну 7 дней или None. direction: up|down."""
        if level not in WORD_LEVELS:
            return None
        correct, total = await self._repo.window(user_id, level, self._since())
        if total < _MIN_ANSWERS:
            return None
        acc = round(correct / total * 100)
        i = WORD_LEVELS.index(level)
        if acc >= _THRESH_UP and i < len(WORD_LEVELS) - 1:
            return "up", WORD_LEVELS[i + 1], acc
        if acc <= _THRESH_DOWN and i > 0:
            return "down", WORD_LEVELS[i - 1], acc
        return None
