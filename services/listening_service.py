from __future__ import annotations

from models import ListeningText
from models.difficulty import DIFFICULTY_ORDER, text_difficulty
from repositories.base import AbstractTextRepository
from providers.tts import AbstractTTSProvider, Speed


class ListeningService:
    def __init__(self, texts: AbstractTextRepository, tts: AbstractTTSProvider):
        self._texts = texts
        self._tts = tts

    async def levels(self) -> list[str]:
        """Сложности, для которых есть тексты (EASY/MEDIUM/HARD, по возрастанию)."""
        present = {text_difficulty(t.level.value) for t in await self._texts.get_all()}
        return [d.value for d in DIFFICULTY_ORDER if d in present]

    async def by_level(self, difficulty: str) -> list[ListeningText]:
        """Тексты выбранной сложности (difficulty — код EASY/MEDIUM/HARD)."""
        return [t for t in await self._texts.get_all()
                if text_difficulty(t.level.value).value == difficulty]

    async def get(self, text_id: int) -> ListeningText | None:
        return await self._texts.get_by_id(text_id)

    async def audio(self, text: ListeningText, speed: Speed, voice: str | None = None) -> str:
        return await self._tts.synthesize(text.content, speed, voice)
