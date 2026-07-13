"""Интеграция: реальный контейнер + Dispatcher, все пользовательские сценарии.

Прогоняет апдейты через настоящие хендлеры/эффекты с мок-ботом (фикстура bot_env),
проверяет и реакцию, и побочные записи (progress/srs/stats/mistakes).
"""
import callbacks as cb


def _texts(sent):
    return [t for kind, t in sent if kind in ("send", "edit") and t]


async def _answer_all(env, correct=True):
    """Отвечает на все вопросы активного теста; возвращает список финальных sent."""
    last = []
    for _ in range(60):
        s = env.container.sessions.get("quiz:1")
        if s is None:
            break
        q = s["questions"][s["i"]]
        idx = q["correct"] if correct else next(
            i for i in range(len(q["options"])) if i != q["correct"])
        last = await env.cb(cb.answer(s["qid"], idx))
    return last


async def test_start_shows_main_menu(bot_env):
    sent = await bot_env.msg("/start")
    assert any("Привет" in t for t in _texts(sent))
    await bot_env.bot.session.close()


async def test_full_vocabulary_test_records_progress_and_srs(bot_env):
    await bot_env.msg("📖 Слова")
    s = bot_env.container.sessions.get("quiz:1")
    assert s and s["section"] == "vocabulary"
    total = len(s["questions"])
    await _answer_all(bot_env, correct=True)
    assert bot_env.container.sessions.get("quiz:1") is None      # завершился и очистился
    prog = await bot_env.container.progress.summary(1)
    srs = await bot_env.container.srs.progress(1)
    assert prog["today"] == total and srs["total"] == total       # прогресс и SRS записаны
    await bot_env.bot.session.close()


async def test_adaptive_suggestion_then_apply(bot_env):
    await bot_env.msg("📖 Слова")
    final = await _answer_all(bot_env, correct=True)              # 100% → предложить сложнее
    assert any("усложнить" in t.lower() for t in _texts(final))
    await bot_env.cb(cb.level_set("MEDIUM"))
    assert (await bot_env.container.settings.get(1)).level == "MEDIUM"
    await bot_env.bot.session.close()


async def test_mistakes_flow_end_to_end(bot_env):
    await bot_env.msg("📖 Слова")
    await _answer_all(bot_env, correct=False)                    # всё неверно → копим ошибки
    assert await bot_env.container.mistakes.count(1) >= 1
    # меню тестов показывает кнопку «Мои ошибки (N)»
    from keyboards.factory import to_markup
    effs = await bot_env.container.quiz_vm.tests_menu(1)
    labels = [b.text for row in to_markup(effs[0].view.keyboard).keyboard for b in row]
    assert any("Мои ошибки" in l for l in labels)
    # запуск режима ошибок
    sent = await bot_env.msg("❗ Мои ошибки (5)")
    assert any("Мои ошибки" in t for t in _texts(sent))
    await bot_env.bot.session.close()


async def test_endless_never_ends_until_stop(bot_env):
    await bot_env.msg("♾ Без конца")
    s = bot_env.container.sessions.get("quiz:1")
    assert s and s["endless"]
    base = len(s["questions"])
    for _ in range(20):
        s = bot_env.container.sessions.get("quiz:1")
        assert s is not None, "бесконечный тест завершился сам"
        await bot_env.cb(cb.answer(s["qid"], s["questions"][s["i"]]["correct"]))
    s = bot_env.container.sessions.get("quiz:1")
    assert len(s["questions"]) > base                                     # буфер дозагружался
    stop = await bot_env.msg("⏹ Остановить тест")
    assert any("остановлен" in t.lower() for t in _texts(stop))
    assert bot_env.container.sessions.get("quiz:1") is None
    await bot_env.bot.session.close()


async def test_study_session_mixes(bot_env):
    sent = await bot_env.msg("⚡ Учить сейчас")
    s = bot_env.container.sessions.get("quiz:1")
    assert s and s["section"] == "study" and len(s["questions"]) >= 1
    assert any("Учить сейчас" in t for t in _texts(sent))
    await bot_env.bot.session.close()


