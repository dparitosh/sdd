"""Standard contracts for an agentic runtime.

These contracts are designed to:
- Make tool boundaries explicit (Tool Use pattern)
- Make retrieval explicit and pluggable (RAG pattern)
- Make planning + reflection explicit and testable
- Support orchestrator + worker agents (multi-agent collaboration)

The goal is architecture standardization; implementations can be local/dev or
Azure-hosted.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence, runtime_checkable


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: Mapping[str, Any]


@dataclass(frozen=True)
class ToolResult:
    name: str
    output: Any
    duration_ms: float | None = None


@dataclass(frozen=True)
class RetrievedChunk:
    id: str
    text: str
    source: str | None = None
    metadata: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class PlanStep:
    id: str
    description: str
    tool_call: ToolCall | None = None


@dataclass(frozen=True)
class Plan:
    goal: str
    steps: Sequence[PlanStep]


@runtime_checkable
class ToolRegistry(Protocol):
    """Registry for tools exposed to agents/orchestrators."""

    def list_tools(self) -> Sequence[ToolSpec]:
        raise NotImplementedError

    def call(self, tool_call: ToolCall) -> ToolResult:
        raise NotImplementedError


@runtime_checkable
class Retriever(Protocol):
    """Retrieval interface for RAG grounding."""

    def retrieve(
        self, query: str, *, top_k: int = 5, filters: Mapping[str, Any] | None = None
    ) -> Sequence[RetrievedChunk]:
        raise NotImplementedError


@runtime_checkable
class Planner(Protocol):
    """Planning interface (goal -> explicit steps)."""

    def plan(self, goal: str, *, context: Mapping[str, Any] | None = None) -> Plan:
        raise NotImplementedError


@runtime_checkable
class Reflector(Protocol):
    """Reflection interface (review outcome -> improvements)."""

    def reflect(
        self,
        *,
        goal: str,
        plan: Plan,
        results: Sequence[ToolResult],
        draft_response: str,
    ) -> Mapping[str, Any]:
        raise NotImplementedError


@runtime_checkable
class Agent(Protocol):
    """Worker agent interface."""

    name: str

    def run(
        self,
        goal: str,
        *,
        tool_registry: ToolRegistry,
        retriever: Retriever | None = None,
    ) -> str:
        raise NotImplementedError


@runtime_checkable
class Orchestrator(Protocol):
    """Orchestrator interface (delegation + retries + audit)."""

    def run(self, goal: str) -> str:
        raise NotImplementedError
