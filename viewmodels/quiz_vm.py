"""ViewModel теста: стейт-машина вопрос→вопрос, дедлайн, ✅/❌, адаптив.

Вся логика решений здесь; хендлер только исполняет эффекты. Состояние теста —
QuizSession в SessionStore (не в aiogram FSM), поэтому VM тестируема без Telegram.
Защита от гонок таймера — поле qid: ответ/переход увеличивает его, устаревший
таймаут видит несовпадение и ничего не делает.
"""
from __future__ import annotations

import logging
import random
from typing import Any, Awaitable, Dict, List, Optional, Tuple

from keyboards import builders as kb
from models import QuizSession, QuizQuestion, UserSettings
from presenters import SECTION_TITLE as _SECTION_TITLE, SECTION_FALLBACK
from services.mistakes_service import MistakesService
from services.progress_service import ProgressService, DAILY_GOAL
from services.quiz_service import QuizService, QuizItem, QuestionProvider
from services.study_service import StudyService
from services.settings_service import SettingsService
from services.srs_service import SrsService
from services.stats_service import StatsService
from repositories.session_repo import SessionStore
from viewmodels.base import (
    Effect, EditMessage, Send, StartTimer, SwapPanel, ViewState,
)

logger = logging.getLogger(__name__)

_INTRO = "🎯 <b>Поехали!</b> Отвечай кнопками в сообщениях.\n<i>Остановить — кнопкой снизу.</i>"

_ENDLESS_LOW = 3     # осталось ≤ этого вопросов в буфере → подкачать ещё
_ENDLESS_BATCH = 10  # сколько вопросов добавлять за подкачку


