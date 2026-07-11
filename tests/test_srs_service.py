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
