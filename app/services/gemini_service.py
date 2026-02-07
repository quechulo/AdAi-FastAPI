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
            used_tokens = 0
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                used_tokens = getattr(
                    response.usage_metadata, "total_token_count", 0
                )

            text = getattr(response, "text", None)
            if isinstance(text, str) and text.strip():
                return {"response": text, "generation_time": generation_time, "used_tokens": used_tokens}
            return {"response": str(response), "generation_time": generation_time, "used_tokens": used_tokens}

        try:
            return await asyncio.to_thread(_send)
        except Exception:
            logger.exception("Gemini request failed")
            raise

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        expected_dim = int(self._settings.gemini_embedding_dim)

        @retry(
            stop=stop_after_attempt(4),
            wait=wait_exponential_jitter(initial=1, max=20),
            reraise=True,
        )
        def _embed() -> list[list[float]]:
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
            return vectors

        try:
            return await asyncio.to_thread(_embed)
        except Exception:
            logger.exception("Gemini embeddings request failed")
            raise

    async def embed_text(self, text: str) -> list[float]:
        vectors = await self.embed_texts([text])
        return vectors[0]
