# System Architecture

## Overview

The MBSE Knowledge Graph system uses a **modern decoupled architecture** with separate frontend and backend services.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     User Browser                             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ HTTPS
                         ▼
┌─────────────────────────────────────────────────────────────┐
│           React Frontend (Port 3001)                         │
│  • Modern TypeScript/React Dashboard                         │
│  • ISO AP239/AP242/AP243 Dashboards                         │
│  • Requirements Manager & Parts Explorer                     │
│  • Vite dev server with HMR                                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Proxy: /api/* → localhost:5000
                         ▼
┌─────────────────────────────────────────────────────────────┐
│          FastAPI REST API (Port 5000)                        │
│  • REST API endpoints (/api/*)                               │
│  • Neo4j database integration                                │
│  • Authentication & Authorization                            │
│  • Root (/) redirects to frontend                            │
│  • OpenAPI/Swagger docs at /api/docs                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ neo4j+s://
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Neo4j Aura Database                             │
│  • 3,275+ nodes (AP239/AP242/AP243)                         │
│  • 10+ cross-level relationship types                        │
│  • ISO 10303 SMRL compliant schema                           │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Frontend (Port 3001)
**Location:** `/workspaces/mbse-neo4j-graph-rep/frontend/`

**Technology Stack:**
- React 18 + TypeScript
- Vite (build tool with HMR)
- TanStack Query (data fetching)
- Tailwind CSS + shadcn/ui
- React Router (navigation)

**Key Routes:**
- `/dashboard` - Main system overview with periodic table visualization
- `/ap239/requirements` - AP239 Requirements Dashboard
- `/ap242/parts` - AP242 Parts & Materials Explorer
- `/search` - Advanced search interface
- `/query-editor` - Cypher query editor
- `/traceability` - Cross-schema traceability matrix

**How to Start:**
```bash
cd frontend
npm install
npm run dev
```

**Environment:**
- `VITE_PORT=3001` - Frontend port
- `API_BASE_URL=http://127.0.0.1:5000` - Backend API URL

### 2. Backend (Port 5000)
**Location:** `/workspaces/mbse-neo4j-graph-rep/src/web/`

**Technology Stack:**
- **FastAPI** (async Python web framework) ✅ **100% Migration Complete**
- Neo4j Python Driver
- Pydantic (request/response validation)
- Uvicorn (ASGI server)
- **15/15 routes converted** from Flask to FastAPI

**Key Endpoints:**
- `GET /` - **Redirects to frontend dashboard**
- `GET /info` - API information and architecture overview
- `GET /api/health` - Health check with database connectivity
- `GET /api/stats` - Graph statistics
- `GET /api/ap239/*` - ISO 10303-239 PLCS endpoints
- `GET /api/ap242/*` - ISO 10303-242 CAD endpoints
- `GET /api/ap243/*` - ISO 10303-243 Reference data endpoints
- `GET /api/hierarchy/*` - Cross-schema navigation & traceability

**How to Start:**
```bash
cd /workspaces/mbse-neo4j-graph-rep
export PYTHONPATH=/workspaces/mbse-neo4j-graph-rep
python -m uvicorn src.web.app_fastapi:app --host 0.0.0.0 --port 5000 --reload
# OR use the startup script
./start_backend.sh
```

**Environment:**
- `NEO4J_URI=neo4j+s://...` - Neo4j Aura connection string
- `NEO4J_USER=neo4j` - Database username
- `NEO4J_PASSWORD=...` - Database password
- `FRONTEND_URL=https://...` - Frontend URL for redirects

### 3. Database (Neo4j Aura)
**Connection:** `neo4j+s://2cccd05b.databases.neo4j.io`

**Schema:**
- **AP239 Nodes:** Requirements, Specifications, Approvals, Changes, Versions
- **AP242 Nodes:** Parts, Materials, Properties, Geometries, Assemblies
- **AP243 Nodes:** Units, ValueTypes, OntologyClasses, Classifications
- **Cross-Level:** Traceability links connecting AP239 ↔ AP242 ↔ AP243

## Unified Access

### Production Setup

**User Access:**
1. Visit frontend URL: `https://vigilant-space-goldfish-5x6rp4rvpxg244wj-3001.app.github.dev/dashboard`
2. All UI interactions happen in React frontend
3. API calls are automatically proxied to backend (port 5000)

**Developer Access:**
- Frontend Dev: Port 3001
- Backend API: Port 5000
- Database: Neo4j Aura (cloud)

### Why This Architecture?

**Benefits:**
1. **Separation of Concerns:** UI logic separate from business logic
2. **Modern Development:** HMR for instant frontend updates
3. **Scalability:** Frontend and backend can scale independently
4. **API-First:** Backend serves as reusable REST API
5. **Better UX:** React provides responsive, interactive dashboards

**Previous Setup (Deprecated):**
- Flask served HTML template at `/` (3000+ lines of embedded JS)
- Mixing backend rendering with frontend logic
- Difficult to maintain and extend

**Current Setup (Dec 2025):**
- **FastAPI** with async support and automatic OpenAPI docs
- All 15 routes migrated from Flask to FastAPI
- FastAPI redirects `/` to React frontend
- Clean REST API under `/api/*`
- Modern React dashboards with TypeScript
- Comprehensive Pydantic models for type safety
- Interactive API docs at `/api/docs`

## Key Features

### ISO 10303 Application Protocol Support

**AP239 - Product Life Cycle Support**
- Requirements management with versions
- Change control and approval workflows
- Specifications and analysis
- Full traceability chains

**AP242 - 3D Managed Product Data**
- Parts catalog with BOMs
- Materials library with properties
- CAD geometry references
- Assembly structures

**AP243 - Reference Data**
- Units and measurements
- Classification ontologies
- Cross-schema linking
- Standardized value types

### Cross-Schema Navigation

The system provides **traceability matrix** functionality:
- Requirement → Part mapping
- Part → Material → Unit relationships
- Change → Approval → Version history
- Full graph traversal capabilities

## Development Workflow

### Starting Both Services

```bash
# Terminal 1: Start Backend
cd /workspaces/mbse-neo4j-graph-rep
export PYTHONPATH=$(pwd)
python3 src/web/app.py

# Terminal 2: Start Frontend
cd frontend
npm run dev
```

### Testing the Integration

```bash
# Test backend health
curl http://localhost:5000/api/health

# Test redirect
curl -I http://localhost:5000/

# Test AP239 endpoint
curl http://localhost:5000/api/ap239/requirements

# Test info endpoint
curl http://localhost:5000/info | jq
```

### Making Changes

**Frontend Changes:**
1. Edit files in `frontend/src/`
2. Vite HMR instantly reflects changes
3. No restart needed

**Backend Changes:**
1. Edit files in `src/web/routes/`
2. Uvicorn auto-reloads (with `--reload` flag)
3. Changes reflected immediately
4. Visit `/api/docs` to see updated OpenAPI documentation

## URLs Reference

| Service | Development URL | Production URL |
|---------|----------------|----------------|
| Frontend | http://localhost:3001 | https://vigilant-space-goldfish-5x6rp4rvpxg244wj-3001.app.github.dev |
| Backend | http://localhost:5000 | https://vigilant-space-goldfish-5x6rp4rvpxg244wj-5000.app.github.dev |
| Database | neo4j+s://2cccd05b.databases.neo4j.io | (same) |

## Recent Achievements

## Azure AI Baseline Alignment

For a standardized component model and an Azure-aligned “agentic system” decomposition (tool-use, RAG, planning, reflection, multi-agent, orchestrator), see:
- [docs/azure-ai-baseline/README.md](docs/azure-ai-baseline/README.md) - Overview and pattern catalog
- [docs/azure-ai-baseline/ALIGNMENT.md](docs/azure-ai-baseline/ALIGNMENT.md) - Design pattern alignment
- [docs/azure-ai-baseline/COMPONENT_MODEL.md](docs/azure-ai-baseline/COMPONENT_MODEL.md) - Component boundaries and Azure mapping
- [docs/azure-ai-baseline/OBSERVABILITY.md](docs/azure-ai-baseline/OBSERVABILITY.md) - Instrumentation guidance
- [docs/azure-ai-baseline/DEPLOYMENT_REFERENCE.md](docs/azure-ai-baseline/DEPLOYMENT_REFERENCE.md) - Deployment checklist

**Implemented Agentic Patterns** (vendor-neutral, Azure-compatible):
- ✅ **Tool Use**: `src/agentic/tool_registry.py`, `src/agentic/adapters.py` (exposes MBSETools + MCP tools)
- ✅ **Planning**: `src/agentic/planning.py` (KeywordPlanner, extensible to LLM planner)
- ✅ **Reflection**: `src/agentic/reflection.py` (SimpleReflector for post-tool outcome review)
- ✅ **Orchestrator-Agent**: `src/agentic/orchestrator.py` (BaselineOrchestrator coordinates plan → tools → reflect)
- ✅ **Multi-Agent Collaboration**: `src/agents/orchestrator_workflow.py` (LangGraph workflow + baseline orchestrator integration)
- ✅ **RAG Boundary**: `src/agentic/retrieval.py` (StaticRetriever + AzureAISearchRetriever placeholder)

**Verification**: Integration tests in `tests/test_baseline_orchestrator.py` (6/6 passing).

1. ✅ **Backend redirects to frontend** - Eliminates duplicate UI
2. ✅ **REST APIs working** - 15/15 routes functional
3. ✅ **React dashboards implemented** - AP239/AP242/AP243 views ready
4. ✅ **FastAPI migration complete** - 100% converted from Flask (Dec 2025)
5. ✅ **API documentation** - Interactive OpenAPI docs at `/api/docs`
6. ✅ **Type safety** - 63 Pydantic models across all routes
7. ✅ **Azure AI baseline alignment** - Standardized agentic runtime (Dec 14, 2025)

## Next Steps

1. 🔄 **Frontend testing** - Verify all dashboards load real data
2. 📋 **Performance optimization** - Add caching, optimize queries
3. 🔒 **Security hardening** - JWT authentication, rate limiting
4. 📦 **Production deployment** - Docker, Kubernetes, CI/CD

## Support

For issues or questions:
- Backend issues: Check `/api/health` and server logs
- Frontend issues: Check browser console and network tab
- Database issues: Verify Neo4j Aura connectivity
- Architecture questions: See `/info` endpoint