class QuizViewModel:
    def __init__(
        self,
        quiz: QuizService,
        providers: Dict[str, QuestionProvider],
        srs: SrsService,
        stats: StatsService,
        progress: ProgressService,
        settings: SettingsService,
        mistakes: MistakesService,
        study: StudyService,
        sessions: SessionStore,
        n_options: int,
    ):
        self._quiz = quiz
        self._providers = providers          # {секция: провайдер} — OCP
        self._vocabulary = providers["vocabulary"]  # для пула повторения/дистракторов
        self._srs = srs
        self._stats = stats
        self._progress = progress
        self._settings = settings
        self._mistakes = mistakes
        self._study = study
        self._sessions = sessions
        self._n_options = n_options

    # ── доступ к сессии ──
    def _key(self, user_id: int) -> str:
        return f"quiz:{user_id}"

    def _load(self, user_id: int) -> Optional[QuizSession]:
        raw = self._sessions.get(self._key(user_id))
        return QuizSession.from_dict(raw) if raw else None

    def _save(self, user_id: int, session: QuizSession) -> None:
        self._sessions.set(self._key(user_id), session.to_dict())

    def _clear(self, user_id: int) -> None:
        self._sessions.pop(self._key(user_id))

    def has_active(self, user_id: int) -> bool:
        return self._load(user_id) is not None

    # ── меню выбора теста ──
    async def tests_menu(self, user_id: int) -> List[Effect]:
        due = len(await self._srs.due_ids(user_id))
        mistakes = await self._mistakes.count(user_id)
        return [SwapPanel(ViewState("📝 <b>Выбери тест:</b>", kb.tests_menu(due, mistakes)))]

    # ── запуск ──
    async def start(self, chat_id: int, user_id: int, section: str, endless: bool = False) -> List[Effect]:
        us = await self._settings.get(user_id)
        questions, level = await self._questions_for_start(user_id, section, us)

        if not questions:
            return [SwapPanel(ViewState(self._empty_message(section), kb.main_menu()))]

        session = QuizSession(
            section=section, user_id=user_id, chat_id=chat_id,
            questions=questions, level=level, deadline=us.quiz_seconds, endless=endless,
            seen_ids=[q.ref for q in questions if q.ref is not None] if endless else [],
        )
        self._save(user_id, session)
        effects: List[Effect] = [
            SwapPanel(ViewState(self._intro(session), kb.test_panel())),
            Send(ViewState(self._question_text(session, session.i),
                           kb.quiz_options(session.qid, session.current.options)),
                 track_key="question"),
        ]
        if session.deadline:
            effects.append(StartTimer(user_id, session.qid, session.deadline))
        return effects

    async def _questions_for_start(
        self, user_id: int, section: str, us: UserSettings
    ) -> Tuple[List[QuizQuestion], Optional[str]]:
        """(questions, level) для старта. level=None где адаптив неприменим."""
        if section == "review":
            pool = await self._vocabulary.items(None)
            due = set(await self._srs.due_ids(user_id))
            ask = [it for it in pool if it.ref in due]
            if not ask:
                return [], None
            return self._quiz.build(pool, us.quiz_size, self._n_options, ask_from=ask), None

        if section == "mistakes":
            wanted = set(await self._mistakes.top(user_id))
            if not wanted:
                return [], None
            questions = await self._build_from_pairs(wanted)
            random.shuffle(questions)
            return questions[:us.quiz_size], None

        if section == "study":
            done = (await self._progress.summary(user_id)).get("today", 0)
            target = self._study.target(DAILY_GOAL, done)
            study_due = list(await self._srs.due_ids(user_id))
            mistakes = await self._mistakes.top(user_id)
            mistake_words = {ref for kind, ref in mistakes if kind == "word"}
            due_set = set(study_due)
            # новые слова текущей сложности, не в SRS-долге и не среди ошибок
            level_words = await self._vocabulary.items(us.level)
            new_refs = [it.ref for it in level_words
                        if it.ref is not None and it.ref not in due_set and it.ref not in mistake_words]
            random.shuffle(new_refs)
            picks = self._study.compose(study_due, mistakes, new_refs, target)
            if not picks:
                return [], None
            questions = await self._build_from_pairs(set(picks))
            random.shuffle(questions)
            return questions[:target], None

        items = await self._items_for(section, us.level)
        return self._quiz.build(items, us.quiz_size, self._n_options), us.level

    async def _build_from_pairs(self, wanted: set[Tuple[str, int]]) -> List[QuizQuestion]:
        """Строит вопросы по набору (kind, ref), ПО ТИПАМ — дистракторы того же вида."""
        questions: List[QuizQuestion] = []
        for prov in self._providers.values():
            pool = await prov.items(None)
            ask = [it for it in pool if (it.kind, it.ref) in wanted]
            if ask:
                questions += self._quiz.build(pool, len(ask), self._n_options, ask_from=ask)
        return questions

    def _empty_message(self, section: str) -> str:
        if section == "review":
            return ("🎉 Пока нечего повторять!\n"
                    "Пройди «📖 Слова» — и они начнут возвращаться к повторению по расписанию.")
        if section == "mistakes":
            return "🎉 Ошибок нет! Отвечай в тестах — промахи попадут сюда на отработку."
        if section == "study":
            return "🎉 На сегодня всё! Отличная работа. Возвращайся завтра или открой «📝 Тесты»."
        return "❌ Недостаточно данных для теста."

    def _intro(self, session: QuizSession) -> str:
        if session.endless:
            return ("♾ <b>Бесконечный режим.</b> Вопросы идут без остановки.\n"
                    "<i>Закончить — «⏹ Остановить тест» снизу.</i>")
        if session.section == "study":
            return ("⚡ <b>Учить сейчас</b> — смесь повторения, твоих ошибок и новых слов.\n"
                    "<i>Остановить — кнопкой снизу.</i>")
        return _INTRO

    async def _items_for(self, section: str, difficulty: Optional[str]) -> List[QuizItem]:
        provider = self._providers.get(section, self._vocabulary)
        return await provider.items(difficulty)

    async def _refill(self, session: QuizSession) -> None:
        """Бесконечный режим: дозагрузить пул, исключая уже показанные (seen_ids).

        Пул исчерпан → разрешаем повтор (сбрасываем seen) — на HARD слов мало.
        Буфер держим окном (не грузим весь пул сразу) — память/плавность.
        """
        provider = self._providers.get(session.section, self._vocabulary)
        pool = await provider.items(session.level)
        seen = set(session.seen_ids)
        fresh = [it for it in pool if it.ref not in seen]
        if not fresh:                      # слова закончились → цикл заново
            session.seen_ids = []
            fresh = pool
        if not fresh:
            return
        chosen = random.sample(fresh, min(_ENDLESS_BATCH, len(fresh)))
        new_questions = self._quiz.build(pool, len(chosen), self._n_options, ask_from=chosen)
        session.questions.extend(new_questions)
        session.seen_ids.extend([q.ref for q in new_questions if q.ref is not None])

    # хендлер вызывает после отправки вопроса, сообщая его message_id
    def track_question_message(self, user_id: int, msg_id: int) -> None:
        s = self._load(user_id)
        if s is not None:
            s.msg_id = msg_id
            self._save(user_id, s)

    # ── ответ / таймаут ──
    def ack_text(self, user_id: int, qid: int, chosen: int) -> str:
        """Мгновенная всплывашка на кнопку (дешёвый peek по сессии в памяти).

        Вызывается хендлером ДО тяжёлой работы, чтобы спиннер на кнопке гас сразу.
        """
        s = self._load(user_id)
        if s is None or s.qid != qid:
            return "Этот вопрос уже закрыт ⏱"
        return "✅ Верно!" if chosen == s.current.correct else "❌ Неверно"

    async def answer(self, user_id: int, qid: int, chosen: int) -> List[Effect]:
        s = self._load(user_id)
        if s is None or s.qid != qid:
            return []  # всплывашку уже показал ack_text
        return await self._resolve(s, user_id, chosen)

    async def timeout(self, user_id: int, qid: int) -> List[Effect]:
        s = self._load(user_id)
        if s is None or s.qid != qid:
            return []  # уже ответили / сессия сменилась
        return await self._resolve(s, user_id, None)

    async def _resolve(self, s: QuizSession, user_id: int, chosen: Optional[int]) -> List[Effect]:
        index = s.i
        q = s.current
        prev_msg_id = s.msg_id
        is_correct = s.check(chosen)
        s.register(is_correct)
        s.advance()
        if s.endless and (s.total - s.i) <= _ENDLESS_LOW:
            await self._refill(s)   # держим буфер полным → бесконечность без пауз
        self._save(user_id, s)

        if s.section == "vocabulary":
            await self._safe(self._stats.record(user_id, s.level, is_correct), "stats")
        # SRS — только слова (у verbs/sentences id из другого пространства, будет коллизия)
        if q.kind == "word" and q.ref is not None:
            await self._safe(self._srs.review(user_id, q.ref, is_correct), "srs")
        # Лог ошибок — по любому типу с (kind, ref)
        if q.kind is not None and q.ref is not None:
            if is_correct:
                await self._safe(self._mistakes.record_correct(user_id, q.kind, q.ref), "mistakes")
            else:
                await self._safe(self._mistakes.record_wrong(user_id, q.kind, q.ref), "mistakes")
        await self._safe(self._progress.record(user_id), "progress")

        if chosen is None:
            verdict = "⏱ <b>Время вышло!</b>"
        elif is_correct:
            verdict = "✅ <b>Верно!</b>"
        else:
            verdict = "❌ <b>Неверно.</b>"
        reveal_text = self._question_text(s, index) + f"\n\n{verdict}"
        if q.note:
            reveal_text += f"\n\n💬 {q.note}"

        effects: List[Effect] = []
        if prev_msg_id is not None:
            effects.append(EditMessage(prev_msg_id, ViewState(
                reveal_text, kb.quiz_reveal(q.options, q.correct, chosen, q.option_notes))))

        if s.is_finished:
            effects += await self._finish(s, user_id)
        else:
            effects.append(Send(ViewState(self._question_text(s, s.i),
                                          kb.quiz_options(s.qid, s.current.options)),
                                track_key="question"))
            if s.deadline:
                effects.append(StartTimer(user_id, s.qid, s.deadline))
        return effects

    # ── стоп ──
    async def stop(self, user_id: int) -> List[Effect]:
        s = self._load(user_id)
        if s is None:
            return [SwapPanel(ViewState("Активного теста нет 🙂", kb.main_menu()))]
        effects: List[Effect] = []
        if s.msg_id is not None:
            effects.append(EditMessage(s.msg_id, ViewState(
                self._question_text(s, s.i) + "\n\n⏹ <i>Тест остановлен</i>", None)))
        s.qid += 1  # инвалидируем таймер текущего вопроса
        effects += await self._finish(s, user_id, stopped=True)
        return effects

    # ── финал + адаптив ──
    async def _finish(self, s: QuizSession, user_id: int, stopped: bool = False) -> List[Effect]:
        c, w, pct = s.correct, s.wrong, s.percent
        total = c + w
        if stopped:
            head = "⏹ <b>Тест остановлен</b>"
        else:
            emoji = "🏆" if pct >= 80 else "👍" if pct >= 50 else "📚"
            head = f"{emoji} <b>Тест завершён!</b>"
        text = (
            f"{head}  ({_SECTION_TITLE.get(s.section, '')})\n\n"
            f"✅ Верно: {c}/{total}\n"
            f"❌ Ошибок: {w}/{total}\n"
            f"📊 Результат: <b>{pct}%</b>\n\n"
            f"<i>Прокрути вверх, чтобы разобрать ошибки.</i>"
        )
        section, level = s.section, s.level
        # для «Учить сейчас» — прогресс дневной цели
        if section == "study":
            summ = await self._progress.summary(user_id)
            text += f"\n\n⚡ Сегодня: <b>{summ.get('today', 0)}/{summ.get('goal', DAILY_GOAL)}</b>"
        self._clear(user_id)
        effects: List[Effect] = [SwapPanel(ViewState(text, kb.main_menu()))]

        if not stopped and section == "vocabulary":
            sug = await self._safe_return(self._stats.suggestion(user_id, level))
            if sug:
                direction, target, acc = sug
                if direction == "up":
                    msg = f"🚀 <b>Отлично — {acc}% верно!</b>\nГотов усложнить слова?"
                else:
                    msg = f"🙂 <b>Пока сложновато ({acc}%).</b>\nПопробуем уровень полегче?"
                effects.append(Send(ViewState(msg, kb.level_suggestion(direction, target, level))))
        return effects

    # ── рендер текста вопроса ──
    def _question_text(self, session: QuizSession, index: int) -> str:
        q = session.questions[index]
        title = _SECTION_TITLE.get(session.section, SECTION_FALLBACK)
        timer = f"   ⏱ {session.deadline} сек" if session.deadline else ""
        return f"{title} · вопрос <b>{index + 1}/{session.total}</b>{timer}\n\n{q.prompt}"

    # ── безопасные обёртки для побочных записей ──
    async def _safe(self, coro: Awaitable[Any], what: str) -> None:
        try:
            await coro
        except Exception:
            logger.exception("quiz: не удалось записать %s", what)

    async def _safe_return(self, coro: Awaitable[Any]) -> Any:
        try:
            return await coro
        except Exception:
            logger.exception("quiz: сбой предложения адаптива")
            return None
