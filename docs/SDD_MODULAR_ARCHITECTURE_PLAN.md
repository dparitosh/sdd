# Comprehensive Modular Architecture & FaaS Realignment Plan (v4.0)

**Date:** February 25, 2026
**Status:** ACTIVE — Supersedes ALL previous trackers, sprint docs, and plan versions
**Methodology:** Full codebase audit → Gap analysis → FaaS + FSD architecture mapping

---

## Executive Summary

This plan is the product of a **line-by-line audit** of the entire MBSEsmrl codebase:
- **27 backend FastAPI routers** exposing **~162 endpoints**
- **17 backend services** (Neo4j, OSLC, SHACL, SMRL, Simulation, Export, etc.)
- **29 frontend pages**, **5 frontend service modules**, **25+ UI primitives**
- **7 backend infrastructure subsystems** (Engine, Graph, Models, Parsers, Integrations, Web Services, Container)
- **1 reference SDD app** with **10 business workflows** and **15 identified feature gaps**

Every component is mapped below. Nothing is omitted.

---

## PART 1: CURRENT STATE — What Exists Today

### 1.1 Backend Routers — Complete Inventory (27 routers, ~162 endpoints)

| # | Router File | Prefix | Tag | Endpoints | Domain |
|---|---|---|---|---|---|
| 1 | `admin_fastapi.py` | `/api/admin` | Admin | 1 | DB management |
| 2 | `agents_fastapi.py` | `/api/agents` | AI Agents & Orchestration | 1 | AI orchestrator |
| 3 | `ap239_fastapi.py` | `/api/ap239` | AP239 - Requirements | 8 | Requirements, analyses, approvals, documents |
| 4 | `ap242_fastapi.py` | `/api/ap242` | AP242 - CAD Integration | 8 | Parts, assemblies, materials, geometry |
| 5 | `ap243_fastapi.py` | `/api/ap243` | AP243 - Product Structure | 12 | Domain classes, packages, ontologies, units, value types |
| 6 | `auth_fastapi.py` | `/api/auth` | Authentication | 5 | Login, refresh, logout, verify, change-password |
| 7 | `cache_fastapi.py` | `/api/cache` | Cache Management | 6 | Stats, clear, invalidate, config, health |
| 8 | `core_fastapi.py` | `/api` | Core | 10 | Packages, classes, search, artifacts, stats, cypher |
| 9 | `export_fastapi.py` | `/api/export` | Data Export | 8 | Schema, GraphML, JSON-LD, CSV, STEP, PlantUML, **RDF**, Cytoscape |
| 10 | `express_parser_fastapi.py` | `/api/express` | EXPRESS Parser | 18 | Parse, query, analyze, export EXPRESS schemas |
| 11 | `graph_fastapi.py` | `/api/graph` | Graph | 3 | Graph data, node types, relationship types |
| 12 | `graphql_fastapi.py` | `/api/graphql` | GraphQL | 2 | Strawberry GraphQL (statistics, cypher_read) |
| 13 | `hierarchy_fastapi.py` | `/api/hierarchy` | Hierarchy & Traceability | 5 | Traceability matrix, navigation, search, impact |
| 14 | `metrics_fastapi.py` | `/api/metrics` | Metrics | 3 | Summary, history, health |
| 15 | `ontology_ingest_fastapi.py` | `/api/ontology` | **Ontology Ingestion** | 1 | **OWL/RDF → Neo4j ingestion** |
| 16 | `oslc_fastapi.py` | `/oslc` | **OSLC Semantic Web** | 6 | **Root services, catalog, service provider, RDF/XML, Turtle, requirement CRUD** |
| 17 | `oslc_client_fastapi.py` | `/api/oslc/client` | **OSLC Client** | 2 | **Connect & discover, execute OSLC query** |
| 18 | `plm_connectors_fastapi.py` | `/api/v1/plm` | PLM | 3 | Connectors list, sync trigger, status |
| 19 | `plm_fastapi.py` | `/api/plm` | PLM Integration | 5 | Traceability, composition, impact, parameters, constraints |
| 20 | `sessions_fastapi.py` | `/api/sessions` | Session Management | 7 | User sessions, admin session management |
| 21 | `shacl_fastapi.py` | `/api/validate` | **SHACL Validation** | 2 | **Validate RDF against SHACL shapes (AP239, AP242)** |
| 22 | `simulation_fastapi.py` | `/api/simulation` | Simulation Integration | 16 | Parameters, models, results, dossiers CRUD, artifacts, runs CRUD, MoSSEC trace |
| 23 | `smrl_v1_fastapi.py` | `/api/v1` | **SMRL v1 - ISO 10303-4443** | 17 | **Generic CRUD for any SMRL resource type, health, traceability, versioning, diff, match** |
| 24 | `step_ingest_fastapi.py` | `/api/step` | **STEP Ingestion** | 1 | **ISO 10303 Part 21 / Part 28 file ingestion** |
| 25 | `trs_fastapi.py` | `/api/oslc/trs` | **OSLC Tracked Resource Set** | 3 | **TRS base, changelog (RDF change feed)** |
| 26 | `upload_fastapi.py` | `/api/upload` | File Upload | 5 | Upload (XMI, XML, CSV, JSON, STEP), job status, job list |
| 27 | `version_fastapi.py` | `/api/version` | Version Control | 4 | Node versions, diff, history, checkpoint |

### 1.2 Backend Services — Complete Inventory (17 services)

