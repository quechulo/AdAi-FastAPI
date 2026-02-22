from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    UniqueConstraint,
    and_,
    func,
    or_,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pgvector.sqlalchemy import Vector

from app.db.base import Base


class Ad(Base):
    __tablename__ = "ads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    keywords: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    url: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str | None] = mapped_column(Text)

    cpc: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        server_default="0.00"
        )
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    campaign_links: Mapped[list["AdCampaign"]] = relationship(
        "AdCampaign",
        back_populates="ad",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class AdCampaign(Base):
    __tablename__ = "ad_campaigns"
    __table_args__ = (
        UniqueConstraint("ad_id", "campaign_id", name="uq_ad_campaign"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    ad_id: Mapped[int] = mapped_column(
        ForeignKey("ads.id", ondelete="CASCADE"), nullable=False
    )
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False
    )

    click_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0"
        )

    ad: Mapped[Ad] = relationship("Ad", back_populates="campaign_links")
    campaign: Mapped["Campaign"] = relationship(
        "Campaign",
        back_populates="ad_links"
        )


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    company: Mapped[str] = mapped_column(Text, nullable=False)

    budget: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False, server_default="0.00"
    )
    spending: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False, server_default="0.00"
    )

    # 1 = Active, 0 = Paused
    is_enabled: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default="1"
    )

    start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    ad_links: Mapped[list[AdCampaign]] = relationship(
        "AdCampaign",
        back_populates="campaign",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @hybrid_property
    def is_running(self) -> bool:
        """Check if campaign is running (for Python instance access)."""
        now = datetime.now(timezone.utc)

        # 1) Manual switch
        if self.is_enabled == 0:
            return False

        # 2) Dates
        start = self.start_date
        end = self.end_date

        # Defensive: normalize naive datetimes to UTC
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end is not None and end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)

        if end is not None and now > end:
            return False
        if now < start:
            return False

        # 3) Budget
        # SQLAlchemy Numeric typically yields Decimal; keep comparisons stable.
        budget = self.budget if isinstance(self.budget, Decimal) \
            else Decimal(str(self.budget))
        spending = (
            self.spending
            if isinstance(self.spending, Decimal)
            else Decimal(str(self.spending))
        )
        if spending >= budget:
            return False

        return True

    @is_running.expression
    def is_running(cls):
        """SQL expression for filtering running campaigns in database queries."""
        now_func = func.now()
        return and_(
            cls.is_enabled == 1,
            cls.start_date <= now_func,
            or_(cls.end_date.is_(None), cls.end_date > now_func),
            cls.spending < cls.budget
        )


class ChatSession(Base):
    """Store immutable snapshots of complete chat conversations."""

    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    mode: Mapped[str] = mapped_column(Text, nullable=False)

    # JSONB array of message objects with structure:
    # [{role: str, parts: list[str], generation_time: float,
    # used_tokens: int}, ...]
    history: Mapped[dict] = mapped_column(JSONB, nullable=False)

    version: Mapped[float | None] = mapped_column(Float)

    helpful: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
