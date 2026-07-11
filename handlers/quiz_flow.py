"""Тест: меню выбора, запуск, ответы, стоп. Тонкий адаптер над QuizViewModel."""
from __future__ import annotations

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery

import callbacks as cb
from containers import Container
from keyboards import builders as kb
from handlers.effects import execute

router = Router()

# reply-кнопка типа теста → секция
_SECTION_BY_BTN = {
    kb.BTN_WORDS: "vocabulary",
    kb.BTN_VERBS: "verbs",
    kb.BTN_SENTENCES: "sentences",
}


@router.message(F.text == kb.BTN_TESTS)
async def tests_menu(message: Message, bot: Bot, container: Container) -> None:
    await execute(await container.quiz_vm.tests_menu(message.from_user.id),
                  bot=bot, chat_id=message.chat.id, user_id=message.from_user.id)


@router.message(F.text.in_(set(_SECTION_BY_BTN)))
async def start_section(message: Message, bot: Bot, container: Container) -> None:
    section = _SECTION_BY_BTN[message.text]
    await execute(
        await container.quiz_vm.start(message.chat.id, message.from_user.id, section),
        bot=bot, chat_id=message.chat.id, user_id=message.from_user.id,
    )


@router.message(F.text.startswith(kb.BTN_REVIEW))
async def start_review(message: Message, bot: Bot, container: Container) -> None:
    await execute(
        await container.quiz_vm.start(message.chat.id, message.from_user.id, "review"),
        bot=bot, chat_id=message.chat.id, user_id=message.from_user.id,
    )


@router.message(F.text == kb.BTN_STOP)
async def stop(message: Message, bot: Bot, container: Container) -> None:
    await execute(await container.quiz_vm.stop(message.from_user.id),
                  bot=bot, chat_id=message.chat.id, user_id=message.from_user.id)


@router.callback_query(F.data.startswith(cb.ANSWER))
async def on_answer(callback: CallbackQuery, bot: Bot, container: Container) -> None:
    qid, chosen = cb.parse_answer(callback.data)
    effects = await container.quiz_vm.answer(callback.from_user.id, qid, chosen)
    await execute(effects, bot=bot, chat_id=callback.message.chat.id,
                  user_id=callback.from_user.id, callback=callback)


@router.callback_query(F.data == cb.NOOP)
async def on_noop(callback: CallbackQuery) -> None:
    await callback.answer()
