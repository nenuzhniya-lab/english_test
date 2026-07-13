"""Абстрактные репозитории (DAO).

Сервисы зависят ТОЛЬКО от этих интерфейсов. Добавление нового источника
(Google Sheets) = новый класс-реализация, без правок в services/handlers.
Методы async — чтобы сетевой GoogleSheetsRepository вписался без изменений выше.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from models import Word, IrregularVerb, ListeningText, Sentence, UserSettings, UserProgress


class AbstractWordRepository(ABC):
    """Контракт (LSP) для всех реализаций (PyFile, будущий GoogleSheets):
    get_all → всегда список (пустой при отсутствии данных, не None);
    get_by_id → Word или None (без исключений на «не найдено»).
    """

    @abstractmethod
    async def get_all(self) -> list[Word]: ...

    @abstractmethod
    async def get_by_id(self, word_id: int) -> Word | None: ...

    @abstractmethod
    async def get_random(self, count: int) -> list[Word]: ...


class AbstractVerbRepository(ABC):
    @abstractmethod
    async def get_all(self) -> list[IrregularVerb]: ...

    @abstractmethod
    async def get_by_id(self, verb_id: int) -> IrregularVerb | None: ...

    @abstractmethod
    async def get_random(self, count: int) -> list[IrregularVerb]: ...


class AbstractTextRepository(ABC):
    @abstractmethod
    async def get_all(self) -> list[ListeningText]: ...

    @abstractmethod
    async def get_by_id(self, text_id: int) -> ListeningText | None: ...


class AbstractSentenceRepository(ABC):
    @abstractmethod
    async def get_all(self) -> list[Sentence]: ...


class AbstractSettingsRepository(ABC):
    """Read-write: персональные настройки пользователя."""

    @abstractmethod
    async def get(self, user_id: int) -> UserSettings: ...

    @abstractmethod
    async def save(self, settings: UserSettings) -> None: ...


class AbstractStatsRepository(ABC):
    """Read-write: точность по уровням, разбитая по дням (для оконного адаптива).

    `day` — порядковый номер дня (date.toordinal()). Сервис задаёт окно.
    """

    @abstractmethod
    async def add(self, user_id: int, level: str, correct: int, total: int, day: int) -> None: ...

    @abstractmethod
    async def window(self, user_id: int, level: str, since_day: int) -> tuple[int, int]:
        """Суммарные (correct, total) по дням `>= since_day`."""
        ...

    @abstractmethod
    async def reset(self, user_id: int, level: str) -> None: ...


class AbstractProgressRepository(ABC):
    """Read-write: ежедневная активность (серия/цель)."""

    @abstractmethod
    async def get(self, user_id: int) -> UserProgress: ...

    @abstractmethod
    async def save(self, progress: UserProgress) -> None: ...


class AbstractMistakesRepository(ABC):
    """Read-write: лог фактических ошибок по (kind, ref). Отдельно от SRS-расписания."""

    @abstractmethod
    async def bump(self, user_id: int, kind: str, ref: int, day: str) -> None:
        """Неверный ответ: count += 1, streak = 0, last = day."""
        ...

    @abstractmethod
    async def get(self, user_id: int, kind: str, ref: int) -> tuple[int, int] | None:
        """(count, streak) или None, если ошибки по сущности нет."""
        ...

    @abstractmethod
    async def set_streak(self, user_id: int, kind: str, ref: int, streak: int) -> None: ...

    @abstractmethod
    async def remove(self, user_id: int, kind: str, ref: int) -> None: ...

    @abstractmethod
    async def entries(self, user_id: int) -> list[tuple[str, int, int, str]]:
        """Список (kind, ref, count, last) всех ошибок пользователя."""
        ...


class AbstractSrsRepository(ABC):
    """Read-write: интервальное повторение — коробка и срок по слову."""

    @abstractmethod
    async def get(self, user_id: int, word_id: int) -> tuple[int, int]:
        """(box, due_day). Для незнакомого слова — (0, 0)."""
        ...

    @abstractmethod
    async def set(self, user_id: int, word_id: int, box: int, due_day: int) -> None: ...

    @abstractmethod
    async def due(self, user_id: int, today: int) -> list[int]:
        """id слов, у которых подошёл срок (due_day <= today)."""
        ...

    @abstractmethod
    async def boxes(self, user_id: int) -> list[int]:
        """Номера коробок всех слов пользователя (для статистики)."""
        ...

    @abstractmethod
    async def users(self) -> list[int]:
        """Все пользователи с записями SRS (для напоминаний)."""
        ...
