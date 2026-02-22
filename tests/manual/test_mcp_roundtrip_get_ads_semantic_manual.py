"""Manual runner for a full MCP roundtrip to `get_ads_semantic`.

This tests:
- spawning the MCP server subprocess (stdio)
- connecting a ClientSession
- calling the tool by name via MCP transport

Run (example):
  DATABASE_URL='postgresql+psycopg2://user:pass@localhost:5432/db' \
  GEMINI_API_KEY='...' \
  RUN_MANUAL=1 \
  python -m pytest -s tests/manual/test_mcp_roundtrip_get_ads_semantic_manual.py

Optional env vars:
- SALES_INTENTS: comma-separated list
- LIMIT: integer; defaults to 5
- MCP_SERVER_SCRIPT: path to server script; defaults to app/mcp/server.py

Notes:
- Run from the repo root so the subprocess PYTHONPATH=os.getcwd() works.
- This hits your real DB.
- Requires Gemini API key (GEMINI_API_KEY or GOOGLE_API_KEY).
"""

from __future__ import annotations

import os

import anyio
import pytest

from app.core.settings import get_settings
from app.services.mcp_client import McpClient


def _parse_sales_intents() -> list[str]:
    raw = os.getenv("SALES_INTENTS", "").strip()
    if not raw:
        return [
            "running shoes for women with great cushioning",
            "wireless noise cancelling headphones for travel",
            "budget-friendly gaming laptop for students",
        ]
    return [s.strip() for s in raw.split(",") if s.strip()]


def _parse_limit() -> int:
    raw = os.getenv("LIMIT", "5").strip()
    try:
        return int(raw)
    except Exception:
        return 5


async def _run_roundtrip() -> None:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError(
            "Manual runner requires GEMINI_API_KEY or GOOGLE_API_KEY (or set it via .env/.env-model)"
        )

    server_script = os.getenv("MCP_SERVER_SCRIPT", "app/mcp/server.py")
    sales_intents = _parse_sales_intents()
    limit = _parse_limit()

    client = McpClient(server_script_path=server_script)

    async with client.session() as session:
        tools = await session.list_tools()
        tool_names = [t.name for t in getattr(tools, "tools", [])]
        print("\n=== MCP tools ===")
        print(tool_names)

        if "get_ads_semantic" not in tool_names:
            raise AssertionError("Tool get_ads_semantic not exposed by MCP server")

        for search_query in sales_intents:
            print("\n=== get_ads_semantic (MCP roundtrip) ===")
            print(f"search_query={search_query!r} limit={limit}")

            result = await session.call_tool(
                "get_ads_semantic",
                arguments={"search_query": search_query, "limit": limit},
            )

            if hasattr(result, "content") and isinstance(result.content, list):
                text_parts = [
                    c.text for c in result.content if hasattr(c, "text") and c.text
                ]
                if text_parts:
                    print("\n".join(text_parts))
                else:
                    print(result)
            else:
                print(result)

            assert getattr(result, "isError", False) in (False, None)


def test_manual_get_ads_semantic_mcp_roundtrip() -> None:
    if os.getenv("RUN_MANUAL") != "1":
        pytest.skip("Manual runner; set RUN_MANUAL=1 to execute")

    anyio.run(_run_roundtrip)
