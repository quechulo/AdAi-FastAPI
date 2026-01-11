import logging

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_gemini_service, get_tool_runner
from app.models.chat import ChatRequest, ChatResponse
from app.services.gemini_service import GeminiService
from app.services.tool_runner import ToolRunner

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/mcp", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    gemini_service: GeminiService = Depends(get_gemini_service),
    tools: ToolRunner = Depends(get_tool_runner),
) -> ChatResponse:
    try:
        response_text = await gemini_service.generate_chat_response(
            message=request.message,
            history=request.history,
            tools=tools,
        )
        return ChatResponse(response=response_text)
    except Exception as e:
        logger.exception("Chat endpoint failed")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")
