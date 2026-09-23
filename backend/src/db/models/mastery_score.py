import uuid

from sqlalchemy import CheckConstraint, Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class MasteryScore(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A student's current mastery of one topic, in `[0, 1]`.

    One row per (student, topic); `agents.score_and_update_mastery` updates
    it in place rather than appending a new row per quiz.
    """

    __tablename__ = "mastery_scores"
    __table_args__ = (
        UniqueConstraint("student_id", "topic_id", name="uq_mastery_scores_student_topic"),
        CheckConstraint("score >= 0 AND score <= 1", name="score_range"),
    )

    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
