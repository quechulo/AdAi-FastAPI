"""add chat_sessions table

Revision ID: 20260204_0002
Revises: 20251220_0001
Create Date: 2026-02-04

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260204_0002"
down_revision = "20251220_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("mode", sa.Text(), nullable=False),
        sa.Column(
            "history",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("version", sa.Float(), nullable=True),
        sa.Column(
            "helpful",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )

    # Create indexes for efficient querying
    op.create_index("ix_chat_sessions_created_at", "chat_sessions", ["created_at"])
    op.create_index("ix_chat_sessions_mode", "chat_sessions", ["mode"])
    op.create_index("ix_chat_sessions_version", "chat_sessions", ["version"])
    
    # GIN index for JSONB queries (optional, for future text search in history)
    op.execute(
        "CREATE INDEX ix_chat_sessions_history_gin ON chat_sessions USING GIN (history)"
    )


def downgrade() -> None:
    op.drop_index("ix_chat_sessions_history_gin", table_name="chat_sessions")
    op.drop_index("ix_chat_sessions_version", table_name="chat_sessions")
    op.drop_index("ix_chat_sessions_mode", table_name="chat_sessions")
    op.drop_index("ix_chat_sessions_created_at", table_name="chat_sessions")
    op.drop_table("chat_sessions")
