from __future__ import annotations

from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.core.settings import get_settings


@lru_cache
def get_engine(database_url: str | None = None) -> Engine:
    settings = get_settings()
    url = database_url or settings.database_url

    # Connection pooling optimized for serverless databases (Neon)
    # - pool_size: Maximum persistent connections (5 for serverless)
    # - max_overflow: Additional connections when pool exhausted (10)
    # - pool_pre_ping: Test connections before use (important for serverless)
    # - pool_recycle: Refresh connections hourly (prevents stale connections)
    # Total max connections per instance: pool_size + max_overflow = 15
    return create_engine(
        url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,  # Recycle connections after 1 hour
        future=True,
    )
