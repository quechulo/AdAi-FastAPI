from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.db.session import get_db_session
from app.services.gemini_service import GeminiService
from app.services.rag_service import RagService
from app.services.adAgent_service import AdAgentService


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

def get_agentic_service(
    #gemini_service: GeminiService = Depends(get_gemini_service),
) -> AdAgentService:
    try:
        return AdAgentService(settings=get_settings())
    except RuntimeError as e:
        # Misconfiguration (missing Gemini key) should be explicit for API clients.
        raise HTTPException(status_code=500, detail=str(e))