## Instructions for manual tests:

`RUN_MANUAL=1 python -m pytest -s tests/manual/test_mcp_get_ads_by_keyword_manual.py`

`RUN_MANUAL=1 python -m pytest -s tests/manual/test_mcp_roundtrip_get_ads_by_keyword_manual.py`

`RUN_MANUAL=1 KEYWORDS="sport headphones" python -m pytest -s tests/manual/test_mcp_roundtrip_get_ads_by_keyword_manual.py`