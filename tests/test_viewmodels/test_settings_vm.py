"""SettingsViewModel без aiogram: открытие, выбор поля, применение, валидация."""
import pytest

from repositories.json_settings_repo import JsonSettingsRepository
from repositories.json_stats_repo import JsonStatsRepository
from services.settings_service import SettingsService
from services.stats_service import StatsService
from viewmodels.settings_vm import SettingsViewModel
from viewmodels.base import SwapPanel, Send, EditCurrent, Notify
from keyboards.spec import InlineSpec, ReplySpec


@pytest.fixture
def vm(tmp_path):
    settings = SettingsService(JsonSettingsRepository(str(tmp_path / "settings.json")))
    stats = StatsService(JsonStatsRepository(str(tmp_path / "stats.json")))
    return SettingsViewModel(settings, stats), settings


async def test_open_shows_sections_panel(vm):
    svm, _ = vm
    effs = await svm.open(1)
    assert isinstance(effs[0], SwapPanel)
    assert isinstance(effs[0].view.keyboard, ReplySpec)


async def test_open_field_shows_inline_values(vm):
    svm, _ = vm
    effs = await svm.open_field(1, "🎚 Сложность")
    assert isinstance(effs[0], Send)
    assert isinstance(effs[0].view.keyboard, InlineSpec)


async def test_apply_updates_and_confirms(vm):
    svm, settings = vm
    effs = await svm.apply(1, "level", "HARD")
    assert [type(e).__name__ for e in effs] == ["EditCurrent", "Notify"]
    assert (await settings.get(1)).level == "HARD"


async def test_apply_invalid_value_alerts(vm):
    svm, settings = vm
    effs = await svm.apply(1, "level", "NONSENSE")
    assert len(effs) == 1 and isinstance(effs[0], Notify) and effs[0].alert


async def test_apply_none_sets_all_levels(vm):
    svm, settings = vm
    await svm.apply(1, "level", "none")
    assert (await settings.get(1)).level is None


async def test_set_and_keep_level(vm):
    svm, settings = vm
    effs = await svm.set_level(1, "MEDIUM")
    assert isinstance(effs[0], EditCurrent)
    assert (await settings.get(1)).level == "MEDIUM"
    keep = await svm.keep_level(1)
    assert isinstance(keep[0], EditCurrent)
