import uuid

from fastapi import APIRouter
from pydantic import BaseModel

from src.agents.mastery import score_and_update_mastery
from src.agents.quiz_grading import grade_quiz
from src.agents.remediation import build_remediation_plan
from src.agents.schemas import QuizAnswer, QuizSubmission, RemediationPlan
from src.api.deps import CurrentStudent
from src.core.errors import AppError
from src.db.models import StudyKitType
from src.db.session import DbSession
from src.domain import study_kits as study_kits_domain

router = APIRouter(prefix="/quiz", tags=["quiz"])


class QuizSubmitRequest(BaseModel):
    topic_id: uuid.UUID
    study_kit_id: uuid.UUID
    answers: list[QuizAnswer]


class QuizSubmitResponse(BaseModel):
    score: float
    is_pass: bool
    previous_mastery_score: float
    new_mastery_score: float
    consecutive_failures: int
    remediation: RemediationPlan | None


@router.post("/submit", response_model=QuizSubmitResponse)
async def submit_quiz(
    payload: QuizSubmitRequest, db: DbSession, student: CurrentStudent
) -> QuizSubmitResponse:
    """Grade a quiz submission server-side and update the topic's mastery.

    The score is computed here from `study_kit.content`'s stored correct
    answers (`agents.quiz_grading.grade_quiz`) — never taken from the
    client, so a student can't self-report their own mastery. Remediation
    fires automatically when `score_and_update_mastery` says it should.
    """
    study_kit = await study_kits_domain.get_for_student(db, student.id, payload.study_kit_id)
    if study_kit.kit_type != StudyKitType.QUIZ or study_kit.topic_id != payload.topic_id:
        raise AppError("invalid_quiz_reference", "study_kit_id does not match a quiz for the given topic_id")

    score = grade_quiz(study_kit.content, payload.answers)
    submission = QuizSubmission(study_kit_id=study_kit.id, answers=payload.answers, score=score)
    mastery_result = await score_and_update_mastery(db, student.id, payload.topic_id, submission)

    remediation = None
    if mastery_result.remediation_triggered:
        remediation = await build_remediation_plan(db, student.id, payload.topic_id, mastery_result)

    await db.commit()
    return QuizSubmitResponse(
        score=score,
        is_pass=mastery_result.is_pass,
        previous_mastery_score=mastery_result.previous_score,
        new_mastery_score=mastery_result.new_score,
        consecutive_failures=mastery_result.consecutive_failures,
        remediation=remediation,
    )
