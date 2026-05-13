from __future__ import annotations

from dataclasses import dataclass

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.db.models import Ad, AdCampaign, Campaign


@dataclass(frozen=True)
class AdMatch:
    ad: Ad
    score: float  # cosine similarity in [-1, 1]; higher is better
    distance: float  # cosine distance in [0, 2]; lower is better


class AdsVectorRepository:
    def __init__(self, db: Session):
        self._db = db

    def search_ads_by_embedding(self, query_embedding: list[float], top_k: int) -> list[AdMatch]:
        if top_k <= 0:
            return []

        # Index-friendly: order by cosine distance ascending (pgvector <=> operator)
        distance_expr = sa.cast(Ad.embedding.op("<=>")(query_embedding), sa.Float)
        distance_labeled = distance_expr.label("distance")
        score_expr = (sa.literal(1.0) - distance_expr).label("score")

        stmt = (
            sa.select(Ad, score_expr, distance_labeled)
            .join(AdCampaign, Ad.id == AdCampaign.ad_id)
            .join(Campaign, AdCampaign.campaign_id == Campaign.id)
            .where(
                Ad.embedding.is_not(None),
                Campaign.is_running
            )
            .distinct()
            .order_by(distance_expr.asc())
            .limit(top_k)
        )

        rows = self._db.execute(stmt).all()
        matches: list[AdMatch] = []
        for ad, score, distance in rows:
            matches.append(AdMatch(ad=ad, score=float(score), distance=float(distance)))
        return matches
