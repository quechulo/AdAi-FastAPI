from typing import Optional
from sqlalchemy.orm import Session
from app.db.models import Ad


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
