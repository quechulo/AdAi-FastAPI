import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException

from app.models.chat import ChatRequest, ChatResponse
from app.services.mcp_client import McpClient
from app.services.mcp_service import McpService
from app.core.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()

mcp_client_instance = McpClient(server_script_path="app/mcp/server.py")


def get_mcp_service():
    settings = get_settings()
    return McpService(
        mcp_client=mcp_client_instance,
        system_prompt=settings.mcp_system_prompt,
    )


@router.post("/mcp-chat", response_model=ChatResponse)
async def mcp_endpoint(
    request: ChatRequest,
    mcp_service: McpService = Depends(get_mcp_service),
) -> ChatResponse:
    try:
        response_text = await mcp_service.answer(
            message=request.message,
            history=request.history,
        )
        return ChatResponse(response=response_text)
    except TimeoutError as e:
        raise HTTPException(
            status_code=504,
            detail=str(e) or "Upstream timeout",
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Upstream timeout while waiting for MCP tool or Gemini response",
        )
    except Exception as e:
        logger.exception("Agent endpoint failed")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")
