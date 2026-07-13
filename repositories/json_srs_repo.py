from __future__ import annotations

from repositories.base import AbstractSrsRepository
from repositories._jsonio import JsonStore


class JsonSrsRepository(JsonStore, AbstractSrsRepository):
    """Интервальное повторение: {user_id: {word_id: {"box": n, "due": day}}}."""

    def __init__(self, file_path: str):
        super().__init__(file_path)
        self._cache: dict = self._read()

    async def _flush(self) -> None:
        await self._write(self._cache, indent=None)

    async def get(self, user_id: int, word_id: int) -> tuple[int, int]:
        e = self._cache.get(str(user_id), {}).get(str(word_id))
        return (e["box"], e["due"]) if e else (0, 0)

    async def set(self, user_id: int, word_id: int, box: int, due_day: int) -> None:
        async with self._lock:
            self._cache.setdefault(str(user_id), {})[str(word_id)] = {"box": box, "due": due_day}
            await self._flush()

    async def due(self, user_id: int, today: int) -> list[int]:
        user = self._cache.get(str(user_id), {})
        return [int(wid) for wid, e in user.items() if e["due"] <= today]

    async def boxes(self, user_id: int) -> list[int]:
        return [e["box"] for e in self._cache.get(str(user_id), {}).values()]

    async def users(self) -> list[int]:
        return [int(uid) for uid in self._cache]
