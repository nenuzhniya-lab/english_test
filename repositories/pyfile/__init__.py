"""Read-only репозитории контента из .py-источников (list[dict] → доменные модели).

Данные иммутабельны и грузятся один раз в память — для read-only контента этого
достаточно (KISS). Переход на Google Sheets = новый класс с тем же интерфейсом.
"""
from __future__ import annotations

import random

from models import Word, IrregularVerb, ListeningText, Sentence
from repositories.base import (
    AbstractWordRepository,
    AbstractVerbRepository,
    AbstractTextRepository,
    AbstractSentenceRepository,
)


class PyFileWordRepository(AbstractWordRepository):
    def __init__(self, source: list[dict]):
        self._words: list[Word] = [Word.from_dict(row) for row in source]
        self._by_id: dict[int, Word] = {w.id: w for w in self._words}

    async def get_all(self) -> list[Word]:
        return list(self._words)

    async def get_by_id(self, word_id: int) -> Word | None:
        return self._by_id.get(word_id)

    async def get_random(self, count: int) -> list[Word]:
        return random.sample(self._words, min(count, len(self._words)))


class PyFileVerbRepository(AbstractVerbRepository):
    def __init__(self, source: list[dict]):
        self._verbs: list[IrregularVerb] = [IrregularVerb.from_dict(row) for row in source]
        self._by_id: dict[int, IrregularVerb] = {v.id: v for v in self._verbs}

    async def get_all(self) -> list[IrregularVerb]:
        return list(self._verbs)

    async def get_by_id(self, verb_id: int) -> IrregularVerb | None:
        return self._by_id.get(verb_id)

    async def get_random(self, count: int) -> list[IrregularVerb]:
        return random.sample(self._verbs, min(count, len(self._verbs)))


class PyFileTextRepository(AbstractTextRepository):
    def __init__(self, source: list[dict]):
        self._texts: list[ListeningText] = [ListeningText.from_dict(row) for row in source]
        self._by_id: dict[int, ListeningText] = {t.id: t for t in self._texts}

    async def get_all(self) -> list[ListeningText]:
        return list(self._texts)

    async def get_by_id(self, text_id: int) -> ListeningText | None:
        return self._by_id.get(text_id)


class PyFileSentenceRepository(AbstractSentenceRepository):
    def __init__(self, source: list[dict]):
        self._items: list[Sentence] = [Sentence.from_dict(row) for row in source]

    async def get_all(self) -> list[Sentence]:
        return list(self._items)
