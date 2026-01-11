from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.db.session import get_db_session, get_db_session_readonly
from app.services.gemini_service import GeminiService
from app.services.rag_service import RagService
from app.services.tool_runner import ToolRunner
from app.services.tooling import ToolRegistry
from app.services.tools_ads import make_get_ads_by_keyword_tool


@lru_cache
def get_gemini_service() -> GeminiService:
    return GeminiService(settings=get_settings())


def get_db() -> Generator[Session, None, None]:
    yield from get_db_session()


def get_db_readonly() -> Generator[Session, None, None]:
    yield from get_db_session_readonly()


def get_tool_registry(db: Session = Depends(get_db_readonly)) -> ToolRegistry:
    tools = [
        make_get_ads_by_keyword_tool(db=db),
    ]
    return ToolRegistry(tools)


def get_tool_runner(
    db: Session = Depends(get_db_readonly),
    registry: ToolRegistry = Depends(get_tool_registry),
) -> ToolRunner:
    return ToolRunner(db=db, registry=registry)


def get_rag_service(
    db: Session = Depends(get_db_readonly),
    gemini_service: GeminiService = Depends(get_gemini_service),
    tools: ToolRunner = Depends(get_tool_runner),
) -> RagService:
    return RagService(
        db=db,
        gemini_service=gemini_service,
        tools=tools,
        settings=get_settings(),
    )
