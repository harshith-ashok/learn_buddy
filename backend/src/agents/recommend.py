import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.schemas import NoRecommendation, Recommendation
from src.core.config import Settings, get_settings
from src.core.logging import get_logger
from src.db.models import Document, MasteryScore, Topic, TopicPrerequisite

logger = get_logger(__name__)


def _exam_urgency(exam_date: datetime | None, now: datetime, window_days: int) -> float:
    """`0` for no exam or one far off, ramping to `1` as it arrives or passes.

    `exam_date` is stored naive (see `db.models.Document.exam_date`), so
    `now` must be naive too — both are treated as UTC.
    """
    if exam_date is None:
        return 0.0
    days_left = (exam_date - now).days
    if days_left <= 0:
        return 1.0
    if days_left >= window_days:
        return 0.0
    return (window_days - days_left) / window_days


async def recommend_next_topic(
    db: AsyncSession, student_id: uuid.UUID, settings: Settings | None = None
) -> Recommendation | NoRecommendation:
    """Pick the next topic to study: lowest mastery among prerequisite-ready topics,
    weighted by how close the owning document's exam date is.

    "Ready" means every prerequisite already clears `mastery_ready_threshold`;
    a topic already at or above `mastery_target_threshold` isn't a candidate.
    Returns `NoRecommendation` if the student has no ingested topics yet, or
    has mastered everything they're currently ready for.
    """
    settings = settings or get_settings()

    topics = list(
        (
            await db.scalars(
                select(Topic)
                .join(Document, Topic.document_id == Document.id)
                .where(Document.student_id == student_id)
            )
        ).all()
    )
    if not topics:
        return NoRecommendation(reason="No topics found yet — upload a document to get started.")

    topic_ids = [topic.id for topic in topics]
    document_ids = {topic.document_id for topic in topics}

    mastery_rows = (
        await db.scalars(
            select(MasteryScore).where(
                MasteryScore.student_id == student_id, MasteryScore.topic_id.in_(topic_ids)
            )
        )
    ).all()
    mastery_by_topic = {row.topic_id: row.score for row in mastery_rows}

    prereq_rows = (
        await db.scalars(select(TopicPrerequisite).where(TopicPrerequisite.topic_id.in_(topic_ids)))
    ).all()
    prereqs_by_topic: dict[uuid.UUID, list[uuid.UUID]] = {}
    for edge in prereq_rows:
        prereqs_by_topic.setdefault(edge.topic_id, []).append(edge.prerequisite_topic_id)

    documents = (await db.scalars(select(Document).where(Document.id.in_(document_ids)))).all()
    exam_date_by_document = {document.id: document.exam_date for document in documents}

    def mastery(topic_id: uuid.UUID) -> float:
        return mastery_by_topic.get(topic_id, 0.0)

    def is_ready(topic: Topic) -> bool:
        return all(
            mastery(prereq_id) >= settings.mastery_ready_threshold
            for prereq_id in prereqs_by_topic.get(topic.id, [])
        )

    candidates = [
        topic for topic in topics if mastery(topic.id) < settings.mastery_target_threshold and is_ready(topic)
    ]
    if not candidates:
        return NoRecommendation(
            reason="You've mastered everything you're currently ready for — nothing left to recommend."
        )

    now = datetime.utcnow()

    def priority(topic: Topic) -> tuple[float, int, str]:
        gap = settings.mastery_target_threshold - mastery(topic.id)
        exam_date = exam_date_by_document.get(topic.document_id)
        urgency = _exam_urgency(exam_date, now, settings.exam_urgency_window_days)
        return (gap * (1 + urgency), -topic.position, topic.name)

    chosen = max(candidates, key=priority)
    chosen_mastery = mastery(chosen.id)
    urgency = _exam_urgency(
        exam_date_by_document.get(chosen.document_id), now, settings.exam_urgency_window_days
    )

    justification = (
        f"{chosen.name} has the lowest mastery ({chosen_mastery:.0%}) among topics you're ready for."
    )
    if urgency > 0:
        justification += " Your exam is coming up, so this is prioritized."

    logger.info(
        "Recommended next topic",
        extra={"student_id": str(student_id), "topic_id": str(chosen.id), "mastery": chosen_mastery},
    )
    return Recommendation(
        topic_id=chosen.id, topic_name=chosen.name, mastery_score=chosen_mastery, justification=justification
    )
