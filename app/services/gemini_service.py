from __future__ import annotations

import asyncio
import logging
import math

from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from app.core.settings import Settings, get_settings
from app.models.chat import ChatMessage
from app.services.tool_runner import ToolRunner

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
        history: list[ChatMessage],
        *,
        tools: ToolRunner | None = None,
        max_tool_steps: int = 6,
    ):
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

        def _send_once(config: types.GenerateContentConfig | None) -> types.GenerateContentResponse:
            return self._client.models.generate_content(
                model=self._settings.gemini_model,
                contents=contents,
                config=config,
            )

        def _extract_text(response: types.GenerateContentResponse) -> str | None:
            text = getattr(response, "text", None)
            if isinstance(text, str) and text.strip():
                return text
            return None

        def _extract_function_calls(response: types.GenerateContentResponse) -> list[types.FunctionCall]:
            calls: list[types.FunctionCall] = []
            candidates = getattr(response, "candidates", None) or []
            for cand in candidates:
                content = getattr(cand, "content", None)
                if content is None:
                    continue
                parts = getattr(content, "parts", None) or []
                for part in parts:
                    fc = getattr(part, "function_call", None)
                    # SDK uses field name `function_call` on deserialized responses.
                    if fc is None:
                        fc = getattr(part, "functionCall", None)
                    if fc is not None:
                        calls.append(fc)
            return calls

        def _build_tools_config() -> types.GenerateContentConfig | None:
            if tools is None:
                return None

            declarations = [t.as_function_declaration() for t in tools.registry.list()]
            tool = types.Tool(functionDeclarations=declarations)
            tool_config = types.ToolConfig(
                functionCallingConfig=types.FunctionCallingConfig(
                    mode=types.FunctionCallingConfigMode.AUTO,
                    allowedFunctionNames=[t.name for t in tools.registry.list()],
                )
            )
            return types.GenerateContentConfig(
                tools=[tool],
                toolConfig=tool_config,
            )

        try:
            config = _build_tools_config()

            if tools is None:
                response = await asyncio.to_thread(_send_once, config)
                text = _extract_text(response)
                return text if text is not None else str(response)

            # Tool loop: model can call tools, we execute and feed results back.
            for _ in range(max(0, int(max_tool_steps))):
                response = await asyncio.to_thread(_send_once, config)

                calls = _extract_function_calls(response)
                if calls:
                    for call in calls:
                        name = getattr(call, "name", None) or ""
                        args = getattr(call, "args", None)
                        tool_result = tools.run(name=name, args=args)

                        contents.append(
                            types.Content(
                                role="user",
                                parts=[
                                    types.Part.from_function_response(
                                        name=name,
                                        response=tool_result,
                                    )
                                ],
                            )
                        )
                    continue

                text = _extract_text(response)
                return text if text is not None else str(response)

            # If the model keeps calling tools, return the last response's text.
            response = await asyncio.to_thread(_send_once, config)
            text = _extract_text(response)
            return text if text is not None else str(response)
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
                raise RuntimeError("Gemini embed_content returned no embeddings")

            vectors: list[list[float]] = []
            for emb in embeddings:
                values = getattr(emb, "values", None)
                if values is None:
                    raise RuntimeError("Gemini embedding item had no values")
                vec = [float(x) for x in values]
                if len(vec) != expected_dim:
                    raise ValueError(
                        f"Embedding dimension mismatch: got {len(vec)} expected {expected_dim}"
                    )
                if not all(math.isfinite(x) for x in vec):
                    raise ValueError("Embedding contains non-finite values")
                vectors.append(vec)

            if len(vectors) != len(texts):
                raise RuntimeError(
                    f"Gemini embeddings count mismatch: got {len(vectors)} expected {len(texts)}"
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