from __future__ import annotations

from repositories.base import AbstractStatsRepository
from repositories._jsonio import JsonStore


class JsonStatsRepository(JsonStore, AbstractStatsRepository):
    """Точность по дням: {user_id: {level: {day: {"c": correct, "t": total}}}}.

    Разбивка по дням нужна для оконной точности («за 7 дней») и оконного адаптива.
    """

    def __init__(self, file_path: str):
        super().__init__(file_path)
        self._cache: dict = self._read()

    async def _flush(self) -> None:
        await self._write(self._cache)

    async def add(self, user_id: int, level: str, correct: int, total: int, day: int) -> None:
        async with self._lock:
            days = self._cache.setdefault(str(user_id), {}).setdefault(level, {})
            e = days.setdefault(str(day), {"c": 0, "t": 0})
            e["c"] += correct
            e["t"] += total
            await self._flush()

    async def window(self, user_id: int, level: str, since_day: int) -> tuple[int, int]:
        days = self._cache.get(str(user_id), {}).get(level, {})
        c = t = 0
        for day_str, e in days.items():
            try:
                if int(day_str) >= since_day:
                    c += e.get("c", 0)
                    t += e.get("t", 0)
            except (TypeError, ValueError):
                continue
        return c, t

    async def reset(self, user_id: int, level: str) -> None:
        async with self._lock:
            self._cache.get(str(user_id), {}).pop(level, None)
            await self._flush()
