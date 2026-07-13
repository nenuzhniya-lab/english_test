"""Распознавание речи (для раздела Speaking). Реализация — позже (Whisper/облако)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class STTResult:
    text: str
    confidence: float = 0.0


class AbstractSTTProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio_path: str) -> STTResult:
        """Распознаёт речь из аудиофайла в текст."""
        ...


class StubSTTProvider(AbstractSTTProvider):
    """Заглушка: фиксирует интерфейс до подключения реального движка."""

    async def transcribe(self, audio_path: str) -> STTResult:
        raise NotImplementedError("STT провайдер ещё не реализован")
