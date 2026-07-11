"""Смоук диспетчеризации: апдейт → хендлер → execute, с мок-ботом.

Ловит регрессии проводки (например, забытый container= в execute) — то, что
проверка VM в изоляции пропускает, т.к. не проходит через хендлеры.
"""
import datetime

import pytest
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Update, Message, Chat, User


class _FakeSent:
    def __init__(self, mid):
        self.message_id = mid
        self.chat = Chat(id=1, type="private")


@pytest.fixture
def dispatcher(tmp_path, monkeypatch):
    import config
    for attr, name in [("settings_file", "s.json"), ("stats_file", "st.json"),
                       ("srs_file", "sr.json"), ("progress_file", "p.json"),
                       ("migrations_state_file", "m.json")]:
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
        sent.append(text)
        return _FakeSent(counter["n"])

    async def edit_message_text(text, **k):
        sent.append(text)
        return True

    async def delete_message(*a, **k):
        return True

    monkeypatch.setattr(bot, "send_message", send_message)
    monkeypatch.setattr(bot, "edit_message_text", edit_message_text)
    monkeypatch.setattr(bot, "delete_message", delete_message)

    dp = Dispatcher()
    dp["container"] = container
    for module in (start, quiz_flow, listening, settings_handler, progress, fallback):
        dp.include_router(module.router)
    return dp, bot, sent


def _message(text):
    return Update(update_id=1, message=Message(
        message_id=1, date=datetime.datetime.now(),
        chat=Chat(id=1, type="private"),
        from_user=User(id=1, is_bot=False, first_name="T"),
        text=text))


_SCREENS = [
    "/start", "📝 Тесты", "📖 Слова", "🎧 Аудирование", "🟢 Лёгкий",
    "⚙️ Настройки", "🎚 Сложность", "📊 Прогресс", "🗣 Говорение",
    "⬅️ Назад", "неизвестный текст",
]


async def test_all_message_screens_respond(dispatcher):
    """Каждый экран отвечает хотя бы одним сообщением, без исключений.

    Именно это ловит забытый container= в execute (регрессия «бот молчит»).
    Роутеры — модульные синглтоны, поэтому диспетчер один на тест, экраны в цикле.
    """
    dp, bot, sent = dispatcher
    for text in _SCREENS:
        sent.clear()
        await dp.feed_update(bot, _message(text))
        assert sent, f"экран {text!r} ничего не ответил"
    await bot.session.close()
