"""Planning implementations.

Keep these lightweight: the goal is to make planning explicit and testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .contracts import Plan, PlanStep, Planner, ToolCall


@dataclass
class KeywordPlanner(Planner):
    """A deterministic planner for local runs.

    This intentionally avoids LLM dependencies while still exercising the Planning boundary.
    """

    def plan(self, goal: str, *, context: Mapping[str, Any] | None = None) -> Plan:
        _ = context
        normalized = goal.lower()

        if any(k in normalized for k in ["traceability", "trace", "requirements to design", "matrix"]):
            return Plan(
                goal=goal,
                steps=(
                    PlanStep(id="s1", description="Get traceability matrix", tool_call=ToolCall(name="get_traceability", arguments={})),
                ),
            )

        if any(k in normalized for k in ["impact", "change impact"]):
            # Without an explicit node id, start with a search step.
            return Plan(
                goal=goal,
                steps=(
                    PlanStep(
                        id="s1",
                        description="Search likely impacted artifacts",
                        tool_call=ToolCall(name="search_artifacts", arguments={"query": goal, "limit": 5}),
                    ),
                ),
            )

        if any(k in normalized for k in ["stats", "statistics", "how many"]):
            return Plan(
                goal=goal,
                steps=(
                    PlanStep(id="s1", description="Get graph statistics", tool_call=ToolCall(name="get_statistics", arguments={})),
                ),
            )

        # Default: search first.
        return Plan(
            goal=goal,
            steps=(
                PlanStep(
                    id="s1",
                    description="Search artifacts relevant to the goal",
                    tool_call=ToolCall(name="search_artifacts", arguments={"query": goal, "limit": 5}),
                ),
            ),
        )
