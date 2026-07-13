"""Тесты ViewModel без aiogram (quiz / settings / listening / progress)."""

# ═══════════════════════ test_quiz_vm ═══════════════════════
"""QuizViewModel без aiogram: старт, ответ, финал, защита от устаревшего вопроса."""
import pytest

from repositories.json_srs_repo import JsonSrsRepository
from repositories.json_stats_repo import JsonStatsRepository
from repositories.json_progress_repo import JsonProgressRepository
from repositories.json_settings_repo import JsonSettingsRepository
from repositories.json_mistakes_repo import JsonMistakesRepository
from repositories.session_repo import SessionStore
from services.quiz_service import QuizService
from services.vocabulary_service import VocabularyService
from services.srs_service import SrsService
from services.stats_service import StatsService
from services.progress_service import ProgressService
from services.settings_service import SettingsService
from services.mistakes_service import MistakesService
from services.study_service import StudyService
from viewmodels.quiz_vm import QuizViewModel
from viewmodels.base import SwapPanel, Send, StartTimer, EditMessage


@pytest.fixture
def env_q(tmp_path, word_repo):
    vocab = VocabularyService(word_repo)
    return QuizViewModel(
        QuizService(),
        {"vocabulary": vocab},
        SrsService(JsonSrsRepository(str(tmp_path / "srs.json"))),
        StatsService(JsonStatsRepository(str(tmp_path / "stats.json"))),
        ProgressService(JsonProgressRepository(str(tmp_path / "progress.json"))),
        SettingsService(JsonSettingsRepository(str(tmp_path / "settings.json"))),
        MistakesService(JsonMistakesRepository(str(tmp_path / "mistakes.json"))),
        StudyService(),
        SessionStore(),
        n_options=4,
    )


def _types(effs):
    return [type(e).__name__ for e in effs]


async def test_start_emits_panel_question_timer(env_q):
    effs = await env_q.start(1, 1, "vocabulary")
    assert _types(effs) == ["SwapPanel", "Send", "StartTimer"]
    assert isinstance(effs[0], SwapPanel)
    assert effs[1].track_key == "question"
    assert env_q.has_active(1)


async def test_answer_correct_then_next(env_q):
    await env_q.start(1, 1, "vocabulary")
    env_q.track_question_message(1, 500)
    s = env_q._load(1)
    # мгновенная всплывашка считается отдельно (до записи на диск)
    assert env_q.ack_text(1, s.qid, s.current.correct) == "✅ Верно!"
    effs = await env_q.answer(1, s.qid, s.current.correct)
    assert _types(effs) == ["EditMessage", "Send", "StartTimer"]
    assert isinstance(effs[0], EditMessage) and effs[0].message_id == 500


async def test_stale_qid_rejected(env_q):
    await env_q.start(1, 1, "vocabulary")
    assert env_q.ack_text(1, 999, 0) == "Этот вопрос уже закрыт ⏱"
    assert await env_q.answer(1, 999, 0) == []


async def test_full_run_finishes_and_clears(env_q):
    await env_q.start(1, 1, "vocabulary")
    env_q.track_question_message(1, 500)
    steps, saw_finish = 0, False
    while env_q.has_active(1) and steps < 20:
        s = env_q._load(1)
        effs = await env_q.answer(1, s.qid, s.current.correct)
        steps += 1
        for e in effs:
            if isinstance(e, Send) and e.track_key == "question":
                env_q.track_question_message(1, 500 + steps)
            if isinstance(e, SwapPanel):
                saw_finish = True
    assert saw_finish and not env_q.has_active(1)
    assert steps == 6  # 6 слов EASY в фикстуре


async def test_timeout_reveals(env_q):
    await env_q.start(1, 1, "vocabulary")
    env_q.track_question_message(1, 500)
    s = env_q._load(1)
    effs = await env_q.timeout(1, s.qid)
    assert any(isinstance(e, EditMessage) for e in effs)


async def test_stop_when_no_session(env_q):
    effs = await env_q.stop(1)
    assert len(effs) == 1 and isinstance(effs[0], SwapPanel)


