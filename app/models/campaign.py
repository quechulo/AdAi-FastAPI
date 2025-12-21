from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CampaignCreate(BaseModel):
    title: str
    company: str

    budget: Decimal = Field(default=Decimal("0.00"))
    spending: Decimal = Field(default=Decimal("0.00"))

    # 1 = Active, 0 = Paused
    is_enabled: int = 1

    start_date: datetime | None = None
    end_date: datetime | None = None


class CampaignUpdate(BaseModel):
    title: str | None = None
    company: str | None = None

    budget: Decimal | None = None
    spending: Decimal | None = None

    is_enabled: int | None = None

    start_date: datetime | None = None
    end_date: datetime | None = None


class CampaignRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    company: str

    budget: Decimal
    spending: Decimal

    is_enabled: int

    start_date: datetime
    end_date: datetime | None = None

    # Exposed from ORM @property Campaign.is_running
    is_running: bool
