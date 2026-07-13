"""Юнит-тесты моделей и сервисов (difficulty, quiz-session, srs, stats, mistakes, study, json-store)."""

# ═══════════════════════ test_difficulty_mapper ═══════════════════════
"""CEFR → Difficulty: маппинг и балансировка объёмов."""
from collections import Counter

from models.difficulty import (
    Difficulty, word_difficulty, text_difficulty, difficulty_label, label_to_difficulty,
)


def test_word_mapping():
    assert word_difficulty("A1") is Difficulty.EASY
    assert word_difficulty("A2") is Difficulty.MEDIUM
    assert word_difficulty("B1") is Difficulty.HARD
    assert word_difficulty("B2") is Difficulty.HARD


def test_text_mapping_differs_from_words():
    # тексты: A2 → EASY (у слов A2 → MEDIUM)
    assert text_difficulty("A2") is Difficulty.EASY
    assert text_difficulty("B1") is Difficulty.MEDIUM
    assert text_difficulty("C1") is Difficulty.HARD


def test_unknown_code_falls_back_hard():
    assert word_difficulty("Z9") is Difficulty.HARD
    assert text_difficulty("Z9") is Difficulty.HARD


def test_labels_roundtrip():
    assert difficulty_label(None) == "🌍 Все"
    assert label_to_difficulty(difficulty_label("EASY")) == "EASY"
    assert label_to_difficulty("нет такого") is None


def test_word_balance_on_real_data():
    from data.words_data import WORDS
    counts = Counter(word_difficulty(w["level"]).value for w in WORDS)
    assert counts == {"EASY": 511, "MEDIUM": 314, "HARD": 174}


def test_text_balance_on_real_data():
    from data.texts_data import TEXTS
    counts = Counter(text_difficulty(t["level"]).value for t in TEXTS)
    assert counts == {"EASY": 60, "MEDIUM": 60, "HARD": 30}

# ═══════════════════════ test_quiz_session ═══════════════════════
"""Чистая логика QuizSession: проверка ответа, счёт, переходы, %."""
from models.quiz import QuizSession, QuizQuestion


def _session(n=3):
    qs = [QuizQuestion(prompt=f"q{i}", options=["a", "b"], correct=i % 2, ref=i) for i in range(n)]
    return QuizSession(section="vocabulary", user_id=1, chat_id=1, questions=qs, deadline=15)


def test_check_and_percent():
    s = _session()
    assert s.total == 3 and s.percent == 0
    assert s.check(s.current.correct) is True
    assert s.check(None) is False
    s.register(True)
    s.register(False)
    assert s.percent == 50  # 1 из 2


def test_advance_bumps_qid_and_index():
    s = _session()
    assert s.i == 0 and s.qid == 0
    s.advance()
    assert s.i == 1 and s.qid == 1
    assert s.current is s.questions[1]


def test_is_finished():
    s = _session(1)
    assert not s.is_finished
    s.advance()
    assert s.is_finished


def test_serialization_roundtrip():
    s = _session()
    s.register(True)
    s.advance()
    s.msg_id = 555
    restored = QuizSession.from_dict(s.to_dict())
    assert restored.correct == 1 and restored.i == 1 and restored.qid == 1
    assert restored.msg_id == 555
    assert restored.questions[0].ref == 0

# ═══════════════════════ test_srs_service ═══════════════════════
"""SRS: рост коробок Лейтнера при верных ответах, сброс при ошибке."""
import datetime

import pytest

from repositories.json_srs_repo import JsonSrsRepository
from services.srs_service import SrsService


@pytest.fixture
def srs(tmp_path):
    return SrsService(JsonSrsRepository(str(tmp_path / "srs.json")))


def _today():
    return datetime.date.today().toordinal()


async def test_correct_grows_box_and_interval(srs):
    uid, wid = 1, 100
    # box 1→2→3→4→5, интервалы 1,3,7,14,30
    expected = [(1, 1), (2, 3), (3, 7), (4, 14), (5, 30)]
    for box, interval in expected:
        await srs.review(uid, wid, True)
        got_box, due = await srs._repo.get(uid, wid)
        assert (got_box, due - _today()) == (box, interval)


