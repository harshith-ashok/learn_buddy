import uuid

from sqlalchemy import JSON, Boolean, CheckConstraint, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class WorkedAnswerAttempt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One attempt at working out a specific problem, graded step by step.

    `study_kit_id` + `problem_index` locate the reference `Problem` inside
    that `problem_guide` study kit's `content.problems` list — there's no
    separate "problems" table, the study kit's own stored content is the
    reference. `step_feedback` is the graded per-step list
    (`agents.schemas.WorkedStepFeedback`, as JSON); `first_error_step`
    lets the frontend jump straight to where reasoning first broke down
    rather than just showing right/wrong on the final answer.
    """

    __tablename__ = "worked_answer_attempts"

    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    study_kit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("study_kits.id", ondelete="CASCADE"), nullable=False, index=True
    )
    problem_index: Mapped[int] = mapped_column(Integer, nullable=False)
    work: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    accuracy_score: Mapped[float] = mapped_column(nullable=False)
    overall_feedback: Mapped[str] = mapped_column(Text, nullable=False)
    step_feedback: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    first_error_step: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "accuracy_score >= 0 AND accuracy_score <= 1", name="ck_worked_answer_attempts_score_range"
        ),
    )
