"""Сессии экранов (состояние теста, контекст аудио, id служебной панели) с TTL.

Значения — JSON-сериализуемые (dict/int/str/list): состояние теста и аудио
хранятся как `to_dict()`. Если задан `path`, стор зеркалит себя в JSON-файл и
загружается при старте — активный тест переживает redeploy (на Railway-volume).
TTL считается по wall-clock (`time.time`), чтобы истечение работало и после рестарта.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_DEFAULT_TTL = 60 * 60  # 1 час на брошенную сессию

# На диск пишем только эти ключи (переживают redeploy). `panel:<uid>` (id служебного
# сообщения) — транзиентный, часто меняется при навигации → держим только в памяти,
# чтобы не писать файл на каждый переход экрана.
_PERSIST_PREFIXES = ("quiz:", "listen:")


class SessionStore:
    """Ключ → значение с истечением по TTL. Ключи: 'quiz:<uid>' / 'listen:<uid>' / 'panel:<uid>'."""

    def __init__(self, ttl_seconds: int = _DEFAULT_TTL, path: Optional[str] = None):
        self._ttl = ttl_seconds
        self._path = Path(path) if path else None
        self._store: dict[str, tuple[float, Any]] = {}
        if self._path is not None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._load()

    def _now(self) -> float:
        return time.time()

    # ── персистентность ──
    def _load(self) -> None:
        assert self._path is not None
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning("Не удалось прочитать сессии %s — начинаю с пустого", self._path)
            return
        now = self._now()
        store: dict[str, tuple[float, Any]] = {}
        for key, entry in (raw.items() if isinstance(raw, dict) else []):
            try:
                exp = float(entry[0])
                value = entry[1]
            except (TypeError, IndexError, ValueError):
                continue
            if exp > now:
                store[key] = (exp, value)
        self._store = store

    def _persistent(self, key: str) -> bool:
        return self._path is not None and key.startswith(_PERSIST_PREFIXES)

    def _flush(self) -> None:
        if self._path is None:
            return
        try:
            data = {k: [exp, val] for k, (exp, val) in self._store.items()
                    if k.startswith(_PERSIST_PREFIXES)}
            self._path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except OSError:
            logger.exception("Не удалось сохранить сессии в %s", self._path)

    # ── доступ ──
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
            if self._persistent(key):
                self._flush()
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._sweep()
        self._store[key] = (self._now() + self._ttl, value)
        if self._persistent(key):
            self._flush()

    def pop(self, key: str) -> None:
        if self._store.pop(key, None) is not None and self._persistent(key):
            self._flush()
