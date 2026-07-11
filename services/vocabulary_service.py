from __future__ import annotations

from models.difficulty import word_difficulty
from repositories.base import AbstractWordRepository
from services.quiz_service import QuizItem

_MIN_ITEMS = 4  # минимум для теста (4 варианта); иначе игнорируем фильтр сложности


class VocabularyService:
    def __init__(self, words: AbstractWordRepository):
        self._words = words

    async def items(self, difficulty: str | None = None) -> list[QuizItem]:
        """Вопросы по словам. difficulty — код EASY/MEDIUM/HARD или None («все»)."""
        words = await self._words.get_all()
        if difficulty:
            filtered = [w for w in words if word_difficulty(w.level.value).value == difficulty]
            if len(filtered) >= _MIN_ITEMS:
                words = filtered  # иначе оставляем все — чтобы тест собрался
        items = []
        for w in words:
            if not w.primary_translation:
                continue
            ipa = f"[{w.transcription}]" if w.transcription else ""
            ru = f"[{w.ru}]" if w.ru else ""
            phon = " ".join(p for p in (ipa, ru) if p)
            items.append(
                QuizItem(
                    prompt=f"🇬🇧 <b>{w.english}</b>  {phon}\n\nКак переводится?".replace("  \n", "\n"),
                    answer=w.primary_translation,
                    ref=w.id,
                )
            )
        return items
