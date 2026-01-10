from __future__ import annotations

from dataclasses import dataclass

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.db.models import Ad


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
        # NOTE: `.op()` inherits the left operand's SQLAlchemy type (Vector), but
        # the `<=>` operator returns a scalar float. Cast explicitly so SQLAlchemy
        # doesn't try to decode the float using pgvector's Vector processor.
        distance_expr = sa.cast(Ad.embedding.op("<=>")(query_embedding), sa.Float)
        distance_labeled = distance_expr.label("distance")
        score_expr = (sa.literal(1.0) - distance_expr).label("score")

        stmt = (
            sa.select(Ad, score_expr, distance_labeled)
            .where(Ad.embedding.is_not(None))
            .order_by(distance_expr.asc())
            .limit(top_k)
        )

        rows = self._db.execute(stmt).all()
        matches: list[AdMatch] = []
        for ad, score, distance in rows:
            try:
                score_f = float(score)
            except Exception:
                score_f = float("nan")
            try:
                distance_f = float(distance)
            except Exception:
                distance_f = float("nan")
            matches.append(AdMatch(ad=ad, score=score_f, distance=distance_f))
        return matches
