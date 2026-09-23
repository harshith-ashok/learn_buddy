import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.errors import NotFoundError
from src.db.models import StudyKit


async def get_for_student(db: AsyncSession, student_id: uuid.UUID, study_kit_id: uuid.UUID) -> StudyKit:
    """Fetch `study_kit_id`, scoped to `student_id`."""
    study_kit = await db.scalar(
        select(StudyKit).where(StudyKit.id == study_kit_id, StudyKit.student_id == student_id)
    )
    if study_kit is None:
        raise NotFoundError("Study kit not found")
    return study_kit


async def list_for_topic(db: AsyncSession, student_id: uuid.UUID, topic_id: uuid.UUID) -> list[StudyKit]:
    """Every study kit generated for `topic_id`, scoped to `student_id`, newest first."""
    result = await db.scalars(
        select(StudyKit)
        .where(StudyKit.student_id == student_id, StudyKit.topic_id == topic_id)
        .order_by(StudyKit.created_at.desc())
    )
    return list(result)
