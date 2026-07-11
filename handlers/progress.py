"""Экран прогресса. Тонкий адаптер над ProgressViewModel."""
from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message

from containers import Container
from keyboards import builders as kb
from handlers.effects import dispatch_message

router = Router()


@router.message(F.text == kb.BTN_PROGRESS)
async def show_progress(message: Message, container: Container) -> None:
    await dispatch_message(message, container, await container.progress_vm.open(message.from_user.id))
