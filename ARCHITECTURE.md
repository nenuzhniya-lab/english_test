# ARCHITECTURE.md

MVVM поверх чистой слоистой архитектуры. Поток: **команды вниз, состояние вверх**.

```
Telegram update
   │
   ▼
handlers/*.py ─ парсит апдейт → зовёт метод ViewModel ─┐
   ▲                                                    │
   │ Effect'ы                                           ▼
handlers/effects.py ◀──── list[Effect] ────────── viewmodels/*.py
   │ (send/edit/delete/voice/timer/panel)               │ зовёт
   ▼                                                     ▼
aiogram Bot                                        services/*.py → repositories/* → data/json/providers
```

## Ключевые контракты

- `ViewState(text, keyboard: KeyboardSpec|None, parse_mode)` — что показать.
- `Effect` = `Send | SwapPanel | SendVoice | EditCurrent | EditMessage | DeleteMessage | StartTimer | Notify`.
- VM метод → `list[Effect]`. `handlers/effects.execute(effects, bot, chat_id, user_id, container, callback?)`.
- `KeyboardSpec` = `InlineSpec | ReplySpec` (домен) → `keyboards.factory.to_markup` → aiogram markup.

## Карта файлов

| Файл | Слой | Ответственность | Зависит от |
|---|---|---|---|
| `handlers/*.py` | View | Апдейт → intent → `execute` | VM, effects, callbacks |
| `handlers/effects.py` | View | Единственный мост Effect→aiogram | factory, utils, VM(timeout) |
| `keyboards/spec.py` | View | Домен клавиатур (без aiogram) | — |
| `keyboards/factory.py` | View | Спека → aiogram markup | aiogram, spec |
| `keyboards/builders.py` | View | Раскладки + текст-константы reply | callbacks, models, spec |
| `presenters/*` | View | Форматирование текста (бары, карточки) | models |
| `viewmodels/base.py` | ViewModel | ViewState + словарь Effect | spec |
| `viewmodels/quiz_vm.py` | ViewModel | Стейт-машина теста: start/answer/timeout/stop/finish, адаптив | quiz/srs/stats/progress/settings, session_repo, providers |
| `viewmodels/listening_vm.py` | ViewModel | Уровни → тексты → плеер, курсор в сессии | listening/settings, session_repo |
| `viewmodels/settings_vm.py` | ViewModel | Разделы/значения, валидация, адаптив-переход | settings/stats |
| `viewmodels/progress_vm.py` | ViewModel | Агрегат streak+коробки+точность → снапшот | progress/srs/stats/settings |
| `services/quiz_service.py` | Model | Сборка вопросов: дистракторы, перемешивание | models |
| `services/question_provider.py` | Model | Протокол `items(difficulty)` (OCP) | quiz_service |
| `services/srs_service.py` | Model | Коробки Лейтнера, due, разбивка групп | srs repo |
| `services/stats_service.py` | Model | Адаптив 3 уровня, точность по уровням | stats repo |
| `services/timer_service.py` | Model | Отложенные колбэки, ≤1 на ключ | asyncio |
| `models/difficulty.py` | Model | CEFR→Difficulty (раздельно слова/тексты), подписи | — |
| `repositories/session_repo.py` | Repo | Эфемерные сессии экранов (TTL) | — |
| `repositories/json_*` | Repo | Данные юзера (read-write, кэш+lock) | models |
| `migrations/` | Infra | m001 CEFR→Difficulty + runner (idempotent) | difficulty |

## Полный сценарий: тест слов от старта до адаптива

```
"📖 Слова" (reply)
  → handlers/quiz_flow.start_section → quiz_vm.start(chat, uid, "vocabulary")
      · settings.get → сложность; providers["vocabulary"].items(difficulty) → пул
      · quiz_service.build(pool, size, n_options) → list[QuizQuestion]
      · SessionStore["quiz:uid"] = QuizSession
      · effects: [SwapPanel(intro, панель «Стоп»), Send(вопрос, inline, track="question"), StartTimer]
  → effects.execute: swap панель; send вопрос → msg_id → quiz_vm.track_question_message; timer.schedule

ответ (inline callback ans:qid:idx)
  → quiz_flow.on_answer → quiz_vm.answer(uid, qid, chosen)
      · qid != session.qid → [Notify("закрыт")]  (защита от гонок)
      · session.check/register/advance; save
      · stats.record (слова) · srs.review(ref) · progress.record   (в try/except)
      · effects: [Notify(✅/❌), EditMessage(prev → reveal ✅/❌+перевод),
                  Send(следующий вопрос) | finish]

финал (session.is_finished)
  → quiz_vm._finish: [SwapPanel(итог %, главное меню)]
      · если слова и stats.suggestion → Send(предложение ⬆️/⬇️, inline level_set/keep)
  → user жмёт ⬆️ → settings.set_level → stats.reset (свежий отсчёт)
```

## Почему так

- **VM без aiogram** → логику экранов покрываем юнит-тестами без Telegram (см. `tests/test_viewmodels/`).
- **Эффекты вместо прямого I/O** → VM детерминирована и проверяема; весь Telegram-I/O в одном месте.
- **session_repo, не FSM** → состояние отвязано от aiogram; TTL чистит брошенные сессии.
  (И FSM MemoryStorage, и session_repo одинаково эфемерны — переживание redeploy обеспечивает Volume, не код.)
- **Реестр провайдеров** → новый тип теста не трогает движок (OCP).