| # | Service | Key Classes | Purpose |
|---|---|---|---|
| 1 | `neo4j_service.py` | `Neo4jService` | **Central DB service**: connection pooling (50 max), Redis caching, CRUD, search, statistics |
| 2 | `simulation_service.py` | `SimulationService` | Dossier CRUD, artifact queries, MoSSEC trace chains (depth 7), run CRUD |
| 3 | `oslc_service.py` | `OSLCService` | **OSLC RDF generation** via `rdflib`: root services, catalogs, providers (RDF/XML, Turtle, JSON-LD) |
| 4 | `oslc_client.py` | `OSLCClient` | **OSLC consumer**: connects to external OSLC servers, discovers services, executes queries |
| 5 | `oslc_trs_service.py` | `TRSService` | **Tracked Resource Set**: generates TRS base + changelog (RDF change feed) |
| 6 | `ontology_ingest_service.py` | `OntologyIngestService` | **OWL/RDF → Neo4j**: parses with `rdflib`, creates ExternalOwlClass, ExternalUnit (QUDT/OM), ValueType, Classification (SKOS) |
| 7 | `shacl_validator.py` | `SHACLValidator` | **SHACL validation**: uses `pyshacl` against AP239/AP242 TTL shape files with RDFS inference |
| 8 | `smrl_adapter.py` | `SMRLAdapter` | Converts Neo4j nodes → ISO 10303-4443 SMRL format (30+ type mappings, strict/simplified modes) |
| 9 | `smrl_validator.py` | `SMRLSchemaValidator` | JSON Schema validation against `DomainModel.json` for ISO 10303-4443 compliance |
| 10 | `export_service.py` | `ExportService` | Multi-format export: JSON, CSV, XML, GraphML, **RDF/Turtle**, PlantUML, Cytoscape JSON |
| 11 | `cache_service.py` | `CacheService` | In-memory + Redis cache with TTL and pattern invalidation |
| 12 | `query_cache.py` | `QueryCache` | Specialized Cypher query result caching |
| 13 | `redis_service.py` | `RedisService` | Redis connection management |
| 14 | `step_ingest_service.py` | `StepIngestService` | STEP Part 21/28 file parsing and Neo4j ingestion |
| 15 | `upload_job_store.py` | `UploadJobStore` | Async file upload job tracking |
| 16 | `job_store.py` | `JobStore` | General background job management |
| 17 | `session_manager.py` | `SessionManager` | User session lifecycle management |

### 1.3 Backend Infrastructure — 7 Subsystems

| Subsystem | Key Files | Purpose |
|---|---|---|
| **Engine** | `protocol.py`, `registry.py`, `pipeline.py`, `ingesters/xmi_ingester.py`, `ingesters/oslc_ingester.py` | Modular ingestion pipeline with `GraphStore` protocol (supports Neo4j, Spark, Memgraph, Neptune) |
| **Stores** | `neo4j_store.py`, `spark_store.py` | `GraphStore` implementations for Neo4j (direct) and Spark (connector) |
| **Graph** | `connection.py`, `builder.py`, `queries.py` | Low-level Neo4j driver, graph building, pre-built Cypher queries |
| **Parsers** | `xmi_parser.py`, `semantic_loader.py` (1321 lines), `apoc_loader.py`, `step_parser.py`, `express_parser.py`, `express/` (Pydantic models + analyzer + converter + exporter) | XMI, STEP, EXPRESS, and Semantic (RDF) parsing |
| **Integrations** | `base_connector.py`, `teamcenter_connector.py`, `windchill_connector.py`, `sap_odata_connector.py` | PLM connectors (Siemens Teamcenter, PTC Windchill, SAP S/4HANA) |
| **Models/Shapes** | `ap239_requirement.ttl`, `ap242_part.ttl` | **SHACL shape files** for RDF validation |
| **Container** | `container.py` | DI container: shared Neo4j driver pool between web services and engine layer |

### 1.4 Frontend Pages — Complete Inventory (29 pages, 26 routed)

| # | Component | Route | API Service Consumed | Domain |
|---|---|---|---|---|
| 1 | `Login` | `/login` | `POST /auth/login` | Auth |
| 2 | `AuthCallback` | `/auth/callback` | `POST /auth/oauth/callback` | Auth |
| 3 | `Dashboard` | `/dashboard` | `POST /graphql` (statistics) | Overview |
| 4 | `AdvancedSearch` | `/search` | `GET /artifacts` | Core |
| 5 | `RestApiExplorer` | `/api-explorer` | Any user-entered URL | System |
| 6 | `QueryEditor` | `/query-editor` | `POST /cypher` | Data Exploration |
| 7 | `RequirementsManager` | `/requirements` | SMRL CRUD: `GET/POST/PUT/DELETE /v1/Requirement` | Systems Engineering |
| 8 | `TraceabilityMatrix` | `/traceability` | `GET /v1/Requirement`, `POST /ap239/requirements/traceability/bulk` | Systems Engineering |
| 9 | `PLMIntegration` | `/plm` | `GET /v1/plm/connectors`, `POST /v1/plm/connectors/:id/sync` | PLM |
| 10 | `SystemMonitoring` | `/monitoring` | `GET /metrics/health`, `GET /metrics/summary`, `GET /metrics/history` | System |
| 11 | `RequirementsDashboard` | `/ap239/requirements` | 5 AP239 endpoints + hierarchy + SMRL CRUD | AP239 |
| 12 | `MossecDashboard` | `/mossec-dashboard` | 9 AP243 endpoints | AP243 |
| 13 | `PartsExplorer` | `/ap242/parts` | 6 AP242 endpoints | AP242 |
| 14 | `GraphBrowser` | `/graph` | `GET /graph/node-types`, `GET /graph/data` | Graph |
| 15 | `DataImport` | `/import` | `POST /upload/`, `GET /upload/status/:id`, `GET /upload/jobs` | Data Management |
| 16 | `AIInsights` | `/ai/insights` | **None (placeholder)** | AI |
| 17 | `SmartAnalysis` | `/ai/analysis` | **None (placeholder)** | AI |
| 18 | `ModelChat` | `/ai/chat` | `POST /agents/orchestrator/run` | AI |
| 19 | `ModelRepository` | `/simulation/models` | `GET /simulation/models`, `GET /simulation/parameters` | Simulation |
| 20 | `WorkflowStudio` | `/simulation/workflows` | `GET /simulation/parameters`, `POST /simulation/validate`, `POST /agents/orchestrator/run` | Simulation |
| 21 | `ResultsAnalysis` | `/simulation/results` | `GET /simulation/results`, `GET /oslc/trs/changelog` | Simulation |
| 22 | `DossierList` | `/simulation/dossiers` | `GET /simulation/dossiers`, `GET /simulation/statistics` | SDD |
| 23 | `DossierDetail` | `/simulation/dossiers/:id` | `GET /simulation/dossiers/:id` | SDD |
| 24 | `SimulationRuns` | `/simulation/runs` | `GET /simulation/runs` | Simulation |
| 25-29 | `AP239Graph`, `AP242Graph`, `AP243Graph`, `OntologyGraph`, `OSLCGraph` | **(Not routed)** | Delegate to `GraphBrowser` with different props | Graph wrappers |

### 1.5 Frontend Services — Complete Inventory (5 modules)

