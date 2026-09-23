import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.schemas import MasteryUpdateResult, QuizSubmission
from src.core.config import Settings, get_settings
from src.core.logging import get_logger
from src.db.models import MasteryScore, QuizAttempt
from src.domain import topics as topics_domain

logger = get_logger(__name__)


async def _get_or_create_mastery_score(
    db: AsyncSession, student_id: uuid.UUID, topic_id: uuid.UUID
) -> MasteryScore:
    mastery = await db.scalar(
        select(MasteryScore).where(MasteryScore.student_id == student_id, MasteryScore.topic_id == topic_id)
    )
    if mastery is None:
        mastery = MasteryScore(student_id=student_id, topic_id=topic_id, score=0.0, consecutive_failures=0)
        db.add(mastery)
        await db.flush()
    return mastery


async def apply_mastery_observation(
    db: AsyncSession,
    student_id: uuid.UUID,
    topic_id: uuid.UUID,
    observed_score: float,
    settings: Settings | None = None,
) -> MasteryUpdateResult:
    """Move `topic_id`'s mastery toward one observed assessment score, whatever kind.

    The shared core of every assessment type this app has (quiz, Feynman
    explanation grading, worked-answer grading): an exponential moving
    average (`mastery_ema_alpha`) rather than jumping straight to the
    observed score, so one lucky or unlucky attempt doesn't overwrite the
    running estimate. `consecutive_failures` resets on a pass and
    increments on a fail (`quiz_pass_threshold` — the same "did this count
    as passing" bar applies regardless of assessment type), both feeding
    `trigger_remediation`'s condition.

    Does **not** persist an attempt row itself — callers (`score_and_update_mastery`,
    `agents.feynman`, `agents.worked_answer`) each own their own attempt
    table, since the record of *what was submitted* differs per assessment
    type; this only owns the mastery math they all share.
    """
    settings = settings or get_settings()
    await topics_domain.get_for_student(db, student_id, topic_id)

    mastery = await _get_or_create_mastery_score(db, student_id, topic_id)
    previous_score = mastery.score
    is_pass = observed_score >= settings.quiz_pass_threshold

    new_score = (
        previous_score * (1 - settings.mastery_ema_alpha) + observed_score * settings.mastery_ema_alpha
    )
    mastery_drop = max(0.0, previous_score - new_score)
    consecutive_failures = 0 if is_pass else mastery.consecutive_failures + 1

    mastery.score = new_score
    mastery.consecutive_failures = consecutive_failures
    await db.flush()

    remediation_triggered = (
        consecutive_failures >= settings.remediation_consecutive_failures
        or mastery_drop >= settings.remediation_mastery_drop
    )

    logger.info(
        "Updated mastery from an assessment",
        extra={
            "student_id": str(student_id),
            "topic_id": str(topic_id),
            "previous_score": previous_score,
            "new_score": new_score,
            "is_pass": is_pass,
            "consecutive_failures": consecutive_failures,
            "remediation_triggered": remediation_triggered,
        },
    )
    return MasteryUpdateResult(
        topic_id=topic_id,
        previous_score=previous_score,
        new_score=new_score,
        is_pass=is_pass,
        consecutive_failures=consecutive_failures,
        mastery_drop=mastery_drop,
        remediation_triggered=remediation_triggered,
    )


async def score_and_update_mastery(
    db: AsyncSession,
    student_id: uuid.UUID,
    topic_id: uuid.UUID,
    submission: QuizSubmission,
    settings: Settings | None = None,
) -> MasteryUpdateResult:
    """Record a quiz `submission` and update the student's mastery of `topic_id`.

    See `apply_mastery_observation` for the mastery math itself; this adds
    the quiz-specific `QuizAttempt` persistence around it.
    """
    result = await apply_mastery_observation(db, student_id, topic_id, submission.score, settings)
    db.add(
        QuizAttempt(
            student_id=student_id,
            topic_id=topic_id,
            study_kit_id=submission.study_kit_id,
            score=submission.score,
            answers=[answer.model_dump() for answer in submission.answers],
        )
    )
    await db.flush()
    return result
