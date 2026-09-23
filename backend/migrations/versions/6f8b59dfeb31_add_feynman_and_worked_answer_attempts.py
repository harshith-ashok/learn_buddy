"""add feynman and worked answer attempts

Revision ID: 6f8b59dfeb31
Revises: 100780c51275
Create Date: 2026-09-23 16:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6f8b59dfeb31"
down_revision: str | None = "100780c51275"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "feynman_attempts",
        sa.Column("student_id", sa.UUID(), nullable=False),
        sa.Column("topic_id", sa.UUID(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("accuracy_score", sa.Float(), nullable=False),
        sa.Column("overall_feedback", sa.Text(), nullable=False),
        sa.Column("breakdown", sa.JSON(), nullable=False),
        sa.Column("missing_concepts", sa.JSON(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "accuracy_score >= 0 AND accuracy_score <= 1", name=op.f("ck_feynman_attempts_score_range")
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
            name=op.f("fk_feynman_attempts_student_id_students"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"], ["topics.id"], name=op.f("fk_feynman_attempts_topic_id_topics"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_feynman_attempts")),
    )
    op.create_index(op.f("ix_feynman_attempts_student_id"), "feynman_attempts", ["student_id"], unique=False)
    op.create_index(op.f("ix_feynman_attempts_topic_id"), "feynman_attempts", ["topic_id"], unique=False)

    op.create_table(
        "worked_answer_attempts",
        sa.Column("student_id", sa.UUID(), nullable=False),
        sa.Column("topic_id", sa.UUID(), nullable=False),
        sa.Column("study_kit_id", sa.UUID(), nullable=False),
        sa.Column("problem_index", sa.Integer(), nullable=False),
        sa.Column("work", sa.Text(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("accuracy_score", sa.Float(), nullable=False),
        sa.Column("overall_feedback", sa.Text(), nullable=False),
        sa.Column("step_feedback", sa.JSON(), nullable=False),
        sa.Column("first_error_step", sa.Integer(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "accuracy_score >= 0 AND accuracy_score <= 1",
            name=op.f("ck_worked_answer_attempts_score_range"),
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
            name=op.f("fk_worked_answer_attempts_student_id_students"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["study_kit_id"],
            ["study_kits.id"],
            name=op.f("fk_worked_answer_attempts_study_kit_id_study_kits"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["topics.id"],
            name=op.f("fk_worked_answer_attempts_topic_id_topics"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_worked_answer_attempts")),
    )
    op.create_index(
        op.f("ix_worked_answer_attempts_student_id"), "worked_answer_attempts", ["student_id"], unique=False
    )
    op.create_index(
        op.f("ix_worked_answer_attempts_study_kit_id"),
        "worked_answer_attempts",
        ["study_kit_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_worked_answer_attempts_topic_id"), "worked_answer_attempts", ["topic_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_worked_answer_attempts_topic_id"), table_name="worked_answer_attempts")
    op.drop_index(op.f("ix_worked_answer_attempts_study_kit_id"), table_name="worked_answer_attempts")
    op.drop_index(op.f("ix_worked_answer_attempts_student_id"), table_name="worked_answer_attempts")
    op.drop_table("worked_answer_attempts")

    op.drop_index(op.f("ix_feynman_attempts_topic_id"), table_name="feynman_attempts")
    op.drop_index(op.f("ix_feynman_attempts_student_id"), table_name="feynman_attempts")
    op.drop_table("feynman_attempts")