async def test_verbs_and_sentences_start(bot_env):
    for text, section in [("🔄 Глаголы", "verbs"), ("✍️ Предложения", "sentences")]:
        await bot_env.msg(text)
        s = bot_env.container.sessions.get("quiz:1")
        assert s and s["section"] == section and len(s["questions"]) >= 1
        await bot_env.msg("⏹ Остановить тест")
    await bot_env.bot.session.close()


async def test_listening_flow(bot_env):
    await bot_env.msg("🎧 Аудирование")
    sent = await bot_env.msg("🟢 Лёгкий")
    assert any("выбери текст" in t.lower() for t in _texts(sent))
    text = (await bot_env.container.listening.by_level("EASY"))[0]
    await bot_env.cb(cb.listen_open(text.id))
    assert bot_env.container.sessions.get("listen:1") is not None
    voice = await bot_env.msg("🐢 Медленно")                     # → голос (мок TTS)
    assert any(kind == "voice" for kind, _ in voice)
    tr = await bot_env.msg("🌐 Перевод")
    assert any("Перевод" in t for t in _texts(tr))
    await bot_env.bot.session.close()


async def test_settings_all_fields_apply(bot_env):
    await bot_env.msg("⚙️ Настройки")
    await bot_env.msg("🎚 Сложность")
    await bot_env.cb(cb.setting_apply("level", "HARD"))
    await bot_env.msg("⏱ Таймер")
    await bot_env.cb(cb.setting_apply("time", "25"))
    await bot_env.msg("🔢 Вопросы")
    await bot_env.cb(cb.setting_apply("size", "5"))
    s = await bot_env.container.settings.get(1)
    assert s.level == "HARD" and s.quiz_seconds == 25 and s.quiz_size == 5
    await bot_env.bot.session.close()


async def test_timeout_marks_and_advances(bot_env):
    await bot_env.msg("📖 Слова")
    s = bot_env.container.sessions.get("quiz:1")
    effs = await bot_env.container.quiz_vm.timeout(1, s["qid"])   # эмулируем дедлайн
    from viewmodels.base import EditMessage
    assert any(isinstance(e, EditMessage) for e in effs)
    await bot_env.bot.session.close()


async def test_profile_middleware_does_not_break(bot_env):
    from bot import _profile_middleware
    bot_env.dp.update.outer_middleware(_profile_middleware)
    sent = await bot_env.msg("/start")
    assert sent
    await bot_env.bot.session.close()


async def test_unknown_message_falls_back_to_menu(bot_env):
    sent = await bot_env.msg("абырвалг")
    assert any("меню" in t.lower() for t in _texts(sent))
    await bot_env.bot.session.close()


# ═══════════════════════ смоук хендлеров ═══════════════════════


_SCREENS = [
    "/start", "⚡ Учить сейчас", "📝 Тесты", "📖 Слова", "♾ Без конца",
    "🎧 Аудирование", "🟢 Лёгкий", "⚙️ Настройки", "🎚 Сложность",
    "📊 Прогресс", "⬅️ Назад", "неизвестный текст",
]


async def test_all_message_screens_respond(bot_env):
    """Каждый экран отвечает хотя бы одним сообщением, без исключений."""
    for text in _SCREENS:
        sent = await bot_env.msg(text)
        assert sent, f"экран {text!r} ничего не ответил"
    await bot_env.bot.session.close()


async def test_callback_paths(bot_env):
    """Callback-хендлеры (ответ в тесте, применение настройки) доходят до execute."""
    await bot_env.msg("📖 Слова")
    s = bot_env.container.sessions.get("quiz:1")   # хранится как dict
    assert s is not None
    correct = s["questions"][s["i"]]["correct"]
    sent = await bot_env.cb(cb.answer(s["qid"], correct))
    assert sent, "ответ в тесте не дал реакции"

    await bot_env.cb(cb.setting_apply("level", "HARD"))
    assert (await bot_env.container.settings.get(1)).level == "HARD"
    await bot_env.bot.session.close()
