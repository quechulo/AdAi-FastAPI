"""add campaign filtering indexes

Revision ID: 20260221_0003
Revises: 20260204_0002
Create Date: 2026-02-21

"""

from __future__ import annotations

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260221_0003"
down_revision = "20260204_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Composite index for campaign filtering in ad retrieval queries
    # Supports WHERE clauses checking is_running conditions:
    # - is_enabled = 1
    # - start_date <= NOW()
    # - end_date IS NULL OR end_date > NOW()
    # - spending < budget
    op.create_index(
        "ix_campaigns_running_check",
        "campaigns",
        ["is_enabled", "start_date", "end_date", "spending", "budget"],
        unique=False,
    )

    # Foreign key index for ad_campaigns.campaign_id to optimize joins
    # PostgreSQL does not automatically index foreign keys
    op.create_index(
        "ix_ad_campaigns_campaign_id",
        "ad_campaigns",
        ["campaign_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ad_campaigns_campaign_id", table_name="ad_campaigns")
    op.drop_index("ix_campaigns_running_check", table_name="campaigns")