async def test_max_box_caps_at_5(srs):
    uid, wid = 1, 7
    for _ in range(8):
        await srs.review(uid, wid, True)
    box, _ = await srs._repo.get(uid, wid)
    assert box == 5


async def test_wrong_resets_to_box1_due_today(srs):
    uid, wid = 1, 100
    for _ in range(3):
        await srs.review(uid, wid, True)  # уехало в коробку 3
    await srs.review(uid, wid, False)
    box, due = await srs._repo.get(uid, wid)
    assert box == 1 and due == _today()
    assert wid in await srs.due_ids(uid)  # снова к повторению сегодня


async def test_boxes_breakdown_groups(srs):
    uid = 1
    await srs.review(uid, 1, False)                 # box1 → Новые
    for _ in range(2):
        await srs.review(uid, 2, True)              # box2 → Знакомые
    for _ in range(4):
        await srs.review(uid, 3, True)              # box4 → Выучено
    b = await srs.boxes_breakdown(uid)
    assert b["new"] == 1 and b["familiar"] == 1 and b["learned"] == 1
    assert b["studying"] == 3

# ═══════════════════════ test_stats_service ═══════════════════════
"""Адаптив сложности на 3 уровнях: пороги 85/45, крайние переходы = no-op."""
import pytest

from repositories.json_stats_repo import JsonStatsRepository
from services.stats_service import StatsService


@pytest.fixture
def stats(tmp_path):
    return StatsService(JsonStatsRepository(str(tmp_path / "stats.json")))


async def _feed(stats, uid, level, correct, wrong):
    for _ in range(correct):
        await stats.record(uid, level, True)
    for _ in range(wrong):
        await stats.record(uid, level, False)


async def test_suggest_up_at_85(stats):
    await _feed(stats, 1, "EASY", correct=9, wrong=1)  # 90%
    sug = await stats.suggestion(1, "EASY")
    assert sug == ("up", "MEDIUM", 90)


async def test_suggest_down_at_45(stats):
    await _feed(stats, 1, "MEDIUM", correct=4, wrong=6)  # 40%
    sug = await stats.suggestion(1, "MEDIUM")
    assert sug == ("down", "EASY", 40)


async def test_no_suggestion_in_middle(stats):
    await _feed(stats, 1, "MEDIUM", correct=6, wrong=4)  # 60%
    assert await stats.suggestion(1, "MEDIUM") is None


async def test_min_answers_gate(stats):
    await _feed(stats, 1, "EASY", correct=5, wrong=0)  # 100% но всего 5 < 8
    assert await stats.suggestion(1, "EASY") is None


async def test_edge_levels_are_noop(stats):
    await _feed(stats, 1, "HARD", correct=10, wrong=0)   # 100% но выше HARD некуда
    assert await stats.suggestion(1, "HARD") is None
    await _feed(stats, 2, "EASY", correct=0, wrong=10)   # 0% но ниже EASY некуда
    assert await stats.suggestion(2, "EASY") is None


async def test_accuracy_by_level(stats):
    await _feed(stats, 1, "EASY", correct=8, wrong=2)
    await _feed(stats, 1, "HARD", correct=3, wrong=7)
    acc = await stats.accuracy_by_level(1)
    assert acc == [("EASY", 8, 10), ("HARD", 3, 10)]  # порядок EASY→HARD, MEDIUM без данных пропущен


async def test_unknown_level_ignored(stats):
    await stats.record(1, "A1", True)  # старый CEFR-код — не из WORD_LEVELS
    assert await stats.suggestion(1, "A1") is None
    assert await stats.accuracy_by_level(1) == []


async def test_window_excludes_old_days(stats):
    import datetime
    today = datetime.date.today().toordinal()
    # данные 10 дней назад — вне окна 7 дней
    await stats._repo.add(1, "EASY", 8, 10, today - 10)
    assert await stats.accuracy_by_level(1) == []
    assert await stats.suggestion(1, "EASY") is None
    # свежие данные — в окне
    await stats._repo.add(1, "EASY", 9, 10, today)
    assert await stats.accuracy_by_level(1) == [("EASY", 9, 10)]

# ═══════════════════════ test_mistakes_service ═══════════════════════
"""Лог ошибок: запись, реабилитация (2 верных подряд), (kind,ref) без коллизий."""
import pytest

