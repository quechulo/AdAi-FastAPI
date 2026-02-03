import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_agentic_service, get_gemini_service
from app.models.chat import ChatRequest
from app.services.adAgent_service import AdAgentService
from app.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/agentic-chat")
async def chat_agentic(
    request: ChatRequest,
    gemini_service: GeminiService = Depends(get_gemini_service),
    ad_agent_service: AdAgentService = Depends(get_agentic_service),
):
    """
    Orchestrates the conversation:
    1. Parses History
    2. Runs Chat and Ad Agent in PARALLEL (for speed)
    3. Merges results
    """
    try:
        chat_task = gemini_service.generate_chat_response(
            message=request.message,
            history=request.history,
        )

        ad_task = ad_agent_service.analyze_and_get_ad(
            history=request.history,
            latest_message=request.message,
        )

        chat_response_text, ad_response_text = await asyncio.gather(chat_task, ad_task)

        final_response = chat_response_text
        if ad_response_text:
            final_response += (
                "\n\n----------------\nSponsored Suggestion:\n"
                f"{ad_response_text}"
            )

        return {
            "response": final_response,
            "metadata": {"ad_injected": bool(ad_response_text)},
        }
    except Exception as e:
        logger.exception("Agentic chat endpoint failed")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {e}"
            )
