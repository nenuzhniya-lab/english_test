"""Старт, приветствие, «Говорение», возврат в главное меню. Тонкий адаптер над VM."""
from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart

from containers import Container
from keyboards import builders as kb
from handlers.effects import dispatch_message

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, container: Container) -> None:
    await dispatch_message(message, container, container.main_vm.welcome())


@router.message(F.text == kb.BTN_STUDY_NOW)
async def study_now(message: Message, container: Container) -> None:
    effects = await container.quiz_vm.start(message.chat.id, message.from_user.id, "study")
    await dispatch_message(message, container, effects)


@router.message(F.text == kb.BTN_BACK)
async def go_home(message: Message, container: Container) -> None:
    await dispatch_message(message, container, container.main_vm.home())
