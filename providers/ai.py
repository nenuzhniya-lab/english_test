"""Абстракция LLM/AI (генерация вопросов, разбор ошибок). Реализация — позже."""
from __future__ import annotations

from abc import ABC, abstractmethod


class AbstractAIProvider(ABC):
    @abstractmethod
    async def complete(self, prompt: str) -> str:
        """Базовый текстовый запрос к модели."""
        ...


class StubAIProvider(AbstractAIProvider):
    """Заглушка: фиксирует интерфейс до подключения реальной модели."""

    async def complete(self, prompt: str) -> str:
        raise NotImplementedError("AI провайдер ещё не реализован")
