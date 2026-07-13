"""Лог фактических ошибок + правило реабилитации.

Отличается от SRS: SRS — ритм повторения по расписанию; здесь — «долг» по словам,
где пользователь ошибся, пока не отработает их (K верных подряд → из лога уходит).
"""
from __future__ import annotations

import datetime

from repositories.base import AbstractMistakesRepository

_REHAB_STREAK = 2  # столько верных подряд — и слово «реабилитировано» (уходит из ошибок)


class MistakesService:
    def __init__(self, repo: AbstractMistakesRepository):
        self._repo = repo

    @staticmethod
    def _today() -> str:
        return datetime.date.today().isoformat()

    async def record_wrong(self, user_id: int, kind: str, ref: int) -> None:
        await self._repo.bump(user_id, kind, ref, self._today())

    async def record_correct(self, user_id: int, kind: str, ref: int) -> None:
        """Если слово в логе ошибок — растим серию; на _REHAB_STREAK убираем из лога."""
        entry = await self._repo.get(user_id, kind, ref)
        if entry is None:
            return
        _count, streak = entry
        streak += 1
        if streak >= _REHAB_STREAK:
            await self._repo.remove(user_id, kind, ref)
        else:
            await self._repo.set_streak(user_id, kind, ref, streak)

    async def count(self, user_id: int) -> int:
        return len(await self._repo.entries(user_id))

    async def top(self, user_id: int, limit: int | None = None) -> list[tuple[str, int]]:
        """(kind, ref) по убыванию частоты, затем свежести. Для наполнения режима «Мои ошибки»."""
        entries = await self._repo.entries(user_id)
        entries.sort(key=lambda e: (e[2], e[3]), reverse=True)  # count, last
        pairs = [(kind, ref) for kind, ref, _count, _last in entries]
        return pairs[:limit] if limit else pairs
