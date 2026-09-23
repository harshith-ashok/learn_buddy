import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.agents.feynman import grade_explanation
from src.agents.schemas import FeynmanBreakdownPoint, RemediationPlan
from src.api.deps import CurrentStudent, LLMClientDep, VectorStoreDep, rate_limiter
from src.core.config import get_settings
from src.db.models import FeynmanAttempt
from src.db.session import DbSession
from src.domain import feynman as feynman_domain

_settings = get_settings()

router = APIRouter(
    prefix="/feynman",
    tags=["feynman"],
    dependencies=[
        Depends(
            rate_limiter(
                "feynman_grade",
                _settings.feynman_grade_rate_limit,
                _settings.feynman_grade_rate_limit_window_seconds,
            )
        )
    ],
)


class GradeRequest(BaseModel):
    topic_id: uuid.UUID
    explanation: str = Field(min_length=1, max_length=4000)


class GradeResponse(BaseModel):
    covered: bool
    accuracy_score: float
    overall_feedback: str
    breakdown: list[FeynmanBreakdownPoint]
    missing_concepts: list[str]
    previous_mastery_score: float | None
    new_mastery_score: float | None
    consecutive_failures: int | None
    remediation: RemediationPlan | None


class AttemptOut(BaseModel):
    id: uuid.UUID
    topic_id: uuid.UUID
    explanation: str
    accuracy_score: float
    overall_feedback: str
    breakdown: list[FeynmanBreakdownPoint]
    missing_concepts: list[str]


def _to_out(attempt: FeynmanAttempt) -> AttemptOut:
    return AttemptOut(
        id=attempt.id,
        topic_id=attempt.topic_id,
        explanation=attempt.explanation,
        accuracy_score=attempt.accuracy_score,
        overall_feedback=attempt.overall_feedback,
        breakdown=[FeynmanBreakdownPoint.model_validate(point) for point in attempt.breakdown],
        missing_concepts=attempt.missing_concepts,
    )


@router.post("/grade", response_model=GradeResponse)
async def grade(
    payload: GradeRequest,
    db: DbSession,
    student: CurrentStudent,
    llm_client: LLMClientDep,
    vectorstore: VectorStoreDep,
) -> GradeResponse:
    """Grade a Feynman-mode explanation of `topic_id` and update its mastery.

    Rate-limited (`feynman_grade_rate_limit` per
    `feynman_grade_rate_limit_window_seconds`) — this calls the model.
    `covered=false` means the retrieval or model guardrail refused (see
    `agent-design.md` → "Feynman mode"); mastery fields are then `null`
    since nothing was graded.
    """
    result = await grade_explanation(
        db, student.id, payload.topic_id, payload.explanation, llm_client, vectorstore
    )
    await db.commit()
    return GradeResponse(
        covered=result.covered,
        accuracy_score=result.accuracy_score,
        overall_feedback=result.overall_feedback,
        breakdown=result.breakdown,
        missing_concepts=result.missing_concepts,
        previous_mastery_score=result.mastery.previous_score if result.mastery else None,
        new_mastery_score=result.mastery.new_score if result.mastery else None,
        consecutive_failures=result.mastery.consecutive_failures if result.mastery else None,
        remediation=result.remediation,
    )


@router.get("", response_model=list[AttemptOut])
async def list_attempts(topic_id: uuid.UUID, db: DbSession, student: CurrentStudent) -> list[AttemptOut]:
    """Every past Feynman-mode attempt for `topic_id`, newest first."""
    attempts = await feynman_domain.list_for_topic(db, student.id, topic_id)
    return [_to_out(attempt) for attempt in attempts]
