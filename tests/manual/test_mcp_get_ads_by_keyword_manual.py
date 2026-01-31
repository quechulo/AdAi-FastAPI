"""Manual runner for the MCP tool implementation (direct function call).

This does NOT test MCP transport; it imports and calls the tool function directly.

Run (example):
  DATABASE_URL='postgresql+psycopg2://user:pass@localhost:5432/db' \
  RUN_MANUAL=1 \
  python -m pytest -s tests/manual/test_mcp_get_ads_by_keyword_manual.py

Optional env vars:
- KEYWORDS: comma-separated list, e.g. "shoes,iphone,car"
- LIMIT: integer; defaults to 8

Notes:
- This hits your real DB. Ensure migrations are applied and `ads` table has data.
"""

from __future__ import annotations

import json
import os

import anyio
import pytest

from app.mcp.server import get_ads_by_keyword


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


def test_manual_get_ads_by_keyword_direct() -> None:
    if os.getenv("RUN_MANUAL") != "1":
        pytest.skip("Manual runner; set RUN_MANUAL=1 to execute")

    keywords = _parse_keywords()
    limit = _parse_limit()

    for keyword in keywords:
        result = anyio.run(get_ads_by_keyword, keyword, limit)
        print("\n=== get_ads_by_keyword (direct) ===")
        print(f"keyword={keyword!r} limit={limit}")
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        assert isinstance(result, dict)
        assert result.get("keyword") == keyword
