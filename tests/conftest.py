"""Общие фикстуры/хелперы тестов.

config требует BOT_TOKEN — задаём фиктивный до импорта проекта, чтобы тесты
не зависели от .env.
"""
from __future__ import annotations

import os

os.environ.setdefault("BOT_TOKEN", "test:token")

import pytest  # noqa: E402

from repositories.pyfile import PyFileWordRepository  # noqa: E402


def make_words():
    """12 слов-заглушек: 6 A1(EASY), 3 A2(MEDIUM), 3 B1(HARD) — для тестов теста."""
    rows = []
    for i in range(1, 7):
        rows.append({"id": i, "english": f"easy{i}", "level": "A1",
                     "meanings": [{"russian": f"лёгкий{i}"}]})
    for i in range(7, 10):
        rows.append({"id": i, "english": f"med{i}", "level": "A2",
                     "meanings": [{"russian": f"средний{i}"}]})
    for i in range(10, 13):
        rows.append({"id": i, "english": f"hard{i}", "level": "B1",
                     "meanings": [{"russian": f"сложный{i}"}]})
    return rows


@pytest.fixture
def word_repo() -> PyFileWordRepository:
    return PyFileWordRepository(make_words())
