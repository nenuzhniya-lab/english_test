"""Исполнитель эффектов ViewModel — единственный мост VM → aiogram.

VM возвращает список Effect (что сделать); здесь они превращаются в реальные
вызовы Bot/Message/CallbackQuery. Больше нигде в хендлерах Telegram-I/O нет.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from aiogram import Bot
from aiogram.types import CallbackQuery, FSInputFile

from keyboards.factory import to_markup
from handlers.utils import safe_edit, safe_edit_by_id, swap_reply_keyboard
from viewmodels.base import (
    Effect, EditCurrent, EditMessage, DeleteMessage, Notify, Send, SendVoice,
    StartTimer, SwapPanel,
)

logger = logging.getLogger(__name__)


def _panel_key(user_id: int) -> str:
    return f"panel:{user_id}"


async def execute(
    effects: List[Effect],
    *,
    bot: Bot,
    chat_id: int,
    user_id: int,
    container,
    callback: Optional[CallbackQuery] = None,
) -> None:
    for eff in effects:
        if isinstance(eff, Send):
            sent = await bot.send_message(chat_id, eff.view.text, reply_markup=to_markup(eff.view.keyboard))
            if eff.track_key == "question":
                container.quiz_vm.track_question_message(user_id, sent.message_id)

        elif isinstance(eff, SwapPanel):
            prev = container.sessions.get(_panel_key(user_id))
            new_id = await swap_reply_keyboard(bot, chat_id, eff.view.text, eff.view.keyboard, prev)
            container.sessions.set(_panel_key(user_id), new_id)

        elif isinstance(eff, SendVoice):
            await bot.send_voice(chat_id, FSInputFile(eff.file_path), caption=eff.caption)

        elif isinstance(eff, EditCurrent):
            if callback is not None and callback.message is not None:
                await safe_edit(callback.message, eff.view.text, to_markup(eff.view.keyboard))

        elif isinstance(eff, EditMessage):
            await safe_edit_by_id(bot, chat_id, eff.message_id, eff.view.text, to_markup(eff.view.keyboard))

        elif isinstance(eff, DeleteMessage):
            try:
                await bot.delete_message(chat_id, eff.message_id)
            except Exception:
                pass

        elif isinstance(eff, StartTimer):
            container.timers.schedule(
                f"quiz:{eff.user_id}", eff.seconds,
                _timeout_callback(bot, chat_id, eff.user_id, eff.qid, container),
            )

        elif isinstance(eff, Notify):
            if callback is not None:
                await callback.answer(eff.text, show_alert=eff.alert)

        else:  # pragma: no cover
            logger.warning("Неизвестный эффект: %r", eff)


def _timeout_callback(bot: Bot, chat_id: int, user_id: int, qid: int, container):
    async def _cb() -> None:
        effects = await container.quiz_vm.timeout(user_id, qid)
        await execute(effects, bot=bot, chat_id=chat_id, user_id=user_id, container=container)
    return _cb
