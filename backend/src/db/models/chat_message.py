import uuid
from enum import Enum as PyEnum

from sqlalchemy import JSON, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ChatMessageRole(str, PyEnum):
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One turn in a topic-scoped Q&A chat, user or assistant.

    Every assistant turn records its own grounding — `source_chunk_ids`
    (Chroma chunk ids, as in `StudyKit`) and `related_topic_ids` (sibling
    topics in the same document whose material the answer also touched) —
    so a refusal is indistinguishable in the schema from an answer with
    empty citations, and the history renders as a plain transcript either
    way (see `src.agents.chat.answer_topic_question`).
    """

    __tablename__ = "chat_messages"

    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[ChatMessageRole] = mapped_column(
        Enum(ChatMessageRole, name="chat_message_role"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_chunk_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    related_topic_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
