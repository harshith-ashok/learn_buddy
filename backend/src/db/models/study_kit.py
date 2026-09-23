import uuid
from enum import Enum as PyEnum

from sqlalchemy import JSON, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class StudyKitType(str, PyEnum):
    SUMMARY = "summary"
    FLASHCARDS = "flashcards"
    QUIZ = "quiz"
    PROBLEM_GUIDE = "problem_guide"


class StudyKit(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A generated study asset for one topic, with its grounding sources.

    `content` is the kit-type-specific payload (validated by a Pydantic
    schema at generation time, in `src.agents`); `source_chunk_ids` records
    the Chroma chunk ids every fact was grounded in, for citation.
    """

    __tablename__ = "study_kits"

    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kit_type: Mapped[StudyKitType] = mapped_column(Enum(StudyKitType, name="study_kit_type"), nullable=False)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    source_chunk_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
