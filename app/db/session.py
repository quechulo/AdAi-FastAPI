from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session, sessionmaker

from app.core.settings import get_settings
from app.db.engine import get_engine


def get_sessionmaker(database_url: str | None = None) -> sessionmaker[Session]:
    engine = get_engine(database_url)

    return sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def get_db_session() -> Generator[Session, None, None]:
    SessionLocal = get_sessionmaker()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session_readonly() -> Generator[Session, None, None]:
    settings = get_settings()
    SessionLocal = get_sessionmaker(settings.database_url_readonly)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