| Service File | Methods | Endpoints Called |
|---|---|---|
| `api.ts` (525 lines) | **`apiService`** mega-object: `graph.*`, `smrl.*`, `requirements.*`, `ap239.*`, `ap242.*`, `ap243.*`, `hierarchy.*`, `plm.*`, `agents.*`, `trs.*`, `oslcClient.*`, `upload.*`, `query.*`, `simulation.*` | ~60 distinct API calls |
| `graphql.ts` | `graphqlService.getStatistics()` | `POST /graphql` |
| `metrics.ts` | `getMetricsSummary()`, `getMetricsHistory()`, `getHealthCheck()` | 3 metrics endpoints |
| `plm.ts` | `getConnectors()`, `triggerSync()`, `getConnectorStatus()` | 3 PLM endpoints |
| `websocket.ts` | `WebSocketService` class | Socket.IO: graph_update, node/relationship CRUD events |

### 1.6 ServiceContainer (DI) — Critical Architecture

The `ServiceContainer` in `container.py` is a thread-safe singleton that manages the lifecycle of all services. **Crucially**, it ensures the Neo4j driver pool is shared between the web layer (`Neo4jService`) and the engine layer (`Neo4jGraphStore`):

```
ServiceContainer.startup()
  ├── Neo4j driver (50 max connections, 30s acquisition timeout)
  │   ├── Neo4jService (web) ── used by all 27 routers
  │   └── Neo4jGraphStore (engine) ── used by ingestion pipeline
  ├── startup_async()
  │   ├── RedisService
  │   ├── SessionManager
  │   └── QueryCache
  └── shutdown()
      └── Closes Neo4j pool + Redis connections
```

**FaaS implication**: In a serverless context, cold starts must initialize this shared pool. The `core/database.py` extraction (Phase 1) must preserve this shared-pool architecture.

---

## PART 2: THE GAP — What the Reference SDD App Has That We Don't

The `sdd---simulation-data-dossier` reference app contains **15 critical features** missing from `mbsesmrl`:

| # | Gap | Severity | Description |
|---|---|---|---|
| **G1** | Role-Based UI Switching | HIGH | Dual persona (Sim Engineer vs Quality Head) with different sidebars, dashboards, actions. Main app shows same UI to everyone. |
| **G2** | Compliance Audit Engine | HIGH | Automated `runAudit()` checking artifact completeness, integrity (checksums), traceability → health score + categorized findings. **Completely absent.** |
| **G3** | MOSSEC Link Inspector | HIGH | Side panel with source→relation→target visualization, semantic descriptions, artifact drill-through. Main app has flat table only. |
| **G4** | Artifact Preview Modal | MEDIUM | SHA-256 checksum display, authenticated download, signature chain viewer. **Absent.** |
| **G5** | Decision History / Audit Trail | HIGH | `DecisionLog[]` with reviewer, timestamp, comment, signatureId. **No data model or UI.** |
| **G6** | Quality Head Review & Certify | HIGH | Approve/reject panel with comments, feeding decision log. **No approval workflow.** |
| **G7** | Context-Aware AI Chatbot | LOW | Floating Gemini-powered assistant with dossier/compliance context. Main app has `ModelChat` (different purpose). |
| **G8** | Simulation Terminal | MEDIUM | Interactive solver execution with progress bar, log stream, ISO compliance messaging. Main app has list view only. |
| **G9** | Evidence Category Pipeline | HIGH | 8-category evidence pipeline (A1→H1) with status tracking per dossier. **Absent.** |
| **G10** | Product Specification Page | LOW | Motor parameters, constraints, system assets reference page. **Absent.** |
| **G11** | KPI Trend Charts | MEDIUM | Per-dossier bar + line charts showing convergence across iterations. Main dashboard has summary stats only. |
| **G12** | Certification Analytics | MEDIUM | Quality Head pie/bar charts for dossier health, weekly throughput, priority queue. **Absent.** |
| **G13** | `MOSSECLink` typed model | MEDIUM | 9 entity types, 8 relation types in TypeScript. Main app uses untyped API data. |
| **G14** | `AuditFinding` typed model | HIGH | Compliance/Integrity/Traceability categories with severity levels. **No equivalent type.** |
| **G15** | Dossier Create workflow | LOW | "Create New Dossier" button. Main app has no create action in UI. |

---

## PART 3: THE TARGET STATE — FaaS + FSD Architecture

### 3.1 Frontend: Feature-Sliced Design (FSD)

All 29 existing pages + 15 new features from the reference app are organized into strictly bounded feature modules. The `apps/` layer composes features into role-based entry points.

