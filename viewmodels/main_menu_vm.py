"""ViewModel главного меню и статичных экранов (приветствие, «Говорение»)."""
from __future__ import annotations

from typing import List

from keyboards import builders as kb
from viewmodels.base import Effect, Send, SwapPanel, ViewState

_WELCOME = (
    "👋 <b>Привет!</b> Я помогу учить английский.\n\n"
    "⚡ <b>Учить сейчас</b> — умная дневная сессия: повторение, твои ошибки и новые слова\n"
    "📝 <b>Тесты</b> — слова, глаголы, предложения; бесконечный режим и работа над ошибками\n"
    "🎧 <b>Аудирование</b> — тексты с озвучкой и переводом\n"
    "📊 <b>Прогресс</b> — серия, точность, повторение\n"
    "⚙️ <b>Настройки</b> — сложность, время, голос озвучки\n\n"
    "Выбери раздел в меню ниже 👇"
)


class MainMenuViewModel:
    def welcome(self) -> List[Effect]:
        return [Send(ViewState(_WELCOME, kb.main_menu()))]

    def home(self) -> List[Effect]:
        return [SwapPanel(ViewState("🏠 Главное меню", kb.main_menu()))]
