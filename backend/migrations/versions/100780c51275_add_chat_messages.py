"""add chat_messages

Revision ID: 100780c51275
Revises: cf1214a1efd2
Create Date: 2026-09-23 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "100780c51275"
down_revision: str | None = "cf1214a1efd2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chat_messages",
        sa.Column("student_id", sa.UUID(), nullable=False),
        sa.Column("topic_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.Enum("USER", "ASSISTANT", name="chat_message_role"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_chunk_ids", sa.JSON(), nullable=False),
        sa.Column("related_topic_ids", sa.JSON(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
            name=op.f("fk_chat_messages_student_id_students"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"], ["topics.id"], name=op.f("fk_chat_messages_topic_id_topics"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chat_messages")),
    )
    op.create_index(op.f("ix_chat_messages_student_id"), "chat_messages", ["student_id"], unique=False)
    op.create_index(op.f("ix_chat_messages_topic_id"), "chat_messages", ["topic_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_chat_messages_topic_id"), table_name="chat_messages")
    op.drop_index(op.f("ix_chat_messages_student_id"), table_name="chat_messages")
    op.drop_table("chat_messages")
    sa.Enum(name="chat_message_role").drop(op.get_bind(), checkfirst=True)