```
frontend/src/
├── apps/                          # Composition layer — imports from features/
│   ├── engineer/                  # SimulationEngineer persona
│   │   ├── routes.tsx             # Composes: sdd, simulation, systems-eng, graph, ai
│   │   └── layout.tsx             # Engineer sidebar, header, notifications
│   ├── quality/                   # QualityHead persona
│   │   ├── routes.tsx             # Composes: sdd (audit/approval), telemetry, compliance
│   │   └── layout.tsx             # Quality sidebar, approval queue badge
│   └── admin/                     # SystemAdmin persona
│       ├── routes.tsx             # Composes: system-mgmt, semantic-web, data-import
│       └── layout.tsx             # Admin sidebar
│
├── features/                      # Self-contained business domains
│   ├── auth/                      # LOGIN + OAUTH
│   │   ├── components/            # LoginForm, AuthCallback, RoleSelector (NEW)
│   │   ├── hooks/                 # useAuth, useRole
│   │   └── types.ts               # UserRole enum (NEW from ref app)
│   │
│   ├── sdd/                       # SIMULATION DATA DOSSIER + COMPLIANCE
│   │   ├── components/
│   │   │   ├── DossierList.jsx    # (migrated from pages/)
│   │   │   ├── DossierDetail.jsx  # (migrated + upgraded with AuditPanel, ReviewPanel)
│   │   │   ├── AuditPanel.tsx     # (NEW) Compliance audit engine UI [G2]
│   │   │   ├── ReviewPanel.tsx    # (NEW) Quality Head approve/reject workflow [G6]
│   │   │   ├── ArtifactPreview.tsx # (NEW) SHA-256 viewer, signature chain [G4]
│   │   │   ├── EvidencePipeline.tsx # (NEW) 8-category evidence tracker [G9]
│   │   │   └── MossecInspector.tsx # (NEW) Link inspector side panel [G3]
│   │   ├── hooks/
│   │   │   ├── useDossierAudit.ts # (NEW) Calls audit_service
│   │   │   └── useApproval.ts     # (NEW) Calls approval_service
│   │   └── types.ts               # Dossier, Artifact, AuditFinding [G14], DecisionLog [G5],
│   │                              # MOSSECLink [G13], CredibilityLevel
│   │
│   ├── simulation/                # EXECUTION & MODELS
│   │   ├── components/
│   │   │   ├── SimulationRuns.jsx   # (migrated)
│   │   │   ├── ModelRepository.jsx  # (migrated)
│   │   │   ├── ResultsAnalysis.jsx  # (migrated)
│   │   │   ├── WorkflowStudio.jsx   # (migrated)
│   │   │   └── SimulationWorkspace.tsx # (NEW) Interactive terminal [G8]
│   │   ├── hooks/
│   │   │   └── useSimRunner.ts      # (NEW) Calls workspace_service, polls status
│   │   └── types.ts
│   │
│   ├── systems-engineering/       # AP239 REQUIREMENTS + AP242 PARTS + TRACEABILITY
│   │   ├── components/
│   │   │   ├── RequirementsManager.jsx   # (migrated)
│   │   │   ├── RequirementsDashboard.jsx # (migrated)
│   │   │   ├── TraceabilityMatrix.jsx    # (migrated + MossecInspector integration)
│   │   │   ├── PartsExplorer.jsx         # (migrated)
│   │   │   └── ProductSpecs.tsx          # (NEW) Motor params, constraints [G10]
│   │   └── hooks/
│   │       └── useTraceability.ts
│   │
│   ├── graph-explorer/            # GRAPH VISUALIZATION + ONTOLOGY
│   │   ├── components/
│   │   │   ├── GraphBrowser.jsx    # (migrated — 1128 lines, force-directed 2D)
│   │   │   ├── AP239Graph.jsx      # (migrated wrapper)
│   │   │   ├── AP242Graph.jsx      # (migrated wrapper)
│   │   │   ├── AP243Graph.jsx      # (migrated wrapper)
│   │   │   ├── OntologyGraph.jsx   # (migrated wrapper)
│   │   │   └── OSLCGraph.jsx       # (migrated wrapper)
│   │   └── hooks/
│   │       └── useGraphData.ts
│   │
│   ├── semantic-web/              # OSLC + RDF + OWL + SHACL + GRAPHQL + EXPRESS
│   │   ├── components/
│   │   │   ├── OntologyManager.tsx   # (NEW) Browse/ingest OWL ontologies
│   │   │   ├── OSLCBrowser.tsx       # (NEW) Browse OSLC root services, catalogs, providers
│   │   │   ├── SHACLValidator.tsx    # (NEW) UI for /api/validate/shacl
│   │   │   ├── GraphQLPlayground.tsx # (NEW) UI for /api/graphql (Strawberry)
│   │   │   ├── TRSFeed.tsx          # (NEW) Visualize TRS changelog
│   │   │   ├── ExpressExplorer.tsx   # (NEW) Parse/analyze EXPRESS schemas
│   │   │   └── RDFExporter.tsx       # (NEW) UI for /api/export/rdf and /api/export/jsonld
│   │   └── hooks/
│   │       ├── useOSLC.ts           # Calls oslc_service + trs_service
│   │       ├── useOntology.ts       # Calls ontology_service
│   │       └── useSHACL.ts          # Calls validation_service
│   │
│   ├── ai-studio/                 # AI AGENTS + CHAT + ANALYSIS
│   │   ├── components/
│   │   │   ├── ModelChat.jsx       # (migrated)
│   │   │   ├── AIInsights.jsx      # (migrated placeholder → upgrade to real)
│   │   │   ├── SmartAnalysis.jsx   # (migrated placeholder → upgrade to real)
│   │   │   └── Chatbot.tsx         # (NEW) Floating context-aware AI assistant [G7]
│   │   └── hooks/
│   │       └── useAgent.ts
│   │
│   ├── telemetry/                 # DASHBOARDS & ANALYTICS
│   │   ├── components/
│   │   │   ├── Dashboard.jsx           # (migrated)
│   │   │   ├── MossecDashboard.jsx     # (migrated)
│   │   │   ├── DashboardEngineer.tsx   # (NEW) KPI bar/line charts [G11]
│   │   │   ├── QualityDashboard.tsx    # (NEW) Approval queue, certification [G12]
│   │   │   └── SystemMonitoring.jsx    # (migrated)
│   │   └── hooks/
│   │       └── useMetrics.ts
│   │
│   └── system-management/         # IMPORT + PLM + ADMIN + EXPORT + VERSION
│       ├── components/
│       │   ├── DataImport.jsx        # (migrated)
│       │   ├── PLMIntegration.jsx    # (migrated)
│       │   ├── RestApiExplorer.jsx   # (migrated)
│       │   ├── QueryEditor.jsx       # (migrated)
│       │   ├── AdvancedSearch.jsx     # (migrated)
│       │   └── StepImporter.tsx      # (NEW) UI for /api/step/ingest
│       └── hooks/
│           └── useUpload.ts
│
├── services/                      # Thin API clients (one per FaaS function)
│   ├── api.ts                     # Base Axios client (auth interceptors, error handling)
│   ├── sdd.service.ts             # Dossier CRUD → sdd_service
│   ├── audit.service.ts           # Audit engine → audit_service
│   ├── approval.service.ts        # Approval workflow → approval_service
│   ├── simulation.service.ts      # Models, runs, workspace → simulation_service + workspace_service
│   ├── standards.service.ts       # AP239, AP242, AP243, SMRL → standards_service
│   ├── oslc.service.ts            # OSLC provider, client, TRS → oslc_service
│   ├── ontology.service.ts        # OWL/RDF ingestion → ontology_service
│   ├── validation.service.ts      # SHACL validation → validation_service
│   ├── graph.service.ts           # Graph data, GraphQL → graph_service
│   ├── export.service.ts          # All export formats → export_service
│   ├── express.service.ts         # EXPRESS parser → express_service
│   ├── plm.service.ts             # PLM connectors → plm_service
│   ├── metrics.service.ts         # System metrics → telemetry_service
│   ├── auth.service.ts            # Auth + sessions → auth_service
│   ├── graphql.service.ts         # (existing) Strawberry GQL
│   └── websocket.service.ts       # (existing) Socket.IO
│
└── components/                    # Shared UI primitives (existing 25+ shadcn/ui + layout)
    ├── auth/
    ├── layout/
    └── ui/
```

### 3.2 How Features Are Composed Into SDD Apps

