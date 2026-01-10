from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.db.session import get_db_session
from app.services.gemini_service import GeminiService
from app.services.rag_service import RagService


@lru_cache
def get_gemini_service() -> GeminiService:
    return GeminiService(settings=get_settings())


def get_db() -> Generator[Session, None, None]:
    yield from get_db_session()


def get_rag_service(
    db: Session = Depends(get_db),
    gemini_service: GeminiService = Depends(get_gemini_service),
) -> RagService:
    return RagService(db=db, gemini_service=gemini_service, settings=get_settings())
