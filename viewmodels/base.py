"""Контракт View↔ViewModel: ViewState + словарь эффектов.

ViewState — что показать (текст + клавиатура-спека). Effect — что сделать помимо
простого ответа: отправить голос, отредактировать/удалить сообщение, сменить
нижнюю панель, запустить таймер, показать всплывашку. Хендлер исполняет эффекты
по порядку; VM про aiogram ничего не знает.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Union

from keyboards.spec import KeyboardSpec


@dataclass(frozen=True)
class ViewState:
    text: str
    keyboard: Optional[KeyboardSpec] = None
    parse_mode: str = "HTML"


# ─────────────────────────── эффекты ───────────────────────────
@dataclass(frozen=True)
class Send:
    """Отправить новое сообщение. Если track_key задан — вернуть его message_id в VM."""
    view: ViewState
    track_key: Optional[str] = None


@dataclass(frozen=True)
class SwapPanel:
    """Сменить нижнюю reply-панель (удалить прошлое служебное сообщение, отправить новое)."""
    view: ViewState


@dataclass(frozen=True)
class SendVoice:
    file_path: str
    caption: str


@dataclass(frozen=True)
class EditCurrent:
    """Отредактировать сообщение, к которому привязан текущий callback."""
    view: ViewState


@dataclass(frozen=True)
class EditMessage:
    """Отредактировать существующее сообщение по id (текст + клавиатура)."""
    message_id: int
    view: ViewState


@dataclass(frozen=True)
class DeleteMessage:
    message_id: int


@dataclass(frozen=True)
class StartTimer:
    """Запустить дедлайн-таймер вопроса (исполняется через timer_service)."""
    user_id: int
    qid: int
    seconds: int


@dataclass(frozen=True)
class Notify:
    """Короткая всплывашка на callback (answer к CallbackQuery)."""
    text: str
    alert: bool = False


Effect = Union[Send, SwapPanel, SendVoice, EditCurrent, EditMessage, DeleteMessage, StartTimer, Notify]