The `apps/` layer is where all features (including OSLC, Semantic Web, GraphQL, RDF, OWL, EXPRESS, SHACL) get assembled into complete role-based applications:

#### `apps/engineer/routes.tsx` (Simulation Engineer)
```tsx
// Composition imports from 6+ different feature domains
import { DossierList, DossierDetail, EvidencePipeline } from '@/features/sdd'
import { SimulationWorkspace, ModelRepository, SimulationRuns, ResultsAnalysis, WorkflowStudio } from '@/features/simulation'
import { RequirementsManager, TraceabilityMatrix, PartsExplorer, ProductSpecs } from '@/features/systems-engineering'
import { GraphBrowser, AP239Graph, AP242Graph, AP243Graph, OntologyGraph, OSLCGraph } from '@/features/graph-explorer'
import { OntologyManager, SHACLValidator, ExpressExplorer, TRSFeed, RDFExporter } from '@/features/semantic-web'
import { ModelChat, Chatbot } from '@/features/ai-studio'
import { DashboardEngineer, MossecDashboard } from '@/features/telemetry'
import { DataImport, PLMIntegration } from '@/features/system-management'

// Sidebar Groups:
// 1. Dashboard         → DashboardEngineer
// 2. Simulation        → SimulationWorkspace, ModelRepository, SimulationRuns, ResultsAnalysis
// 3. Dossiers          → DossierList, DossierDetail (EvidencePipeline, MossecInspector embedded)
// 4. Systems Eng       → RequirementsManager, TraceabilityMatrix, PartsExplorer, ProductSpecs
// 5. Graph & Ontology  → GraphBrowser, AP239/242/243 graphs, OntologyGraph, OSLCGraph
// 6. Semantic Web      → OntologyManager (OWL), SHACLValidator, ExpressExplorer, TRSFeed, RDFExporter
// 7. AI Studio         → ModelChat, WorkflowStudio
// 8. Data Management   → DataImport, PLMIntegration
// Global: Floating Chatbot
```

#### `apps/quality/routes.tsx` (Quality Head)
```tsx
import { DossierList, DossierDetail, AuditPanel, ReviewPanel } from '@/features/sdd'
import { QualityDashboard } from '@/features/telemetry'
import { TraceabilityMatrix } from '@/features/systems-engineering'
import { SHACLValidator, TRSFeed } from '@/features/semantic-web'
import { Chatbot } from '@/features/ai-studio'

// Sidebar Groups:
// 1. Approval Queue    → DossierList (filtered: Pending Review), DossierDetail (AuditPanel + ReviewPanel)
// 2. Quality Dashboard → QualityDashboard (approval pie chart, certification throughput, priority queue)
// 3. Compliance        → AuditPanel, SHACLValidator (shape validation)
// 4. Traceability      → TraceabilityMatrix (MoSSEC link inspection)
// 5. Change Feed       → TRSFeed (OSLC Tracked Resource Set changelog)
// Global: Floating Chatbot
```

#### `apps/admin/routes.tsx` (System Administrator)
```tsx
import { DataImport, PLMIntegration, RestApiExplorer, QueryEditor, AdvancedSearch, StepImporter } from '@/features/system-management'
import { SystemMonitoring } from '@/features/telemetry'
import { OntologyManager, GraphQLPlayground, ExpressExplorer, OSLCBrowser } from '@/features/semantic-web'
import { GraphBrowser } from '@/features/graph-explorer'

// Sidebar Groups:
// 1. System Health     → SystemMonitoring
// 2. Data Import       → DataImport (XMI, CSV, JSON), StepImporter (STEP files)
// 3. Semantic Tools    → OntologyManager (OWL), GraphQLPlayground, ExpressExplorer, OSLCBrowser
// 4. Graph Explorer    → GraphBrowser, QueryEditor (Cypher)
// 5. API & PLM         → RestApiExplorer, PLMIntegration
// 6. Search            → AdvancedSearch
```

### 3.3 Backend: FaaS (Function-as-a-Service) Architecture

Every existing router and service is mapped to an independent, deployable serverless function. The `core/` layer provides shared infrastructure (Neo4j pooling, Pydantic models, config).

