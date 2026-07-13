"""Доменные модели контента: слово, неправильный глагол, текст, предложение."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from models.difficulty import Level


@dataclass(frozen=True)
class WordMeaning:
    """Одно значение слова. Слово может иметь несколько значений."""
    russian: str
    example_en: str | None = None
    example_ru: str | None = None


@dataclass(frozen=True)
class Word:
    id: int
    english: str
    transcription: str | None = None      # IPA, напр. "skuːl"
    ru: str | None = None                  # русская транскрипция, напр. "скул"
    level: Level = Level.A1
    topic: str = "general"
    meanings: list[WordMeaning] = field(default_factory=list)
    formation: str | None = None           # словообразование — точка расширения

    @property
    def primary_translation(self) -> str:
        """Основной перевод (первое значение) — для краткого показа и вариантов теста."""
        return self.meanings[0].russian if self.meanings else ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Word":
        return cls(
            id=data["id"],
            english=data["english"],
            transcription=data.get("transcription"),
            ru=data.get("ru"),
            level=Level(data.get("level", "A1")),
            topic=data.get("topic", "general"),
            meanings=[WordMeaning(**m) for m in data.get("meanings", [])],
            formation=data.get("formation"),
        )


@dataclass(frozen=True)
class IrregularVerb:
    id: int
    v1: str           # Present (infinitive)
    v2: str           # Past Simple
    v3: str           # Past Participle
    translation: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IrregularVerb":
        return cls(id=data["id"], v1=data["v1"], v2=data["v2"], v3=data["v3"],
                   translation=data["translation"])


@dataclass(frozen=True)
class ListeningText:
    id: int
    title: str
    content: str
    translation: str
    level: Level = Level.A1

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ListeningText":
        return cls(id=data["id"], title=data["title"], content=data["content"],
                   translation=data["translation"], level=Level(data.get("level", "A1")))


@dataclass(frozen=True)
class Sentence:
    id: int
    text: str            # с символом «_» на месте пропуска
    answer: str          # правильное слово
    translation: str | None = None

    @property
    def blanked(self) -> str:
        """Текст с видимым пропуском для показа пользователю."""
        return self.text.replace("_", "_____")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Sentence":
        return cls(id=data["id"], text=data["text"], answer=data["answer"],
                   translation=data.get("translation"))
