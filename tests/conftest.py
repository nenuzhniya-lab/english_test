"""Общие фикстуры/хелперы тестов.

config требует BOT_TOKEN — задаём фиктивный до импорта проекта, чтобы тесты
не зависели от .env.
"""
from __future__ import annotations

import datetime
import os

os.environ.setdefault("BOT_TOKEN", "test:token")

import pytest  # noqa: E402
from aiogram import Bot, Dispatcher  # noqa: E402
from aiogram.client.default import DefaultBotProperties  # noqa: E402
from aiogram.enums import ParseMode  # noqa: E402
from aiogram.types import Update, Message, Chat, User, CallbackQuery  # noqa: E402

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


# ─────────── общая инфраструктура для смоука/интеграции через диспетчер ───────────
class _FakeSent:
    def __init__(self, mid):
        self.message_id = mid
        self.chat = Chat(id=1, type="private")


def make_message(text, user_id=1):
    return Update(update_id=1, message=Message(
        message_id=1, date=datetime.datetime.now(),
        chat=Chat(id=user_id, type="private"),
        from_user=User(id=user_id, is_bot=False, first_name="T"),
        text=text))


def make_callback(data, user_id=1, msg_id=200):
    return Update(update_id=1, callback_query=CallbackQuery(
        id="1", chat_instance="x", data=data,
        from_user=User(id=user_id, is_bot=False, first_name="T"),
        message=Message(message_id=msg_id, date=datetime.datetime.now(),
                        chat=Chat(id=user_id, type="private"),
                        from_user=User(id=user_id, is_bot=False, first_name="T"), text="q")))


@pytest.fixture
def bot_env(tmp_path, monkeypatch):
    """Собранный контейнер + Dispatcher + мок-бот. Возвращает объект с dp/bot/sent/container."""
    import config
    for attr, name in [("settings_file", "s.json"), ("stats_file", "st.json"),
                       ("srs_file", "sr.json"), ("progress_file", "p.json"),
                       ("migrations_state_file", "m.json"), ("session_file", "sess.json"),
                       ("mistakes_file", "mis.json")]:
        monkeypatch.setattr(config.settings, attr, str(tmp_path / name))

    from containers import build_container
    from handlers import (
        start, quiz_flow, listening, settings as settings_handler, progress, fallback,
    )

    container = build_container()
    bot = Bot(token="123:ABC", default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    sent: list = []
    counter = {"n": 100}

    async def send_message(chat_id, text, **k):
        counter["n"] += 1
        sent.append(("send", text))
        return _FakeSent(counter["n"])

    async def send_voice(chat_id, voice, **k):
        sent.append(("voice", None))
        return _FakeSent(counter["n"])

    async def edit_message_text(text, **k):
        sent.append(("edit", text))
        return True

    async def delete_message(*a, **k):
        return True

    async def noop(self, *a, **k):
        return True

    monkeypatch.setattr(bot, "send_message", send_message)
    monkeypatch.setattr(bot, "send_voice", send_voice)
    monkeypatch.setattr(bot, "edit_message_text", edit_message_text)
    monkeypatch.setattr(bot, "delete_message", delete_message)
    monkeypatch.setattr(CallbackQuery, "answer", noop)
    monkeypatch.setattr(Message, "edit_text", noop)

    # TTS без сети (аудирование + фоновый прогрев)
    from providers.tts import EdgeTTSProvider

    async def fake_synth(self, text, speed=None, voice=None):
        return "/tmp/fake.mp3"
    monkeypatch.setattr(EdgeTTSProvider, "synthesize", fake_synth)

    dp = Dispatcher()
    dp["container"] = container
    for module in (start, quiz_flow, listening, settings_handler, progress, fallback):
        module.router._parent_router = None  # роутеры — модульные синглтоны
        dp.include_router(module.router)

    class Env:
        def __init__(self):
            self.dp, self.bot, self.sent, self.container = dp, bot, sent, container

        async def feed(self, update):
            self.sent.clear()
            await self.dp.feed_update(self.bot, update)
            return self.sent

        async def msg(self, text, user_id=1):
            return await self.feed(make_message(text, user_id))

        async def cb(self, data, user_id=1):
            return await self.feed(make_callback(data, user_id))

    return Env()
