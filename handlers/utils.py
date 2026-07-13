"""Мелкие переиспользуемые утилиты хендлеров (DRY)."""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from aiogram import Bot
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest

from keyboards.factory import to_markup
from keyboards.spec import KeyboardSpec

logger = logging.getLogger(__name__)


async def swap_reply_keyboard(
    bot: Bot, chat_id: int, text: str, spec: Optional[KeyboardSpec],
    prev_service_msg_id: Optional[int] = None,
) -> int:
    """Меняет нижнюю reply-панель, не плодя мусор.

    Telegram не даёт сменить reply-клавиатуру без нового сообщения. Поэтому шлём
    одно служебное сообщение с новой панелью и удаляем предыдущее служебное (если
    передан его id). Сообщения-вопросы теста сюда не попадают — они остаются в чате.

    Возвращает id нового служебного сообщения — сохрани его, чтобы удалить в следующий раз.

    Сначала шлём новое, потом удаляем старое — иначе на миг остаётся экран без панели
    (визуально «рвано»). Удаление старого — фоном, не задерживает ответ.
    """
    sent = await bot.send_message(chat_id, text, reply_markup=to_markup(spec))
    if prev_service_msg_id is not None:
        async def _cleanup() -> None:
            try:
                await bot.delete_message(chat_id, prev_service_msg_id)
            except Exception:
                pass  # уже удалено / слишком старое — не критично
        asyncio.create_task(_cleanup())
    return sent.message_id


def _is_not_modified(error: Exception) -> bool:
    return "message is not modified" in str(error)


async def safe_edit(message: Message, text: str, reply_markup=None) -> None:
    """edit_text по объекту Message, игнорируя ошибку «message is not modified».

    Telegram падает, если новое содержимое идентично текущему (напр. «Дальше»
    выпало то же слово или выбран тот же счётчик). Для пользователя это не ошибка.
    """
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if not _is_not_modified(e):
            raise


async def safe_edit_by_id(bot: Bot, chat_id: int, message_id: int, text: str, reply_markup=None) -> None:
    """edit_message_text по chat_id+message_id (когда объекта Message нет под рукой).

    Устойчива: любые ошибки правки логируются и гасятся — правка второстепенна и
    не должна ронять поток (напр. отметка отвеченного вопроса в тесте).
    """
    try:
        await bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, reply_markup=reply_markup)
    except Exception:
        logger.exception("Не удалось отредактировать сообщение %s/%s", chat_id, message_id)
