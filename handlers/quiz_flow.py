"""Тест: меню выбора, запуск, ответы, стоп. Тонкий адаптер над QuizViewModel."""
from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

import callbacks as cb
from containers import Container
from keyboards import builders as kb
from handlers.effects import dispatch_message, dispatch_callback

router = Router()

# reply-кнопка типа теста → секция
_SECTION_BY_BTN = {
    kb.BTN_WORDS: "vocabulary",
    kb.BTN_VERBS: "verbs",
    kb.BTN_SENTENCES: "sentences",
}


@router.message(F.text == kb.BTN_TESTS)
async def tests_menu(message: Message, container: Container) -> None:
    await dispatch_message(message, container, await container.quiz_vm.tests_menu(message.from_user.id))


@router.message(F.text.in_(set(_SECTION_BY_BTN)))
async def start_section(message: Message, container: Container) -> None:
    section = _SECTION_BY_BTN[message.text]
    effects = await container.quiz_vm.start(message.chat.id, message.from_user.id, section)
    await dispatch_message(message, container, effects)


@router.message(F.text.startswith(kb.BTN_REVIEW))
async def start_review(message: Message, container: Container) -> None:
    effects = await container.quiz_vm.start(message.chat.id, message.from_user.id, "review")
    await dispatch_message(message, container, effects)


@router.message(F.text.startswith(kb.BTN_MISTAKES))
async def start_mistakes(message: Message, container: Container) -> None:
    effects = await container.quiz_vm.start(message.chat.id, message.from_user.id, "mistakes")
    await dispatch_message(message, container, effects)


@router.message(F.text == kb.BTN_ENDLESS)
async def start_endless(message: Message, container: Container) -> None:
    effects = await container.quiz_vm.start(
        message.chat.id, message.from_user.id, "vocabulary", endless=True)
    await dispatch_message(message, container, effects)


@router.message(F.text == kb.BTN_STOP)
async def stop(message: Message, container: Container) -> None:
    await dispatch_message(message, container, await container.quiz_vm.stop(message.from_user.id))


@router.callback_query(F.data.startswith(cb.ANSWER))
async def on_answer(callback: CallbackQuery, container: Container) -> None:
    uid = callback.from_user.id
    qid, chosen = cb.parse_answer(callback.data)
    # мгновенный ack с вердиктом (гасит спиннер на кнопке ДО записи на диск)
    await callback.answer(container.quiz_vm.ack_text(uid, qid, chosen))
    effects = await container.quiz_vm.answer(uid, qid, chosen)
    await dispatch_callback(callback, container, effects)


@router.callback_query(F.data == cb.NOOP)
async def on_noop(callback: CallbackQuery) -> None:
    await callback.answer()