```
backend/src/
├── core/                              # Shared infrastructure (Lambda layer / shared package)
│   ├── database.py                    # Neo4j pooling (from neo4j_service.py + container.py)
│   ├── config.py                      # Environment variables
│   ├── cache.py                       # Redis/in-memory caching (from cache_service.py + query_cache.py)
│   ├── models/                        # Shared Pydantic schemas
│   │   ├── smrl_types.py             # ISO 10303-4443 resource types
│   │   ├── sdd_types.py              # Dossier, Artifact, AuditFinding, DecisionLog
│   │   ├── oslc_types.py             # OSLC RDF structures
│   │   └── simulation_types.py       # SimulationRun, SimulationModel, KPIData
│   ├── smrl_adapter.py               # (from services/) SMRL data transformation
│   └── smrl_validator.py             # (from services/) JSON Schema validation
│
├── functions/                         # Independent deployable serverless functions
│   │
│   ├── sdd_service/                   # Dossier CRUD + Versioning
│   │   ├── handler.py                 # FaaS entrypoint (Mangum/Azure)
│   │   ├── router.py                  # From simulation_fastapi.py (dossier endpoints)
│   │   └── service.py                 # From simulation_service.py (dossier logic)
│   │
│   ├── audit_service/                 # (NEW) ISO-CASCO Compliance Engine
│   │   ├── handler.py
│   │   ├── router.py                  # GET /api/v1/audit/dossier/{id}
│   │   └── service.py                 # Ports runAudit() from reference app
│   │
│   ├── approval_service/              # (NEW) Quality Head Sign-off
│   │   ├── handler.py
│   │   ├── router.py                  # POST /api/v1/approvals/dossier/{id}
│   │   └── service.py                 # Creates ApprovalRecord + DecisionLog nodes
│   │
│   ├── workspace_service/             # (NEW) Interactive Simulation Execution
│   │   ├── handler.py
│   │   ├── router.py                  # POST /api/v1/workspace/execute, GET status
│   │   └── service.py
│   │
│   ├── simulation_service/            # Models, runs, params, results
│   │   ├── handler.py
│   │   ├── router.py                  # From simulation_fastapi.py (non-dossier: 10 endpoints)
│   │   └── service.py
│   │
│   ├── ap239_service/                 # AP239 Requirements Management
│   │   ├── handler.py
│   │   ├── router.py                  # From ap239_fastapi.py (8 endpoints)
│   │   └── service.py
│   │
│   ├── ap242_service/                 # AP242 CAD Integration
│   │   ├── handler.py
│   │   ├── router.py                  # From ap242_fastapi.py (8 endpoints)
│   │   └── service.py
│   │
│   ├── ap243_service/                 # AP243 Product Structure & Ontologies
│   │   ├── handler.py
│   │   ├── router.py                  # From ap243_fastapi.py (12 endpoints)
│   │   └── service.py
│   │
│   ├── smrl_service/                  # ISO 10303-4443 Generic CRUD
│   │   ├── handler.py
│   │   ├── router.py                  # From smrl_v1_fastapi.py (17 endpoints)
│   │   └── service.py
│   │
│   ├── oslc_service/                  # OSLC Provider + Client + TRS
│   │   ├── handler.py
│   │   ├── router.py                  # oslc (6) + oslc_client (2) + trs (3) = 11 endpoints
│   │   └── service.py                 # oslc_service + oslc_client + oslc_trs_service
│   │
│   ├── ontology_service/              # OWL/RDF Ingestion + SHACL Validation
│   │   ├── handler.py
│   │   ├── router.py                  # ontology_ingest (1) + shacl (2) = 3 endpoints
│   │   └── service.py                 # ontology_ingest_service + shacl_validator
│   │
│   ├── graphql_service/               # Strawberry GraphQL Endpoint
│   │   ├── handler.py
│   │   ├── router.py                  # From graphql_fastapi.py (2 endpoints)
│   │   └── schema.py
│   │
│   ├── graph_service/                 # Raw Graph Data + Hierarchy
│   │   ├── handler.py
│   │   ├── router.py                  # graph (3) + hierarchy (5) = 8 endpoints
│   │   └── service.py
│   │
│   ├── export_service/                # Multi-Format Export (RDF, GraphML, JSON-LD, CSV, etc.)
│   │   ├── handler.py
│   │   ├── router.py                  # From export_fastapi.py (8 endpoints)
│   │   └── service.py                 # From export_service.py
│   │
│   ├── express_service/               # EXPRESS Schema Parser & Analyzer
│   │   ├── handler.py
│   │   ├── router.py                  # From express_parser_fastapi.py (18 endpoints)
│   │   └── service.py                 # Wraps parsers/express/
│   │
│   ├── plm_service/                   # PLM Connectors (Teamcenter, Windchill, SAP)
│   │   ├── handler.py
│   │   ├── router.py                  # plm_connectors (3) + plm (5) = 8 endpoints
│   │   └── service.py                 # Wraps integrations/ connectors
│   │
│   ├── upload_service/                # File Upload & STEP Ingestion
│   │   ├── handler.py
│   │   ├── router.py                  # upload (5) + step_ingest (1) = 6 endpoints
│   │   └── service.py                 # upload_job_store + step_ingest_service
│   │
│   ├── auth_service/                  # Authentication + Sessions
│   │   ├── handler.py
│   │   ├── router.py                  # auth (5) + sessions (7) = 12 endpoints
│   │   └── service.py
│   │
│   ├── telemetry_service/             # Metrics + KPI Analytics
│   │   ├── handler.py
│   │   ├── router.py                  # metrics (3) + NEW: GET /api/v1/telemetry/kpis
│   │   └── service.py
│   │
│   ├── core_service/                  # Core API (packages, classes, search, stats, cypher)
│   │   ├── handler.py
│   │   ├── router.py                  # From core_fastapi.py (10 endpoints)
│   │   └── service.py
│   │
│   ├── version_service/               # Version Control + Admin + Cache Management
│   │   ├── handler.py
│   │   ├── router.py                  # version (4) + admin (1) + cache (6) = 11 endpoints
│   │   └── service.py
│   │
│   └── agent_service/                 # AI Agent Orchestrator
│       ├── handler.py
│       ├── router.py                  # From agents_fastapi.py (1 endpoint)
│       └── service.py
│
├── engine/                            # (PRESERVED) Modular ingestion pipeline
│   ├── protocol.py                    # GraphStore protocol (Neo4j, Spark, Memgraph, Neptune)
│   ├── registry.py                    # Ingester plugin registry (@registry.register)
│   ├── pipeline.py                    # Ingestion orchestrator
│   ├── ingesters/
│   │   ├── xmi_ingester.py           # XMI → Neo4j
│   │   └── oslc_ingester.py          # OSLC TTL seed + external OWL → Neo4j
│   └── stores/
│       ├── neo4j_store.py            # Neo4j GraphStore implementation
│       └── spark_store.py            # Spark GraphStore implementation
│
├── parsers/                           # (PRESERVED) Format-specific parsers
│   ├── xmi_parser.py
│   ├── semantic_loader.py            # 1321 lines — UML/SysML/AP metamodel (175 node types)
│   ├── apoc_loader.py
│   ├── step_parser.py
│   ├── express_parser.py
│   └── express/                      # Pydantic models + analyzer + converter + exporter
│
├── integrations/                      # (PRESERVED) PLM connectors
│   ├── base_connector.py
│   ├── teamcenter_connector.py
│   ├── windchill_connector.py
│   └── sap_odata_connector.py
│
├── models/                            # (PRESERVED) SHACL shapes
│   └── shapes/
│       ├── ap239_requirement.ttl
│       └── ap242_part.ttl
│
└── main.py                            # Local dev server — mounts ALL function routers
```

### 3.4 FaaS Function Summary Table

