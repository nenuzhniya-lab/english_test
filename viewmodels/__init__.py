"""ViewModel-слой: состояние экранов и решения, без aiogram.

VM принимает интент (вызов метода с примитивами: user_id, chat_id, выбор) и
возвращает ViewState + список Effect. Хендлер только исполняет эффекты через
keyboards.factory. Так вся логика экранов тестируется без Telegram.
"""
from viewmodels.base import (
    ViewState,
    Effect,
    Send,
    SendVoice,
    EditCurrent,
    EditMessage,
    DeleteMessage,
    SwapPanel,
    StartTimer,
    Notify,
)

__all__ = [
    "ViewState", "Effect", "Send", "SendVoice", "EditCurrent", "EditMessage",
    "DeleteMessage", "SwapPanel", "StartTimer", "Notify",
]
