"""Agentic runtime contracts and standard components.

This package defines vendor-neutral interfaces for building Agentic AI systems
aligned with Azure baseline patterns (tool-use, RAG, planning, reflection,
multi-agent collaboration, orchestrator).

It is intentionally lightweight and does not require Azure to run locally.
"""

from .contracts import (
	Agent,
	Orchestrator,
	Plan,
	PlanStep,
	Planner,
	Reflector,
	RetrievedChunk,
	Retriever,
	ToolCall,
	ToolRegistry,
	ToolResult,
	ToolSpec,
)
from .orchestrator import BaselineOrchestrator, SingleToolAgent
from .planning import KeywordPlanner
from .reflection import SimpleReflector
from .retrieval import AzureAISearchRetriever, StaticRetriever
from .tool_registry import InProcessToolRegistry

__all__ = [
	"Agent",
	"Orchestrator",
	"Plan",
	"PlanStep",
	"Planner",
	"Reflector",
	"RetrievedChunk",
	"Retriever",
	"ToolCall",
	"ToolRegistry",
	"ToolResult",
	"ToolSpec",
	"BaselineOrchestrator",
	"SingleToolAgent",
	"KeywordPlanner",
	"SimpleReflector",
	"AzureAISearchRetriever",
	"StaticRetriever",
	"InProcessToolRegistry",
]
