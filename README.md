# 🇬🇧 English Learning Bot

Telegram-бот для изучения английского (aiogram 3.x). Тесты со словами, глаголами и
предложениями, аудирование, интервальное повторение (SRS), адаптивная сложность,
экран прогресса и озвучка через TTS.

Архитектура — **MVVM поверх чистой слоистой**: логика экранов в ViewModel (без aiogram),
данные за репозиториями, внешние движки за провайдерами. Три уровня сложности 🟢🟡🔴.

![python](https://img.shields.io/badge/python-3.9%2B-blue)
![aiogram](https://img.shields.io/badge/aiogram-3.7-green)
![tests](https://img.shields.io/badge/tests-39%20passing-brightgreen)
![mypy](https://img.shields.io/badge/mypy-strict-informational)

---

## 🚀 Быстрый старт

```bash
cp .env.example .env        # впиши BOT_TOKEN от @BotFather
pip install -r requirements.txt
python3 bot.py
```

Разработка (тесты и типы — в прод не идут):

```bash
pip install -r requirements-dev.txt
pytest            # 39 тестов
mypy --strict models services viewmodels
```

## 🚄 Railway

1. Залить репозиторий в GitHub.
2. Создать проект в Railway из репозитория.
3. Variables → `BOT_TOKEN = <токен>`.
4. Start Command: `python3 bot.py` (или через `Procfile`).

> **Важно про данные.** `settings/stats/srs/progress/mistakes.json` + `.sessions.json` пишутся
> на диск. Чтобы они переживали redeploy, в Railway должен быть подключён **Volume**, и env-пути
> (`SETTINGS_FILE`, `STATS_FILE`, `SRS_FILE`, `PROGRESS_FILE`, `MISTAKES_FILE`, `SESSION_FILE`,
> `MIGRATIONS_STATE_FILE`) должны указывать в него. Без volume прогресс/ошибки эфемерны.
>
> **Один инстанс.** Бот на long-polling — держи `replicas = 1` (две реплики = конфликт `getUpdates`).

**Стек:** Python 3.9+ (`from __future__ import annotations`), `aiogram==3.7.0`,
`edge-tts==7.2.8`. Прод-зависимостей всего две (+ stdlib-конфиг).

---

## ✨ Возможности

Главное меню (нижняя reply-панель):
**⚡ Учить сейчас / 📝 Тесты · 🎧 Аудирование / 📊 Прогресс · ⚙️ Настройки**

### ⚡ Учить сейчас
Одна кнопка — умная дневная сессия: миксует **просроченные повторения (SRS) + твои ошибки +
новые слова** до дневной цели (20), вперемешку. Убирает вопрос «что учить», держит SRS-долг
под контролем — максимум пользы на готовом контенте.

### 📝 Тесты
Меню (reply): **Слова · Глаголы / Предложения · 🔁 Повторение (N) / ❗ Мои ошибки (N) / ♾ Без конца / ⬅️ Назад**. Единый движок:
- каждый вопрос — **отдельным сообщением** (отвеченные помечаются ✅/❌ и остаются в чате);
- **авто-переход**, **дедлайн-таймер** с авто-провалом (или без таймера);
- варианты ответа — **inline** в сообщении; **⏹ Остановить** — в нижней панели;
- **Слова** (999, 🟢🟡🔴), **Глаголы** (V2/V3), **Предложения** (fill-in-the-gap);
- **🔁 Повторение** — слова к сроку по SRS; **❗ Мои ошибки** — реальные промахи (слова/глаголы/
  предложения) до отработки (2 верных подряд — уходит); **♾ Без конца** — вопросы без остановки.

### 🎧 Аудирование
- **3 уровня сложности** (🟢🟡🔴), тексты выбираются сеткой номеров (inline);
- **3 скорости** озвучки (🐢🚶🏃), перевод, возврат к уровням — reply-панель плеера;
- голос диктора берётся из настроек, аудио кэшируется по хэшу (голос+скорость+текст).

### 📊 Прогресс
Текстовый экран с юникод-барами (без графических зависимостей): серия дней,
слова по 3 SRS-группам (🌱 Новые / 📚 Знакомые / ✅ Выучено), точность по уровням,
сколько слов ждёт повторения.

### ⚙️ Настройки
🎚 Сложность (🟢🟡🔴/Все) · ⏱ Таймер · 🔢 Вопросов · 🔊 Голос. Разделы — reply-панель,
значения — inline с ✅ на текущем.

### 🧠 Обучающие механики
- **SRS** — коробки Лейтнера (интервалы 1→3→7→14→30 дней); ошибка возвращает слово в начало;
- **Лог ошибок** — фактические промахи по `(тип, id)`; отрабатываются, пока не ответишь 2 раза подряд;
- **Адаптивная сложность** — по точности за 7 дней предлагает ⬆️ (≥85%) / ⬇️ (≤45%) на 3 ступенях;
- **Серия (streak)** и дневная цель — любой ответ считается практикой;
- **Напоминания** — раз в день пинг «N слов ждут повторения».

> 🗣 Speaking (голос → STT) пока не в меню, но интерфейс `AbstractSTTProvider` заложен под будущее.

---

## 🎚 Уровни сложности

Контент размечен по CEFR (A1–C1), пользователю показываем **3 уровня**. Маппинг
CEFR→сложность **разный для слов и текстов** — чтобы объёмы были ровными
(см. `models/difficulty.py`):

| Уровень | Слова | Тексты |
|---|---|---|
| 🟢 EASY | A1 — **511** | A1+A2 — **60** |
| 🟡 MEDIUM | A2 — **314** | B1+B2 — **60** |
| 🔴 HARD | B1+B2 — **174** | C1 — **30** |

Ребалансировка живёт в маппере — файлы `data/*.py` не тронуты. Переход старых
пользователей `level: "A2" → "MEDIUM"` делает миграция `m001` при старте (settings + stats).

---

## 🏗 Архитектура (MVVM)

```
View (Telegram I/O)     handlers/*.py + handlers/effects.py, keyboards/*, presenters/*
      ↕  intent (вниз) / ViewState+Effect (вверх)
ViewModel               viewmodels/*.py         ← логика экранов, без aiogram
      ↓
Model (Services)        services/*.py
      ↓
Repositories            repositories/*.py  (+ session_repo — эфемерный)
      ↓
Data / Providers        data/*.py, *.json, providers/*
```

**Ключевое:**
- ViewModel возвращает `ViewState` (текст + спека клавиатуры) и список `Effect`
  (отправить/править/удалить сообщение, голос, таймер, смена панели). aiogram про VM не знает.
- `handlers/effects.py` — **единственный** мост эффект→aiogram. Хендлеры тонкие.
- Состояние экранов (тест, аудио) — в `SessionStore` (in-memory + TTL), не в FSM,
  ради тестируемости VM.
- Клавиатуры — доменные спеки (`keyboards/spec.py`) → `factory.to_markup`. Reply = навигация,
  inline = выбор ответа/значения.

Подробности — в [`ARCHITECTURE.md`](ARCHITECTURE.md). Рабочие инварианты — в [`CLAUDE.md`](CLAUDE.md).

### Структура

```
bot.py                # точка входа: миграции → контейнер → polling
config.py             # .env через stdlib
containers.py         # композиционный корень: repos → services → viewmodels
callbacks.py          # формат callback_data (inline-действия)
settings_catalog.py   # опции настроек

migrations/           # m001 (CEFR→Difficulty) + runner (idempotent, файл-маркер)
models/               # доменные dataclass + difficulty (маппер) + ProgressSnapshot
data/                 # контент как .py (слова 999 · глаголы · предложения · тексты 150)
repositories/         # DAO: pyfile (контент), json_* (данные юзера), session_repo (TTL)
providers/            # tts(edge) · stt(stub) · ai(stub)
services/             # quiz · vocabulary/verb/sentence · listening · settings · stats · srs · progress · timer
viewmodels/           # base (ViewState+Effect) + main/settings/listening/progress/quiz
keyboards/            # spec (домен) · factory (→aiogram) · builders (раскладки)
presenters/           # cards · progress_presenter (бары) · strings (i18n-шов)
handlers/             # тонкие адаптеры + effects (мост в aiogram)
tests/                # pytest: модели, сервисы, миграция, VM без aiogram
```

---

## 🔌 Точки расширения

- **Новый тип теста** — реализовать `QuestionProvider.items()` и добавить в реестр в `containers.py` (OCP, движок не трогаем).
- **Google Sheets** — новый `AbstractWordRepository`, подменить строку в `containers.py`.
- **STT (Speaking)** — реализовать `AbstractSTTProvider.transcribe`.
- **AI/LLM** — реализовать `AbstractAIProvider.complete`.

---

## ✅ Недавно добавлено

- ⚡ **«Учить сейчас»** — умная дневная сессия (SRS-долг + ошибки + новые до цели).
- ❗ **Мои ошибки** — режим отработки фактических промахов (слова/глаголы/предложения).
- ♾ **Бесконечный режим** — вопросы без остановки (буфер дозагружается).
- 🚀 **Скорость** — мгновенный ack кнопок, неблокирующая запись, прогрев TTS, `PROFILE=1`.
- 💾 Персистентность сессий · 📈 точность за 7 дней · 🔊 устойчивый TTS.

## 🔜 Дальше по плану

- 🗣 Speaking: голос → STT → проверка произношения
- ✍️ Активный ввод ответа (typing) вместо выбора из 4
- ☁️ Миграция контента на Google Sheets
- 🔤 i18n через `presenters/strings.py`
