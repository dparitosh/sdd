"""Minimal ToolRegistry implementations.

This is a small, local-friendly implementation intended to standardize how tools
are registered and invoked. It can be replaced with an MCP-backed registry or a
remote registry in an Azure deployment.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from .contracts import ToolCall, ToolRegistry, ToolResult, ToolSpec


@dataclass
class _RegisteredTool:
    spec: ToolSpec
    func: Callable[[Mapping[str, Any]], Any]


class InProcessToolRegistry(ToolRegistry):
    def __init__(
        self, tools: Sequence[tuple[ToolSpec, Callable[[Mapping[str, Any]], Any]]]
    ):
        self._tools: dict[str, _RegisteredTool] = {
            spec.name: _RegisteredTool(spec=spec, func=func) for spec, func in tools
        }

    def list_tools(self) -> Sequence[ToolSpec]:
        return [t.spec for t in self._tools.values()]

    def call(self, tool_call: ToolCall) -> ToolResult:
        tool = self._tools.get(tool_call.name)
        if tool is None:
            raise KeyError(f"Unknown tool: {tool_call.name}")

        start = time.perf_counter()
        output = tool.func(tool_call.arguments)
        duration_ms = (time.perf_counter() - start) * 1000.0
        return ToolResult(name=tool_call.name, output=output, duration_ms=duration_ms)
