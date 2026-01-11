from __future__ import annotations

from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from google.genai import types
from sqlalchemy.orm import Session

from app.db.models import Ad
from app.services.tooling import ToolSpec


def _ad_to_payload(ad: Ad) -> dict[str, Any]:
    cpc = ad.cpc
    if isinstance(cpc, Decimal):
        cpc_out: str | float = str(cpc)
    else:
        cpc_out = float(cpc) if cpc is not None else 0.0

    return {
        "id": ad.id,
        "title": ad.title,
        "description": ad.description,
        "keywords": ad.keywords or [],
        "url": ad.url,
        "image_url": ad.image_url,
        "cpc": cpc_out,
    }


def make_get_ads_by_keyword_tool(*, db: Session) -> ToolSpec:
    def handler(args: dict[str, Any]) -> dict[str, Any]:
        keyword = str(args.get("keyword", "")).strip()
        if not keyword:
            raise ValueError("keyword is required")

        try:
            limit = int(args.get("limit", 8))
        except Exception:
            limit = 8
        limit = max(1, min(limit, 20))

        like = f"%{keyword}%"

        stmt = (
            sa.select(Ad)
            .where(
                sa.or_(
                    Ad.title.ilike(like),
                    Ad.description.ilike(like),
                    # Postgres ARRAY contains check
                    Ad.keywords.any(keyword),
                )
            )
            .order_by(Ad.id.asc())
            .limit(limit)
        )

        ads = db.execute(stmt).scalars().all()
        return {
            "keyword": keyword,
            "count": len(ads),
            "ads": [_ad_to_payload(a) for a in ads],
        }

    parameters = types.Schema(
        type=types.Type.OBJECT,
        required=["keyword"],
        properties={
            "keyword": types.Schema(
                type=types.Type.STRING,
                description="Keyword or phrase to search for in ads (title/description/keywords).",
            ),
            "limit": types.Schema(
                type=types.Type.INTEGER,
                description="Max number of ads to return (1-20).",
            ),
        },
    )

    return ToolSpec(
        name="get_ads_by_keyword",
        description="Search ads by a keyword in title/description/keywords. Returns a small bounded list.",
        parameters=parameters,
        handler=handler,
    )
