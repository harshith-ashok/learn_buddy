import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.agents.schemas import RemediationPlan, WorkedStepFeedback
from src.agents.worked_answer import grade_worked_answer
from src.api.deps import CurrentStudent, LLMClientDep, rate_limiter
from src.core.config import get_settings
from src.db.models import WorkedAnswerAttempt
from src.db.session import DbSession
from src.domain import worked_answer as worked_answer_domain

_settings = get_settings()

router = APIRouter(
    prefix="/worked-answer",
    tags=["worked-answer"],
    dependencies=[
        Depends(
            rate_limiter(
                "worked_answer_grade",
                _settings.worked_answer_grade_rate_limit,
                _settings.worked_answer_grade_rate_limit_window_seconds,
            )
        )
    ],
)


class GradeRequest(BaseModel):
    study_kit_id: uuid.UUID
    problem_index: int = Field(ge=0)
    work: str = Field(min_length=1, max_length=4000)


class GradeResponse(BaseModel):
    covered: bool
    is_correct: bool
    accuracy_score: float
    overall_feedback: str
    step_feedback: list[WorkedStepFeedback]
    first_error_step: int | None
    previous_mastery_score: float | None
    new_mastery_score: float | None
    consecutive_failures: int | None
    remediation: RemediationPlan | None


class AttemptOut(BaseModel):
    id: uuid.UUID
    study_kit_id: uuid.UUID
    problem_index: int
    work: str
    is_correct: bool
    accuracy_score: float
    overall_feedback: str
    step_feedback: list[WorkedStepFeedback]
    first_error_step: int | None


def _to_out(attempt: WorkedAnswerAttempt) -> AttemptOut:
    return AttemptOut(
        id=attempt.id,
        study_kit_id=attempt.study_kit_id,
        problem_index=attempt.problem_index,
        work=attempt.work,
        is_correct=attempt.is_correct,
        accuracy_score=attempt.accuracy_score,
        overall_feedback=attempt.overall_feedback,
        step_feedback=[WorkedStepFeedback.model_validate(step) for step in attempt.step_feedback],
        first_error_step=attempt.first_error_step,
    )


@router.post("/grade", response_model=GradeResponse)
async def grade(
    payload: GradeRequest, db: DbSession, student: CurrentStudent, llm_client: LLMClientDep
) -> GradeResponse:
    """Grade a student's worked solution to one problem, step by step, and update mastery.

    `study_kit_id` must be a `problem_guide` kit owned by the caller;
    `problem_index` selects a problem from its stored `content.problems`
    list — `404`/`400` (`invalid_study_kit_reference` /
    `invalid_problem_index`) if either doesn't resolve. Rate-limited
    (`worked_answer_grade_rate_limit` per
    `worked_answer_grade_rate_limit_window_seconds`) — this calls the
    model. `covered=false` means the model's own guardrail refused (see
    `agent-design.md` → "Worked-answer grading"); mastery fields are then
    `null`.
    """
    result = await grade_worked_answer(
        db, student.id, payload.study_kit_id, payload.problem_index, payload.work, llm_client
    )
    await db.commit()
    return GradeResponse(
        covered=result.covered,
        is_correct=result.is_correct,
        accuracy_score=result.accuracy_score,
        overall_feedback=result.overall_feedback,
        step_feedback=result.step_feedback,
        first_error_step=result.first_error_step,
        previous_mastery_score=result.mastery.previous_score if result.mastery else None,
        new_mastery_score=result.mastery.new_score if result.mastery else None,
        consecutive_failures=result.mastery.consecutive_failures if result.mastery else None,
        remediation=result.remediation,
    )


@router.get("", response_model=list[AttemptOut])
async def list_attempts(
    study_kit_id: uuid.UUID, problem_index: int, db: DbSession, student: CurrentStudent
) -> list[AttemptOut]:
    """Every past attempt at one problem, newest first."""
    attempts = await worked_answer_domain.list_for_problem(db, student.id, study_kit_id, problem_index)
    return [_to_out(attempt) for attempt in attempts]
