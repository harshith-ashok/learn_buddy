import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.schemas import MasteryUpdateResult, RemediationPlan
from src.core.config import Settings, get_settings
from src.core.logging import get_logger
from src.db.models import MasteryScore, Topic, TopicPrerequisite
from src.domain import topics as topics_domain

logger = get_logger(__name__)


async def _weak_prerequisites(
    db: AsyncSession, student_id: uuid.UUID, topic_id: uuid.UUID, settings: Settings
) -> list[tuple[Topic, float]]:
    prereq_ids = (
        await db.scalars(
            select(TopicPrerequisite.prerequisite_topic_id).where(TopicPrerequisite.topic_id == topic_id)
        )
    ).all()
    if not prereq_ids:
        return []

    prereqs = (await db.scalars(select(Topic).where(Topic.id.in_(prereq_ids)))).all()
    mastery_rows = (
        await db.scalars(
            select(MasteryScore).where(
                MasteryScore.student_id == student_id, MasteryScore.topic_id.in_(prereq_ids)
            )
        )
    ).all()
    mastery_by_id = {row.topic_id: row.score for row in mastery_rows}

    return [
        (prereq, mastery_by_id.get(prereq.id, 0.0))
        for prereq in prereqs
        if mastery_by_id.get(prereq.id, 0.0) < settings.mastery_ready_threshold
    ]


async def build_remediation_plan(
    db: AsyncSession,
    student_id: uuid.UUID,
    topic_id: uuid.UUID,
    mastery_result: MasteryUpdateResult,
    settings: Settings | None = None,
) -> RemediationPlan:
    """Build a revised mini-plan after `mastery_result` tripped the remediation trigger.

    Fires on 2 consecutive failures or a >=20% mastery drop (checked by
    the caller via `mastery_result.remediation_triggered`, per
    `CLAUDE.md` → agent guardrails). Reviews the topic's own weakest
    prerequisites first — a repeated failure is often a gap one level
    down, not in the topic itself.
    """
    settings = settings or get_settings()
    topic = await topics_domain.get_for_student(db, student_id, topic_id)

    reasons = []
    if mastery_result.consecutive_failures >= settings.remediation_consecutive_failures:
        reasons.append(f"{mastery_result.consecutive_failures} quizzes in a row below passing")
    if mastery_result.mastery_drop >= settings.remediation_mastery_drop:
        reasons.append(f"a {mastery_result.mastery_drop:.0%} drop in mastery")
    reason = " and ".join(reasons)

    weak_prereqs = await _weak_prerequisites(db, student_id, topic_id, settings)

    actions = []
    if weak_prereqs:
        names = ", ".join(prereq.name for prereq, _ in weak_prereqs)
        actions.append(f"Revisit prerequisite topic(s) first: {names}.")
    actions.append(f"Regenerate a fresh study kit for {topic.name} and review it before retrying.")
    actions.append("Retake a short quiz on this topic once you've reviewed the material.")

    message = f"Remediation triggered for {topic.name}: {reason}."

    logger.info(
        "Built remediation plan",
        extra={"student_id": str(student_id), "topic_id": str(topic_id), "reason": reason},
    )
    return RemediationPlan(topic_id=topic_id, reason=reason, message=message, suggested_actions=actions)
