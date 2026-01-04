"""Adapters from existing components to agentic contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .contracts import ToolCall, ToolRegistry, ToolResult, ToolSpec


@dataclass
class MBSEToolsAdapter(ToolRegistry):
    """Expose `src/agents/langgraph_agent.MBSETools` as a ToolRegistry.

    This provides a consistent Tool Use boundary for orchestrators.
    """

    tools_api: Any

    def list_tools(self) -> Sequence[ToolSpec]:
        return (
            ToolSpec(
                name="search_artifacts",
                description="Search for artifacts by name/description",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer"},
                    },
                },
            ),
            ToolSpec(
                name="get_artifact_details",
                description="Get detailed information for an artifact",
                input_schema={
                    "type": "object",
                    "properties": {
                        "artifact_type": {"type": "string"},
                        "artifact_id": {"type": "string"},
                    },
                },
            ),
            ToolSpec(
                name="get_traceability",
                description="Get traceability matrix",
                input_schema={
                    "type": "object",
                    "properties": {
                        "source_type": {"type": "string"},
                        "target_type": {"type": "string"},
                        "depth": {"type": "integer"},
                    },
                },
            ),
            ToolSpec(
                name="get_impact_analysis",
                description="Analyze impact for a node",
                input_schema={
                    "type": "object",
                    "properties": {
                        "node_id": {"type": "string"},
                        "depth": {"type": "integer"},
                    },
                },
            ),
            ToolSpec(
                name="get_parameters",
                description="Extract design parameters",
                input_schema={
                    "type": "object",
                    "properties": {
                        "class_name": {"type": "string"},
                        "limit": {"type": "integer"},
                    },
                },
            ),
            ToolSpec(
                name="execute_cypher",
                description="Execute a Cypher query",
                input_schema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                },
            ),
            ToolSpec(name="get_statistics", description="Get graph statistics"),
        )

    def call(self, tool_call: ToolCall) -> ToolResult:
        name = tool_call.name
        args: Mapping[str, Any] = tool_call.arguments

        if name == "search_artifacts":
            return ToolResult(
                name=name,
                output=self.tools_api.search_artifacts(
                    args.get("query", ""), limit=int(args.get("limit", 10))
                ),
            )
        if name == "get_artifact_details":
            return ToolResult(
                name=name,
                output=self.tools_api.get_artifact_details(
                    str(args.get("artifact_type", "")), str(args.get("artifact_id", ""))
                ),
            )
        if name == "get_traceability":
            return ToolResult(
                name=name,
                output=self.tools_api.get_traceability(
                    source_type=args.get("source_type"),
                    target_type=args.get("target_type"),
                    depth=int(args.get("depth", 2)),
                ),
            )
        if name == "get_impact_analysis":
            return ToolResult(
                name=name,
                output=self.tools_api.get_impact_analysis(
                    str(args.get("node_id", "")), depth=int(args.get("depth", 3))
                ),
            )
        if name == "get_parameters":
            return ToolResult(
                name=name,
                output=self.tools_api.get_parameters(
                    class_name=args.get("class_name"), limit=int(args.get("limit", 20))
                ),
            )
        if name == "execute_cypher":
            return ToolResult(
                name=name,
                output=self.tools_api.execute_cypher(str(args.get("query", ""))),
            )
        if name == "get_statistics":
            return ToolResult(name=name, output=self.tools_api.get_statistics())

        raise KeyError(f"Unknown tool: {name}")
