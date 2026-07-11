"""ViewModel настроек: разделы (reply) + выбор значения (inline)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List

from keyboards.spec import InlineSpec

from keyboards import builders as kb
from models import difficulty_label
from presenters import settings_view
from services.settings_service import SettingsService
from services.stats_service import StatsService
from settings_catalog import LEVEL_OPTIONS, TIME_OPTIONS, SIZE_OPTIONS, VOICE_OPTIONS
from viewmodels.base import Effect, EditCurrent, Notify, Send, SwapPanel, ViewState


@dataclass(frozen=True)
class _Field:
    section_text: str   # текст reply-кнопки раздела
    model_field: str    # поле UserSettings
    options: List[tuple[Any, str]]   # [(value, label), ...]
    title: str
    per_row: int


# cb-ключ поля → конфиг. cb-ключ используется в callback_data (set:<field>:v:<value>).
_FIELDS = {
    "level": _Field(kb.BTN_S_LEVEL, "level", LEVEL_OPTIONS,
                    "🎚 <b>Сложность</b>\nКакие слова показывать в тестах:", 2),
    "time": _Field(kb.BTN_S_TIME, "quiz_seconds", TIME_OPTIONS,
                   "⏱ <b>Время на ответ</b>\nСколько секунд на вопрос:", 2),
    "size": _Field(kb.BTN_S_SIZE, "quiz_size", SIZE_OPTIONS,
                   "🔢 <b>Вопросов в тесте</b>\nДлина одной сессии:", 3),
    "voice": _Field(kb.BTN_S_VOICE, "voice", VOICE_OPTIONS,
                    "🔊 <b>Голос озвучки</b>\nАкцент и пол диктора:", 2),
}
_BY_SECTION_TEXT = {f.section_text: (cb_field, f) for cb_field, f in _FIELDS.items()}


class SettingsViewModel:
    def __init__(self, settings: SettingsService, stats: StatsService):
        self._settings = settings
        self._stats = stats

    async def open(self, user_id: int) -> List[Effect]:
        s = await self._settings.get(user_id)
        return [SwapPanel(ViewState(settings_view(s), kb.settings_sections()))]

    async def open_field(self, user_id: int, section_text: str) -> List[Effect]:
        entry = _BY_SECTION_TEXT.get(section_text)
        if not entry:
            return []
        cb_field, f = entry
        s = await self._settings.get(user_id)
        return [Send(ViewState(f.title, self._chooser(cb_field, f, getattr(s, f.model_field))))]

    async def apply(self, user_id: int, cb_field: str, raw: str) -> List[Effect]:
        f = _FIELDS[cb_field]
        try:
            s = await self._settings.update(user_id, f.model_field, self._cast(f.model_field, raw))
        except ValueError:
            return [Notify("Неизвестное значение", alert=True)]
        view = ViewState(f.title, self._chooser(cb_field, f, getattr(s, f.model_field)))
        return [EditCurrent(view), Notify("✅ Сохранено")]

    # ── адаптив: применить/оставить предложение сменить сложность ──
    async def set_level(self, user_id: int, level: str) -> List[Effect]:
        await self._settings.update(user_id, "level", level)
        await self._stats.reset(user_id, level)  # свежий отсчёт на новом уровне
        return [
            EditCurrent(ViewState(
                f"✅ Сложность изменена на <b>{difficulty_label(level)}</b>. Продолжаем 💪", None)),
            Notify("Готово"),
        ]

    async def keep_level(self, user_id: int) -> List[Effect]:
        s = await self._settings.get(user_id)
        await self._stats.reset(user_id, s.level)  # не предлагать снова сразу
        return [EditCurrent(ViewState("Ок, оставляем текущий уровень 👍", None)), Notify("")]

    @staticmethod
    def _chooser(cb_field: str, f: _Field, current: Any) -> InlineSpec:
        return kb.settings_values(f.options, current, cb_field, f.per_row)

    @staticmethod
    def _cast(model_field: str, raw: str) -> Any:
        if raw == "none":
            return None
        if model_field in ("quiz_seconds", "quiz_size"):
            return int(raw)
        return raw
