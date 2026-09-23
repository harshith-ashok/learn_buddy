import uuid

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class FeynmanAttempt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One Feynman-mode explanation attempt: the student's own words, graded against the topic's material.

    `breakdown` is the graded claim-by-claim list (`agents.schemas.FeynmanBreakdownPoint`,
    as JSON); `missing_concepts` names material the explanation never
    touched. `accuracy_score` is also fed into `mastery_scores` via
    `agents.mastery.apply_mastery_observation` at grading time — this row
    is the durable record of *why* mastery moved, not a second source of
    truth for the score itself.
    """

    __tablename__ = "feynman_attempts"

    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    accuracy_score: Mapped[float] = mapped_column(nullable=False)
    overall_feedback: Mapped[str] = mapped_column(Text, nullable=False)
    breakdown: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    missing_concepts: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "accuracy_score >= 0 AND accuracy_score <= 1", name="ck_feynman_attempts_score_range"
        ),
    )
