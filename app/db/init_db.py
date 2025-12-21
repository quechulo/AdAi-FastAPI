from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db.base import Base


def init_db(engine: Engine) -> None:
    """Initialize DB objects.

    - Ensures pgvector extension exists
    - Creates ORM tables (dev-friendly; prefer Alembic in production)
    """

    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    Base.metadata.create_all(bind=engine)
