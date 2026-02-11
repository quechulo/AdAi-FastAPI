import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_agentic_service, get_gemini_service
from app.models.chat import ChatRequest, AgenticChatResponse
from app.services.adAgent_service import AdAgentService
from app.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/agentic-chat", response_model=AgenticChatResponse)
async def chat_agentic(
    request: ChatRequest,
    gemini_service: GeminiService = Depends(get_gemini_service),
    ad_agent_service: AdAgentService = Depends(get_agentic_service),
) -> AgenticChatResponse:
    """
    Orchestrates the conversation:
    1. Parses History
    2. Runs Chat and Ad Agent in PARALLEL (for speed)
    3. Merges results and aggregates metrics
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

        chat_response, ad_response = await asyncio.gather(
            chat_task,
            ad_task
        )

        # Extract ad text and metrics from ad agent response
        ad_text = ad_response.get("ad_text")
        ad_generation_time = ad_response.get("generation_time", 0.0)
        ad_used_tokens = ad_response.get("used_tokens", 0)

        # Build final response with merged content
        final_response = chat_response["response"]
        if ad_text:
            final_response += (
                "\n\n----------------\nSponsored Suggestion:\n"
                f"{ad_text}"
            )

        total_generation_time = (
            max(chat_response["generation_time"], ad_generation_time)
        )
        total_used_tokens = chat_response["used_tokens"] + ad_used_tokens

        return AgenticChatResponse(
            response=final_response,
            generation_time=total_generation_time,
            used_tokens=total_used_tokens,
            ad_generation_time=ad_generation_time,
            ad_used_tokens=ad_used_tokens,
            metadata={
                "ad_injected": bool(ad_text),
                "chat_generation_time": chat_response["generation_time"],
                "chat_used_tokens": chat_response["used_tokens"],
            },
        )
    except Exception as e:
        logger.exception("Agentic chat endpoint failed")
        print(e)
        raise HTTPException(
            status_code=e.__dict__.get("code", 500),
            detail=f"Internal server error:\
                {e.__dict__.get('message', str(e))}"
            )
