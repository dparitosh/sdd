"""Reference orchestrator aligned to Azure agentic patterns.

This orchestrator is intentionally lightweight:
- Planning boundary is explicit (Planner)
- Tool Use boundary is explicit (ToolRegistry)
- Optional retrieval boundary (Retriever)
- Reflection boundary (Reflector)

It can be used locally or swapped for an Azure-hosted implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .contracts import (
    Agent,
    Orchestrator,
    Plan,
    Planner,
    Reflector,
    Retriever,
    ToolRegistry,
    ToolResult,
)


@dataclass
class SingleToolAgent(Agent):
    """A minimal worker agent that executes a plan via ToolRegistry."""

    name: str
    planner: Planner

    def run(
        self,
        goal: str,
        *,
        tool_registry: ToolRegistry,
        retriever: Retriever | None = None,
    ) -> str:
        context: dict[str, Any] = {}
        if retriever is not None:
            chunks = retriever.retrieve(goal, top_k=5)
            context["retrieved"] = [c.text for c in chunks]

        plan = self.planner.plan(goal, context=context)
        results: list[ToolResult] = []

        for step in plan.steps:
            if step.tool_call is None:
                continue
            results.append(tool_registry.call(step.tool_call))

        # Keep response simple and deterministic.
        # Higher-level LLM synthesis is an implementation choice and can be provided by a different Agent.
        summary = {r.name: r.output for r in results}
        return str(summary)


@dataclass
class BaselineOrchestrator(Orchestrator):
    """Central orchestrator for predictable, compliance-heavy workflows."""

    tool_registry: ToolRegistry
    planner: Planner
    reflector: Reflector
    agents: Sequence[Agent]
    retriever: Retriever | None = None
    max_retries: int = 1

    def run(self, goal: str) -> str:
        # For now we route all work to the first agent.
        # Multi-agent routing can be implemented by mapping plan steps or task types to specific agents.
        agent = self.agents[0]

        last_response = ""
        last_plan: Plan | None = None
        last_results: list[ToolResult] = []

        for attempt in range(self.max_retries + 1):
            last_response = agent.run(
                goal, tool_registry=self.tool_registry, retriever=self.retriever
            )

            # Build a plan for the reflector to inspect — but do NOT re-execute
            # tools, since agent.run() already executed them above.
            last_plan = self.planner.plan(goal, context=None)
            last_results = []
            for step in last_plan.steps:
                if step.tool_call is None:
                    continue
                # Provide a synthetic result so the reflector has something to review.
                last_results.append(
                    ToolResult(name=step.tool_call.name, output="(executed by agent)")
                )

            reflection = self.reflector.reflect(
                goal=goal,
                plan=last_plan,
                results=last_results,
                draft_response=last_response,
            )

            if reflection.get("recommendation") == "ok":
                break
            if attempt >= self.max_retries:
                break

        return last_response
