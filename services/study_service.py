"""Политика «умной дневной сессии» — чистая, без aiogram и без I/O.

Собирает состав сессии из трёх источников по приоритету (не терять выученное →
латать ошибки → двигаться дальше). Наполнение сборки живёт здесь; сборка вопросов
и запуск — в quiz_vm (тот же движок теста, KISS/DRY).
"""
from __future__ import annotations

from typing import List, Tuple

_MIN_SESSION = 5   # минимум карточек, даже если цель на сегодня уже выполнена


class StudyService:
    def target(self, goal: int, done_today: int) -> int:
        """Сколько карточек в сессии: добить до цели, но не меньше минимума."""
        return max(_MIN_SESSION, goal - done_today)

    def compose(
        self,
        due_word_refs: List[int],
        mistake_pairs: List[Tuple[str, int]],
        new_word_refs: List[int],
        target: int,
    ) -> List[Tuple[str, int]]:
        """(kind, ref) до target по приоритету: SRS-долг → ошибки → новые. Без дублей."""
        picks: List[Tuple[str, int]] = []
        seen: set[Tuple[str, int]] = set()

        def add(pair: Tuple[str, int]) -> None:
            if pair not in seen:
                seen.add(pair)
                picks.append(pair)

        for ref in due_word_refs:
            add(("word", ref))
        for pair in mistake_pairs:
            add(pair)
        for ref in new_word_refs:
            if len(picks) >= target:
                break
            add(("word", ref))
        return picks[:target]
