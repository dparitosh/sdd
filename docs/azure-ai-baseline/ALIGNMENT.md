# Pattern Alignment (Tool Use / RAG / Planning / Reflection / Multi-Agent / Orchestrator)

This repo is standardized to make each agentic design pattern explicit and testable.

## Tool Use Pattern
**Intent:** agents interact with external systems via tools rather than implicit knowledge.

**In-repo mapping:**
- MCP tool boundary: `mcp-server/` exposes Neo4j operations as tools.
- Python tool boundary: `src/agentic/tool_registry.py::InProcessToolRegistry` and adapters.

**Recommended baseline control:**
- Allow-list tools by capability (read-only vs write).
- Record tool calls + durations + inputs (redact secrets) for audit.

## Retrieval-Augmented Generation (RAG) Pattern
**Intent:** ground outputs in enterprise data.

**In-repo mapping:**
- Contract: `src/agentic/contracts.py::Retriever`
- Placeholder: `src/agentic/retrieval.py::AzureAISearchRetriever`

**Recommended baseline control:**
- Keep citations/metadata on RetrievedChunk.
- Enforce data access policies at the retriever boundary.

## Planning Pattern
**Intent:** decompose goal → steps before execution.

**In-repo mapping:**
- Contract: `Planner`
- Reference implementation: rule-based planner (local) or LLM planner (Azure OpenAI).

## Reflection Pattern
**Intent:** review tool outcomes and improve response.

**In-repo mapping:**
- Contract: `Reflector`
- Reference implementation: checks tool errors/coverage and produces follow-up guidance.

## Multi-Agent Collaboration Pattern
**Intent:** multiple specialized agents collaborate.

**In-repo mapping:**
- Existing multi-agent workflow: `src/agents/orchestrator_workflow.py`
- Standard contract boundary: `Agent` workers selected by orchestrator.

## Orchestrator-Agent Pattern
**Intent:** predictable sequencing, retries, compliance.

**In-repo mapping:**
- Contract: `Orchestrator`
- Reference orchestrator implementation lives in `src/agentic/orchestrator.py`.

## Minimal reference flow
1. Orchestrator receives a goal
2. (Optional) retrieve grounding chunks
3. Planner emits steps
4. Orchestrator routes steps to worker agents / tools
5. Reflector reviews and recommends follow-ups
6. Orchestrator returns final response + emits audit events
