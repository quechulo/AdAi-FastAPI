from mcp.server.fastmcp import FastMCP
import anyio
import sqlalchemy as sa
from app.db.session import get_db_session
from app.core.settings import get_settings
from app.db.retrieval import AdsVectorRepository
from app.services.gemini_service import GeminiService
from typing import Any
from decimal import Decimal
from app.db.models import Ad, AdCampaign, Campaign


# Initialize the MCP Server
mcp = FastMCP("AdAI-MCP")


def _ad_to_payload(ad: Ad) -> dict[str, Any]:
    """
    Convert an Ad ORM model to a dictionary payload.

    Note: Return structure differs between tools:
    - get_ads_by_keyword: Returns this dict directly in 'ads' array
    - get_ads_semantic: Wraps this in {'score', 'distance', 'data'} objects
    """
    cpc = ad.cpc
    if isinstance(cpc, Decimal):
        cpc_out: str | float = str(cpc)
    else:
        cpc_out = float(cpc) if cpc is not None else 0.0

    return {
        "id": ad.id,
        "title": ad.title,
        "description": ad.description,
        "keywords": ad.keywords or [],
        "url": ad.url,
        "image_url": ad.image_url,
        "cpc": cpc_out,
    }


@mcp.tool(description="Fast exact-match search for ads by keyword. Use when user mentions specific product names, brands, or short search terms (1-3 words). Performs full text search in title/description/keywords.")
async def get_ads_by_keyword(keyword: str, limit: int = 8) -> dict[str, Any]:
    """
    Fast keyword-based search using exact substring matching (SQL LIKE).
    Best for specific product names, brands, or categorical terms.

    Use this tool when:
    - User mentions specific product/brand names (e.g., "MacBook Pro", "Nike")
    - Query is 1-3 words (e.g., "wireless headphones", "laptop")
    - Looking for exact term matches

    Examples:
    - "MacBook Pro" → finds ads containing "MacBook Pro"
    - "wireless headphones" → finds ads with both "wireless" AND/OR "headphones"
    - "Nike running shoes" → finds ads matching any of these terms

    Performance: Fast, immediate results (no embedding required).

    Args:
        keyword: Keyword or phrase to search for (will be split into words).
        limit: Max number of ads to return (1-20). Default 8.

    Returns:
        {"count": int, "ads": [{"id", "title", "description", "keywords", "url", "image_url", "cpc"}]}
    """
    # Enforce safe limits (match previous chained-tool behavior)
    safe_keyword = str(keyword).strip()
    if not safe_keyword:
        raise ValueError("keyword is required")

    try:
        safe_limit = int(limit)
    except Exception:
        safe_limit = 8
    safe_limit = max(1, min(safe_limit, 20))

    words = safe_keyword.split()

    def _query_ads() -> dict[str, Any]:
        # Use the readonly session generator manually since we are outside FastAPI DI
        # Important: create/use the SQLAlchemy Session inside the worker thread.
        session_gen = get_db_session()
        try:
            db = next(session_gen)
            # Improved query: search for ANY of the words provided
            conditions = []
            for word in words:
                like = f"%{word}%"
                conditions.append(Ad.keywords.any(like))
                conditions.append(Ad.title.match(like))
                conditions.append(Ad.description.match(like))

            stmt = (
                sa.select(Ad)
                .join(AdCampaign, Ad.id == AdCampaign.ad_id)
                .join(Campaign, AdCampaign.campaign_id == Campaign.id)
                .where(
                    sa.or_(*conditions),
                    Campaign.is_running
                )
                .distinct()
                .limit(safe_limit)
            )
            ads = db.execute(stmt).scalars().all()
            return {"count": len(ads), "ads": [_ad_to_payload(a) for a in ads]}
        finally:
            session_gen.close()
    tool_result = await anyio.to_thread.run_sync(_query_ads)

    return tool_result


@mcp.tool(description="Semantic search for ads using AI embeddings. Use when user describes needs, requirements, or problems with multiple attributes. Finds conceptually similar ads even with different wording.")
async def get_ads_semantic(search_query: str, limit: int = 5) -> dict[str, Any]:
    """
    Semantic/vector similarity search using AI embeddings (cosine distance).
    Best for descriptive queries with multiple attributes or requirements.

    Use this tool when:
    - User describes needs/problems rather than specific products
    - Query contains multiple attributes or requirements
    - Query is a descriptive sentence/phrase (5+ words)
    - Need conceptual similarity, not exact term matching

    Examples:
    - "laptop for gaming under $1000" → finds gaming laptops in budget range
    - "headphones for noisy office environment" → finds noise-canceling headphones
    - "CRM software for small business lead tracking" → finds relevant CRM solutions

    Query should be distilled (remove conversational filler like "I'm looking for", "Do you have").
    Focus on: [Product Category] + [Key Features/Benefits] + [Target Audience]

    Performance: Slower than keyword search (requires embedding API call) but finds 
    conceptually similar results even with different terminology.

    Args:
        search_query: Descriptive query about product needs, features, and context.
        limit: Max number of ads to return (1-10). Default 5.

    Returns:
        {"query_intent": str, "count": int, "ads": [{"score", "distance", "data": {...}}]}
        where score is cosine similarity (higher=better) and distance is cosine distance (lower=better).
    """
    settings = get_settings()
    try:
        # Using GeminiService to embed the query string
        gemini = GeminiService(settings=settings)
        query_embedding = await gemini.embed_text(search_query)
    except Exception as e:
        return {"error": f"Failed to embed query: {str(e)}"}

    def _vector_search() -> dict[str, Any]:
        session_gen = get_db_session()
        try:
            db = next(session_gen)
            # Utilizing the AdsVectorRepository for semantic retrieval
            repo = AdsVectorRepository(db)
            matches = repo.search_ads_by_embedding(
                query_embedding=query_embedding,
                top_k=max(1, min(limit, 10))
            )

            return {
                "query_intent": search_query,
                "count": len(matches),
                "ads": [
                    {
                        "score": m.score,
                        "distance": m.distance,
                        "data": _ad_to_payload(m.ad)
                    } for m in matches
                ]
            }
        finally:
            session_gen.close()

    return await anyio.to_thread.run_sync(_vector_search)


if __name__ == "__main__":
    mcp.run()
