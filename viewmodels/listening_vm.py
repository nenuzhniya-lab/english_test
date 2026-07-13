"""ViewModel аудирования: уровни (reply) → тексты (inline) → плеер (reply)."""
from __future__ import annotations

import asyncio
import logging
from typing import List, Optional

from keyboards import builders as kb
from models import ListenState, ListeningText
from presenters import text_view
from providers.tts import Speed
from repositories.session_repo import SessionStore
from services.listening_service import ListeningService
from services.settings_service import SettingsService
from viewmodels.base import Effect, Send, SendVoice, SwapPanel, ViewState

logger = logging.getLogger(__name__)

_LEVELS_TITLE = "🎧 <b>Аудирование</b>\nВыбери сложность:"
_NO_TEXT = "Сначала открой текст: 🎧 Аудирование."

_SPEED_BY_BTN = {kb.BTN_SLOW: Speed.SLOW, kb.BTN_NORM: Speed.NORMAL, kb.BTN_FAST: Speed.FAST}
_SPEED_LABEL = {Speed.SLOW: "🐢 Медленно", Speed.NORMAL: "🚶 Нормально", Speed.FAST: "🏃 Быстро"}


class ListeningViewModel:
    def __init__(self, listening: ListeningService, settings: SettingsService, sessions: SessionStore):
        self._listening = listening
        self._settings = settings
        self._sessions = sessions

    def _key(self, user_id: int) -> str:
        return f"listen:{user_id}"

    def _load(self, user_id: int) -> Optional[ListenState]:
        raw = self._sessions.get(self._key(user_id))
        return ListenState.from_dict(raw) if raw else None

    async def open(self, user_id: int) -> List[Effect]:
        levels = await self._listening.levels()
        if not levels:
            return [Send(ViewState("❌ Тексты не найдены."))]
        return [SwapPanel(ViewState(_LEVELS_TITLE, kb.audio_levels(levels)))]

    async def choose_level(self, user_id: int, difficulty: str) -> List[Effect]:
        texts = await self._listening.by_level(difficulty)
        if not texts:
            return [Send(ViewState("❌ Нет текстов этой сложности."))]
        from models import difficulty_label
        title = f"🎧 <b>{difficulty_label(difficulty)}</b> — выбери текст ({len(texts)}):"
        return [Send(ViewState(title, kb.audio_texts(texts)))]

    async def open_text(self, user_id: int, text_id: int) -> List[Effect]:
        text = await self._listening.get(text_id)
        if not text:
            return [Send(ViewState("Текст не найден."))]
        self._sessions.set(self._key(user_id), ListenState(text.id, text.level.value).to_dict())
        # прогрев обычной скорости в фоне → первое воспроизведение мгновенно
        voice = (await self._settings.get(user_id)).voice
        asyncio.create_task(self._prewarm(text, voice))
        return [SwapPanel(ViewState(text_view(text), kb.audio_player()))]

    async def _prewarm(self, text: ListeningText, voice: str) -> None:
        try:
            await self._listening.audio(text, Speed.NORMAL, voice)
        except Exception:
            pass  # прогрев не критичен

    async def play(self, user_id: int, speed_btn: str) -> List[Effect]:
        listen = self._load(user_id)
        if not listen:
            return [Send(ViewState(_NO_TEXT))]
        text = await self._listening.get(listen.text_id)
        if not text:
            return [Send(ViewState(_NO_TEXT))]
        speed = _SPEED_BY_BTN[speed_btn]
        voice = (await self._settings.get(user_id)).voice
        try:
            path = await self._listening.audio(text, speed, voice)
        except Exception as e:
            logger.exception("Сбой генерации аудио")
            return [Send(ViewState(f"❌ Ошибка аудио: {e}"))]
        return [SendVoice(path, f"🔊 <b>{text.title}</b> — {_SPEED_LABEL[speed]}")]

    async def translate(self, user_id: int) -> List[Effect]:
        listen = self._load(user_id)
        if not listen:
            return [Send(ViewState(_NO_TEXT))]
        text = await self._listening.get(listen.text_id)
        if not text:
            return [Send(ViewState(_NO_TEXT))]
        return [Send(ViewState(f"📝 <b>Перевод: {text.title}</b>\n\n{text.translation}"))]

    async def back_to_levels(self, user_id: int) -> List[Effect]:
        return await self.open(user_id)
