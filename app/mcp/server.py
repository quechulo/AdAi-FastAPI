from mcp.server.fastmcp import FastMCP
import anyio
import sqlalchemy as sa
from app.db.session import get_db_session
from app.core.settings import get_settings
from app.db.retrieval import AdsVectorRepository
from app.services.gemini_service import GeminiService
from typing import Any
from decimal import Decimal
from app.db.models import Ad


# Initialize the MCP Server
mcp = FastMCP("AdAI-MCP")

def _ad_to_payload(ad: Ad) -> dict[str, Any]:
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


@mcp.tool(description="Search ads by a keyword in title/description/keywords. Returns a small bounded list.")
async def get_ads_by_keyword(keyword: str, limit: int = 8) -> dict[str, Any]:
    """
    Search ads by a given keyword in title/description/keywords of ad. Returns a small bounded list.
    
    Args:
        keyword: Keyword or phrase to search for.
        limit: Max number of ads to return (1-20). Default 8.
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
                conditions.append(Ad.title.ilike(like))
                conditions.append(Ad.description.ilike(like))
            
            stmt = sa.select(Ad).where(sa.or_(*conditions)).limit(safe_limit)
            ads = db.execute(stmt).scalars().all()
            return {"count": len(ads), "ads": [_ad_to_payload(a) for a in ads]}
        finally:
            session_gen.close()
    tool_result = await anyio.to_thread.run_sync(_query_ads)

    return tool_result

@mcp.tool(description="Search ads semantically based on a sales intent or product description.")
async def get_ads_semantic(sales_intent: str, limit: int = 5) -> dict[str, Any]:
    """
    Perform a semantic/vector search for ads. Best for broad needs or descriptive queries.
    
    Args:
        sales_intent: A distilled description of the product, features, and audience.
        limit: Max number of ads to return (1-10).
    """
    settings = get_settings()
    try:
        # Using GeminiService to embed the query string
        gemini = GeminiService(settings=settings)
        query_embedding = await gemini.embed_text(sales_intent)
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
                "query_intent": sales_intent,
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