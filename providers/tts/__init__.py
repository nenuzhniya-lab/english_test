"""Озвучка (TTS): абстракция + реализация на edge-tts с файловым кэшем.

Движок меняется без правок выше по стеку (за AbstractTTSProvider).
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path

import edge_tts

logger = logging.getLogger(__name__)

_TIMEOUT = 30       # сек на одну генерацию
_RETRIES = 2        # доп. попыток после первой (итого до 3)
_BACKOFF = 0.5      # база задержки между попытками


class Speed(str, Enum):
    SLOW = "slow"
    NORMAL = "normal"
    FAST = "fast"


class AbstractTTSProvider(ABC):
    @abstractmethod
    async def synthesize(self, text: str, speed: Speed = Speed.NORMAL, voice: str | None = None) -> str:
        """Возвращает путь к аудиофайлу (mp3). voice=None → голос по умолчанию."""
        ...


class EdgeTTSProvider(AbstractTTSProvider):
    """TTS на edge-tts с файловым кэшем. Ключ кэша — хэш от (голос, скорость, текст).

    Устойчивость: генерация оборачивается таймаутом и ретраями; частично записанный
    файл при сбое удаляется, чтобы не закэшировать битый mp3.
    """

    _RATE = {Speed.SLOW: "-25%", Speed.NORMAL: "+0%", Speed.FAST: "+30%"}

    def __init__(self, default_voice: str, cache_dir: str):
        self._default_voice = default_voice
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, text: str, speed: Speed, voice: str) -> Path:
        key = f"{voice}|{speed.value}|{text}"
        digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
        return self._cache_dir / f"{digest}.mp3"

    async def synthesize(self, text: str, speed: Speed = Speed.NORMAL, voice: str | None = None) -> str:
        voice = voice or self._default_voice
        path = self._cache_path(text, speed, voice)
        if path.exists():
            return str(path)

        last_err: Exception | None = None
        for attempt in range(_RETRIES + 1):
            try:
                communicate = edge_tts.Communicate(text, voice, rate=self._RATE[speed])
                await asyncio.wait_for(communicate.save(str(path)), timeout=_TIMEOUT)
                if path.exists() and path.stat().st_size > 0:
                    return str(path)
                raise RuntimeError("edge-tts вернул пустой файл")
            except Exception as e:
                last_err = e
                path.unlink(missing_ok=True)
                logger.warning("TTS попытка %d/%d не удалась: %s", attempt + 1, _RETRIES + 1, e)
                if attempt < _RETRIES:
                    await asyncio.sleep(_BACKOFF * (attempt + 1))

        raise RuntimeError(f"Не удалось синтезировать аудио: {last_err}")
