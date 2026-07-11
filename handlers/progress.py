"""Экран прогресса. Тонкий адаптер над ProgressViewModel."""
from __future__ import annotations

from aiogram import Router, F, Bot
from aiogram.types import Message

from containers import Container
from keyboards import builders as kb
from handlers.effects import execute

router = Router()


@router.message(F.text == kb.BTN_PROGRESS)
async def show_progress(message: Message, bot: Bot, container: Container) -> None:
    await execute(await container.progress_vm.open(message.from_user.id),
                  bot=bot, chat_id=message.chat.id, user_id=message.from_user.id)
