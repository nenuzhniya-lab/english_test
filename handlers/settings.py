"""Настройки: разделы (reply) + значения (inline) + адаптив. Адаптер над VM."""
from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

import callbacks as cb
from containers import Container
from keyboards import builders as kb
from handlers.effects import dispatch_message, dispatch_callback

router = Router()

_SECTION_TEXTS = {kb.BTN_S_LEVEL, kb.BTN_S_TIME, kb.BTN_S_SIZE, kb.BTN_S_VOICE}


@router.message(F.text == kb.BTN_SETTINGS)
async def open_settings(message: Message, container: Container) -> None:
    await dispatch_message(message, container, await container.settings_vm.open(message.from_user.id))


@router.message(F.text.in_(_SECTION_TEXTS))
async def open_field(message: Message, container: Container) -> None:
    effects = await container.settings_vm.open_field(message.from_user.id, message.text)
    await dispatch_message(message, container, effects)


@router.callback_query(lambda c: cb.is_setting_apply(c.data))
async def apply_setting(callback: CallbackQuery, container: Container) -> None:
    field, raw = cb.parse_setting_apply(callback.data)
    effects = await container.settings_vm.apply(callback.from_user.id, field, raw)
    await dispatch_callback(callback, container, effects)


@router.callback_query(F.data.startswith(cb.LEVEL_SET))
async def level_apply(callback: CallbackQuery, container: Container) -> None:
    level = cb.parse_level_set(callback.data)
    effects = await container.settings_vm.set_level(callback.from_user.id, level)
    await dispatch_callback(callback, container, effects)


@router.callback_query(F.data == cb.LEVEL_KEEP)
async def level_keep(callback: CallbackQuery, container: Container) -> None:
    effects = await container.settings_vm.keep_level(callback.from_user.id)
    await dispatch_callback(callback, container, effects)
