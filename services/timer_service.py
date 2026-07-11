"""Планировщик отложенных колбэков (дедлайны вопросов теста).

Раньше таймер жил через asyncio.create_task прямо в хендлере. Теперь — отдельный
сервис: по ключу (user_id) держим не больше одного активного таймера, новый
вопрос отменяет прошлый. Дополнительная защита от гонок — проверка qid в колбэке.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)


class TimerService:
    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task[None]] = {}

    def schedule(self, key: str, seconds: int, callback: Callable[[], Awaitable[None]]) -> None:
        """Через `seconds` вызвать async `callback`. Прошлый таймер по этому ключу отменяется."""
        self.cancel(key)
        self._tasks[key] = asyncio.create_task(self._run(key, seconds, callback))

    def cancel(self, key: str) -> None:
        task = self._tasks.pop(key, None)
        if task is not None:
            task.cancel()

    async def _run(self, key: str, seconds: int, callback: Callable[[], Awaitable[None]]) -> None:
        try:
            await asyncio.sleep(seconds)
            await callback()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Сбой таймера %s", key)
        finally:
            self._tasks.pop(key, None)
