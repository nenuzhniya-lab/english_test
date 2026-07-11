"""Аудирование: уровни (reply) → тексты (inline) → плеер (reply). Адаптер над VM."""
from __future__ import annotations

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery

import callbacks as cb
from containers import Container
from keyboards import builders as kb
from models import label_to_difficulty
from models.difficulty import DIFFICULTY_LABEL
from handlers.effects import execute

router = Router()

_LEVEL_LABELS = set(DIFFICULTY_LABEL.values())
_SPEED_BTNS = {kb.BTN_SLOW, kb.BTN_NORM, kb.BTN_FAST}


@router.message(F.text == kb.BTN_LISTEN)
async def open_listening(message: Message, bot: Bot, container: Container) -> None:
    await execute(await container.listening_vm.open(message.from_user.id),
                  bot=bot, chat_id=message.chat.id, user_id=message.from_user.id)


@router.message(F.text.in_(_LEVEL_LABELS))
async def choose_level(message: Message, bot: Bot, container: Container) -> None:
    difficulty = label_to_difficulty(message.text)
    if difficulty is None:
        return
    await execute(await container.listening_vm.choose_level(message.from_user.id, difficulty),
                  bot=bot, chat_id=message.chat.id, user_id=message.from_user.id)


@router.callback_query(F.data.startswith(cb.LISTEN_OPEN))
async def open_text(callback: CallbackQuery, bot: Bot, container: Container) -> None:
    text_id = cb.parse_listen_open(callback.data)
    effects = await container.listening_vm.open_text(callback.from_user.id, text_id)
    await callback.answer()
    await execute(effects, bot=bot, chat_id=callback.message.chat.id,
                  user_id=callback.from_user.id, callback=callback)


@router.message(F.text.in_(_SPEED_BTNS))
async def play(message: Message, bot: Bot, container: Container) -> None:
    await execute(await container.listening_vm.play(message.from_user.id, message.text),
                  bot=bot, chat_id=message.chat.id, user_id=message.from_user.id)


@router.message(F.text == kb.BTN_TRANSLATE)
async def translate(message: Message, bot: Bot, container: Container) -> None:
    await execute(await container.listening_vm.translate(message.from_user.id),
                  bot=bot, chat_id=message.chat.id, user_id=message.from_user.id)


@router.message(F.text == kb.BTN_BACK_LEVELS)
async def back_to_levels(message: Message, bot: Bot, container: Container) -> None:
    await execute(await container.listening_vm.back_to_levels(message.from_user.id),
                  bot=bot, chat_id=message.chat.id, user_id=message.from_user.id)
