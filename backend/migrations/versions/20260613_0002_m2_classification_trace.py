"""Add classification trace fields to agent_traces.

Revision ID: 20260613_0002
Revises: 20260609_0001
Create Date: 2026-06-13
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260613_0002"
down_revision: str | Sequence[str] | None = "20260609_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "agent_traces",
        sa.Column("emotion_label", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "agent_traces",
        sa.Column("emotion_confidence", sa.Float(), nullable=True),
    )
    op.add_column(
        "agent_traces",
        sa.Column("intent_label", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "agent_traces",
        sa.Column("intent_confidence", sa.Float(), nullable=True),
    )
    op.add_column(
        "agent_traces",
        sa.Column("risk_level", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "agent_traces",
        sa.Column("risk_confidence", sa.Float(), nullable=True),
    )
    op.add_column(
        "agent_traces",
        sa.Column("classification_status", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "agent_traces",
        sa.Column("classification_error_code", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "agent_traces",
        sa.Column("route", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "agent_traces",
        sa.Column("trace_schema_version", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("agent_traces", "trace_schema_version")
    op.drop_column("agent_traces", "route")
    op.drop_column("agent_traces", "classification_error_code")
    op.drop_column("agent_traces", "classification_status")
    op.drop_column("agent_traces", "risk_confidence")
    op.drop_column("agent_traces", "risk_level")
    op.drop_column("agent_traces", "intent_confidence")
    op.drop_column("agent_traces", "intent_label")
    op.drop_column("agent_traces", "emotion_confidence")
    op.drop_column("agent_traces", "emotion_label")
