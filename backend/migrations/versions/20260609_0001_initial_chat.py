"""Create initial chat tables.

Revision ID: 20260609_0001
Revises:
Create Date: 2026-06-09
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260609_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_table(
        "companion_profiles",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("relationship_type", sa.String(length=100), nullable=False),
        sa.Column("speaking_style", sa.Text(), nullable=False),
        sa.Column("boundaries", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_companion_user_name"),
    )
    op.create_index(
        op.f("ix_companion_profiles_user_id"),
        "companion_profiles",
        ["user_id"],
    )
    op.create_table(
        "conversations",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("companion_id", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["companion_id"],
            ["companion_profiles.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_conversations_user_updated",
        "conversations",
        ["user_id", "updated_at"],
    )
    op.create_table(
        "agent_traces",
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_stage", sa.String(length=64), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("node_summary", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id"),
    )
    op.create_index(
        op.f("ix_agent_traces_conversation_id"),
        "agent_traces",
        ["conversation_id"],
    )
    op.create_table(
        "messages",
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("display_text", sa.Text(), nullable=False),
        sa.Column("speech_text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("persist_history", sa.Boolean(), nullable=False),
        sa.Column("allow_memory_extraction", sa.Boolean(), nullable=False),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id", name="uq_messages_request_id"),
    )
    op.create_index(
        "ix_messages_active_generation",
        "messages",
        ["conversation_id", "status"],
    )
    op.create_index(
        "ix_messages_conversation_created",
        "messages",
        ["conversation_id", "created_at", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_messages_conversation_created", table_name="messages")
    op.drop_index("ix_messages_active_generation", table_name="messages")
    op.drop_table("messages")
    op.drop_index(op.f("ix_agent_traces_conversation_id"), table_name="agent_traces")
    op.drop_table("agent_traces")
    op.drop_index("ix_conversations_user_updated", table_name="conversations")
    op.drop_table("conversations")
    op.drop_index(
        op.f("ix_companion_profiles_user_id"),
        table_name="companion_profiles",
    )
    op.drop_table("companion_profiles")
    op.drop_table("users")

