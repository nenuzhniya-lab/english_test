"""Чистая логика QuizSession: проверка ответа, счёт, переходы, %."""
from models.quiz import QuizSession, QuizQuestion


def _session(n=3):
    qs = [QuizQuestion(prompt=f"q{i}", options=["a", "b"], correct=i % 2, ref=i) for i in range(n)]
    return QuizSession(section="vocabulary", user_id=1, chat_id=1, questions=qs, deadline=15)


def test_check_and_percent():
    s = _session()
    assert s.total == 3 and s.percent == 0
    assert s.check(s.current.correct) is True
    assert s.check(None) is False
    s.register(True)
    s.register(False)
    assert s.percent == 50  # 1 из 2


def test_advance_bumps_qid_and_index():
    s = _session()
    assert s.i == 0 and s.qid == 0
    s.advance()
    assert s.i == 1 and s.qid == 1
    assert s.current is s.questions[1]


def test_is_finished():
    s = _session(1)
    assert not s.is_finished
    s.advance()
    assert s.is_finished


def test_serialization_roundtrip():
    s = _session()
    s.register(True)
    s.advance()
    s.msg_id = 555
    restored = QuizSession.from_dict(s.to_dict())
    assert restored.correct == 1 and restored.i == 1 and restored.qid == 1
    assert restored.msg_id == 555
    assert restored.questions[0].ref == 0