| # | Function | Migrates From | Endpoints | New? |
|---|---|---|---|---|
| 1 | `sdd_service` | `simulation_fastapi.py` (dossier endpoints) | 5 | Split |
| 2 | `audit_service` | — | 1 | **NEW** |
| 3 | `approval_service` | — | 1 | **NEW** |
| 4 | `workspace_service` | — | 2 | **NEW** |
| 5 | `simulation_service` | `simulation_fastapi.py` (non-dossier endpoints) | 10 | Split |
| 6 | `ap239_service` | `ap239_fastapi.py` | 8 | Migrate |
| 7 | `ap242_service` | `ap242_fastapi.py` | 8 | Migrate |
| 8 | `ap243_service` | `ap243_fastapi.py` | 12 | Migrate |
| 9 | `smrl_service` | `smrl_v1_fastapi.py` | 17 | Migrate |
| 10 | `oslc_service` | `oslc_fastapi.py` + `oslc_client_fastapi.py` + `trs_fastapi.py` | 11 | Migrate |
| 11 | `ontology_service` | `ontology_ingest_fastapi.py` + `shacl_fastapi.py` | 3 | Migrate |
| 12 | `graphql_service` | `graphql_fastapi.py` | 2 | Migrate |
| 13 | `graph_service` | `graph_fastapi.py` + `hierarchy_fastapi.py` | 8 | Migrate |
| 14 | `export_service` | `export_fastapi.py` | 8 | Migrate |
| 15 | `express_service` | `express_parser_fastapi.py` | 18 | Migrate |
| 16 | `plm_service` | `plm_connectors_fastapi.py` + `plm_fastapi.py` | 8 | Migrate |
| 17 | `upload_service` | `upload_fastapi.py` + `step_ingest_fastapi.py` | 6 | Migrate |
| 18 | `auth_service` | `auth_fastapi.py` + `sessions_fastapi.py` | 12 | Migrate |
| 19 | `telemetry_service` | `metrics_fastapi.py` | 4 | Migrate+NEW |
| 20 | `core_service` | `core_fastapi.py` | 10 | Migrate |
| 21 | `version_service` | `version_fastapi.py` + `admin_fastapi.py` + `cache_fastapi.py` | 11 | Migrate |
| 22 | `agent_service` | `agents_fastapi.py` | 1 | Migrate |
| **TOTAL** | | **27 routers → 22 functions** | **~166** | **4 new** |

---

## PART 4: NEO4J SCHEMA EVOLUTION

### 4.1 Existing Node Labels (The Foundation)

**From `semantic_loader.py` (~175 node types):**
- AP239: `Requirement`, `Person`, `Approval`, `Document`, `Analysis`
- AP242: `Part`, `Assembly`, `CADModel`, `Material`, `GeometryModel`
- AP243: `SimulationModel`, `Property`, `Unit`, `Package`, `Class`, `Stereotype`, `ValueType`, `Classification`
- SMRL: Generic `System`, `Component`, `Interface`, `Parameter`, `Port`
- OSLC: `Ontology`, `OntologyClass`, `OntologyProperty`, `ExternalOntology`, `ExternalOwlClass`, `ExternalUnit`
- SDD: `SimulationDossier`, `SimulationArtifact`, `EvidenceCategory`, `SimulationRun`

### 4.2 New Nodes (Governance Layer — from Reference App)

| Node Label | Properties | Purpose |
|---|---|---|
| `ApprovalRecord` | `id`, `status` (Approved/Rejected), `timestamp`, `reviewer`, `comment`, `signatureId`, `role` | Immutable sign-off (ISO-CASCO) |
| `AuditFinding` | `id`, `category` (Compliance/Integrity/Traceability), `severity` (Critical/Warning/Pass), `message`, `requirement` | Automated compliance check result |
| `DecisionLog` | `id`, `status`, `timestamp`, `reviewer`, `comment`, `signatureId` | Dossier lifecycle audit trail |
| `Standard` | `id`, `name`, `version` (e.g., "ISO 17025", "IEC 61508-3") | Governing standard reference |
| `VV_Plan` | `id`, `name`, `status`, `type` (Verification/Validation) | Verification & Validation Plan |
| `ProductSpec` | `id`, `model`, `parameters`, `constraints` | Motor/product specification reference |

### 4.3 New Relationships (The Digital Thread)

| Relationship | From → To | Purpose |
|---|---|---|
| `[:GENERATED_FROM]` | `Dossier → SimulationRun` | Links dossier to execution |
| `[:USES_MODEL]` | `SimulationRun → SimulationModel` | Links execution to AP243 model |
| `[:REPRESENTS]` | `SimulationModel → CADModel` | Links simulation model to AP242 CAD |
| `[:PROVES_COMPLIANCE_TO]` | `Dossier → Requirement` | Links simulation to AP239 requirement |
| `[:GOVERNS]` | `Dossier → Part` | Links dossier to physical part |
| `[:HAS_APPROVAL]` | `Dossier → ApprovalRecord` | Immutable sign-off chain |
| `[:HAS_FINDING]` | `Dossier → AuditFinding` | Compliance audit results |
| `[:HAS_DECISION]` | `Dossier → DecisionLog` | Lifecycle audit trail |
| `[:GOVERNED_BY]` | `Dossier → Standard` | ISO-CASCO Selection Phase |
| `[:VALIDATED_BY]` | `SimulationRun → VV_Plan` | ISO-CASCO Determination Phase |
| `[:SPEC_FOR]` | `ProductSpec → Part` | Spec-to-part reference |

### 4.4 Semantic Web & OSLC Integration in the Graph

| Feature | How It Integrates |
|---|---|
| **OSLC Links** | OSLC predicates (`oslc:validates`, `oslc:elaborates`, `oslc:satisfies`) mapped as Neo4j relationship types (e.g., `[:OSLC_VALIDATES]`). The `oslc_service` generates RDF/XML, Turtle, and JSON-LD representations of graph nodes on demand. |
| **OWL Classes** | Nodes from `ontology_ingest_service.py` carry their OWL hierarchy: `ExternalOwlClass` nodes linked via `[:SUBCLASS_OF]` and `[:EQUIVALENT_CLASS]`. The `ontology_service` manages ingestion of external OWL files. |
| **SHACL Shapes** | The `shacl_validator.py` validates graph subsets against TTL shape files (`ap239_requirement.ttl`, `ap242_part.ttl`). New shapes will be added for `SimulationDossier` and `ApprovalRecord` validation. |
| **TRS Change Feed** | The `trs_fastapi.py` exposes a Tracked Resource Set. Every graph mutation generates a `TRS_ChangeLog` entry consumable by external RDF tools (IBM DOORS, Siemens Teamcenter). |
| **GraphQL** | Strawberry schema in `graphql_fastapi.py` provides a typed query layer. Will be extended with `Dossier`, `AuditFinding`, and `MOSSECLink` types. |
| **RDF Export** | `export_service.py` already exports the full graph as RDF/Turtle. Will also support JSON-LD and N-Triples. |
| **EXPRESS Schemas** | `express_parser_fastapi.py` (18 endpoints) provides full ISO 10303-11 EXPRESS parsing, analysis, and Neo4j graph generation. |

### 4.5 Neo4j Constraints (New)

