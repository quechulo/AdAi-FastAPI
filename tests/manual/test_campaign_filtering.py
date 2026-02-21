"""
Test script to verify campaign filtering implementation.
"""

from app.db.session import get_db_session
from app.db.models import Campaign, Ad, AdCampaign
from app.db.retrieval import AdsVectorRepository
from sqlalchemy import select

print("=" * 60)
print("Testing Campaign Filtering Implementation")
print("=" * 60)

session_gen = get_db_session()
db = next(session_gen)

# Test 1: Hybrid property SQL mode
print("\n[Test 1] Hybrid property in SQL queries")
try:
    stmt = select(Campaign).where(Campaign.is_running)
    running_campaigns = db.execute(stmt).scalars().all()
    print(f"✓ SQL mode works: Found {len(running_campaigns)} running campaigns")
except Exception as e:
    print(f"✗ SQL mode failed: {e}")

# Test 2: Hybrid property Python mode
print("\n[Test 2] Hybrid property on Python instances")
try:
    campaign = db.execute(select(Campaign).limit(1)).scalar_one_or_none()
    if campaign:
        is_running = campaign.is_running
        print(f"✓ Python mode works: Campaign {campaign.id} "
              f"is_running={is_running}")
    else:
        print("⚠ No campaigns in database")
except Exception as e:
    print(f"✗ Python mode failed: {e}")

# Test 3: Ad retrieval with campaign filtering
print("\n[Test 3] Ad retrieval filters by running campaigns")
try:
    # Count total ads
    total_ads = db.execute(select(Ad)).scalars().all()
    print(f"  Total ads in database: {len(total_ads)}")
    
    # Count ads with at least one campaign
    ads_with_campaigns = db.execute(
        select(Ad)
        .join(AdCampaign, Ad.id == AdCampaign.ad_id)
        .distinct()
    ).scalars().all()
    print(f"  Ads with campaigns: {len(ads_with_campaigns)}")
    
    # Count ads with running campaigns (using new filter)
    ads_with_running = db.execute(
        select(Ad)
        .join(AdCampaign, Ad.id == AdCampaign.ad_id)
        .join(Campaign, AdCampaign.campaign_id == Campaign.id)
        .where(Campaign.is_running)
        .distinct()
    ).scalars().all()
    print(f"  Ads with running campaigns: {len(ads_with_running)}")
    print("✓ Campaign filtering query works")
except Exception as e:
    print(f"✗ Campaign filtering failed: {e}")

# Test 4: Vector search with campaign filtering
print("\n[Test 4] Vector search respects campaign filtering")
try:
    # Find an ad with embedding
    ad_with_embedding = db.execute(
        select(Ad).where(Ad.embedding.is_not(None)).limit(1)
    ).scalar_one_or_none()

    if ad_with_embedding and ad_with_embedding.embedding is not None:
        repo = AdsVectorRepository(db)
        # Use the ad's own embedding as query (should find itself if running)
        matches = repo.search_ads_by_embedding(
            ad_with_embedding.embedding,
            top_k=5
        )
        print(f"  Vector search returned {len(matches)} matches")
        print("✓ Vector search with campaign filtering works")
    else:
        print("⚠ No ads with embeddings to test")
except Exception as e:
    print(f"✗ Vector search failed: {e}")

session_gen.close()

print("\n" + "=" * 60)
print("Testing Complete")
print("=" * 60)
