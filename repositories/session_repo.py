"""In-memory сессии экранов (состояние теста, контекст аудирования) с TTL.

Зачем отдельный репозиторий, а не aiogram FSM: чтобы ViewModel держала состояние
без зависимости от Telegram и была тестируема. Состояние эфемерно (как и FSM
MemoryStorage) — переживать redeploy не обязано; TTL чистит брошенные сессии.
"""
from __future__ import annotations

import time
from typing import Any, Optional

_DEFAULT_TTL = 60 * 60  # 1 час на брошенную сессию


class SessionStore:
    """Ключ → значение с истечением по TTL. Ключи строим как 'namespace:user_id'."""

    def __init__(self, ttl_seconds: int = _DEFAULT_TTL):
        self._ttl = ttl_seconds
        self._store: dict[str, tuple[float, Any]] = {}

    def _now(self) -> float:
        return time.monotonic()

    def _sweep(self) -> None:
        now = self._now()
        expired = [k for k, (exp, _) in self._store.items() if exp <= now]
        for k in expired:
            del self._store[k]

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            return None
        exp, value = entry
        if exp <= self._now():
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._sweep()
        self._store[key] = (self._now() + self._ttl, value)

    def pop(self, key: str) -> None:
        self._store.pop(key, None)
