from __future__ import annotations

from functools import lru_cache

from app.core.settings import get_settings
from app.services.gemini_service import GeminiService


@lru_cache
def get_gemini_service() -> GeminiService:
    return GeminiService(settings=get_settings())
