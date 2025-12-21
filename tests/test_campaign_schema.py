from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from app.db.models import Campaign
from app.models.campaign import CampaignRead


def test_campaign_read_exposes_is_running_property():
    campaign = Campaign(
        id=1,
        title="Test",
        company="ACME",
        budget=Decimal("10.00"),
        spending=Decimal("1.00"),
        is_enabled=1,
        start_date=datetime.now(timezone.utc),
        end_date=None,
    )

    payload = CampaignRead.model_validate(campaign).model_dump()

    assert payload["is_running"] is True
