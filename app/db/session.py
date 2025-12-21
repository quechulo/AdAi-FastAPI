from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session, sessionmaker

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
