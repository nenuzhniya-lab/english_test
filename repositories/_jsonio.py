"""Неблокирующая запись JSON: не держим event-loop на диск-syscall.

Файлы данных крошечные, но на сетевом диске Railway-volume запись может стоить
несколько мс — выносим её в поток, чтобы не тормозить других пользователей.
Вызывать под asyncio.Lock репозитория (последовательная запись в один файл).
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


async def awrite_json(path: Path, data: Any, indent: int | None = 2) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=indent)
    await asyncio.to_thread(path.write_text, text, encoding="utf-8")


class JsonStore:
    """База JSON-репозиториев: путь + каталог + lock + чтение/неблок. запись.

    Убирает повторяющийся boilerplate (__init__/_load/_flush) из json_*-репо.
    Чтение устойчиво к битому файлу — возвращает {} и логирует, а не роняет старт.
    """

    def __init__(self, file_path: str):
        self._path = Path(file_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    def _read(self) -> dict:
        if not self._path.exists():
            return {}
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            logger.warning("Битый JSON %s — начинаю с пустого", self._path)
            return {}

    async def _write(self, data: Any, indent: int | None = 2) -> None:
        await awrite_json(self._path, data, indent)
