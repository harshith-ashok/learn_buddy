import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.errors import NotFoundError
from src.db.models import Document, MasteryScore, Subtopic, Topic, TopicPrerequisite
from src.domain import documents as documents_domain


async def get_for_student(db: AsyncSession, student_id: uuid.UUID, topic_id: uuid.UUID) -> Topic:
    """Fetch `topic_id`, scoped to documents owned by `student_id`."""
    topic = await db.scalar(
        select(Topic)
        .join(Document, Topic.document_id == Document.id)
        .where(Topic.id == topic_id, Document.student_id == student_id)
    )
    if topic is None:
        raise NotFoundError("Topic not found")
    return topic


async def list_siblings(db: AsyncSession, document_id: uuid.UUID, exclude_topic_id: uuid.UUID) -> list[Topic]:
    """Every other topic in `document_id`, for "related topic" citations (e.g. topic chat)."""
    result = await db.scalars(
        select(Topic)
        .where(Topic.document_id == document_id, Topic.id != exclude_topic_id)
        .order_by(Topic.position)
    )
    return list(result)


async def get_names(db: AsyncSession, topic_ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    """Batch id->name lookup, for rendering citations without an N+1 per message."""
    if not topic_ids:
        return {}
    rows = (await db.execute(select(Topic.id, Topic.name).where(Topic.id.in_(topic_ids)))).all()
    return {row.id: row.name for row in rows}


@dataclass
class TopicGraphNode:
    topic: Topic
    mastery_score: float
    subtopics: list[Subtopic] = field(default_factory=list)
    prerequisite_ids: list[uuid.UUID] = field(default_factory=list)


async def get_course_graph(
    db: AsyncSession, student_id: uuid.UUID, document_id: uuid.UUID
) -> list[TopicGraphNode]:
    """Assemble the full topic graph for one document ("course"), scoped to `student_id`.

    Raises `NotFoundError` if the document isn't owned by `student_id` (via
    `documents.get_for_student`), before any topic is fetched.
    """
    await documents_domain.get_for_student(db, student_id, document_id)

    topics = list(
        (
            await db.scalars(select(Topic).where(Topic.document_id == document_id).order_by(Topic.position))
        ).all()
    )
    if not topics:
        return []

    topic_ids = [topic.id for topic in topics]

    subtopics = (
        await db.scalars(select(Subtopic).where(Subtopic.topic_id.in_(topic_ids)).order_by(Subtopic.position))
    ).all()
    subtopics_by_topic: dict[uuid.UUID, list[Subtopic]] = {}
    for subtopic in subtopics:
        subtopics_by_topic.setdefault(subtopic.topic_id, []).append(subtopic)

    prereq_edges = (
        await db.scalars(select(TopicPrerequisite).where(TopicPrerequisite.topic_id.in_(topic_ids)))
    ).all()
    prereqs_by_topic: dict[uuid.UUID, list[uuid.UUID]] = {}
    for edge in prereq_edges:
        prereqs_by_topic.setdefault(edge.topic_id, []).append(edge.prerequisite_topic_id)

    mastery_rows = (
        await db.scalars(
            select(MasteryScore).where(
                MasteryScore.student_id == student_id, MasteryScore.topic_id.in_(topic_ids)
            )
        )
    ).all()
    mastery_by_topic = {row.topic_id: row.score for row in mastery_rows}

    return [
        TopicGraphNode(
            topic=topic,
            mastery_score=mastery_by_topic.get(topic.id, 0.0),
            subtopics=subtopics_by_topic.get(topic.id, []),
            prerequisite_ids=prereqs_by_topic.get(topic.id, []),
        )
        for topic in topics
    ]
