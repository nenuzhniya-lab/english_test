from __future__ import annotations

from dataclasses import dataclass
from typing import Any

DEFAULT_VOICE = "en-US-AriaNeural"


@dataclass
class UserSettings:
    """Пользовательские настройки. quiz_seconds=0 → без таймера.

    `level` хранит КОД СЛОЖНОСТИ (EASY/MEDIUM/HARD) или None → «Все уровни».
    Имя поля историческое (раньше был CEFR-уровень); значение мигрировано
    в Difficulty миграцией m001. По умолчанию EASY — прогрессия с лёгкого,
    адаптив ведёт выше.
    """
    user_id: int
    level: str | None = "EASY"
    quiz_seconds: int = 15
    quiz_size: int = 10
    voice: str = DEFAULT_VOICE

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "level": self.level,
            "quiz_seconds": self.quiz_seconds,
            "quiz_size": self.quiz_size,
            "voice": self.voice,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserSettings":
        return cls(
            user_id=data["user_id"],
            level=data.get("level", "EASY"),
            quiz_seconds=data.get("quiz_seconds", 15),
            quiz_size=data.get("quiz_size", 10),
            voice=data.get("voice", DEFAULT_VOICE),
        )
