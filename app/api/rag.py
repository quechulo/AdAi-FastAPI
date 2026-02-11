import logging

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_rag_service
from app.models.rag import RagRequest, RagResponse
from app.services.rag_service import RagService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/rag-chat", response_model=RagResponse)
async def rag_endpoint(
    request: RagRequest,
    rag_service: RagService = Depends(get_rag_service),
) -> RagResponse:
    try:
        return await rag_service.answer(
            message=request.message,
            history=request.history,
            top_k=request.top_k,
        )
    except Exception as e:
        logger.exception("RAG endpoint failed")
        print(e)
        raise HTTPException(
            status_code=e.__dict__.get("code", 500),
            detail=f"Internal server error:\
                {e.__dict__.get('message', str(e))}"
            )
