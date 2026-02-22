"""
Script to print ads with their campaign data for campaigns that are not running.
"""

from app.db.session import get_db_session
from app.db.models import Campaign, Ad, AdCampaign
from sqlalchemy import select

print("=" * 80)
print("ADS FROM NON-RUNNING CAMPAIGNS")
print("=" * 80)

session_gen = get_db_session()
db = next(session_gen)

try:
    # Query ads with their campaigns, filtering for campaigns that are NOT running
    stmt = (
        select(Ad, Campaign, AdCampaign)
        .join(AdCampaign, Ad.id == AdCampaign.ad_id)
        .join(Campaign, Campaign.id == AdCampaign.campaign_id)
        .where(~Campaign.is_running)  # NOT is_running
        .order_by(Campaign.id, Ad.id)
    )
    
    results = db.execute(stmt).all()
    
    if not results:
        print("\n⚠ No ads found from non-running campaigns")
    else:
        print(f"\nFound {len(results)} ad-campaign associations from non-running campaigns\n")
        
        current_campaign_id = None
        
        for ad, campaign, ad_campaign in results:
            # Print campaign header when we encounter a new campaign
            if campaign.id != current_campaign_id:
                current_campaign_id = campaign.id
                print("\n" + "=" * 80)
                print(f"CAMPAIGN ID: {campaign.id}")
                print(f"Title: {campaign.title}")
                print(f"Company: {campaign.company}")
                print(f"Budget: ${campaign.budget}")
                print(f"Spending: ${campaign.spending}")
                print(f"Is Enabled: {campaign.is_enabled}")
                print(f"Start Date: {campaign.start_date}")
                print(f"End Date: {campaign.end_date}")
                print(f"Is Running: {campaign.is_running}")
                print("-" * 80)
            
            # Print ad details
            # print(f"\n  AD ID: {ad.id}")
            # print(f"  Title: {ad.title}")
            # print(f"  Description: {ad.description}")
            # print(f"  URL: {ad.url}")
            # print(f"  CPC: ${ad.cpc}")
            # if ad.keywords:
            #     print(f"  Keywords: {', '.join(ad.keywords)}")
            # print(f"  Click Count (in this campaign): {ad_campaign.click_count}")
            # print(f"  Created At: {ad.created_at}")

        print("\n" + "=" * 80)
        print(f"Total: {len(results)} ad-campaign associations")
        print("=" * 80)

except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()

finally:
    db.close()
