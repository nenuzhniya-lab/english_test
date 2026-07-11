"""Доменное описание клавиатур — БЕЗ aiogram.

ViewModel отдаёт спеку (что за кнопки и как разложены), а `factory.to_markup`
превращает её в конкретный aiogram-markup. Так решение «reply vs inline» и сам
набор кнопок тестируются без Telegram.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Union


@dataclass(frozen=True)
class Button:
    """Кнопка. Для inline обязателен `data` (callback_data); для reply хватает `text`."""
    text: str
    data: Optional[str] = None


@dataclass(frozen=True)
class InlineSpec:
    """Inline-клавиатура (кнопки в сообщении). Каждая кнопка обязана иметь `data`."""
    rows: List[List[Button]]


@dataclass(frozen=True)
class ReplySpec:
    """Reply-клавиатура (нижняя панель навигации)."""
    rows: List[List[Button]]
    placeholder: Optional[str] = None
    persistent: bool = False
    resize: bool = True


KeyboardSpec = Union[InlineSpec, ReplySpec]


# ── Хелперы сборки строк (DRY для билдеров) ──
def inline(*rows: List[Button]) -> InlineSpec:
    return InlineSpec(rows=list(rows))


def grid(buttons: List[Button], per_row: int) -> List[List[Button]]:
    """Раскладывает плоский список кнопок в сетку по `per_row` в ряд."""
    return [buttons[i:i + per_row] for i in range(0, len(buttons), per_row)]
