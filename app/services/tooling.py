from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from google.genai import types


ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: types.Schema
    handler: ToolHandler

    def as_function_declaration(self) -> types.FunctionDeclaration:
        return types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters=self.parameters,
        )


class ToolRegistry:
    def __init__(self, tools: list[ToolSpec]):
        tool_by_name = {t.name: t for t in tools}
        if len(tool_by_name) != len(tools):
            raise ValueError("Duplicate tool names in ToolRegistry")
        self._tools = tool_by_name

    def list(self) -> list[ToolSpec]:
        return list(self._tools.values())

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)
