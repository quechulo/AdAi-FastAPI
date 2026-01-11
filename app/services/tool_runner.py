from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.services.tooling import ToolRegistry

logger = logging.getLogger(__name__)


class ToolRunner:
    def __init__(self, *, db: Session, registry: ToolRegistry):
        self._db = db
        self._registry = registry

    @property
    def registry(self) -> ToolRegistry:
        return self._registry

    def run(self, *, name: str, args: dict[str, Any] | None) -> dict[str, Any]:
        tool = self._registry.get(name)
        if tool is None:
            return {
                "ok": False,
                "error": f"Unknown tool: {name}",
            }

        try:
            safe_args = args or {}
            result = tool.handler(safe_args)
            if not isinstance(result, dict):
                raise TypeError("Tool handler must return dict")
            return {"ok": True, "result": result}
        except Exception as e:
            logger.exception("Tool execution failed: %s", name)
            return {
                "ok": False,
                "error": str(e),
            }
