from __future__ import annotations

from repositories.base import AbstractMistakesRepository
from repositories._jsonio import JsonStore


class JsonMistakesRepository(JsonStore, AbstractMistakesRepository):
    """Лог ошибок: {user_id: {kind: {ref: {"count": int, "streak": int, "last": "YYYY-MM-DD"}}}}.

    Ключ по (kind, ref) — id разных типов (word/verb/sentence) не конфликтуют.
    """

    def __init__(self, file_path: str):
        super().__init__(file_path)
        self._cache: dict = self._read()

    async def _flush(self) -> None:
        await self._write(self._cache)

    def _entry(self, user_id: int, kind: str, ref: int) -> dict | None:
        return self._cache.get(str(user_id), {}).get(kind, {}).get(str(ref))

    async def bump(self, user_id: int, kind: str, ref: int, day: str) -> None:
        async with self._lock:
            refs = self._cache.setdefault(str(user_id), {}).setdefault(kind, {})
            e = refs.setdefault(str(ref), {"count": 0, "streak": 0, "last": day})
            e["count"] += 1
            e["streak"] = 0
            e["last"] = day
            await self._flush()

    async def get(self, user_id: int, kind: str, ref: int) -> tuple[int, int] | None:
        e = self._entry(user_id, kind, ref)
        return (e["count"], e.get("streak", 0)) if e else None

    async def set_streak(self, user_id: int, kind: str, ref: int, streak: int) -> None:
        async with self._lock:
            e = self._entry(user_id, kind, ref)
            if e is not None:
                e["streak"] = streak
                await self._flush()

    async def remove(self, user_id: int, kind: str, ref: int) -> None:
        async with self._lock:
            kinds = self._cache.get(str(user_id), {})
            refs = kinds.get(kind, {})
            if refs.pop(str(ref), None) is not None:
                if not refs:
                    kinds.pop(kind, None)
                await self._flush()

    async def entries(self, user_id: int) -> list[tuple[str, int, int, str]]:
        result: list[tuple[str, int, int, str]] = []
        for kind, refs in self._cache.get(str(user_id), {}).items():
            for ref_str, e in refs.items():
                try:
                    result.append((kind, int(ref_str), e.get("count", 0), e.get("last", "")))
                except (TypeError, ValueError):
                    continue
        return result
