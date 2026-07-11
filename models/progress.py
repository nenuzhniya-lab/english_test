from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProgressSnapshot:
    """Готовый срез прогресса для экрана (агрегат streak + SRS-коробки + точность)."""
    # серия/цель (из UserProgress)
    streak: int
    best: int
    today: int
    goal: int
    total: int
    level: str | None
    # SRS-группы
    new: int
    familiar: int
    learned: int
    studying: int
    due: int
    # точность по уровням: [(код_сложности, верно, всего), ...]
    accuracy: list[tuple[str, int, int]] = field(default_factory=list)


@dataclass
class UserProgress:
    """Ежедневная активность: серия дней, ответов сегодня, рекорд, всего."""
    user_id: int
    day: int = 0       # ordinal последнего активного дня
    today: int = 0     # ответов за этот день
    streak: int = 0    # серия дней подряд
    best: int = 0      # рекорд серии
    total: int = 0     # всего ответов

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id, "day": self.day, "today": self.today,
            "streak": self.streak, "best": self.best, "total": self.total,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "UserProgress":
        return cls(
            user_id=d["user_id"], day=d.get("day", 0), today=d.get("today", 0),
            streak=d.get("streak", 0), best=d.get("best", 0), total=d.get("total", 0),
        )
