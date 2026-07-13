"""View-слой: форматирование сообщений (чистые функции модель → HTML) + строки.

Собрано в один модуль (карточки, экран прогресса с юникод-барами, справочник строк).
"""
from __future__ import annotations

from models import ListeningText, UserSettings, ProgressSnapshot, difficulty_label
from settings_catalog import (
    LEVEL_OPTIONS, TIME_OPTIONS, SIZE_OPTIONS, VOICE_OPTIONS, label_for,
)

# ─────────────────────────── строки (задел под i18n) ───────────────────────────
SECTION_TITLE = {
    "vocabulary": "📖 Слова",
    "verbs": "🔄 Глаголы",
    "sentences": "✍️ Предложения",
    "review": "🔁 Повторение",
    "mistakes": "❗ Мои ошибки",
    "study": "⚡ Учить сейчас",
}
SECTION_FALLBACK = "❓ Тест"


# ─────────────────────────── карточки ───────────────────────────
def text_view(text: ListeningText) -> str:
    return (
        f"📄 <b>{text.title}</b>  [{text.level.value}]\n\n"
        f"{text.content}\n\n"
        f"<i>Выбери скорость снизу, листай тексты ⬅️ ➡️</i>"
    )


def settings_view(s: UserSettings) -> str:
    return (
        "⚙️ <b>Настройки</b>\n\n"
        f"🎚 Сложность: <b>{label_for(LEVEL_OPTIONS, s.level)}</b>\n"
        f"⏱ Время на ответ: <b>{label_for(TIME_OPTIONS, s.quiz_seconds)}</b>\n"
        f"🔢 Вопросов в тесте: <b>{label_for(SIZE_OPTIONS, s.quiz_size)}</b>\n"
        f"🔊 Голос озвучки: <b>{label_for(VOICE_OPTIONS, s.voice)}</b>\n\n"
        "<i>Выбери, что изменить 👇</i>"
    )


# ─────────────────────────── экран прогресса ───────────────────────────
_FILLED = "█"
_EMPTY = "░"


def render_bar(value: int, total: int, width: int = 10) -> str:
    """Полоса из юникод-блоков: доля value/total на ширину width."""
    if total <= 0:
        return _EMPTY * width
    filled = round(value / total * width)
    filled = max(0, min(width, filled))
    return _FILLED * filled + _EMPTY * (width - filled)


def _pad(label: str, width: int = 11) -> str:
    return label + " " * max(0, width - len(label))


def render_progress(s: ProgressSnapshot) -> str:
    lines = ["📊 <b>Твой прогресс</b>", ""]

    best = f" (рекорд {s.best})" if s.best > s.streak else ""
    lines.append(f"🔥 Серия: <b>{s.streak}</b> дн.{best}")
    lines.append(f"🎯 Сегодня: <b>{s.today}/{s.goal}</b> ответов")
    lines.append(f"🎚 Сложность: <b>{difficulty_label(s.level)}</b>")
    lines.append("")

    if s.studying:
        lines.append("<b>Слова в изучении</b>")
        lines.append("<code>")
        for emoji, name, val in (
            ("🌱", "Новые", s.new),
            ("📚", "Знакомые", s.familiar),
            ("✅", "Выучено", s.learned),
        ):
            bar = render_bar(val, s.studying)
            lines.append(f"{emoji} {_pad(name)}{bar} {val}")
        lines.append("</code>")
    else:
        lines.append("<i>Пройди «📝 Тесты» → 📖 Слова — и здесь появится прогресс.</i>")

    if s.accuracy:
        lines.append("")
        lines.append("<b>Точность за 7 дней</b>")
        lines.append("<code>")
        for code, correct, total in s.accuracy:
            pct = round(correct / total * 100) if total else 0
            bar = render_bar(pct, 100)
            lines.append(f"{_pad(difficulty_label(code), 12)}{bar} {pct}%")
        lines.append("</code>")

    lines.append("")
    lines.append(f"🔁 Ждут повторения: <b>{s.due}</b>")
    return "\n".join(lines)
