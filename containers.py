"""Композиционный корень: единственное место создания конкретных реализаций.

Переход на Google Sheets = заменить строку создания репозитория.
Простая фабрика вместо DI-контейнера — это KISS. Сборка разбита на слои:
репозитории → сервисы → viewmodels, плюс эфемерная инфра (сессии, таймеры).
"""
from __future__ import annotations

from dataclasses import dataclass

from config import settings

from data.words_data import WORDS
from data.verbs_data import VERBS
from data.texts_data import TEXTS
from data.sentences_data import SENTENCES

from repositories.pyfile import (
    PyFileWordRepository,
    PyFileVerbRepository,
    PyFileTextRepository,
    PyFileSentenceRepository,
)
from repositories.json_settings_repo import JsonSettingsRepository
from repositories.json_stats_repo import JsonStatsRepository
from repositories.json_srs_repo import JsonSrsRepository
from repositories.json_progress_repo import JsonProgressRepository
from repositories.session_repo import SessionStore

from providers.tts import EdgeTTSProvider

from services import (
    QuizService,
    VocabularyService,
    VerbService,
    SentenceService,
    ListeningService,
    SettingsService,
    StatsService,
    SrsService,
    ProgressService,
)
from services.timer_service import TimerService

from viewmodels.main_menu_vm import MainMenuViewModel
from viewmodels.settings_vm import SettingsViewModel
from viewmodels.listening_vm import ListeningViewModel
from viewmodels.progress_vm import ProgressViewModel
from viewmodels.quiz_vm import QuizViewModel


@dataclass
class Container:
    # ── сервисы (Model) ──
    vocabulary: VocabularyService
    verbs: VerbService
    sentences: SentenceService
    listening: ListeningService
    quiz: QuizService
    settings: SettingsService
    stats: StatsService
    srs: SrsService
    progress: ProgressService
    # ── инфра (эфемерная) ──
    sessions: SessionStore
    timers: TimerService
    # ── viewmodels (ViewModel) ──
    main_vm: MainMenuViewModel
    settings_vm: SettingsViewModel
    listening_vm: ListeningViewModel
    progress_vm: ProgressViewModel
    quiz_vm: QuizViewModel


def _build_repos():
    # ← здесь меняется .py → Google Sheets
    return dict(
        words=PyFileWordRepository(WORDS),
        verbs=PyFileVerbRepository(VERBS),
        texts=PyFileTextRepository(TEXTS),
        sentences=PyFileSentenceRepository(SENTENCES),
        settings=JsonSettingsRepository(settings.settings_file),
        stats=JsonStatsRepository(settings.stats_file),
        srs=JsonSrsRepository(settings.srs_file),
        progress=JsonProgressRepository(settings.progress_file),
    )


def _build_services(repos: dict) -> dict:
    tts = EdgeTTSProvider(settings.tts_voice, settings.tts_cache_dir)
    return dict(
        vocabulary=VocabularyService(repos["words"]),
        verbs=VerbService(repos["verbs"]),
        sentences=SentenceService(repos["sentences"]),
        listening=ListeningService(repos["texts"], tts),
        quiz=QuizService(),
        settings=SettingsService(repos["settings"]),
        stats=StatsService(repos["stats"]),
        srs=SrsService(repos["srs"]),
        progress=ProgressService(repos["progress"]),
    )


def _build_viewmodels(svc: dict, sessions: SessionStore) -> dict:
    return dict(
        main_vm=MainMenuViewModel(),
        settings_vm=SettingsViewModel(svc["settings"], svc["stats"]),
        listening_vm=ListeningViewModel(svc["listening"], svc["settings"], sessions),
        progress_vm=ProgressViewModel(svc["progress"], svc["srs"], svc["stats"], svc["settings"]),
        quiz_vm=QuizViewModel(
            svc["quiz"],
            {  # реестр провайдеров вопросов (OCP): секция → провайдер
                "vocabulary": svc["vocabulary"],
                "verbs": svc["verbs"],
                "sentences": svc["sentences"],
            },
            svc["srs"], svc["stats"], svc["progress"], svc["settings"],
            sessions, settings.quiz_options,
        ),
    )


def build_container() -> Container:
    repos = _build_repos()
    svc = _build_services(repos)
    sessions = SessionStore()
    timers = TimerService()
    vms = _build_viewmodels(svc, sessions)
    return Container(
        sessions=sessions, timers=timers,
        **svc, **vms,
    )
