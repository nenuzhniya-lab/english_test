"""CEFR → Difficulty: маппинг и балансировка объёмов."""
from collections import Counter

from models.difficulty import (
    Difficulty, word_difficulty, text_difficulty, difficulty_label, label_to_difficulty,
)


def test_word_mapping():
    assert word_difficulty("A1") is Difficulty.EASY
    assert word_difficulty("A2") is Difficulty.MEDIUM
    assert word_difficulty("B1") is Difficulty.HARD
    assert word_difficulty("B2") is Difficulty.HARD


def test_text_mapping_differs_from_words():
    # тексты: A2 → EASY (у слов A2 → MEDIUM)
    assert text_difficulty("A2") is Difficulty.EASY
    assert text_difficulty("B1") is Difficulty.MEDIUM
    assert text_difficulty("C1") is Difficulty.HARD


def test_unknown_code_falls_back_hard():
    assert word_difficulty("Z9") is Difficulty.HARD
    assert text_difficulty("Z9") is Difficulty.HARD


def test_labels_roundtrip():
    assert difficulty_label(None) == "🌍 Все"
    assert label_to_difficulty(difficulty_label("EASY")) == "EASY"
    assert label_to_difficulty("нет такого") is None


def test_word_balance_on_real_data():
    from data.words_data import WORDS
    counts = Counter(word_difficulty(w["level"]).value for w in WORDS)
    assert counts == {"EASY": 511, "MEDIUM": 314, "HARD": 174}


def test_text_balance_on_real_data():
    from data.texts_data import TEXTS
    counts = Counter(text_difficulty(t["level"]).value for t in TEXTS)
    assert counts == {"EASY": 60, "MEDIUM": 60, "HARD": 30}
