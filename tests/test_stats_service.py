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
