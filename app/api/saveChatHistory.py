import logging

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_save_chat_service
from app.models.chat import SaveChatRequest, SaveChatResponse
from app.services.save_chat_service import SaveChatService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/save-chat-history", response_model=SaveChatResponse)
async def save_chat_history(
    request: SaveChatRequest,
    save_chat_service: SaveChatService = Depends(get_save_chat_service),
) -> SaveChatResponse:
    """
    Save a complete chat session snapshot.

    This endpoint persists an immutable snapshot of a chat conversation
    when the user starts a new conversation. Sessions are never edited
    after creation.

    Args:
        request: Chat session data with mode, history, and optional version
        save_chat_service: Injected service for database operations
 
    Returns:
        SaveChatResponse with session ID and metadata
    """
    try:
        if not request.history:
            raise HTTPException(
                status_code=400,
                detail="Chat history cannot be empty"
            )

        if request.mode not in {"basic", "rag", "mcp", "agent"}:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid mode: {request.mode}. "
                    "Must be one of: basic, rag, mcp, agent"
                ),
            )

        response = save_chat_service.save_session(
            mode=request.mode,
            history=request.history,
            version=request.version,
            helpful=request.helpful,
        )

        logger.info(f"Successfully saved chat session {response.id}")
        return response

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception("save_chat_history endpoint failed")
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {e}"
        )
