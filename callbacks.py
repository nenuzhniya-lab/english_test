"""Единый формат callback_data: сборка (для кнопок) и разбор (для хендлеров).

Один источник правды по «проводному» формату колбэков — вместо магических строк
и хрупких split по всему коду. Навигация ушла на reply-панель, поэтому здесь
остались только inline-действия: ответ в тесте, открытие текста, смена уровня,
применение настройки.
"""
from __future__ import annotations

# ── фиксированные колбэки ──
NOOP = "noop"
LEVEL_KEEP = "lvl:keep"

# ── префиксы параметрических колбэков ──
ANSWER = "ans:"
LISTEN_OPEN = "lst:open:"
LEVEL_SET = "lvl:set:"
_SETTING = "set:"

SETTING_FIELDS = ["level", "time", "size", "voice"]
SETTING_APPLY_PREFIXES = [f"{_SETTING}{f}:v:" for f in SETTING_FIELDS]  # ["set:level:v:", ...]


# ── сборка (для клавиатур) ──
def answer(qid: int, option: int) -> str:
    return f"{ANSWER}{qid}:{option}"


def listen_open(text_id: int) -> str:
    return f"{LISTEN_OPEN}{text_id}"


def level_set(level: str) -> str:
    return f"{LEVEL_SET}{level}"


def setting_apply(field: str, value: object) -> str:
    return f"{_SETTING}{field}:v:{value}"


# ── разбор (для хендлеров) ──
def parse_answer(data: str) -> tuple[int, int]:
    _, qid, opt = data.split(":")
    return int(qid), int(opt)


def parse_listen_open(data: str) -> int:
    return int(data[len(LISTEN_OPEN):])


def parse_level_set(data: str) -> str:
    return data[len(LEVEL_SET):]


def parse_setting_apply(data: str) -> tuple[str, str]:
    _, field, _v, value = data.split(":")
    return field, value


def is_setting_apply(data: str | None) -> bool:
    return data is not None and any(data.startswith(p) for p in SETTING_APPLY_PREFIXES)
