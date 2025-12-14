# Azure AI Baseline Alignment (MBSE Neo4j Graph Repo)

This folder documents a vendor-neutral componentization that aligns this repository with an **Azure AI baseline architecture** for agentic systems.

It targets the design patterns typically used for certification-ready deployments:
- **Tool Use** (action via tools, MCP simplifies integration)
- **RAG** (grounding via Azure AI Search or equivalent)
- **Planning** (explicit steps before acting)
- **Reflection** (feedback loop; evaluate outcomes)
- **Multi-Agent Collaboration** (specialized workers)
- **Orchestrator-Agent** (central controller, retries, audit)

## What exists in this repo today
- **Web/API**: FastAPI backend under `src/web/` (REST + GraphQL) and React frontend under `frontend/`.
- **Knowledge graph**: Neo4j Aura (or self-hosted Neo4j).
- **Tool boundary**: `mcp-server/` exposes Neo4j operations via MCP tools.
- **Agent runtime contracts**: `src/agentic/` defines standard contracts (tool registry, retriever, planner, reflector, agent, orchestrator).

## How to use this pack
- Start with **Component Model**: [COMPONENT_MODEL.md](COMPONENT_MODEL.md)
- Review **Pattern Alignment**: [ALIGNMENT.md](ALIGNMENT.md)

If you are deploying to Azure, you can map the contracts to:
- Azure OpenAI (LLM)
- Azure AI Search (RAG)
- Azure Key Vault + Managed Identity (secrets/identity)
- Application Insights / OpenTelemetry (observability)

This documentation intentionally avoids hard dependencies on Azure SDKs so local development remains simple.