async def test_wrong_answer_logs_mistake_and_feeds_mistakes_mode(env_q):
    # пустой режим ошибок → «ошибок нет»
    empty = await env_q.start(1, 1, "mistakes")
    assert isinstance(empty[0], SwapPanel) and "Ошибок нет" in empty[0].view.text

    await env_q.start(1, 1, "vocabulary")
    env_q.track_question_message(1, 500)
    s = env_q._load(1)
    wrong = next(i for i in range(len(s.current.options)) if i != s.current.correct)
    await env_q.answer(1, s.qid, wrong)
    assert await env_q._mistakes.count(1) >= 1

    await env_q.stop(1)
    effs = await env_q.start(1, 1, "mistakes")   # теперь есть что отрабатывать
    assert any(isinstance(e, Send) and e.track_key == "question" for e in effs)


async def test_study_session_builds_from_new_words(env_q):
    # без SRS-долга и ошибок → «Учить сейчас» наполняется новыми словами
    effs = await env_q.start(1, 1, "study")
    assert any(isinstance(e, Send) and e.track_key == "question" for e in effs)
    s = env_q._load(1)
    assert s is not None and s.section == "study" and s.total >= 1


async def test_endless_refills_and_never_finishes(env_q):
    await env_q.start(1, 1, "vocabulary", endless=True)
    env_q.track_question_message(1, 700)
    s = env_q._load(1)
    assert s.endless
    initial_total = s.total
    for _ in range(15):
        s = env_q._load(1)
        assert s is not None, "бесконечный тест не должен завершаться сам"
        await env_q.answer(1, s.qid, s.current.correct)
        env_q.track_question_message(1, 700)
    s = env_q._load(1)
    assert s is not None and s.endless and s.total > initial_total  # буфер дозагрузился
    stop = await env_q.stop(1)
    assert any(isinstance(e, SwapPanel) for e in stop)
    assert env_q._load(1) is None

# ═══════════════════════ test_settings_vm ═══════════════════════
"""SettingsViewModel без aiogram: открытие, выбор поля, применение, валидация."""
import pytest

from repositories.json_settings_repo import JsonSettingsRepository
from repositories.json_stats_repo import JsonStatsRepository
from services.settings_service import SettingsService
from services.stats_service import StatsService
from viewmodels.settings_vm import SettingsViewModel
from viewmodels.base import SwapPanel, Send, EditCurrent
from keyboards.spec import InlineSpec, ReplySpec


@pytest.fixture
def env_s(tmp_path):
    settings = SettingsService(JsonSettingsRepository(str(tmp_path / "settings.json")))
    stats = StatsService(JsonStatsRepository(str(tmp_path / "stats.json")))
    return SettingsViewModel(settings, stats), settings


async def test_open_shows_sections_panel(env_s):
    svm, _ = env_s
    effs = await svm.open(1)
    assert isinstance(effs[0], SwapPanel)
    assert isinstance(effs[0].view.keyboard, ReplySpec)


async def test_open_field_shows_inline_values(env_s):
    svm, _ = env_s
    effs = await svm.open_field(1, "🎚 Сложность")
    assert isinstance(effs[0], Send)
    assert isinstance(effs[0].view.keyboard, InlineSpec)


async def test_apply_updates_and_confirms(env_s):
    svm, settings = env_s
    effs = await svm.apply(1, "level", "HARD")
    assert [type(e).__name__ for e in effs] == ["EditCurrent"]
    assert (await settings.get(1)).level == "HARD"


async def test_apply_invalid_value_ignored(env_s):
    svm, settings = env_s
    effs = await svm.apply(1, "level", "NONSENSE")
    assert effs == []


async def test_apply_none_sets_all_levels(env_s):
    svm, settings = env_s
    await svm.apply(1, "level", "none")
    assert (await settings.get(1)).level is None


async def test_set_and_keep_level(env_s):
    svm, settings = env_s
    effs = await svm.set_level(1, "MEDIUM")
    assert isinstance(effs[0], EditCurrent)
    assert (await settings.get(1)).level == "MEDIUM"
    keep = await svm.keep_level(1)
    assert isinstance(keep[0], EditCurrent)

# ═══════════════════════ test_listening_vm ═══════════════════════
"""ListeningViewModel без aiogram: уровни → тексты → плеер, перевод, воспроизведение."""
import pytest

