"""Manual runner for the MCP tool implementation (direct function call).

This does NOT test MCP transport; it imports and calls the tool function directly.

Run (example):
  DATABASE_URL='postgresql+psycopg2://user:pass@localhost:5432/db' \
  GEMINI_API_KEY='...' \
  RUN_MANUAL=1 \
  python -m pytest -s tests/manual/test_mcp_get_ads_semantic_manual.py

Optional env vars:
- SALES_INTENTS: comma-separated list, e.g. "running shoes for women,phone case for iphone"
- LIMIT: integer; defaults to 5

Notes:
- This hits your real DB.
- Requires Gemini API key (GEMINI_API_KEY or GOOGLE_API_KEY).
"""

from __future__ import annotations

import json
import os

import anyio
import pytest

from app.core.settings import get_settings
from app.mcp.server import get_ads_semantic


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


def test_manual_get_ads_semantic_direct() -> None:
    if os.getenv("RUN_MANUAL") != "1":
        pytest.skip("Manual runner; set RUN_MANUAL=1 to execute")

    settings = get_settings()
    if not settings.gemini_api_key:
        pytest.skip(
            "Manual runner requires GEMINI_API_KEY or GOOGLE_API_KEY (or set it via .env/.env-model)"
        )

    sales_intents = _parse_sales_intents()
    limit = _parse_limit()

    for sales_intent in sales_intents:
        result = anyio.run(get_ads_semantic, sales_intent, limit)
        print("\n=== get_ads_semantic (direct) ===")
        print(f"sales_intent={sales_intent!r} limit={limit}")
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))

        assert isinstance(result, dict)
        assert "error" not in result
        assert result.get("query_intent") == sales_intent
        assert isinstance(result.get("ads"), list)
        assert isinstance(result.get("count"), int)
