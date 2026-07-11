"""Подстраховка: ловит всё, что не поймали разделы.

Решает частую проблему — у пользователя в чате осталась СТАРАЯ reply-клавиатура
или старые inline-кнопки от прежней версии. Регистрируется ПОСЛЕДНИМ.
"""
from __future__ import annotations

from aiogram import Router, Bot
from aiogram.types import Message, CallbackQuery

from containers import Container
from handlers.effects import execute

router = Router()


@router.message()
async def unknown_message(message: Message, bot: Bot, container: Container) -> None:
    # Показываем актуальное главное меню (сбрасывает старую reply-панель).
    await execute(container.main_vm.home(),
                  bot=bot, chat_id=message.chat.id, user_id=message.from_user.id)


@router.callback_query()
async def unknown_callback(callback: CallbackQuery) -> None:
    await callback.answer("Эта кнопка устарела. Нажми /start, чтобы обновить меню.", show_alert=True)
