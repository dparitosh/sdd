# MBSEsmrl — Implementation Prompts for Successful Completion

**Reference:** `docs/SDD_MODULAR_ARCHITECTURE_PLAN.md` (v4.0)
**Usage:** Copy each prompt into your AI coding agent session to execute that phase.

---

## PROMPT 1: Backend Core Extraction (Phase 1a)

```
CONTEXT: I am working on the MBSEsmrl project. Read `docs/SDD_MODULAR_ARCHITECTURE_PLAN.md` (the v4.0 plan) — specifically Part 3.3 (Backend FaaS Architecture) and Section 1.6 (ServiceContainer DI).

TASK: Execute Phase 1, Step 1 — Extract the shared `core/` layer.

1. Create `backend/src/core/__init__.py`
2. Create `backend/src/core/config.py` — extract all environment variable handling (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, REDIS_URL, SECRET_KEY, etc.) from `backend/src/web/container.py` and `backend/src/constants.py` into a single `Settings` class using pydantic-settings.
3. Create `backend/src/core/database.py` — extract Neo4j connection pooling logic from `backend/src/web/services/neo4j_service.py` and `backend/src/web/container.py`. Must preserve the shared driver pool pattern: a single Neo4j driver (50 max connections, 30s acquisition timeout) serving both web services and the engine layer. Expose a `get_driver()` function and a `Neo4jPool` class.
4. Create `backend/src/core/cache.py` — extract caching logic from `backend/src/web/services/cache_service.py` and `backend/src/web/services/query_cache.py` into a unified `CacheManager` class supporting both in-memory and Redis backends.
5. Create `backend/src/core/models/` with:
   - `__init__.py`
   - `smrl_types.py` — move Pydantic models for ISO 10303-4443 resource types
   - `sdd_types.py` — Dossier, Artifact, AuditFinding, DecisionLog, MOSSECLink, CredibilityLevel, EvidenceCategory
   - `oslc_types.py` — OSLC RDF structures
   - `simulation_types.py` — SimulationRun, SimulationModel, KPIData
6. Move `backend/src/web/services/smrl_adapter.py` → `backend/src/core/smrl_adapter.py`
7. Move `backend/src/web/services/smrl_validator.py` → `backend/src/core/smrl_validator.py`

CONSTRAINTS:
- Do NOT break existing imports — update all files that import from the old locations.
- The `ServiceContainer` in `container.py` should now import from `core/` instead of duplicating logic.
- Run `python -m pytest tests/` after changes to verify nothing is broken.
- The engine layer (`backend/src/engine/stores/neo4j_store.py`) must be updated to use `core.database.get_driver()`.
```

---

## PROMPT 2: Backend FaaS Function Structure (Phase 1b)

