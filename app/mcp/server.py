# app/mcp/server.py
from mcp.server.fastmcp import FastMCP
import anyio
import sqlalchemy as sa
from app.db.session import get_db_session
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
    Search for ads matching the given keyword.
    
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

    like = f"%{safe_keyword}%"

    def _query_ads() -> dict[str, Any]:
        # Use the readonly session generator manually since we are outside FastAPI DI
        # Important: create/use the SQLAlchemy Session inside the worker thread.
        session_gen = get_db_session()
        try:
            db = next(session_gen)
            stmt = (
                sa.select(Ad)
                .where(
                    sa.or_(
                        Ad.title.ilike(like),
                        Ad.description.ilike(like),
                        Ad.keywords.any(safe_keyword),
                    )
                )
                .order_by(Ad.id.asc())
                .limit(safe_limit)
            )
            ads = db.execute(stmt).scalars().all()

            return {
                "keyword": safe_keyword,
                "count": len(ads),
                "ads": [_ad_to_payload(a) for a in ads],
            }
        finally:
            session_gen.close()
    tool_result = await anyio.to_thread.run_sync(_query_ads)
    print("--------------------")
    print("Tool result:", tool_result)
    print("--------------------")

    return tool_result


if __name__ == "__main__":
    mcp.run()