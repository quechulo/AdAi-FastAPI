import logging

from fastapi import APIRouter, HTTPException


logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
def root_health_check() -> dict[str, str]:
    try:
        return {"status": "running", "service": "Conversational Ad AI"}
    except Exception as e:
        logger.exception("Root health endpoint failed")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.get("/health")
def health_check() -> dict[str, str]:
    try:
        return {"status": "ok"}
    except Exception as e:
        logger.exception("Health endpoint failed")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")
