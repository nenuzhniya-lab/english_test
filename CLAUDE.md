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
- **repositories/** — DAO. `pyfile/` (контент), `json_*` (данные юзера), `session_repo` (эфемерный TTL).
- **keyboards/** — `spec` (домен) → `factory.to_markup`; `builders` — раскладки + текст-константы reply-кнопок.
- **models/** — dataclass + `difficulty` (мапперы) + `ProgressSnapshot`.

## Конвенции

- **Reply = навигация** (нижняя панель), **inline = выбор ответа/значения**.
  Reply-кнопки матчатся по тексту → их подписи ТОЛЬКО из констант `keyboards/builders.py` (`BTN_*`).
- Состояние экрана (тест/аудио) — в `SessionStore`, ключи `quiz:<uid>` / `listen:<uid>` / `panel:<uid>`.
- Сложность хранится кодом `EASY/MEDIUM/HARD` (или `None`=все). Поле `UserSettings.level` — историческое
  имя, значение = Difficulty (переименование отложено, чтобы не двоить работу).
- callback_data — только `callbacks.py` (единый формат). CallbackData-фабрики сознательно не вводили (KISS).

## Известные ловушки

- **Reply-клавиатуру нельзя сменить без нового сообщения** → `swap_reply_keyboard` шлёт новое
  служебное и удаляет прошлое (id хранится в `panel:<uid>`). Сообщения-вопросы теста НЕ трогаются.
- **Таймер теста**: гонки гасятся полем `qid` (ответ/переход инкрементит его; устаревший таймаут видит
  несовпадение и выходит). `timer_service` держит ≤1 таймер на юзера.
- **Миграции** идемпотентны и отмечаются в `.migrations.json`; запускать ДО `build_container()`
  (репозитории кэшируют файлы в `__init__`).
- **Точность в прогрессе — кумулятивная**, не «за 7 дней» (в данных нет окна) — подпись честная.
- **Тесты пишут JSON** — прогонять на temp-файлах (env `SETTINGS_FILE` и т.д.), иначе засорят проект.

## Как добавить

- **Новый тип теста**: `QuestionProvider.items(difficulty)` → зарегистрировать в реестре в `containers.py`.
  Движок `quiz_vm` не трогается (OCP).
- **Новый уровень/маппинг**: только `models/difficulty.py` (+ миграция, если меняются хранимые значения).
- **Новый экран**: VM в `viewmodels/`, билдеры в `keyboards/builders.py`, тонкий хендлер + `execute`.

## Проверка

```bash
pytest                                          # 39 тестов
mypy --strict models services viewmodels        # 0 ошибок
python3 -c "import bot; from containers import build_container; build_container()"
```
