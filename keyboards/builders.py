"""Доменные билдеры клавиатур → KeyboardSpec.

Правило раскладки: НАВИГАЦИЯ → reply (нижняя панель), ВЫБОР ОТВЕТА в тесте и
выбор значения настройки → inline (в сообщении).

Текстовые подписи reply-кнопок вынесены в константы — единый источник и для
билдеров здесь, и для текст-хендлеров (которые матчат нажатие по тексту).
"""
from __future__ import annotations

from typing import Any, List, Optional

import callbacks as cb
from models import ListeningText, difficulty_label
from keyboards.spec import Button, InlineSpec, ReplySpec, inline, grid

# ─────────────────────────── тексты reply-кнопок ───────────────────────────
# Главное меню
BTN_TESTS = "📝 Тесты"
BTN_LISTEN = "🎧 Аудирование"
BTN_SPEAK = "🗣 Говорение"
BTN_PROGRESS = "📊 Прогресс"
BTN_SETTINGS = "⚙️ Настройки"

# Меню тестов
BTN_WORDS = "📖 Слова"
BTN_VERBS = "🔄 Глаголы"
BTN_SENTENCES = "✍️ Предложения"
BTN_REVIEW = "🔁 Повторение"        # может иметь суффикс « (N)» — матчить по префиксу

# Панель во время теста
BTN_STOP = "⏹ Остановить тест"

# Аудирование
BTN_SLOW, BTN_NORM, BTN_FAST = "🐢 Медленно", "🚶 Нормально", "🏃 Быстро"
BTN_TRANSLATE = "🌐 Перевод"
BTN_BACK_LEVELS = "⬅️ К уровням"

# Настройки (разделы)
BTN_S_LEVEL = "🎚 Сложность"
BTN_S_TIME = "⏱ Таймер"
BTN_S_SIZE = "🔢 Вопросы"
BTN_S_VOICE = "🔊 Голос"

# Общие
BTN_BACK = "⬅️ Назад"   # всегда → главное меню (для top-level под-экранов)
BTN_HOME = "🏠 Меню"

_MENU_PLACEHOLDER = "Выбери раздел 👇"


# ─────────────────────────── главное меню ───────────────────────────
def main_menu() -> ReplySpec:
    return ReplySpec(
        rows=[
            [Button(BTN_TESTS), Button(BTN_LISTEN)],
            [Button(BTN_SPEAK), Button(BTN_PROGRESS)],
            [Button(BTN_SETTINGS)],
        ],
        placeholder=_MENU_PLACEHOLDER,
        persistent=True,
    )


# ─────────────────────────── тесты ───────────────────────────
def tests_menu(review_due: int = 0) -> ReplySpec:
    review = BTN_REVIEW + (f" ({review_due})" if review_due else "")
    return ReplySpec(
        rows=[
            [Button(BTN_WORDS), Button(BTN_VERBS)],
            [Button(BTN_SENTENCES), Button(review)],
            [Button(BTN_BACK)],
        ],
        placeholder="Выбери тип теста 👇",
    )


def quiz_options(qid: int, options: List[str]) -> InlineSpec:
    """Варианты ответа — по одному в ряд (длинные подписи)."""
    return inline(*[[Button(opt, cb.answer(qid, idx))] for idx, opt in enumerate(options)])


def quiz_reveal(options: List[str], correct: int, chosen: Optional[int],
                option_notes: Optional[List[Optional[str]]] = None) -> InlineSpec:
    """Итог вопроса: ✅ у правильного, ❌ у ошибочно выбранного. Остаётся в чате."""
    rows = []
    for idx, opt in enumerate(options):
        prefix = "✅ " if idx == correct else ("❌ " if idx == chosen else "▫️ ")
        label = prefix + opt
        if option_notes and option_notes[idx]:
            label += f" — {option_notes[idx]}"
        rows.append([Button(label, cb.NOOP)])
    return inline(*rows)


def test_panel() -> ReplySpec:
    """Нижняя панель во время теста — только остановка."""
    return ReplySpec(
        rows=[[Button(BTN_STOP)]],
        placeholder="Отвечай кнопками в сообщениях 👆",
    )


# ─────────────────────────── аудирование ───────────────────────────
def audio_levels(levels: List[str]) -> ReplySpec:
    """Выбор сложности аудио — reply-панель (🟢/🟡/🔴)."""
    return ReplySpec(
        rows=[
            [Button(difficulty_label(lvl)) for lvl in levels],
            [Button(BTN_BACK)],
        ],
        placeholder="Выбери сложность 👇",
    )


def audio_texts(texts: List[ListeningText]) -> InlineSpec:
    """Сетка номеров текстов (1..N) — inline."""
    buttons = [Button(str(i), cb.listen_open(t.id)) for i, t in enumerate(texts, 1)]
    return InlineSpec(rows=grid(buttons, per_row=6))


def audio_player() -> ReplySpec:
    """Плеер: скорости + перевод + назад к уровням."""
    return ReplySpec(
        rows=[
            [Button(BTN_SLOW), Button(BTN_NORM), Button(BTN_FAST)],
            [Button(BTN_TRANSLATE), Button(BTN_BACK_LEVELS)],
        ],
        placeholder="Слушай и листай тексты 👇",
    )


# ─────────────────────────── настройки ───────────────────────────
def settings_sections() -> ReplySpec:
    return ReplySpec(
        rows=[
            [Button(BTN_S_LEVEL), Button(BTN_S_TIME)],
            [Button(BTN_S_SIZE), Button(BTN_S_VOICE)],
            [Button(BTN_BACK)],
        ],
        placeholder="Что настроить 👇",
    )


def settings_values(options: List[tuple[Any, str]], current: Any, field: str, per_row: int = 2) -> InlineSpec:
    """Выбор значения настройки: ✅ у текущего. options = [(value, label), ...].

    Кнопки «Назад» нет — навигация в нижней reply-панели (разделы всегда под рукой).
    """
    buttons = []
    for value, lbl in options:
        mark = "✅ " if value == current else ""
        vstr = "none" if value is None else value
        buttons.append(Button(mark + lbl, cb.setting_apply(field, vstr)))
    return InlineSpec(rows=grid(buttons, per_row))


# ─────────────────────────── прогресс ───────────────────────────
def progress_screen(due: int) -> ReplySpec:
    rows = []
    if due:
        rows.append([Button(BTN_REVIEW + f" ({due})")])
    rows.append([Button(BTN_BACK)])
    return ReplySpec(rows=rows, placeholder="📊 Прогресс")


# ─────────────────────────── адаптив (смена уровня) ───────────────────────────
def level_suggestion(direction: str, target: str, current: Optional[str]) -> InlineSpec:
    verb = "⬆️ Повысить" if direction == "up" else "⬇️ Понизить"
    return inline(
        [Button(f"{verb} до {difficulty_label(target)}", cb.level_set(target))],
        [Button(f"Оставить {difficulty_label(current)}", cb.LEVEL_KEEP)],
    )
