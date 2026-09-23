import uuid

from sqlalchemy import JSON, CheckConstraint, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class QuizAttempt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One submitted quiz attempt; `score_and_update_mastery` reads these to
    detect the 2-consecutive-failure / mastery-drop remediation triggers.
    """

    __tablename__ = "quiz_attempts"
    __table_args__ = (CheckConstraint("score >= 0 AND score <= 1", name="score_range"),)

    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    study_kit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("study_kits.id", ondelete="SET NULL"), nullable=True
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    answers: Mapped[dict] = mapped_column(JSON, nullable=False)
