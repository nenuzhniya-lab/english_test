"""Старт, приветствие, «Говорение», возврат в главное меню. Тонкий адаптер над VM."""
from __future__ import annotations

from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import CommandStart

from containers import Container
from keyboards import builders as kb
from handlers.effects import execute

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot, container: Container) -> None:
    await execute(container.main_vm.welcome(),
                  bot=bot, chat_id=message.chat.id, user_id=message.from_user.id)


@router.message(F.text == kb.BTN_SPEAK)
async def speaking(message: Message, bot: Bot, container: Container) -> None:
    await execute(container.main_vm.speaking(),
                  bot=bot, chat_id=message.chat.id, user_id=message.from_user.id)


@router.message(F.text == kb.BTN_BACK)
async def go_home(message: Message, bot: Bot, container: Container) -> None:
    await execute(container.main_vm.home(),
                  bot=bot, chat_id=message.chat.id, user_id=message.from_user.id)
