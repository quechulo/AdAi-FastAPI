from __future__ import annotations

import logging

from langchain_core.prompts import PromptTemplate
from sqlalchemy.orm import Session

from app.core.settings import Settings, get_settings
from app.db.retrieval import AdsVectorRepository
from app.models.chat import ChatMessage
from app.models.rag import RagCitation, RagResponse
from app.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)


_RAG_PROMPT = PromptTemplate.from_template(
    """You are an assistant that helps users with their problems and if possible, choose the best matching ads for a user query/needs. If no ads matches result, just ignore all 'Candidate ads' and provide a helpful answer.

Rules:
- Use ONLY the provided ads as factual sources.
- If none of the ads are relevant, do not provide any ads.
- Do not invent ad URLs, titles, or claims not present in the ads.

User query:
{question}

Candidate ads:
{context}

Write a concise helpful answer to the user.
"""
)


class RagService:
    def __init__(
        self,
        db: Session,
        gemini_service: GeminiService,
        settings: Settings | None = None,
    ) -> None:
        self._db = db
        self._gemini = gemini_service
        self._settings = settings or get_settings()

    async def answer(
        self,
        message: str,
        history: list[ChatMessage],
        top_k: int,
    ) -> RagResponse:
        # 1) Embed the query
        try:
            query_embedding = await self._gemini.embed_text(message)
        except Exception:
            logger.exception("RAG: failed to embed query; falling back to generic answer")
            response_text = await self._gemini.generate_chat_response(message=message, history=history)
            return RagResponse(response=response_text, citations=[])

        # 2) Retrieve similar ads
        repo = AdsVectorRepository(self._db)
        matches = repo.search_ads_by_embedding(query_embedding=query_embedding, top_k=top_k)

        # 3) Fallback when nothing relevant is found
        if not matches:
            response_text = await self._gemini.generate_chat_response(message=message, history=history)
            return RagResponse(response=response_text, citations=[])

        # 4) Build context + citations payload
        context_lines: list[str] = []
        citations: list[RagCitation] = []

        for m in matches:
            ad = m.ad

            kw = ", ".join(ad.keywords) if ad.keywords else ""
            cpc_str = str(ad.cpc)

            context_lines.append(
                "\n".join(
                    [
                        f"- ad_id: {ad.id}",
                        f"  title: {ad.title}",
                        f"  description: {ad.description}",
                        f"  url: {ad.url}",
                        f"  keywords: {kw}",
                        f"  cpc: {cpc_str}",
                    ]
                )
            )

            citations.append(RagCitation(score=m.score, distance=m.distance, ad=ad))

        context = "\n\n".join(context_lines)
        rag_message = _RAG_PROMPT.format(question=message, context=context)

        # 5) Generate grounded answer
        response_text = await self._gemini.generate_chat_response(message=rag_message, history=history)

        return RagResponse(response=response_text, citations=citations)
