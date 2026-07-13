from __future__ import annotations

from models import UserSettings
from repositories.base import AbstractSettingsRepository
from repositories._jsonio import JsonStore


class JsonSettingsRepository(JsonStore, AbstractSettingsRepository):
    """Настройки пользователей в одном JSON-файле {user_id: settings}."""

    def __init__(self, file_path: str):
        super().__init__(file_path)
        self._cache: dict[int, UserSettings] = {
            int(uid): UserSettings.from_dict(s) for uid, s in self._read().items()
        }

    async def _flush(self) -> None:
        data = {str(uid): s.to_dict() for uid, s in self._cache.items()}
        await self._write(data)

    async def get(self, user_id: int) -> UserSettings:
        s = self._cache.get(user_id)
        if s is None:
            s = UserSettings(user_id=user_id)
            self._cache[user_id] = s
        return s

    async def save(self, settings: UserSettings) -> None:
        async with self._lock:
            self._cache[settings.user_id] = settings
            await self._flush()