from providers.tts import AbstractTTSProvider, Speed
from repositories.pyfile import PyFileTextRepository
from repositories.json_settings_repo import JsonSettingsRepository
from repositories.session_repo import SessionStore
from services.listening_service import ListeningService
from services.settings_service import SettingsService
from viewmodels.listening_vm import ListeningViewModel
from viewmodels.base import SwapPanel, Send, SendVoice
from keyboards.spec import InlineSpec, ReplySpec


class _FakeTTS(AbstractTTSProvider):
    async def synthesize(self, text, speed=Speed.NORMAL, voice=None):
        return "/tmp/fake.mp3"  # без сети


_TEXTS = [
    {"id": 1, "title": "One", "content": "Hello world", "translation": "Привет", "level": "A1"},
    {"id": 2, "title": "Two", "content": "Good morning", "translation": "Доброе утро", "level": "A2"},
]


@pytest.fixture
def env_l(tmp_path):
    listening = ListeningService(PyFileTextRepository(_TEXTS), _FakeTTS())
    settings = SettingsService(JsonSettingsRepository(str(tmp_path / "settings.json")))
    return ListeningViewModel(listening, settings, SessionStore())


async def test_open_shows_levels_panel(env_l):
    effs = await env_l.open(1)
    assert isinstance(effs[0], SwapPanel)
    assert isinstance(effs[0].view.keyboard, ReplySpec)


async def test_choose_level_lists_texts(env_l):
    effs = await env_l.choose_level(1, "EASY")   # A1+A2 → оба текста
    assert isinstance(effs[0], Send)
    assert isinstance(effs[0].view.keyboard, InlineSpec)


async def test_open_text_then_translate_and_play(env_l):
    await env_l.open_text(1, 1)
    tr = await env_l.translate(1)
    assert isinstance(tr[0], Send) and "Привет" in tr[0].view.text
    played = await env_l.play(1, "🐢 Медленно")
    assert isinstance(played[0], SendVoice)


async def test_play_without_open_asks_to_open(env_l):
    effs = await env_l.play(1, "🐢 Медленно")
    assert isinstance(effs[0], Send) and "открой текст" in effs[0].view.text.lower()


async def test_back_to_levels(env_l):
    effs = await env_l.back_to_levels(1)
    assert isinstance(effs[0], SwapPanel)

# ═══════════════════════ test_progress_vm ═══════════════════════
"""ProgressViewModel без aiogram: агрегат streak + SRS-коробки + точность."""
import pytest

from repositories.json_progress_repo import JsonProgressRepository
from repositories.json_srs_repo import JsonSrsRepository
from repositories.json_stats_repo import JsonStatsRepository
from repositories.json_settings_repo import JsonSettingsRepository
from services.progress_service import ProgressService
from services.srs_service import SrsService
from services.stats_service import StatsService
from services.settings_service import SettingsService
from viewmodels.progress_vm import ProgressViewModel
from viewmodels.base import SwapPanel
from keyboards.spec import ReplySpec


@pytest.fixture
def env_p(tmp_path):
    return ProgressViewModel(
        ProgressService(JsonProgressRepository(str(tmp_path / "p.json"))),
        SrsService(JsonSrsRepository(str(tmp_path / "srs.json"))),
        StatsService(JsonStatsRepository(str(tmp_path / "st.json"))),
        SettingsService(JsonSettingsRepository(str(tmp_path / "s.json"))),
    ), tmp_path


async def test_open_returns_progress_panel(env_p):
    pvm, _ = env_p
    effs = await pvm.open(1)
    assert isinstance(effs[0], SwapPanel)
    assert isinstance(effs[0].view.keyboard, ReplySpec)
    assert "прогресс" in effs[0].view.text.lower()


async def test_progress_reflects_activity(env_p):
    pvm, _ = env_p
    # накидаем активности через сервисы
    await pvm._progress.record(1)
    await pvm._srs.review(1, 10, True)          # слово в изучении
    await pvm._stats.record(1, "EASY", True)     # точность EASY
    effs = await pvm.open(1)
    text = effs[0].view.text
    assert "Слова в изучении" in text
    assert "Точность за 7 дней" in text