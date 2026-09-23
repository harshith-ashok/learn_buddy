import pytest

from src.agents.quiz_grading import InvalidQuizContentError, grade_quiz
from src.agents.schemas import QuizAnswer

_CONTENT = {
    "questions": [
        {"question": "2+2?", "options": ["3", "4"], "correct_index": 1},
        {"question": "3+3?", "options": ["5", "6"], "correct_index": 1},
    ]
}


def test_grade_quiz_scores_all_correct() -> None:
    score = grade_quiz(
        _CONTENT,
        [QuizAnswer(question_index=0, selected_index=1), QuizAnswer(question_index=1, selected_index=1)],
    )

    assert score == 1.0


def test_grade_quiz_scores_partial_credit() -> None:
    score = grade_quiz(
        _CONTENT,
        [QuizAnswer(question_index=0, selected_index=1), QuizAnswer(question_index=1, selected_index=0)],
    )

    assert score == 0.5


def test_grade_quiz_treats_an_unanswered_question_as_wrong() -> None:
    score = grade_quiz(_CONTENT, [QuizAnswer(question_index=0, selected_index=1)])

    assert score == 0.5


def test_grade_quiz_uses_the_last_answer_for_a_repeated_question_index() -> None:
    score = grade_quiz(
        _CONTENT,
        [
            QuizAnswer(question_index=0, selected_index=0),  # wrong, overwritten below
            QuizAnswer(question_index=0, selected_index=1),  # correct, wins
            QuizAnswer(question_index=1, selected_index=1),
        ],
    )

    assert score == 1.0


def test_grade_quiz_raises_for_content_with_no_questions() -> None:
    with pytest.raises(InvalidQuizContentError):
        grade_quiz({"questions": []}, [])
