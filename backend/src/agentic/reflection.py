"""Reflection implementations.

Reflection is modeled as a structured post-check over tool outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .contracts import Plan, Reflector, ToolResult


@dataclass
class SimpleReflector(Reflector):
    """Minimal reflector for local runs.

    Produces structured metadata that can be logged/audited by an orchestrator.
    """

    def reflect(
        self,
        *,
        goal: str,
        plan: Plan,
        results: Sequence[ToolResult],
        draft_response: str,
    ) -> Mapping[str, Any]:
        errors: list[str] = []
        for r in results:
            if isinstance(r.output, str) and r.output.lower().startswith("error"):
                errors.append(f"{r.name}: {r.output}")

        return {
            "goal": goal,
            "plan_steps": len(plan.steps),
            "tool_calls": len(results),
            "errors": errors,
            "recommendation": "retry_with_more_context" if errors else "ok",
            "draft_chars": len(draft_response),
        }
