"""
Debug vector search issue
"""

from app.db.session import get_db_session
from app.db.models import Ad
from app.db.retrieval import AdsVectorRepository
from sqlalchemy import select

session_gen = get_db_session()
db = next(session_gen)

# Find an ad with embedding
ad_with_embedding = db.execute(
    select(Ad).where(Ad.embedding.is_not(None)).limit(1)
).scalar_one_or_none()

if ad_with_embedding and ad_with_embedding.embedding is not None:
    print(f"Ad ID: {ad_with_embedding.id}")
    print(f"Embedding type: {type(ad_with_embedding.embedding)}")
    print(f"Embedding length: {len(ad_with_embedding.embedding)}")
    print(f"First few values: {ad_with_embedding.embedding[:3]}")

    try:
        repo = AdsVectorRepository(db)
        matches = repo.search_ads_by_embedding(
            ad_with_embedding.embedding,
            top_k=5
        )
        print(f"✓ Success! Found {len(matches)} matches")
        for match in matches:
            print(f"  - Ad {match.ad.id}: score={match.score:.4f}")
    except Exception as e:
        import traceback
        print(f"✗ Error: {e}")
        print("\nFull traceback:")
        traceback.print_exc()
else:
    print("No ads with embeddings")

session_gen.close()
