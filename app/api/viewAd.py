import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.ad import ViewAdResponse
from app.services.view_ad_service import ViewAdService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/view-ad/{ad_id}", response_model=ViewAdResponse)
async def view_ad_endpoint(
    ad_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> ViewAdResponse:
    """
    Retrieve an ad by ID.
    Returns: title, description, and image_url

    Click tracking happens asynchronously in the background after the response
    is returned, ensuring fast response times.
    """
    try:
        service = ViewAdService(db)
        ad = service.get_ad(ad_id)

        if not ad:
            raise HTTPException(
                status_code=404,
                detail=f"Ad with id {ad_id} not found"
                )

        # Schedule click tracking to run after response is sent
        background_tasks.add_task(ViewAdService.track_ad_click, ad_id)

        return ViewAdResponse(
            id=ad.id,
            title=ad.title,
            description=ad.description,
            keywords=ad.keywords,
            image_url=ad.image_url,
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"View ad endpoint failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {e}"
            )
