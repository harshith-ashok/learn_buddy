import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Document, MasteryScore, Topic


@dataclass
class TopicProgress:
    topic_id: uuid.UUID
    topic_name: str
    document_id: uuid.UUID
    mastery_score: float
    consecutive_failures: int


async def list_for_student(db: AsyncSession, student_id: uuid.UUID) -> list[TopicProgress]:
    """Every topic across `student_id`'s documents, with mastery defaulted to 0 where unscored."""
    rows = (
        await db.execute(
            select(Topic, MasteryScore)
            .join(Document, Topic.document_id == Document.id)
            .outerjoin(
                MasteryScore,
                (MasteryScore.topic_id == Topic.id) & (MasteryScore.student_id == student_id),
            )
            .where(Document.student_id == student_id)
            .order_by(Document.created_at, Topic.position)
        )
    ).all()

    return [
        TopicProgress(
            topic_id=topic.id,
            topic_name=topic.name,
            document_id=topic.document_id,
            mastery_score=mastery.score if mastery is not None else 0.0,
            consecutive_failures=mastery.consecutive_failures if mastery is not None else 0,
        )
        for topic, mastery in rows
    ]
