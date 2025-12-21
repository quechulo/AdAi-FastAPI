from __future__ import annotations

import asyncio
import logging

from google import genai
from google.genai import types

from app.core.settings import Settings, get_settings
from app.models.chat import ChatMessage

logger = logging.getLogger(__name__)


class GeminiService:
    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

        if not self._settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")

        # Recommended google-genai usage: instantiate a client.
        # Ref: https://pypi.org/project/google-genai/
        self._client = genai.Client(api_key=self._settings.gemini_api_key)

    async def generate_chat_response(self, message: str, history: list[ChatMessage]):
        contents: list[types.Content] = []

        for msg in history:
            role = msg.role
            if role not in {"user", "model"}:
                # Keep behavior predictable even if callers pass "assistant" etc.
                role = "model" if role == "assistant" else "user"
            contents.append(
                types.Content(
                    role=role, parts=[types.Part.from_text(text=msg.content)]
                )
            )

        contents.append(
            types.Content(role="user", parts=[types.Part.from_text(text=message)])
        )

        def _send() -> str:
            response = self._client.models.generate_content(
                model=self._settings.gemini_model,
                contents=contents,
            )

            # google-genai responses typically expose aggregated text via `.text`.
            text = getattr(response, "text", None)
            if isinstance(text, str) and text.strip():
                return text
            return str(response)

        try:
            return await asyncio.to_thread(_send)
        except Exception:
            logger.exception("Gemini request failed")
            raise