from __future__ import annotations

from models import UserProgress
from repositories.base import AbstractProgressRepository
from repositories._jsonio import JsonStore


class JsonProgressRepository(JsonStore, AbstractProgressRepository):
    """Ежедневная активность в JSON: {user_id: {...}}."""

    def __init__(self, file_path: str):
        super().__init__(file_path)
        self._cache: dict[int, UserProgress] = {
            int(uid): UserProgress.from_dict(p) for uid, p in self._read().items()
        }

    async def _flush(self) -> None:
        data = {str(uid): p.to_dict() for uid, p in self._cache.items()}
        await self._write(data, indent=None)

    async def get(self, user_id: int) -> UserProgress:
        p = self._cache.get(user_id)
        if p is None:
            p = UserProgress(user_id=user_id)
            self._cache[user_id] = p
        return p

    async def save(self, progress: UserProgress) -> None:
        async with self._lock:
            self._cache[progress.user_id] = progress
            await self._flush()
