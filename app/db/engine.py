from __future__ import annotations

from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.core.settings import get_settings


@lru_cache
def get_engine(database_url: str | None = None) -> Engine:
    settings = get_settings()
    url = database_url or settings.database_url

    # Note: do not connect here; SQLAlchemy will connect lazily.
    return create_engine(
        url,
        pool_pre_ping=True,
        future=True,
    )
