"""Integration tests for Azure AI Baseline Orchestrator pattern.

These tests verify that the vendor-neutral agentic runtime correctly implements:
- Tool Use
- Planning
- Reflection
- Orchestrator-Agent
- Multi-Agent (structure in place, single agent used for now)
"""

import pytest

from src.agentic import (
    BaselineOrchestrator,
    KeywordPlanner,
    SimpleReflector,
    SingleToolAgent,
    ToolCall,
    ToolRegistry,
    ToolResult,
)


class MockToolRegistry(ToolRegistry):
    """Mock tool registry for isolated testing."""

    def list_tools(self):
        return []

    def call(self, tool_call: ToolCall) -> ToolResult:
        if tool_call.name == "get_traceability":
            return ToolResult(
                name="get_traceability",
                output={"source": "Requirement-001", "targets": ["Design-001", "Design-002"]},
            )
        if tool_call.name == "search_artifacts":
            return ToolResult(
                name="search_artifacts",
                output=[
                    {"id": "Artifact-001", "name": "Brake System"},
                    {"id": "Artifact-002", "name": "Control Module"},
                ],
            )
        if tool_call.name == "get_statistics":
            return ToolResult(
                name="get_statistics",
                output={"nodes": 1500, "relationships": 3200},
            )
        return ToolResult(name=tool_call.name, output="Mock response")


def test_planner_produces_plan():
    """Planning pattern: verify keyword planner emits a plan."""
    planner = KeywordPlanner()

    plan = planner.plan("Show me traceability from requirements to design")

    assert plan.goal == "Show me traceability from requirements to design"
    assert len(plan.steps) >= 1
    assert plan.steps[0].tool_call is not None
    assert plan.steps[0].tool_call.name == "get_traceability"


def test_planner_routes_by_keyword():
    """Planning pattern: verify keyword routing works."""
    planner = KeywordPlanner()

    impact_plan = planner.plan("What is the change impact for Node-123?")
    assert impact_plan.steps[0].tool_call.name == "search_artifacts"

    stats_plan = planner.plan("How many nodes are in the graph?")
    assert stats_plan.steps[0].tool_call.name == "get_statistics"


def test_reflector_detects_errors():
    """Reflection pattern: verify reflector detects tool errors."""
    reflector = SimpleReflector()

    from src.agentic.contracts import Plan, PlanStep, ToolCall

    plan = Plan(
        goal="test",
        steps=(PlanStep(id="s1", description="test", tool_call=ToolCall(name="test_tool", arguments={})),),
    )

    results = [ToolResult(name="test_tool", output="Error: something broke")]

    reflection = reflector.reflect(goal="test", plan=plan, results=results, draft_response="")

    assert reflection["recommendation"] == "retry_with_more_context"
    assert len(reflection["errors"]) > 0


def test_reflector_ok_when_no_errors():
    """Reflection pattern: verify reflector passes when no errors."""
    reflector = SimpleReflector()

    from src.agentic.contracts import Plan, PlanStep, ToolCall

    plan = Plan(
        goal="test",
        steps=(PlanStep(id="s1", description="test", tool_call=ToolCall(name="test_tool", arguments={})),),
    )

    results = [ToolResult(name="test_tool", output={"status": "success"})]

    reflection = reflector.reflect(goal="test", plan=plan, results=results, draft_response="All good")

    assert reflection["recommendation"] == "ok"
    assert len(reflection["errors"]) == 0


def test_orchestrator_runs_end_to_end():
    """Orchestrator-Agent pattern: verify orchestrator sequences plan → tool → reflection."""
    mock_registry = MockToolRegistry()
    planner = KeywordPlanner()
    reflector = SimpleReflector()
    agent = SingleToolAgent(name="test_agent", planner=planner)

    orchestrator = BaselineOrchestrator(
        tool_registry=mock_registry,
        planner=planner,
        reflector=reflector,
        agents=[agent],
        retriever=None,
        max_retries=0,
    )

    response = orchestrator.run("Show me traceability")

    assert response is not None
    assert isinstance(response, str)
    assert len(response) > 0


def test_orchestrator_retries_on_error():
    """Orchestrator-Agent pattern: verify retry logic when reflection suggests retry."""

    class ErrorThenSuccessRegistry(ToolRegistry):
        def __init__(self):
            self.call_count = 0

        def list_tools(self):
            return []

        def call(self, tool_call: ToolCall) -> ToolResult:
            self.call_count += 1
            if self.call_count == 1:
                return ToolResult(name=tool_call.name, output="Error: first attempt failed")
            return ToolResult(name=tool_call.name, output="Success on retry")

    mock_registry = ErrorThenSuccessRegistry()
    planner = KeywordPlanner()
    reflector = SimpleReflector()
    agent = SingleToolAgent(name="test_agent", planner=planner)

    orchestrator = BaselineOrchestrator(
        tool_registry=mock_registry,
        planner=planner,
        reflector=reflector,
        agents=[agent],
        retriever=None,
        max_retries=1,
    )

    response = orchestrator.run("Test retry logic")

    # Verify multiple calls were made (initial + retry)
    assert mock_registry.call_count >= 2
