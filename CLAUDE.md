# CLAUDE.md — рабочая память проекта

Telegram-бот изучения английского. Python 3.9, aiogram 3.7, MVVM поверх слоистой.

## Инварианты (не ломать)

- **Python 3.9** в проде → в новом коде обязателен `from __future__ import annotations`;
  в рантайме нельзя `X | Y` и голые `list[...]` вне аннотаций (для дженериков — `typing`).
- Формат `settings/stats/srs/progress.json` меняется только через **миграцию** (`migrations/`),
  не перезаписью. Загрузчики JSON делают `int(uid)` по ключам — не класть служебные ключи внутрь.
- Контент `data/*.py` — read-only; уровни меняются в **маппере** (`models/difficulty.py`), не в данных.
- Точка входа `bot.py` и Railway start command (`python3 bot.py`) — стабильны.
- edge-tts кэширует по хэшу (голос+скорость+текст) — ключ кэша не менять бездумно.

## Карта слоёв (где что лежит)

- **handlers/** — тонкие адаптеры: апдейт → метод VM → `effects.execute`. Никакой логики.
- **handlers/effects.py** — ЕДИНСТВЕННЫЙ мост Effect→aiogram (send/edit/delete/voice/timer/panel).
- **viewmodels/** — логика экранов, без aiogram. Возвращают `ViewState` + `list[Effect]`.
- **services/** — бизнес-логика (quiz/srs/stats/…). Не знают про Telegram.
- **repositories/** — DAO. `pyfile/` (контент), `json_*` (данные юзера, база `_jsonio.JsonStore`), `pyfile.py` (контент), `session_repo` (эфемерный TTL).
- **keyboards/** — `spec` (домен) → `factory.to_markup`; `builders` — раскладки + текст-константы reply-кнопок.
- **models/** — dataclass + `difficulty` (мапперы) + `ProgressSnapshot`.

## Конвенции

- **Reply = навигация** (нижняя панель), **inline = выбор ответа/значения**.
  Reply-кнопки матчатся по тексту → их подписи ТОЛЬКО из констант `keyboards/builders.py` (`BTN_*`).
- Хендлеры вызывают **`dispatch_message` / `dispatch_callback`** (из `handlers/effects.py`), НЕ
  `execute(...)` напрямую. Хелперы собирают `bot/chat_id/user_id/container` в одном месте.
- **Callback-хендлеры делают `await callback.answer(...)` ПЕРВЫМ** — до тяжёлой работы (запись на
  диск и т.п.), чтобы спиннер на inline-кнопке гас мгновенно (без «рваной» анимации). Поэтому VM
  НЕ шлют `Notify` для callback-действий — всплывашку показывает хендлер (для теста — `quiz_vm.ack_text`. Строки/презентеры — `presenters.py`, миграции — `migrations.py`).
- Состояние экрана (тест/аудио) — в `SessionStore`, ключи `quiz:<uid>` / `listen:<uid>` / `panel:<uid>`.
- Сложность хранится кодом `EASY/MEDIUM/HARD` (или `None`=все). Поле `UserSettings.level` — историческое
  имя, значение = Difficulty (переименование отложено, чтобы не двоить работу).
- callback_data — только `callbacks.py` (единый формат). CallbackData-фабрики сознательно не вводили (KISS).

## Известные ловушки

- **Reply-клавиатуру нельзя сменить без нового сообщения** → `swap_reply_keyboard` шлёт новое
  служебное и удаляет прошлое (id хранится в `panel:<uid>`). Сообщения-вопросы теста НЕ трогаются.
  Порядок: сначала шлём новое, потом удаляем старое **фоном** (`create_task`) — без мигания.
- **Производительность записи**: `SessionStore` персистит только `quiz:`/`listen:` (переживают
  redeploy); `panel:<uid>` — в памяти, чтобы не писать файл на каждый переход экрана.
- **Таймер теста**: гонки гасятся полем `qid` (ответ/переход инкрементит его; устаревший таймаут видит
  несовпадение и выходит). `timer_service` держит ≤1 таймер на юзера.
- **Миграции** идемпотентны и отмечаются в `.migrations.json`; запускать ДО `build_container()`
  (репозитории кэшируют файлы в `__init__`). Сейчас две (в `migrations.py`): m001 (CEFR→Difficulty), m002 (stats по дням).
- **Сессии персистентны**: `SessionStore(path=.sessions.json)` хранит значения как `to_dict()`
  (JSON), TTL по wall-clock → активный тест переживает redeploy. Поэтому quiz/listen кладут в стор
  **dict**, не объект (`_save` = `to_dict()`, `_load` = `from_dict()`).
- **Точность в прогрессе — за 7 дней** (скользящее окно): `stats.json` разбит по дням
  (`{uid:{level:{day:{c,t}}}}`), `StatsService.WINDOW_DAYS=7`. Старые кумулятивные данные m002
  положил под день «0» — вне окна.
- **TTS** ретраит с таймаутом и не кэширует битый/пустой файл (`providers/tts/edge`); при открытии
  текста обычная скорость прогревается в фоне (`listening_vm._prewarm`).
- **Режимы теста** = `QuizSession.section` (источник) + `endless: bool` (модификатор), НЕ единый enum.
  Источники: vocabulary/verbs/sentences/review(SRS)/mistakes/study. Движок один; отличие — только
  наполнитель пула в `quiz_vm._questions_for_start`. Новый источник = ветка там (или провайдер).
- **Ошибки (mistakes) ≠ SRS.** SRS — ритм по расписанию (только слова); mistakes — лог фактических
  промахов по `(kind, ref)` (word/verb/sentence), реабилитация 2 верных подряд. UI разведён:
  `🔁 Повторение` (SRS due) vs `❗ Мои ошибки` (лог).
- **kind + ref обязателен для трекинга.** У verbs/sentences теперь есть `ref` (их id) и `kind`.
  ВАЖНО: **SRS пишем только для `kind=="word"`** — id глаголов/предложений из другого пространства,
  иначе коллизия в `srs.json`. Ошибки — по `(kind, ref)`, коллизий нет.
- **Endless**: буфер вопросов дозагружается в `_resolve` (когда до конца ≤3), `seen_ids` дедупит;
  пул исчерпан → повтор. `is_finished` завершает только при stop или если refill ничего не дал.
- **Записи на диск неблокирующие** (`repositories/_jsonio.awrite_json` через `asyncio.to_thread`)
  у 5 JSON-репо; `session_repo` — синхронный (вызывается из sync `_save`). Batch НЕ делаем —
  записи немедленные и долговечные (важно для Railway redeploy).
- **JSON-репо наследуют `_jsonio.JsonStore`** (путь/lock/чтение/запись — без дублей). Чтение
  устойчиво к битому файлу: `{}` + лог вместо падения старта.
- **Тесты пишут JSON** — прогонять на temp-файлах (env `SETTINGS_FILE` и т.д.), иначе засорят проект.
- **Проводка хендлеров**: логика VM в изоляции проходит, но забытый `container=` в `execute`
  роняет КАЖДЫЙ апдейт (бот молчит). Поэтому хендлеры идут через `dispatch_*`-хелперы, а
  `tests/test_handlers_smoke.py` гоняет настоящие апдейты через диспетчер — это ловит регрессию.

## Как добавить

- **Новый тип теста (провайдер)**: `QuestionProvider.items(difficulty)` → реестр в `containers.py`.
- **Новый режим-источник** (как study/mistakes): ветка в `quiz_vm._questions_for_start` (собери пул →
  `quiz.build`) + `_empty_message` + reply-кнопка. Движок/эффекты/финал переиспользуются.
- **Новый уровень/маппинг**: только `models/difficulty.py` (+ миграция, если меняются хранимые значения).
- **Новый экран**: VM в `viewmodels/`, билдеры в `keyboards/builders.py`, тонкий хендлер + `execute`.

## Проверка

```bash
pytest                                          # 79 тестов (вкл. смоук хендлеров + callback)
mypy --strict models services viewmodels        # 0 ошибок
python3 -c "import bot; from containers import build_container; build_container()"
```

Прогон бота в тестах пишет JSON — используй временные пути (иначе засорит проект):
`SETTINGS_FILE=/tmp/s.json STATS_FILE=/tmp/st.json SRS_FILE=/tmp/sr.json PROGRESS_FILE=/tmp/pr.json MISTAKES_FILE=/tmp/mis.json MIGRATIONS_STATE_FILE=/tmp/m.json SESSION_FILE=/tmp/sess.json python3 bot.py`

`PROFILE=1` — логировать мс на обработку апдейта (замер до/после оптимизаций).
