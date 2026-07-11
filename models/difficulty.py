"""Три уровня сложности вместо шести CEFR — единый источник правды.

Исходный контент размечен по CEFR (A1..C1). Пользователю показываем 3 уровня.
Маппинг CEFR → Difficulty РАЗНЫЙ для слов и текстов — так распределение объёма
получается ровным (иначе HARD-слов было бы 33 на всю категорию):

  Слова (999):  EASY=A1(511)   MEDIUM=A2(314)      HARD=B1+B2(174)
  Тексты (150): EASY=A1+A2(60) MEDIUM=B1+B2(60)    HARD=C1(30)

Ребалансировка живёт здесь, в маппере — файлы data/*.py не трогаем.
"""
from __future__ import annotations

from enum import Enum


class Difficulty(str, Enum):
    """Уровень сложности. str-Enum — удобно сериализовать в JSON и сравнивать."""
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"

    @property
    def order(self) -> int:
        return DIFFICULTY_ORDER.index(self)


DIFFICULTY_ORDER: list[Difficulty] = [Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD]

# Подписи для кнопок/представления. None → «все уровни».
DIFFICULTY_LABEL: dict[str, str] = {
    Difficulty.EASY.value: "🟢 Лёгкий",
    Difficulty.MEDIUM.value: "🟡 Средний",
    Difficulty.HARD.value: "🔴 Сложный",
}
ALL_LABEL = "🌍 Все"

# CEFR-код (строка) → Difficulty. Два маппера — см. модульный docstring.
WORD_CEFR_TO_DIFFICULTY: dict[str, Difficulty] = {
    "A1": Difficulty.EASY,
    "A2": Difficulty.MEDIUM,
    "B1": Difficulty.HARD,
    "B2": Difficulty.HARD,
    "C1": Difficulty.HARD,
    "C2": Difficulty.HARD,
}
TEXT_CEFR_TO_DIFFICULTY: dict[str, Difficulty] = {
    "A1": Difficulty.EASY,
    "A2": Difficulty.EASY,
    "B1": Difficulty.MEDIUM,
    "B2": Difficulty.MEDIUM,
    "C1": Difficulty.HARD,
    "C2": Difficulty.HARD,
}


def word_difficulty(cefr: str) -> Difficulty:
    """Сложность слова по его CEFR-коду (неизвестный код → HARD, а не падение)."""
    return WORD_CEFR_TO_DIFFICULTY.get(cefr, Difficulty.HARD)


def text_difficulty(cefr: str) -> Difficulty:
    """Сложность текста по его CEFR-коду (неизвестный код → HARD)."""
    return TEXT_CEFR_TO_DIFFICULTY.get(cefr, Difficulty.HARD)


def difficulty_label(code: str | None) -> str:
    """Подпись сложности для отображения. None → «🌍 Все»."""
    if code is None:
        return ALL_LABEL
    return DIFFICULTY_LABEL.get(code, code)


_LABEL_TO_CODE = {label: code for code, label in DIFFICULTY_LABEL.items()}


def label_to_difficulty(label: str) -> str | None:
    """Подпись reply-кнопки → код сложности (для разбора нажатия). Неизвестная → None."""
    return _LABEL_TO_CODE.get(label)
