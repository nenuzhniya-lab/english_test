"""Миграция m001: CEFR → Difficulty в settings.json и stats.json + идемпотентность."""
import json
from types import SimpleNamespace

from migrations import m001_cefr_to_difficulty as m001
from migrations.runner import run_migrations


def test_migrate_settings_values():
    data = {"1": {"user_id": 1, "level": "A1"},
            "2": {"user_id": 2, "level": "B2"},
            "3": {"user_id": 3, "level": None}}
    out = m001.migrate_settings({k: dict(v) for k, v in data.items()})
    assert out["1"]["level"] == "EASY"
    assert out["2"]["level"] == "HARD"
    assert out["3"]["level"] is None


def test_migrate_settings_idempotent():
    once = m001.migrate_settings({"1": {"user_id": 1, "level": "A2"}})
    twice = m001.migrate_settings({k: dict(v) for k, v in once.items()})
    assert once == twice == {"1": {"user_id": 1, "level": "MEDIUM"}}


def test_migrate_stats_merges_b1_b2():
    data = {"1": {"A1": {"c": 5, "t": 10}, "A2": {"c": 2, "t": 4},
                  "B1": {"c": 1, "t": 3}, "B2": {"c": 4, "t": 6}}}
    out = m001.migrate_stats(data)
    assert out["1"] == {"EASY": {"c": 5, "t": 10},
                        "MEDIUM": {"c": 2, "t": 4},
                        "HARD": {"c": 5, "t": 9}}  # B1+B2 слиты


def test_migrate_stats_idempotent():
    data = {"1": {"A1": {"c": 1, "t": 2}}}
    once = m001.migrate_stats(data)
    twice = m001.migrate_stats(once)
    assert once == twice


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

    run_migrations(s)
    settings_after = json.loads((tmp_path / "settings.json").read_text())
    stats_after = json.loads((tmp_path / "stats.json").read_text())
    assert settings_after["1"]["level"] == "HARD"
    assert stats_after["1"] == {"HARD": {"c": 1, "t": 2}}

    state = json.loads((tmp_path / ".migrations.json").read_text())
    assert m001.MIGRATION_ID in state["applied"]

    # повторный прогон ничего не меняет (миграция отмечена применённой)
    run_migrations(s)
    assert json.loads((tmp_path / "settings.json").read_text()) == settings_after


def test_runner_no_files_is_safe(tmp_path):
    s = _settings(tmp_path)
    run_migrations(s)  # файлов нет — не падает
    state = json.loads((tmp_path / ".migrations.json").read_text())
    assert state["applied"] == [m001.MIGRATION_ID]