```
CONTEXT: I am working on the MBSEsmrl project. Read `docs/SDD_MODULAR_ARCHITECTURE_PLAN.md` (v4.0) — specifically Part 3.3 and Table 3.4 (FaaS Function Summary). The `core/` layer was already extracted in the previous step.

TASK: Execute Phase 1, Steps 2-3 — Create the `functions/` directory and migrate existing routers.

For EACH of the 22 function domains listed in Table 3.4, create:
- `backend/src/functions/{name}/__init__.py`
- `backend/src/functions/{name}/handler.py` — FaaS entrypoint using Mangum pattern:
  ```python
  from fastapi import FastAPI
  from mangum import Mangum
  from .router import router

  app = FastAPI()
  app.include_router(router)
  handler = Mangum(app)
  ```
- `backend/src/functions/{name}/router.py` — MOVE the router code from the corresponding `backend/src/web/routers/*_fastapi.py` file. Keep the same route prefixes, tags, and endpoint signatures. Import services from `core/` or from a local `service.py`.
- `backend/src/functions/{name}/service.py` — Extract business logic from `backend/src/web/services/` into domain-specific service classes.

MIGRATION MAPPING (from Table 3.4):
1. sdd_service ← simulation_fastapi.py (dossier endpoints only: CRUD dossiers, artifacts, evidence)
2. simulation_service ← simulation_fastapi.py (non-dossier: models, runs, params, results, validate, units, trace, stats)
3. ap239_service ← ap239_fastapi.py (8 endpoints)
4. ap242_service ← ap242_fastapi.py (8 endpoints)
5. ap243_service ← ap243_fastapi.py (12 endpoints)
6. smrl_service ← smrl_v1_fastapi.py (17 endpoints)
7. oslc_service ← oslc_fastapi.py (6) + oslc_client_fastapi.py (2) + trs_fastapi.py (3)
8. ontology_service ← ontology_ingest_fastapi.py (1) + shacl_fastapi.py (2)
9. graphql_service ← graphql_fastapi.py (2)
10. graph_service ← graph_fastapi.py (3) + hierarchy_fastapi.py (5)
11. export_service ← export_fastapi.py (8)
12. express_service ← express_parser_fastapi.py (18)
13. plm_service ← plm_connectors_fastapi.py (3) + plm_fastapi.py (5)
14. upload_service ← upload_fastapi.py (5) + step_ingest_fastapi.py (1)
15. auth_service ← auth_fastapi.py (5) + sessions_fastapi.py (7)
16. telemetry_service ← metrics_fastapi.py (3)
17. core_service ← core_fastapi.py (10)
18. version_service ← version_fastapi.py (4) + admin_fastapi.py (1) + cache_fastapi.py (6)
19. agent_service ← agents_fastapi.py (1)

THEN create `backend/src/main.py` that mounts ALL function routers for local development:
```python
from fastapi import FastAPI
from src.functions.sdd_service.router import router as sdd_router
from src.functions.simulation_service.router import router as simulation_router
# ... all 22
app = FastAPI(title="MBSEsmrl API", version="4.0")
app.include_router(sdd_router)
# ... mount all
```

CONSTRAINTS:
- Do NOT delete the original `backend/src/web/routers/` yet — keep them as reference until the new functions are verified.
- All ~162 existing endpoints must be accessible through the new `main.py`.
- Preserve all middleware (CORS, GZip, rate limiting, security headers) in the new `main.py`.
- Run the backend and test: `curl http://localhost:5000/api/health` and a few other endpoints.
```

---

## PROMPT 3: New Backend Services — Audit, Approval, Workspace (Phase 1c)

```
CONTEXT: I am working on the MBSEsmrl project. Read `docs/SDD_MODULAR_ARCHITECTURE_PLAN.md` (v4.0) — specifically Part 2 (The Gap: G2, G5, G6, G8, G9) and Part 4 (Neo4j Schema Evolution).

TASK: Implement the 3 NEW FaaS functions that don't exist yet.

1. **audit_service** — ISO-CASCO Compliance Audit Engine [G2, G14]
   - `backend/src/functions/audit_service/router.py`:
     - `GET /api/v1/audit/dossier/{dossier_id}` → runs full audit, returns `AuditReport`
   - `backend/src/functions/audit_service/service.py`:
     - `AuditService.run_audit(dossier_id)` must:
       a. Fetch dossier + all linked artifacts from Neo4j
       b. Check **Completeness**: Are all 8 evidence categories (A1-H1) populated?
       c. Check **Integrity**: Verify artifact checksums (SHA-256) if present
       d. Check **Traceability**: Walk MOSSEC relationships (depth 7) and verify chain completeness
       e. Return: `{ healthScore: 0-100, findings: AuditFinding[], summary: { critical, warnings, passed } }`
     - Each `AuditFinding` has: `id, category (Compliance|Integrity|Traceability), severity (Critical|Warning|Pass), message, requirement`
     - Write findings as `AuditFinding` nodes in Neo4j linked via `[:HAS_FINDING]` to the dossier

2. **approval_service** — Quality Head Sign-off [G5, G6]
   - `backend/src/functions/approval_service/router.py`:
     - `POST /api/v1/approvals/dossier/{dossier_id}` — body: `{ status, comment, reviewer, signatureId }`
     - `GET /api/v1/approvals/dossier/{dossier_id}/history` — returns decision log
   - `backend/src/functions/approval_service/service.py`:
     - `ApprovalService.approve(dossier_id, payload)` must:
       a. Create `ApprovalRecord` node (immutable — no updates allowed)
       b. Create `DecisionLog` node
       c. Link both to dossier via `[:HAS_APPROVAL]` and `[:HAS_DECISION]`
       d. Update dossier status (Draft → Under Review → Approved/Rejected)
     - `ApprovalService.get_history(dossier_id)` returns all DecisionLog nodes ordered by timestamp

3. **workspace_service** — Interactive Simulation Execution [G8]
   - `backend/src/functions/workspace_service/router.py`:
     - `POST /api/v1/workspace/execute` — body: `{ dossierId, modelId, parameters }`
     - `GET /api/v1/workspace/status/{job_id}` — returns execution status + logs
   - `backend/src/functions/workspace_service/service.py`:
     - `WorkspaceService.execute(payload)` must:
       a. Create a background job entry
       b. Create a `SimulationRun` node linked to dossier via `[:GENERATED_FROM]`
       c. Link run to model via `[:USES_MODEL]`
       d. Return `{ jobId, status: "running" }`
     - `WorkspaceService.get_status(job_id)` returns `{ status, progress, logs[], completedAt }`

ALSO: Add these functions' routers to `main.py`.

CONSTRAINTS:
- Use Pydantic models from `core/models/sdd_types.py` for all request/response schemas.
- Use `core/database.py` for Neo4j connections.
- Write unit tests in `backend/tests/test_audit_service.py`, `test_approval_service.py`, `test_workspace_service.py`.
```

---

## PROMPT 4: Neo4j Schema Evolution (Phase 2)

```
CONTEXT: I am working on the MBSEsmrl project. Read `docs/SDD_MODULAR_ARCHITECTURE_PLAN.md` (v4.0) — Part 4 (Neo4j Schema Evolution), including Sections 4.2-4.5.

TASK: Execute Phase 2 — Neo4j schema migration.

1. Create `backend/scripts/migrate_schema_v4.cypher` containing:
   - All 8 uniqueness constraints from Section 4.5
   - Sample `Standard` nodes: "ISO 17025", "IEC 61508-3", "AP243 MoSSEC", "ISO 10303-4443 SMRL"
   - INDEX creation for frequently queried properties

2. Create `backend/scripts/migrate_digital_thread.cypher` containing:
   - All 11 relationship types from Section 4.3
   - Sample relationships linking existing test data (if any SimulationDossier nodes exist)

3. Create `backend/src/models/shapes/sdd_dossier.ttl` — a new SHACL shape for SimulationDossier validation:
   - Required properties: id, name, status, createdAt
   - Cardinality: at least 1 `[:HAS_ARTIFACT]` relationship
   - Valid statuses: Draft, UnderReview, Approved, Rejected, Archived

4. Create `backend/src/models/shapes/approval_record.ttl` — SHACL shape for ApprovalRecord:
   - Required properties: id, status, timestamp, reviewer
   - Valid statuses: Approved, Rejected
   - Must have exactly 1 `[:HAS_DECISION]` relationship

5. Update `backend/src/web/services/shacl_validator.py` to load the new shape files.

6. Create `backend/scripts/run_migration_v4.py` that:
   - Connects to Neo4j using `core/database.py`
   - Executes both .cypher files
   - Reports results

CONSTRAINTS:
- Do NOT delete existing nodes or relationships.
- Run the migration script and verify with: `CALL db.constraints()` and `CALL db.indexes()`.
```

---

## PROMPT 5: Frontend FSD Structure + Page Migration (Phase 3a)

```
CONTEXT: I am working on the MBSEsmrl project. Read `docs/SDD_MODULAR_ARCHITECTURE_PLAN.md` (v4.0) — Part 3.1 (Frontend FSD tree) and Section 1.4 (Frontend Pages inventory).

TASK: Execute Phase 3, Steps 1-2 — Create the FSD directory structure and migrate all 29 existing pages.

1. Create the full `frontend/src/features/` directory tree with all 9 feature domains:
   - `auth/components/`, `auth/hooks/`, `auth/types.ts`
   - `sdd/components/`, `sdd/hooks/`, `sdd/types.ts`
   - `simulation/components/`, `simulation/hooks/`, `simulation/types.ts`
   - `systems-engineering/components/`, `systems-engineering/hooks/`
   - `graph-explorer/components/`, `graph-explorer/hooks/`
   - `semantic-web/components/`, `semantic-web/hooks/`
   - `ai-studio/components/`, `ai-studio/hooks/`
   - `telemetry/components/`, `telemetry/hooks/`
   - `system-management/components/`, `system-management/hooks/`

2. MOVE existing page files from `frontend/src/pages/` into their feature directories. Use the exact mapping from Section 3.1:
   - `Login.jsx` → `features/auth/components/Login.jsx`
   - `AuthCallback.jsx` → `features/auth/components/AuthCallback.jsx`
   - `DossierList.jsx` → `features/sdd/components/DossierList.jsx`
   - `DossierDetail.jsx` → `features/sdd/components/DossierDetail.jsx`
   - `SimulationRuns.jsx` → `features/simulation/components/SimulationRuns.jsx`
   - `ModelRepository.jsx` → `features/simulation/components/ModelRepository.jsx`
   - `ResultsAnalysis.jsx` → `features/simulation/components/ResultsAnalysis.jsx`
   - `WorkflowStudio.jsx` → `features/simulation/components/WorkflowStudio.jsx`
   - `RequirementsManager.jsx` → `features/systems-engineering/components/RequirementsManager.jsx`
   - `RequirementsDashboard.jsx` → `features/systems-engineering/components/RequirementsDashboard.jsx`
   - `TraceabilityMatrix.jsx` → `features/systems-engineering/components/TraceabilityMatrix.jsx`
   - `PartsExplorer.jsx` → `features/systems-engineering/components/PartsExplorer.jsx`
   - `GraphBrowser.jsx` → `features/graph-explorer/components/GraphBrowser.jsx`
   - `AP239Graph.jsx` → `features/graph-explorer/components/AP239Graph.jsx`
   - `AP242Graph.jsx` → `features/graph-explorer/components/AP242Graph.jsx`
   - `AP243Graph.jsx` → `features/graph-explorer/components/AP243Graph.jsx`
   - `OntologyGraph.jsx` → `features/graph-explorer/components/OntologyGraph.jsx`
   - `OSLCGraph.jsx` → `features/graph-explorer/components/OSLCGraph.jsx`
   - `ModelChat.jsx` → `features/ai-studio/components/ModelChat.jsx`
   - `AIInsights.jsx` → `features/ai-studio/components/AIInsights.jsx`
   - `SmartAnalysis.jsx` → `features/ai-studio/components/SmartAnalysis.jsx`
   - `Dashboard.jsx` → `features/telemetry/components/Dashboard.jsx`
   - `MossecDashboard.jsx` → `features/telemetry/components/MossecDashboard.jsx`
   - `SystemMonitoring.jsx` → `features/telemetry/components/SystemMonitoring.jsx`
   - `DataImport.jsx` → `features/system-management/components/DataImport.jsx`
   - `PLMIntegration.jsx` → `features/system-management/components/PLMIntegration.jsx`
   - `RestApiExplorer.jsx` → `features/system-management/components/RestApiExplorer.jsx`
   - `QueryEditor.jsx` → `features/system-management/components/QueryEditor.jsx`
   - `AdvancedSearch.jsx` → `features/system-management/components/AdvancedSearch.jsx`

3. Create barrel `index.ts` exports for each feature:
   ```typescript
   // features/sdd/index.ts
   export { default as DossierList } from './components/DossierList'
   export { default as DossierDetail } from './components/DossierDetail'
   ```

4. Update ALL import paths in `frontend/src/App.tsx` (or wherever routing is defined) to point to the new feature locations.

5. Verify: `npm run build` must succeed with zero errors.

CONSTRAINTS:
- Use `git mv` for moves so git tracks the rename.
- Fix any relative import paths inside the moved files (e.g., `../../services/api` → `../../../services/api` or use `@/` alias).
- Do NOT change any component logic — this is a pure file reorganization.
```

---

## PROMPT 6: Frontend Apps Composition + Role Routing (Phase 3b)

```
CONTEXT: I am working on the MBSEsmrl project. Read `docs/SDD_MODULAR_ARCHITECTURE_PLAN.md` (v4.0) — Section 3.2 (How Features Are Composed Into SDD Apps). All pages have been migrated to features/ already (Prompt 5).

TASK: Execute Phase 3, Steps 3-4 — Create the apps/ composition layer and role-based routing.

1. Create `frontend/src/features/auth/types.ts`:
   ```typescript
   export type UserRole = 'engineer' | 'quality' | 'admin'
   ```

2. Create `frontend/src/features/auth/hooks/useRole.ts`:
   - Returns current user role from auth context/localStorage
   - Default to 'engineer' if not set

3. Create `frontend/src/features/auth/components/RoleSelector.tsx`:
   - Dropdown/toggle allowing user to switch between Engineer, Quality Head, Admin
   - Persists choice to localStorage and reloads routing

4. Create `frontend/src/apps/engineer/layout.tsx`:
   - Sidebar with 8 groups matching Section 3.2 (Dashboard, Simulation, Dossiers, Systems Eng, Graph & Ontology, Semantic Web, AI Studio, Data Management)
   - Standard page layout with header showing role badge

5. Create `frontend/src/apps/engineer/routes.tsx`:
   - Define all routes for Simulation Engineer persona
   - Import components from `@/features/sdd`, `@/features/simulation`, `@/features/systems-engineering`, `@/features/graph-explorer`, `@/features/semantic-web`, `@/features/ai-studio`, `@/features/telemetry`, `@/features/system-management`

6. Create `frontend/src/apps/quality/layout.tsx`:
   - Sidebar with 5 groups: Approval Queue, Quality Dashboard, Compliance, Traceability, Change Feed
   - Approval queue badge count in sidebar

7. Create `frontend/src/apps/quality/routes.tsx`:
   - Import from `@/features/sdd` (DossierList, DossierDetail), `@/features/telemetry` (QualityDashboard), `@/features/systems-engineering` (TraceabilityMatrix), `@/features/semantic-web` (SHACLValidator, TRSFeed)

8. Create `frontend/src/apps/admin/layout.tsx` and `routes.tsx`:
   - Sidebar: System Health, Data Import, Semantic Tools, Graph Explorer, API & PLM, Search

9. Update `frontend/src/App.tsx`:
   - Wrap routing in a `RoleProvider`
   - Route `/engineer/*` → engineer app, `/quality/*` → quality app, `/admin/*` → admin app
   - Default redirect based on user role
   - Keep `/login` and `/auth/callback` outside role routing

10. Verify: `npm run build` succeeds and manually test role switching.

CONSTRAINTS:
- Use React Router v6 nested routes with `<Outlet />`.
- Each app layout must use the existing shadcn/ui sidebar components from `components/layout/`.
- The RoleSelector must be in the header of every layout.
```

---

## PROMPT 7: Frontend Service Layer Split (Phase 3c)

```
CONTEXT: I am working on the MBSEsmrl project. Read `docs/SDD_MODULAR_ARCHITECTURE_PLAN.md` (v4.0) — Section 3.1 (services/ directory listing in the FSD tree) and Section 1.5 (current Frontend Services inventory).

TASK: Execute Phase 3, Step 5 — Split the monolithic `api.ts` (~525 lines) into per-domain service files.

1. Refactor `frontend/src/services/api.ts`:
   - Keep ONLY the base `ApiClient` class (Axios instance, auth interceptors, error handling, base URL config).
   - Export the configured axios instance as `apiClient`.

2. Create these service files, each importing `apiClient` from `api.ts`:

   - `sdd.service.ts` — dossier CRUD: getDossiers, getDossier, createDossier, updateDossier, getDossierArtifacts, getDossierStatistics
   - `audit.service.ts` — runAudit(dossierId), getAuditFindings(dossierId)
   - `approval.service.ts` — submitApproval(dossierId, payload), getApprovalHistory(dossierId)
   - `simulation.service.ts` — getModels, getRuns, getResults, getParameters, validateModel, executeWorkspace, getWorkspaceStatus
   - `standards.service.ts` — AP239 (requirements, analyses, approvals, documents), AP242 (parts, assemblies, materials, geometry), AP243 (classes, packages, ontologies, units, valueTypes), SMRL generic CRUD
   - `oslc.service.ts` — getRootServices, getCatalog, getProvider, connectOSLC, queryOSLC, getTRSBase, getTRSChangelog
   - `ontology.service.ts` — ingestOntology(file)
   - `validation.service.ts` — validateSHACL(data, shapeName)
   - `graph.service.ts` — getGraphData, getNodeTypes, getRelTypes, getHierarchy, getTraceability, searchHierarchy, getImpact
   - `export.service.ts` — exportSchema, exportGraphML, exportJSONLD, exportCSV, exportSTEP, exportPlantUML, exportRDF, exportCytoscape
   - `express.service.ts` — parseExpress, queryExpress, analyzeExpress, exportExpress (wrapping all 18 endpoints)
   - `plm.service.ts` — getConnectors, triggerSync, getStatus, getTraceability, getComposition, getImpact, getParameters, getConstraints
   - `metrics.service.ts` — getSummary, getHistory, getHealth
   - `auth.service.ts` — login, refresh, logout, verify, changePassword, getSessions, adminGetSessions, deleteSession

3. Update ALL imports across all feature components:
   - Find every `import { apiService } from '../../services/api'` (or similar)
   - Replace with the specific domain service: `import { getDossiers } from '@/services/sdd.service'`

4. Keep `graphql.service.ts`, `websocket.service.ts` as they are (already separate).

5. Delete the old `apiService` mega-object from `api.ts` once all imports are migrated.

6. Verify: `npm run build` succeeds with zero errors. `npm run test` passes.

CONSTRAINTS:
- Each service file should be <100 lines.
- Use TypeScript for all new service files.
- All API calls must use the shared `apiClient` for consistent auth/error handling.
```

---

## PROMPT 8: Port Reference App — Audit + Approval + Evidence UI (Phase 4a)

```
CONTEXT: I am working on the MBSEsmrl project. Read `docs/SDD_MODULAR_ARCHITECTURE_PLAN.md` (v4.0) — Part 2 gaps G2, G4, G5, G6, G9, G13, G14, G15. Also read the reference SDD app at `sdd---simulation-data-dossier/src/` for the implementation patterns.

TASK: Execute Phase 4, Steps 1-3 and 7-9 — Port the core compliance and governance UI from the reference app.

1. Create `frontend/src/features/sdd/types.ts` with TypeScript types:
   - `Dossier` (id, name, status, type, createdAt, updatedAt, healthScore, artifacts, mossecLinks, evidence)
   - `DossierStatus` = 'Draft' | 'UnderReview' | 'Approved' | 'Rejected' | 'Archived'
   - `Artifact` (id, name, type, size, checksum, signedBy, uploadedAt, status)
   - `AuditFinding` (id, category: 'Compliance'|'Integrity'|'Traceability', severity: 'Critical'|'Warning'|'Pass', message, requirement)
   - `DecisionLog` (id, status, timestamp, reviewer, comment, signatureId)
   - `MOSSECLink` (id, source, target, relationType, semanticDescription) with 9 entity types and 8 relation types
   - `CredibilityLevel` = 'Low' | 'Medium' | 'High' | 'VeryHigh'
   - `EvidenceCategory` (id, code: 'A1'|'B1'|...|'H1', name, status: 'NotStarted'|'InProgress'|'Complete', artifacts)

2. Create `frontend/src/features/sdd/components/AuditPanel.tsx` [G2]:
   - "Run Audit" button calling `audit.service.ts`
   - Displays healthScore gauge (0-100, color-coded)
   - Lists findings grouped by category with severity badges (Critical=red, Warning=amber, Pass=green)
   - Summary: X critical, Y warnings, Z passed
   - Reference: `sdd---simulation-data-dossier/src/components/DossierDetail.tsx` compliance section

3. Create `frontend/src/features/sdd/components/ReviewPanel.tsx` [G6]:
   - Approve/Reject buttons with required comment textarea
   - Displays decision history timeline (DecisionLog[]) [G5]
   - Status badge showing current approval state
   - Only visible for Quality Head role
   - Reference: `sdd---simulation-data-dossier/src/components/DossierDetail.tsx` review section

4. Create `frontend/src/features/sdd/components/ArtifactPreview.tsx` [G4]:
   - Modal dialog showing artifact details
   - SHA-256 checksum display with copy button
   - Download button
   - Signature chain viewer (who signed, when)
   - File type icon based on artifact type

5. Create `frontend/src/features/sdd/components/EvidencePipeline.tsx` [G9]:
   - 8-category pipeline visualization (A1: Geometry, B1: Mesh, C1: Solver Setup, D1: Run Results, E1: Post-Processing, F1: V&V, G1: Peer Review, H1: Certification)
   - Each category shows status (NotStarted/InProgress/Complete) with colored indicators
   - Click to expand and see linked artifacts per category
   - Progress bar showing overall completion percentage

6. Create `frontend/src/features/sdd/components/MossecInspector.tsx` [G3]:
   - Side panel (drawer) showing MOSSEC links for a dossier
   - Each link: source entity → relation type → target entity
   - Clickable to navigate to the linked entity in the graph
   - Semantic description tooltip
   - Reference: `sdd---simulation-data-dossier/src/components/DossierDetail.tsx` MOSSEC inspector tab

7. Add "Create New Dossier" workflow [G15]:
   - Add a "New Dossier" button to `DossierList.jsx`
   - Modal form: name, type (dropdown), description, linked part (search), linked requirement (search)
   - Calls `sdd.service.createDossier()`

8. Create hooks:
   - `frontend/src/features/sdd/hooks/useDossierAudit.ts` — wraps `audit.service` with loading/error state
   - `frontend/src/features/sdd/hooks/useApproval.ts` — wraps `approval.service` with optimistic updates

9. Upgrade existing `DossierDetail.jsx`:
   - Add tabs: Overview | Artifacts | MOSSEC Links | Audit | Review | Evidence
   - Embed AuditPanel, ReviewPanel, EvidencePipeline, MossecInspector as tab content
   - Show ArtifactPreview modal on artifact click

CONSTRAINTS:
- Use shadcn/ui components (Card, Badge, Button, Dialog, Sheet, Tabs, Progress, Tooltip).
- Use Recharts for the healthScore gauge.
- All components must be responsive.
- Verify: `npm run build` + `npm run test`.
```

---

## PROMPT 9: Port Reference App — Dashboards + Simulation Terminal (Phase 4b)

```
CONTEXT: I am working on the MBSEsmrl project. Read `docs/SDD_MODULAR_ARCHITECTURE_PLAN.md` (v4.0) — Part 2 gaps G1, G8, G11, G12. Also study:
- `sdd---simulation-data-dossier/src/components/DashboardEngineer.tsx`
- `sdd---simulation-data-dossier/src/components/QualityDashboard.tsx`
- `sdd---simulation-data-dossier/src/components/SimulationWorkspace.tsx`

TASK: Execute Phase 4, Steps 4-6 — Port dashboards and simulation workspace.

1. Create `frontend/src/features/telemetry/components/DashboardEngineer.tsx` [G11]:
   - KPI cards: Total Dossiers, Average Health Score, Active Simulations, Pending Reviews
   - Bar chart: Dossier health scores across all dossiers (Recharts BarChart)
   - Line chart: Convergence trend showing health scores over simulation iterations
   - Evidence pipeline summary: horizontal bar showing aggregate A1-H1 completion
   - Recent activity feed
   - Port patterns from `sdd---simulation-data-dossier/src/components/DashboardEngineer.tsx`

2. Create `frontend/src/features/telemetry/components/QualityDashboard.tsx` [G12]:
   - Pie chart: Dossier status distribution (Draft/UnderReview/Approved/Rejected)
   - Bar chart: Weekly approval throughput
   - Priority queue table: dossiers sorted by health score ascending (worst first)
   - Approval history timeline
   - Certification progress: standards compliance overview
   - Port patterns from `sdd---simulation-data-dossier/src/components/QualityDashboard.tsx`

3. Create `frontend/src/features/simulation/components/SimulationWorkspace.tsx` [G8]:
   - Split pane: left = configuration, right = terminal output
   - Configuration panel: select model, set parameters, pick target dossier
   - "Execute" button calling `simulation.service.executeWorkspace()`
   - Terminal panel: real-time log output (poll `getWorkspaceStatus()` every 2s)
   - Progress bar with percentage
   - ISO compliance status messages during execution
   - On completion: link to created SimulationRun node
   - Port patterns from `sdd---simulation-data-dossier/src/components/SimulationWorkspace.tsx`

4. Create `frontend/src/features/telemetry/hooks/useMetrics.ts`:
   - `useKPIs()` — fetches from `telemetry_service`
   - `useDossierHealth()` — aggregates dossier health data for charts
   - `useApprovalQueue()` — fetches pending-review dossiers sorted by score

5. Create `frontend/src/features/simulation/hooks/useSimRunner.ts`:
   - Manages execute → poll → complete lifecycle
   - Returns: `{ execute, status, progress, logs, isRunning, error }`

6. Wire into apps:
   - `apps/engineer/routes.tsx`: add DashboardEngineer as the `/engineer/dashboard` route, SimulationWorkspace as `/engineer/workspace`
   - `apps/quality/routes.tsx`: add QualityDashboard as the `/quality/dashboard` route

CONSTRAINTS:
- Use Recharts (BarChart, LineChart, PieChart, ResponsiveContainer) — already in project dependencies.
- Use Lucide React icons — already in project dependencies.
- Responsive layout: stack charts vertically on mobile.
- `npm run build` must succeed.
```

---

## PROMPT 10: Semantic Web UI Components (Phase 5)

```
CONTEXT: I am working on the MBSEsmrl project. Read `docs/SDD_MODULAR_ARCHITECTURE_PLAN.md` (v4.0) — Section 3.1 features/semantic-web/ and Part 1.1 (routers 10, 12, 15, 16, 17, 21, 25 — EXPRESS, GraphQL, Ontology, OSLC, SHACL, TRS). These backend endpoints already exist.

TASK: Execute Phase 5 — Build the Semantic Web UI feature.

1. Create `frontend/src/features/semantic-web/components/OntologyManager.tsx`:
   - File upload for OWL/RDF files (calls `ontology.service.ingestOntology()`)
   - List of ingested ontologies from the graph
   - Tree view showing OWL class hierarchy (ExternalOwlClass → SUBCLASS_OF → parent)
   - Click a class to see its properties, descriptions, equivalent classes

2. Create `frontend/src/features/semantic-web/components/OSLCBrowser.tsx`:
   - Calls `oslc.service.getRootServices()` to show OSLC root service document
   - Expandable tree: Root Services → Catalogs → Service Providers → Services
   - Each service shows: creation/query/selection dialogs
   - "Connect" button for OSLC client (calls `oslc.service.connectOSLC()`)

3. Create `frontend/src/features/semantic-web/components/SHACLValidator.tsx`:
   - Select shape file: AP239 Requirement, AP242 Part, SDD Dossier, Approval Record
   - Paste or upload RDF data to validate
   - "Validate" button calls `validation.service.validateSHACL()`
   - Results: conformance status (pass/fail), violations list with path and message

4. Create `frontend/src/features/semantic-web/components/GraphQLPlayground.tsx`:
   - Query editor (textarea with syntax highlighting or Monaco editor)
   - Pre-filled example queries: statistics, cypher_read
   - "Execute" button calls `graphql.service.execute(query)`
   - Results panel: JSON tree viewer
   - Variables panel for parameterized queries

5. Create `frontend/src/features/semantic-web/components/TRSFeed.tsx`:
   - Calls `oslc.service.getTRSBase()` to show base resources
   - Calls `oslc.service.getTRSChangelog()` to show change events
   - Timeline view: each event shows type (Creation/Modification/Deletion), resource URI, timestamp
   - Auto-refresh toggle (poll every 30s)

6. Create `frontend/src/features/semantic-web/components/ExpressExplorer.tsx`:
   - File upload for EXPRESS (.exp) files (calls `express.service.parseExpress()`)
   - Schema browser: entities, types, rules, functions
   - Entity detail view: attributes, inverse attributes, supertypes, subtypes
   - "Analyze" button for schema analysis (calls `express.service.analyzeExpress()`)
   - Export options: JSON, Neo4j graph, PlantUML

7. Create `frontend/src/features/semantic-web/components/RDFExporter.tsx`:
   - Export format selector: RDF/Turtle, JSON-LD, N-Triples
   - Node type filter: select which node labels to export
   - "Export" button calls `export.service.exportRDF()` or `export.service.exportJSONLD()`
   - Download link for the generated file

8. Create hooks:
   - `useOSLC.ts` — wraps oslc.service + trs.service
   - `useOntology.ts` — wraps ontology.service
   - `useSHACL.ts` — wraps validation.service

9. Wire into apps:
   - `apps/engineer/routes.tsx`: add all 7 components under `/engineer/semantic/*`
   - `apps/admin/routes.tsx`: add OntologyManager, GraphQLPlayground, ExpressExplorer, OSLCBrowser under `/admin/semantic/*`

CONSTRAINTS:
- Use shadcn/ui: Card, Tabs, Select, Textarea, Button, Dialog, Badge, ScrollArea, Tree (custom).
- For code editing (GraphQL, SHACL), use a `<textarea>` with monospace font — keep it simple.
- `npm run build` must succeed.
```

---

## PROMPT 11: Digital Thread + Role UI + AI Chatbot (Phase 6)

```
CONTEXT: I am working on the MBSEsmrl project. Read `docs/SDD_MODULAR_ARCHITECTURE_PLAN.md` (v4.0) — Phase 6 roadmap, Part 4.3 (Digital Thread Relationships), and Part 2 gaps G1, G7.

TASK: Execute Phase 6 — Digital Thread Integration, Role-Based UI completion, and AI Chatbot.

1. **Digital Thread Navigation** — Upgrade `GraphBrowser.jsx`:
   - Add a "Digital Thread" view mode (toggle alongside existing "Force-Directed" mode)
   - In Digital Thread mode, show a linear flow: Dossier → SimulationRun → SimulationModel → CADModel → Part → Requirement
   - Color-code relationship types:
     - GENERATED_FROM = blue, USES_MODEL = purple, REPRESENTS = green
     - PROVES_COMPLIANCE_TO = orange, GOVERNS = red
     - HAS_APPROVAL = gold, HAS_FINDING = amber
   - Click any node to navigate to its detail page
   - Add breadcrumb trail showing the current path through the digital thread

2. **Authoring Mode** — Add to `DossierDetail`:
   - "Link Entity" button opens a search dialog (searches all node types in the graph)
   - User selects a node and a relationship type (from a dropdown of valid relationship types for that pair)
   - Creates the relationship in Neo4j via the existing `graph.service`
   - Updates the MOSSEC inspector in real-time

3. **TraceabilityMatrix Integration**:
   - Embed `MossecInspector` as a right-side panel in `TraceabilityMatrix`
   - Clicking a cell in the matrix opens the inspector showing the MOSSEC link details
   - Add filter: show only links related to a specific dossier

4. **Role-Based UI Polish** [G1]:
   - Verify all 3 app layouts (engineer, quality, admin) have complete sidebars
   - Ensure the RoleSelector appears in the header of all layouts
   - Add role-specific welcome messages on each dashboard
   - Quality layout: show pending approval count badge on sidebar
   - Engineer layout: show active simulation count on sidebar
   - Admin layout: show system health status indicator on sidebar

5. **Floating AI Chatbot** [G7]:
   - Create `frontend/src/features/ai-studio/components/Chatbot.tsx`
   - Floating action button (bottom-right corner) that opens a chat drawer
   - Sends messages to `POST /api/agents/orchestrator/run` with context about current page
   - Displays responses with Markdown rendering
   - Context injection: when user is on a dossier page, automatically include dossier ID and status in the prompt
   - History: keep conversation in session state
   - Add to all 3 app layouts as a global floating component

6. **Product Specification Page** [G10]:
   - Create `frontend/src/features/systems-engineering/components/ProductSpecs.tsx`
   - Display product parameters table (name, value, unit, tolerance)
   - System constraints list
   - Linked graphview: show which dossiers, models, and parts relate to this spec
   - Wire to `apps/engineer/routes.tsx` as `/engineer/product-specs`

FINAL VERIFICATION:
- `npm run build` — zero errors
- `npm run test` — all tests pass
- Manually verify: switch between all 3 roles and confirm correct sidebar, routes, and features
- Verify digital thread: navigate Dossier → Run → Model → Part from the graph browser

CONSTRAINTS:
- The Chatbot must not block the main UI (use a portal or absolute positioning).
- Digital Thread view should work with existing graph data — degrade gracefully if relationships don't exist.
- All new routes must be added to the respective apps/ routes files.
```

---

## PROMPT 12: Final Cleanup + Verification (Post-Implementation)

```
CONTEXT: I am working on the MBSEsmrl project. All 6 phases of the v4.0 architecture plan have been implemented.

TASK: Final cleanup and comprehensive verification.

1. **Delete old directories**:
   - Remove `frontend/src/pages/` (all pages now in `features/`)
   - Remove `backend/src/web/routers/` (all routers now in `functions/`)
   - Clean up any dead imports or unused files

2. **Update root configuration**:
   - Update `frontend/vite.config.ts` if path aliases need updating
   - Update `frontend/tsconfig.json` paths for `@/features/*` and `@/apps/*`
   - Update `backend/setup.py` if package structure changed

3. **Update README.md**:
   - Document the new project structure (features/, apps/, functions/, core/)
   - Update startup instructions
   - Add role-based access section (Engineer, Quality Head, Admin)

4. **Update INSTALL.md**:
   - Add migration steps for existing installations
   - Document new environment variables if any

5. **Run full test suite**:
   - Backend: `cd backend && python -m pytest tests/ -v`
   - Frontend: `cd frontend && npm run test`
   - Frontend build: `cd frontend && npm run build`
   - Backend lint: `cd backend && python -m flake8 src/`

6. **Endpoint verification** — Write a quick smoke test:
   - Start backend: `uvicorn src.main:app --host 0.0.0.0 --port 5000`
   - Hit 5 representative endpoints from different function domains:
     - `GET /api/simulation/dossiers` (sdd_service)
     - `GET /api/v1/Requirement` (smrl_service)
     - `GET /oslc/rootservices` (oslc_service)
     - `GET /api/graph/node-types` (graph_service)
     - `GET /api/metrics/health` (telemetry_service)

7. **Git cleanup**: Stage all changes and create a clean commit message summarizing the v4.0 restructuring.

CONSTRAINTS:
- Do NOT delete the v4.0 plan (`docs/SDD_MODULAR_ARCHITECTURE_PLAN.md`).
- Ensure backwards-compatible API URLs (same prefixes as before).
```

---

## Quick Reference: Prompt Execution Order

| Order | Prompt | Phase | Depends On | Est. Effort |
|-------|--------|-------|------------|-------------|
| 1 | Core Extraction | 1a | — | Medium |
| 2 | FaaS Structure | 1b | Prompt 1 | Large |
| 3 | New Services | 1c | Prompt 2 | Medium |
| 4 | Neo4j Schema | 2 | Prompt 3 | Small |
| 5 | Frontend FSD Migration | 3a | — | Medium |
| 6 | Apps + Role Routing | 3b | Prompt 5 | Medium |
| 7 | Service Layer Split | 3c | Prompt 5 | Medium |
| 8 | Audit/Approval/Evidence UI | 4a | Prompts 3, 6, 7 | Large |
| 9 | Dashboards + Terminal UI | 4b | Prompts 6, 7 | Medium |
| 10 | Semantic Web UI | 5 | Prompts 6, 7 | Large |
| 11 | Digital Thread + Role + Chatbot | 6 | Prompts 8, 9, 10 | Large |
| 12 | Final Cleanup | Post | All above | Small |

**Prompts 1-4 (Backend) and 5-7 (Frontend) can run in parallel tracks.**
