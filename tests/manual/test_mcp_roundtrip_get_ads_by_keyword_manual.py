"""Manual runner for a full MCP roundtrip to `get_ads_by_keyword`.

This tests:
- spawning the MCP server subprocess (stdio)
- connecting a ClientSession
- calling the tool by name via MCP transport

Run (example):
  DATABASE_URL='postgresql+psycopg2://user:pass@localhost:5432/db' \
  RUN_MANUAL=1 \
  python -m pytest -s tests/manual/test_mcp_roundtrip_get_ads_by_keyword_manual.py

Optional env vars:
- KEYWORDS: comma-separated list, e.g. "shoes,iphone,car"
- LIMIT: integer; defaults to 8
- MCP_SERVER_SCRIPT: path to server script; defaults to app/mcp/server.py

Notes:
- Run from the repo root so the subprocess PYTHONPATH=os.getcwd() works.
- This hits your real DB.
"""

from __future__ import annotations

import os

import anyio
import pytest

from app.services.mcp_client import McpClient


def _parse_keywords() -> list[str]:
    raw = os.getenv("KEYWORDS", "").strip()
    if not raw:
        return [
            "shoes",
            "iphone",
            "car",
            "travel",
        ]
    return [k.strip() for k in raw.split(",") if k.strip()]


def _parse_limit() -> int:
    raw = os.getenv("LIMIT", "8").strip()
    try:
        return int(raw)
    except Exception:
        return 8


async def _run_roundtrip() -> None:
    server_script = os.getenv("MCP_SERVER_SCRIPT", "app/mcp/server.py")
    keywords = _parse_keywords()
    limit = _parse_limit()

    client = McpClient(server_script_path=server_script)

    async with client.session() as session:
        tools = await session.list_tools()
        tool_names = [t.name for t in getattr(tools, "tools", [])]
        print("\n=== MCP tools ===")
        print(tool_names)

        if "get_ads_by_keyword" not in tool_names:
            raise AssertionError("Tool get_ads_by_keyword not exposed by MCP server")

        for keyword in keywords:
            print("\n=== get_ads_by_keyword (MCP roundtrip) ===")
            print(f"keyword={keyword!r} limit={limit}")

            result = await session.call_tool(
                "get_ads_by_keyword",
                arguments={"keyword": keyword, "limit": limit},
            )

            # MCP result is typically a list of content parts (text, images, etc.)
            if hasattr(result, "content") and isinstance(result.content, list):
                text_parts = [c.text for c in result.content if hasattr(c, "text") and c.text]
                if text_parts:
                    print("\n".join(text_parts))
                else:
                    print(result)
            else:
                print(result)

            # Basic sanity: tool invocation didn't mark error
            assert getattr(result, "isError", False) in (False, None)


def test_manual_get_ads_by_keyword_mcp_roundtrip() -> None:
    if os.getenv("RUN_MANUAL") != "1":
        pytest.skip("Manual runner; set RUN_MANUAL=1 to execute")

    anyio.run(_run_roundtrip)
