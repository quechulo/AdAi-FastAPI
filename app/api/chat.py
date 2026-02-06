import logging

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_gemini_service
from app.models.chat import ChatRequest, ChatResponse
from app.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    gemini_service: GeminiService = Depends(get_gemini_service),
) -> ChatResponse:
    try:
        (
            response_text,
            generation_time,
            used_tokens,
        ) = await gemini_service.generate_chat_response(
            message=request.message,
            history=request.history,
        )
        return ChatResponse(
            response=response_text,
            generation_time=generation_time,
            used_tokens=used_tokens,
        )
    except Exception as e:
        logger.exception("Chat endpoint failed")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")
