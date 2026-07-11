"""Протокол поставщика вопросов теста (OCP).

Движок теста (quiz_vm) работает только с этим интерфейсом и реестром
{секция: провайдер}. Новый тип теста = новый провайдер + запись в реестр,
ноль правок в движке.
"""
from __future__ import annotations

from typing import List, Optional, Protocol

from services.quiz_service import QuizItem


class QuestionProvider(Protocol):
    async def items(self, difficulty: Optional[str] = None) -> List[QuizItem]:
        """Вопросы теста. difficulty учитывается там, где применим (иначе игнорируется)."""
        ...
