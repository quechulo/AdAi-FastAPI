from __future__ import annotations

import asyncio
import logging
import math
import time

from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

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

    @staticmethod
    def _extract_total_tokens(usage: object | None) -> int:
        if usage is None:
            return 0
        return (
            getattr(usage, "total_token_count", None)
            or getattr(usage, "total_tokens", None)
            or getattr(usage, "prompt_token_count", None)
            or getattr(usage, "input_token_count", 0)
            or 0
        )

    async def generate_chat_response(
            self,
            message: str,
            history: list[ChatMessage]
            ):
        contents: list[types.Content] = []

        for msg in history:
            role = msg.role
            if role not in {"user", "model"}:
                # Keep behavior predictable even if callers pass "assistant" etc.
                role = "model" if role == "assistant" else "user"
            parts = [types.Part.from_text(text=part) for part in msg.parts]
            if not parts:
                parts = [types.Part.from_text(text="")]
            contents.append(types.Content(role=role, parts=parts))

        contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=message)]
            )
        )

        def _send() -> tuple[str, float, int]:
            # Measure generation time
            start_time = time.perf_counter()

            response = self._client.models.generate_content(
                model=self._settings.gemini_model,
                contents=contents,
            )

            end_time = time.perf_counter()
            generation_time = end_time - start_time

            # Extract token usage
            usage = getattr(response, "usage_metadata", None)
            used_tokens = self._extract_total_tokens(usage)

            text = getattr(response, "text", None)
            if isinstance(text, str) and text.strip():
                return (text, generation_time, used_tokens)
            return (str(response), generation_time, used_tokens)

        try:
            return await asyncio.to_thread(_send)
        except Exception:
            logger.exception("Gemini request failed")
            raise

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors, _ = await self.embed_texts_with_usage(texts)
        return vectors

    async def embed_texts_with_usage(
        self,
        texts: list[str],
    ) -> tuple[list[list[float]], int]:
        if not texts:
            return ([], 0)

        expected_dim = int(self._settings.gemini_embedding_dim)

        @retry(
            stop=stop_after_attempt(4),
            wait=wait_exponential_jitter(initial=1, max=20),
            reraise=True,
        )
        def _embed() -> tuple[list[list[float]], int]:
            response = self._client.models.embed_content(
                model=self._settings.gemini_embedding_model,
                contents=texts,
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_DOCUMENT",
                    output_dimensionality=expected_dim,
                ),
            )

            embeddings = getattr(response, "embeddings", None)
            if embeddings is None:
                raise RuntimeError(
                    "Gemini embed_content returned no embeddings"
                )

            vectors: list[list[float]] = []
            for emb in embeddings:
                values = getattr(emb, "values", None)
                if values is None:
                    raise RuntimeError("Gemini embedding item had no values")
                vec = [float(x) for x in values]
                if len(vec) != expected_dim:
                    raise ValueError(
                        f"Embedding dimension mismatch: got {len(vec)}\
                        expected {expected_dim}"
                    )
                if not all(math.isfinite(x) for x in vec):
                    raise ValueError("Embedding contains non-finite values")
                vectors.append(vec)

            if len(vectors) != len(texts):
                raise RuntimeError(
                    f"Gemini embeddings count mismatch: got {len(vectors)}\
                    expected {len(texts)}"
                )
            usage = getattr(response, "usage_metadata", None)
            used_tokens = self._extract_total_tokens(usage)
            return (vectors, used_tokens)

        try:
            return await asyncio.to_thread(_embed)
        except Exception:
            logger.exception("Gemini embeddings request failed")
            raise



    async def embed_text_with_usage(self, text: str) -> tuple[list[float], int]:
        vectors, used_tokens = await self.embed_texts_with_usage([text])
        return vectors[0], used_tokens
