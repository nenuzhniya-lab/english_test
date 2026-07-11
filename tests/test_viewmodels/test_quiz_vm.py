"""QuizViewModel без aiogram: старт, ответ, финал, защита от устаревшего вопроса."""
import pytest

from repositories.json_srs_repo import JsonSrsRepository
from repositories.json_stats_repo import JsonStatsRepository
from repositories.json_progress_repo import JsonProgressRepository
from repositories.json_settings_repo import JsonSettingsRepository
from repositories.session_repo import SessionStore
from services.quiz_service import QuizService
from services.vocabulary_service import VocabularyService
from services.srs_service import SrsService
from services.stats_service import StatsService
from services.progress_service import ProgressService
from services.settings_service import SettingsService
from viewmodels.quiz_vm import QuizViewModel
from viewmodels.base import SwapPanel, Send, StartTimer, EditMessage, Notify


@pytest.fixture
def vm(tmp_path, word_repo):
    vocab = VocabularyService(word_repo)
    return QuizViewModel(
        QuizService(),
        {"vocabulary": vocab},
        SrsService(JsonSrsRepository(str(tmp_path / "srs.json"))),
        StatsService(JsonStatsRepository(str(tmp_path / "stats.json"))),
        ProgressService(JsonProgressRepository(str(tmp_path / "progress.json"))),
        SettingsService(JsonSettingsRepository(str(tmp_path / "settings.json"))),
        SessionStore(),
        n_options=4,
    )


def _types(effs):
    return [type(e).__name__ for e in effs]


async def test_start_emits_panel_question_timer(vm):
    effs = await vm.start(1, 1, "vocabulary")
    assert _types(effs) == ["SwapPanel", "Send", "StartTimer"]
    assert isinstance(effs[0], SwapPanel)
    assert effs[1].track_key == "question"
    assert vm.has_active(1)


async def test_answer_correct_then_next(vm):
    await vm.start(1, 1, "vocabulary")
    vm.track_question_message(1, 500)
    s = vm._load(1)
    effs = await vm.answer(1, s.qid, s.current.correct)
    assert _types(effs) == ["Notify", "EditMessage", "Send", "StartTimer"]
    assert effs[0].text == "✅ Верно!"
    assert isinstance(effs[1], EditMessage) and effs[1].message_id == 500


async def test_stale_qid_rejected(vm):
    await vm.start(1, 1, "vocabulary")
    effs = await vm.answer(1, 999, 0)
    assert len(effs) == 1 and isinstance(effs[0], Notify)


async def test_full_run_finishes_and_clears(vm):
    await vm.start(1, 1, "vocabulary")
    vm.track_question_message(1, 500)
    steps, saw_finish = 0, False
    while vm.has_active(1) and steps < 20:
        s = vm._load(1)
        effs = await vm.answer(1, s.qid, s.current.correct)
        steps += 1
        for e in effs:
            if isinstance(e, Send) and e.track_key == "question":
                vm.track_question_message(1, 500 + steps)
            if isinstance(e, SwapPanel):
                saw_finish = True
    assert saw_finish and not vm.has_active(1)
    assert steps == 6  # 6 слов EASY в фикстуре


async def test_timeout_reveals(vm):
    await vm.start(1, 1, "vocabulary")
    vm.track_question_message(1, 500)
    s = vm._load(1)
    effs = await vm.timeout(1, s.qid)
    assert any(isinstance(e, EditMessage) for e in effs)


async def test_stop_when_no_session(vm):
    effs = await vm.stop(1)
    assert len(effs) == 1 and isinstance(effs[0], SwapPanel)