from repositories.json_mistakes_repo import JsonMistakesRepository
from services.mistakes_service import MistakesService


@pytest.fixture
def m(tmp_path):
    return MistakesService(JsonMistakesRepository(str(tmp_path / "m.json")))


async def test_wrong_then_two_correct_rehabilitates(m):
    await m.record_wrong(1, "word", 5)
    assert await m.count(1) == 1
    await m.record_correct(1, "word", 5)   # streak 1 — ещё в логе
    assert await m.count(1) == 1
    await m.record_correct(1, "word", 5)   # streak 2 — реабилитирован
    assert await m.count(1) == 0


async def test_wrong_resets_streak(m):
    await m.record_wrong(1, "word", 5)
    await m.record_correct(1, "word", 5)   # streak 1
    await m.record_wrong(1, "word", 5)     # ошибка снова → streak 0
    await m.record_correct(1, "word", 5)   # streak 1 — не реабилитация
    assert await m.count(1) == 1


async def test_kind_ref_no_collision(m):
    await m.record_wrong(1, "word", 5)
    await m.record_wrong(1, "verb", 5)     # тот же id, другой тип
    assert await m.count(1) == 2
    assert set(await m.top(1)) == {("word", 5), ("verb", 5)}


async def test_correct_for_non_mistake_is_noop(m):
    await m.record_correct(1, "word", 99)
    assert await m.count(1) == 0


async def test_top_sorted_by_frequency(m):
    await m.record_wrong(1, "word", 1)
    for _ in range(3):
        await m.record_wrong(1, "word", 2)
    assert (await m.top(1))[0] == ("word", 2)
    assert (await m.top(1, limit=1)) == [("word", 2)]

# ═══════════════════════ test_study_service ═══════════════════════
"""Политика «Учить сейчас»: размер сессии и приоритет микса."""
from services.study_service import StudyService


def test_target_fills_to_goal_with_minimum():
    s = StudyService()
    assert s.target(20, 0) == 20
    assert s.target(20, 15) == 5     # осталось 5
    assert s.target(20, 20) == 5     # цель выполнена → всё равно минимум 5
    assert s.target(20, 100) == 5


def test_compose_priority_due_then_mistakes_then_new():
    s = StudyService()
    picks = s.compose([1, 2], [("word", 2), ("verb", 9)], [3, 4, 5], target=4)
    # due: (word,1),(word,2); mistakes: (word,2) дубль → пропуск, (verb,9); добор новыми: (word,3)
    assert picks == [("word", 1), ("word", 2), ("verb", 9), ("word", 3)]


def test_compose_trims_to_target():
    s = StudyService()
    assert len(s.compose([1, 2, 3, 4, 5], [], [], 3)) == 3


def test_compose_empty():
    s = StudyService()
    assert s.compose([], [], [], 20) == []

# ═══════════════════════ test_json_store ═══════════════════════
"""Базовый JSON-стор: устойчивость к битому файлу (не ронять старт бота)."""
from repositories.json_stats_repo import JsonStatsRepository
from repositories.json_settings_repo import JsonSettingsRepository
from repositories.json_mistakes_repo import JsonMistakesRepository


def test_corrupt_json_loads_empty_not_crash(tmp_path):
    p = tmp_path / "stats.json"
    p.write_text("{ это не json", encoding="utf-8")
    repo = JsonStatsRepository(str(p))   # раньше здесь падал json.loads → бот не стартовал
    assert repo._cache == {}


def test_corrupt_settings_loads_empty(tmp_path):
    p = tmp_path / "settings.json"
    p.write_text("сломано", encoding="utf-8")
    repo = JsonSettingsRepository(str(p))
    assert repo._cache == {}


async def test_repo_still_writes_after_corrupt_load(tmp_path):
    p = tmp_path / "mistakes.json"
    p.write_text("[]", encoding="utf-8")   # dict ожидается, а тут список → пустой кэш
    repo = JsonMistakesRepository(str(p))
    assert repo._cache == {}
    await repo.bump(1, "word", 5, "2026-01-01")
    assert await repo.get(1, "word", 5) == (1, 0)
