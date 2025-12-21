"""init campaigns/ads schema

Revision ID: 20251220_0001
Revises: 
Create Date: 2025-12-20

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision = "20251220_0001"
down_revision = None
branch_labels = None
depends_on = None


def _require_pgvector_extension() -> None:
    """Fail fast with a clear message if pgvector isn't enabled.

    Your application DB user is not allowed to CREATE EXTENSION, so pgvector must
    be enabled by a privileged user (or via managed DB provisioning) before
    running migrations.
    """

    conn = op.get_bind()
    exists = conn.execute(
        sa.text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
    ).scalar()

    if not exists:
        raise RuntimeError(
            "pgvector extension is not enabled. "
            "Enable it as a privileged user (CREATE EXTENSION vector) before running Alembic."  # noqa: E501
        )


def upgrade() -> None:
    _require_pgvector_extension()

    op.create_table(
        "campaigns",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("company", sa.Text(), nullable=False),
        sa.Column("budget", sa.Numeric(10, 2), server_default=sa.text("0.00"), nullable=False),
        sa.Column(
            "spending",
            sa.Numeric(10, 2),
            server_default=sa.text("0.00"),
            nullable=False,
        ),
        sa.Column(
            "is_enabled",
            sa.SmallInteger(),
            server_default=sa.text("1"),
            nullable=True,
        ),
        sa.Column(
            "start_date",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "ads",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("keywords", sa.ARRAY(sa.Text()), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("cpc", sa.Numeric(10, 2), server_default=sa.text("0.00"), nullable=False),
        sa.Column("embedding", Vector(768), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),
    )

    op.create_table(
        "ad_campaigns",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column(
            "ad_id",
            sa.Integer(),
            sa.ForeignKey("ads.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "campaign_id",
            sa.Integer(),
            sa.ForeignKey("campaigns.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "click_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=True,
        ),
        sa.UniqueConstraint("ad_id", "campaign_id", name="uq_ad_campaign"),
    )

    op.create_index(
        "ix_ads_embedding_hnsw",
        "ads",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_ads_embedding_hnsw", table_name="ads")
    op.drop_table("ad_campaigns")
    op.drop_table("ads")
    op.drop_table("campaigns")
