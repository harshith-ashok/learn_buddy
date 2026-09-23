import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import ChatMessage, ChatMessageRole


async def list_for_topic(db: AsyncSession, student_id: uuid.UUID, topic_id: uuid.UUID) -> list[ChatMessage]:
    """The full chat transcript for `topic_id`, scoped to `student_id`, oldest first."""
    result = await db.scalars(
        select(ChatMessage)
        .where(ChatMessage.student_id == student_id, ChatMessage.topic_id == topic_id)
        .order_by(ChatMessage.created_at.asc())
    )
    return list(result)


async def add_message(
    db: AsyncSession,
    student_id: uuid.UUID,
    topic_id: uuid.UUID,
    role: ChatMessageRole,
    content: str,
    source_chunk_ids: list[str] | None = None,
    related_topic_ids: list[uuid.UUID] | None = None,
) -> ChatMessage:
    message = ChatMessage(
        student_id=student_id,
        topic_id=topic_id,
        role=role,
        content=content,
        source_chunk_ids=source_chunk_ids or [],
        related_topic_ids=[str(related_id) for related_id in (related_topic_ids or [])],
    )
    db.add(message)
    await db.flush()
    return message