```cypher
CREATE CONSTRAINT IF NOT EXISTS FOR (d:SimulationDossier) REQUIRE d.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (r:SimulationRun) REQUIRE r.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (m:SimulationModel) REQUIRE m.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (a:ApprovalRecord) REQUIRE a.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (f:AuditFinding) REQUIRE f.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (dl:DecisionLog) REQUIRE dl.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (s:Standard) REQUIRE s.name IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (v:VV_Plan) REQUIRE v.id IS UNIQUE;
```

---

## PART 5: EXECUTION ROADMAP

### Phase 1: Backend FaaS Restructuring (Weeks 1-2)
1. Create `backend/src/core/` — extract `database.py` (Neo4j pooling from `container.py` + `neo4j_service.py`), `config.py`, `cache.py` (from `cache_service.py` + `query_cache.py`).
2. Create `backend/src/functions/` directory structure for all 22 function domains.
3. **Migrate existing routers**: Move each `*_fastapi.py` into its corresponding `functions/*/router.py`. Extract business logic into `service.py`.
4. **Implement NEW functions**: `audit_service` (ports `runAudit()` from reference app), `approval_service` (creates ApprovalRecord + DecisionLog nodes), `workspace_service` (simulation execution + polling).
5. Create `main.py` that mounts all function routers for local development.
6. Verify: all ~162 existing endpoints still work via `main.py`.

### Phase 2: Neo4j Schema Evolution (Week 2)
1. Write migration Cypher scripts for new constraints.
2. Create `ApprovalRecord`, `AuditFinding`, `DecisionLog`, `Standard`, `VV_Plan`, `ProductSpec` node types.
3. Create digital thread relationships (`GENERATED_FROM`, `USES_MODEL`, `REPRESENTS`, `PROVES_COMPLIANCE_TO`, `GOVERNS`, `HAS_APPROVAL`, `HAS_FINDING`, `HAS_DECISION`, `GOVERNED_BY`, `VALIDATED_BY`, `SPEC_FOR`).
4. Add new SHACL shapes for `SimulationDossier` and `ApprovalRecord` validation.

### Phase 3: Frontend FSD Restructuring (Weeks 3-4)
1. Create `frontend/src/features/` directory structure for all 9 feature domains.
2. Move existing 29 `.jsx` pages into their respective `features/*/components/` directories.
3. Create `frontend/src/apps/` with `engineer/`, `quality/`, `admin/` — each composing features (see Section 3.2).
4. Implement the `RoleSelector` component and role-based routing wrapper.
5. Split the monolithic `api.ts` (~525 lines) into per-domain service files (see Section 3.1 `services/`).
6. Verify: all existing routes still work under the new FSD structure.

### Phase 4: Porting Reference App Features (Weeks 5-6)
1. **Compliance Audit Engine** [G2]: Implement `AuditPanel` + `useDossierAudit` calling `audit_service`.
2. **Quality Review Workflow** [G5, G6]: Implement `ReviewPanel` + `useApproval` calling `approval_service`.
3. **Evidence Pipeline** [G9]: Implement `EvidencePipeline` component with 8-category tracking.
4. **MOSSEC Inspector** [G3]: Implement `MossecInspector` side panel with source→target visualization.
5. **Simulation Terminal** [G8]: Implement `SimulationWorkspace` calling `workspace_service`.
6. **KPI & Quality Dashboards** [G11, G12]: Implement `DashboardEngineer` and `QualityDashboard` with Recharts.
7. **Dossier Create** [G15]: Add "Create New Dossier" workflow to `DossierList`.
8. **Artifact Preview** [G4]: Implement `ArtifactPreview` modal with SHA-256 and signature chain.
9. **Decision History** [G5]: Implement `DecisionLog` timeline in `DossierDetail`.

### Phase 5: Semantic Web UI (Week 7)
1. **OntologyManager**: Browse/ingest OWL ontologies (calling `ontology_service`).
2. **OSLCBrowser**: Browse OSLC root services and service providers (calling `oslc_service`).
3. **SHACLValidator**: Run SHACL validation against shape files (calling `ontology_service`).
4. **GraphQLPlayground**: Interactive query UI for the Strawberry GraphQL endpoint (calling `graphql_service`).
5. **TRSFeed**: Visualize OSLC TRS changelog (calling `oslc_service`).
6. **ExpressExplorer**: Parse/analyze EXPRESS schemas with all 18 endpoints (calling `express_service`).
7. **RDFExporter**: Export graph as RDF/Turtle or JSON-LD (calling `export_service`).

### Phase 6: Digital Thread Integration (Week 8)
1. Build click-through navigation: Dossier → Run → Model → CAD → Part → Requirement.
2. Implement "Authoring Mode" allowing engineers to link existing graph nodes to a Draft Dossier.
3. Extend `GraphBrowser` to visualize the full digital thread with colored relationship types.
4. Extend `TraceabilityMatrix` with MossecInspector integration.
5. **Role-Based UI** [G1]: Complete dual-persona experience with persona-specific sidebars, dashboards, and actions.
6. **AI Chatbot** [G7]: Implement floating context-aware assistant.

---

## Appendix A: v3.0 → v4.0 Changelog

| What Changed | v3.0 | v4.0 |
|---|---|---|
| Backend routers counted | "12+ monolithic" | **27 (exact), with file names and endpoint counts** |
| Backend services documented | Not listed | **17 services fully cataloged** |
| Missing routers | 12 routers NOT in plan | **All 27 mapped**: admin, agents, cache, core, export, express_parser, shacl, step_ingest, trs, upload, version, plm (separate from plm_connectors) |
| Engine layer | Not addressed | **Fully documented**: GraphStore protocol, registry, pipeline, stores |
| Parsers | Not addressed | **Fully documented**: XMI, Semantic (1321 lines), STEP, EXPRESS, APOC |
| Integrations | Not addressed | **Fully documented**: Teamcenter, Windchill, SAP OData connectors |
| ServiceContainer (DI) | Not addressed | **Architecture diagram** showing shared driver pool (Section 1.6) |
| FaaS function count | Incomplete | **22 functions mapping all 27 routers** |
| Frontend pages | Listed but not exhaustive | **29 pages with routes, API calls, and domains** |
| Frontend services | Not listed | **5 service modules fully cataloged** |
| Reference app gaps | Not enumerated | **15 gaps (G1-G15) with severity ratings** |
| Execution roadmap | 4 phases, some duplicated | **6 phases, each gap referenced by ID** |

---

*This document is the sole source of truth for all architectural decisions. All previous trackers, sprint docs, and plan versions are superseded.*