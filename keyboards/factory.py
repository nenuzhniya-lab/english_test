"""Спека → aiogram markup. Единственное место, где спека встречает Telegram."""
from __future__ import annotations

from typing import Optional, Union

from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

from keyboards.spec import KeyboardSpec, InlineSpec, ReplySpec

Markup = Union[InlineKeyboardMarkup, ReplyKeyboardMarkup]


def to_markup(spec: Optional[KeyboardSpec]) -> Optional[Markup]:
    if spec is None:
        return None
    if isinstance(spec, InlineSpec):
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=b.text, callback_data=b.data) for b in row]
            for row in spec.rows
        ])
    if isinstance(spec, ReplySpec):
        return ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=b.text) for b in row] for row in spec.rows],
            resize_keyboard=spec.resize,
            persistent=spec.persistent,
            input_field_placeholder=spec.placeholder,
        )
    raise TypeError(f"Неизвестная спека клавиатуры: {type(spec)!r}")
