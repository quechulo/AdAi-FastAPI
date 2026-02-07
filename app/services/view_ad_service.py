import logging
from typing import Optional
from sqlalchemy.orm import Session, joinedload
from app.db.models import Ad
from app.db.session import get_sessionmaker

logger = logging.getLogger(__name__)


class ViewAdService:
    def __init__(self, db: Session):
        self.db = db

    def get_ad(self, ad_id: int) -> Optional[Ad]:
        """
        Retrieve an ad by ID.
        Note: click_count is tracked in ad_campaigns table, not ads table.
        """
        ad = self.db.query(Ad).filter(Ad.id == ad_id).first()
        return ad

    @staticmethod
    def track_ad_click(ad_id: int) -> None:
        """
        Track a click on an ad by incrementing click_count for all
        running campaigns and increasing campaign spending by the ad's CPC.
        
        This method creates its own database session and runs in a
        transaction. Designed to run as a background task without
        blocking the response.
        
        Args:
            ad_id: The ID of the ad that was clicked
        """
        SessionLocal = get_sessionmaker()
        db = SessionLocal()

        try:
            # Load ad with campaign_links and nested campaign relationship
            ad = db.query(Ad).options(
                joinedload(Ad.campaign_links).joinedload(
                    "campaign"
                )
            ).filter(Ad.id == ad_id).first()

            if not ad:
                logger.warning(f"Ad {ad_id} not found for click tracking")
                return

            # Track which campaigns were updated for logging
            updated_campaigns = []

            # Update click_count and spending for all running campaigns
            for ad_campaign in ad.campaign_links:
                campaign = ad_campaign.campaign

                # Only track clicks for running campaigns
                if campaign.is_running:
                    # Increment click count
                    ad_campaign.click_count += 1

                    # Increase campaign spending by CPC
                    campaign.spending += ad.cpc

                    updated_campaigns.append(
                        f"Campaign {campaign.id} ({campaign.title})"
                    )

            # Commit all updates in a single transaction
            db.commit()

            if updated_campaigns:
                logger.info(
                    f"Click tracked for Ad {ad_id}. "
                    f"Updated campaigns: {', '.join(updated_campaigns)}"
                )
            else:
                logger.info(
                    f"Click on Ad {ad_id} not tracked - no running campaigns"
                )

        except Exception as e:
            # Rollback transaction on any error
            db.rollback()
            logger.error(
                f"Failed to track click for Ad {ad_id}: {e}",
                exc_info=True
            )
        finally:
            # Always close the session
            db.close()
