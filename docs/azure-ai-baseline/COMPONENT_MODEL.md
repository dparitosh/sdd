# Component Model (Azure AI Baseline)

This document defines the component boundaries for an Azure-aligned agentic architecture.

## High-level components

### Experience layer
- **React UI** (`frontend/`)
  - Calls API endpoints (REST/GraphQL) and renders dashboards + graph explorer.

### API & application layer
- **FastAPI backend** (`src/web/`)
  - Authoritative API boundary.
  - Responsible for authn/authz, rate limiting, request validation, and audit logging.

### Data layer
- **Neo4j** (Aura or self-hosted)
  - System-of-record for MBSE graph data.

### Agent layer (agentic runtime)
- **Orchestrator** (contract: `src/agentic/contracts.py::Orchestrator`)
  - Owns sequencing, retries, error handling, and audit.
- **Worker agents** (contract: `Agent`)
  - Specialized: MBSE analysis, PLM impact, simulation validation, compliance.
- **Tool registry** (contract: `ToolRegistry`)
  - Provides a stable interface to tools.
  - Can be backed by:
    - In-process tools (Python adapters)
    - MCP tools (`mcp-server/`) for standardized tool I/O
- **Retriever** (contract: `Retriever`)
  - RAG boundary, typically Azure AI Search in Azure.
- **Planner / Reflector** (contracts: `Planner`, `Reflector`)
  - Explicit planning and reflection loops.

## Azure mapping (reference)

| Baseline need | Azure service | Repo interface |
|---|---|---|
| LLM inference | Azure OpenAI | Planner/Agent internal LLM client (implementation-specific) |
| Retrieval | Azure AI Search | `Retriever` (e.g., `AzureAISearchRetriever`) |
| Tools | Functions, APIs, databases | `ToolRegistry` / MCP tools |
| Secrets | Key Vault | env + deployment wiring |
| Identity | Managed Identity | deployment wiring |
| Observability | Application Insights / OTel | middleware + instrumentation |

## Certification-minded controls (where they live)
- **Identity**: enforce API key/JWT at FastAPI boundary.
- **Secrets**: Key Vault / Managed Identity (no secrets in code).
- **Audit**: orchestrator emits structured events for tool calls + outcomes.
- **Safety**: tool allow-lists + read-only modes for Neo4j write operations.
