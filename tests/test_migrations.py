"""Миграции m001 (CEFR→Difficulty) и m002 (stats по дням) + runner (idempotent)."""
import json
from types import SimpleNamespace

import migrations as m


def test_m001_settings_values():
    out = m.m001_settings({"1": {"user_id": 1, "level": "A1"},
                           "2": {"user_id": 2, "level": "B2"},
                           "3": {"user_id": 3, "level": None}})
    assert out["1"]["level"] == "EASY"
    assert out["2"]["level"] == "HARD"
    assert out["3"]["level"] is None


def test_m001_settings_idempotent():
    once = m.m001_settings({"1": {"user_id": 1, "level": "A2"}})
    twice = m.m001_settings({k: dict(v) for k, v in once.items()})
    assert once == twice == {"1": {"user_id": 1, "level": "MEDIUM"}}


def test_m001_stats_merges_b1_b2():
    out = m.m001_stats({"1": {"A1": {"c": 5, "t": 10}, "A2": {"c": 2, "t": 4},
                              "B1": {"c": 1, "t": 3}, "B2": {"c": 4, "t": 6}}})
    assert out["1"] == {"EASY": {"c": 5, "t": 10},
                        "MEDIUM": {"c": 2, "t": 4},
                        "HARD": {"c": 5, "t": 9}}


def test_m001_stats_idempotent():
    once = m.m001_stats({"1": {"A1": {"c": 1, "t": 2}}})
    assert m.m001_stats(once) == once


def test_m002_wraps_cumulative_under_ancient_day():
    out = m.m002_stats({"1": {"HARD": {"c": 5, "t": 10}, "EASY": {"c": 2, "t": 4}}})
    assert out["1"]["HARD"] == {"0": {"c": 5, "t": 10}}
    assert out["1"]["EASY"] == {"0": {"c": 2, "t": 4}}


def test_m002_idempotent():
    once = m.m002_stats({"1": {"HARD": {"c": 5, "t": 10}}})
    assert m.m002_stats(json.loads(json.dumps(once))) == once


def test_m002_already_per_day_untouched():
    per_day = {"1": {"HARD": {"739000": {"c": 3, "t": 5}}}}
    assert m.m002_stats(json.loads(json.dumps(per_day))) == per_day


def _settings(tmp_path):
    return SimpleNamespace(
        settings_file=str(tmp_path / "settings.json"),
        stats_file=str(tmp_path / "stats.json"),
        migrations_state_file=str(tmp_path / ".migrations.json"),
    )


def test_runner_applies_once_and_marks(tmp_path):
    s = _settings(tmp_path)
    (tmp_path / "settings.json").write_text(json.dumps({"1": {"user_id": 1, "level": "B1"}}))
    (tmp_path / "stats.json").write_text(json.dumps({"1": {"B1": {"c": 1, "t": 2}}}))

    m.run_migrations(s)
    assert json.loads((tmp_path / "settings.json").read_text())["1"]["level"] == "HARD"
    # m001 слил B1→HARD, затем m002 положил под «древний» день 0
    assert json.loads((tmp_path / "stats.json").read_text())["1"] == {"HARD": {"0": {"c": 1, "t": 2}}}

    state = json.loads((tmp_path / ".migrations.json").read_text())
    assert m.M001_ID in state["applied"] and m.M002_ID in state["applied"]

    before = (tmp_path / "stats.json").read_text()
    m.run_migrations(s)                                  # повторно ничего не меняет
    assert (tmp_path / "stats.json").read_text() == before


def test_runner_no_files_is_safe(tmp_path):
    s = _settings(tmp_path)
    m.run_migrations(s)
    state = json.loads((tmp_path / ".migrations.json").read_text())
    assert m.M001_ID in state["applied"]
