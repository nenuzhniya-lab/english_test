"""ViewModel экрана прогресса: агрегирует streak + SRS-коробки + точность."""
from __future__ import annotations

from typing import List

from keyboards import builders as kb
from models import ProgressSnapshot
from presenters import render_progress
from services.progress_service import ProgressService
from services.settings_service import SettingsService
from services.srs_service import SrsService
from services.stats_service import StatsService
from viewmodels.base import Effect, SwapPanel, ViewState


class ProgressViewModel:
    def __init__(self, progress: ProgressService, srs: SrsService,
                 stats: StatsService, settings: SettingsService):
        self._progress = progress
        self._srs = srs
        self._stats = stats
        self._settings = settings

    async def open(self, user_id: int) -> List[Effect]:
        summary = await self._progress.summary(user_id)
        breakdown = await self._srs.boxes_breakdown(user_id)
        accuracy = await self._stats.accuracy_by_level(user_id)
        level = (await self._settings.get(user_id)).level
        snap = ProgressSnapshot(
            streak=summary["streak"], best=summary["best"], today=summary["today"],
            goal=summary["goal"], total=summary["total"], level=level,
            new=breakdown["new"], familiar=breakdown["familiar"], learned=breakdown["learned"],
            studying=breakdown["studying"], due=breakdown["due"], accuracy=accuracy,
        )
        return [SwapPanel(ViewState(render_progress(snap), kb.progress_screen(breakdown["due"])))]
