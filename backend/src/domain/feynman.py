import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import FeynmanAttempt


async def list_for_topic(
    db: AsyncSession, student_id: uuid.UUID, topic_id: uuid.UUID
) -> list[FeynmanAttempt]:
    """Every Feynman-mode attempt for `topic_id`, scoped to `student_id`, newest first."""
    result = await db.scalars(
        select(FeynmanAttempt)
        .where(FeynmanAttempt.student_id == student_id, FeynmanAttempt.topic_id == topic_id)
        .order_by(FeynmanAttempt.created_at.desc())
    )
    return list(result)
