from src.agents.schemas import QuizAnswer
from src.core.errors import AppError


class InvalidQuizContentError(AppError):
    """A `study_kits` row claims to be a quiz but its `content` has no questions."""

    def __init__(self) -> None:
        super().__init__("invalid_quiz_content", "This study kit has no quiz questions to grade")


def grade_quiz(content: dict, answers: list[QuizAnswer]) -> float:
    """Grade `answers` against a persisted `QuizContent`-shaped `content` dict.

    The score is computed server-side from the student's own submitted
    answers and the quiz's stored `correct_index` — never trusted as a
    raw client-supplied number, so a student can't self-report mastery.
    A question left unanswered, or answered more than once, counts once
    using its last submitted answer.
    """
    questions = content.get("questions") or []
    if not questions:
        raise InvalidQuizContentError()

    selected_by_question = {answer.question_index: answer.selected_index for answer in answers}
    correct = sum(
        1
        for index, question in enumerate(questions)
        if selected_by_question.get(index) == question.get("correct_index")
    )
    return correct / len(questions)
