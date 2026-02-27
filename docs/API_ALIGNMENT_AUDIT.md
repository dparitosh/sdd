# Frontend ↔ Backend API Alignment Audit

**Generated:** 2025-01  
**Scope:** All frontend service files (`frontend/src/services/*.ts`) vs. backend FastAPI routes (`backend/src/web/routes/*_fastapi.py`) + app mount (`backend/src/web/app_fastapi.py`)

> **Conventions:**  
> - Frontend `apiClient` prepends **`/api`** (from `API_CONFIG.BASE_URL`).  
> - All frontend paths listed below show what the browser actually sends (already includes `/api`).  
> - Backend "Final URL" = `app.include_router(prefix=…)` + `router(prefix=…)` + `@router.method("/path")`.

---

## Legend

| Tag | Meaning |
|---|---|
| **ALIGNED** | Path, HTTP method, and payload shape all match |
| **MISALIGNED** | Route exists on both sides but path, method, or payload shape differs |
| **MISSING_BACKEND** | Frontend calls an endpoint that has **no** backend implementation |
| **MISSING_FRONTEND** | Backend exposes an endpoint that **no** frontend service calls |

---

## 1. Standards Service (`standards.service.ts`)

### AP239 — Backend: `ap239_fastapi.py` → mounted at `/api/ap239`

| # | Frontend Call | Method | Backend Endpoint | Status | Notes |
|---|---|---|---|---|---|
| 1 | `/api/ap239/requirements` | GET | `/api/ap239/requirements` | **ALIGNED** | params: `type`, `status`, `priority`, `search` |
| 2 | `/api/ap239/requirements/{id}` | GET | `/api/ap239/requirements/{id}` | **ALIGNED** | |
| 3 | `/api/ap239/requirements/{id}/traceability` | GET | `/api/ap239/requirements/{id}/traceability` | **ALIGNED** | |
| 4 | `/api/ap239/requirements/traceability/bulk` | POST | `/api/ap239/requirements/traceability/bulk` | **ALIGNED** | body: `{requirement_ids}` |
| 5 | `/api/ap239/approvals` | GET | `/api/ap239/approvals` | **ALIGNED** | |
| 6 | `/api/ap239/analyses` | GET | `/api/ap239/analyses` | **ALIGNED** | |
| 7 | `/api/ap239/documents` | GET | `/api/ap239/documents` | **ALIGNED** | |
| 8 | `/api/ap239/statistics` | GET | `/api/ap239/statistics` | **ALIGNED** | |

### AP242 — Backend: `ap242_fastapi.py` → mounted at `/api/ap242`

| # | Frontend Call | Method | Backend Endpoint | Status | Notes |
|---|---|---|---|---|---|
| 9 | `/api/ap242/parts` | GET | `/api/ap242/parts` | **ALIGNED** | params: `status`, `search` |
| 10 | `/api/ap242/parts/{id}` | GET | `/api/ap242/parts/{id}` | **ALIGNED** | |
| 11 | `/api/ap242/parts/{id}/bom` | GET | `/api/ap242/parts/{id}/bom` | **ALIGNED** | |
| 12 | `/api/ap242/materials` | GET | `/api/ap242/materials` | **ALIGNED** | params: `type`, `search` |
| 13 | `/api/ap242/materials/{name}` | GET | `/api/ap242/materials/{name}` | **ALIGNED** | |
| 14 | `/api/ap242/assemblies` | GET | `/api/ap242/assemblies` | **ALIGNED** | |
| 15 | `/api/ap242/geometry` | GET | `/api/ap242/geometry` | **ALIGNED** | |
| 16 | `/api/ap242/statistics` | GET | `/api/ap242/statistics` | **ALIGNED** | |

### AP243 — Backend: `ap243_fastapi.py` → mounted at `/api/ap243`

| # | Frontend Call | Method | Backend Endpoint | Status | Notes |
|---|---|---|---|---|---|
| 17 | `/api/ap243/overview` | GET | `/api/ap243/overview` | **ALIGNED** | |
| 18 | `/api/ap243/domain-classes` | GET | `/api/ap243/domain-classes` | **ALIGNED** | params: `search`, `stereotype`, `is_abstract`, `package`, `skip`, `limit` |
| 19 | `/api/ap243/domain-classes/{name}` | GET | `/api/ap243/domain-classes/{name}` | **ALIGNED** | |
| 20 | `/api/ap243/domain-search` | GET | `/api/ap243/domain-search` | **ALIGNED** | params: `q`, `node_type`, `skip`, `limit` |
| 21 | `/api/ap243/packages` | GET | `/api/ap243/packages` | **ALIGNED** | |
| 22 | `/api/ap243/stereotypes` | GET | `/api/ap243/stereotypes` | **ALIGNED** | |
| 23 | `/api/ap243/ontologies` | GET | `/api/ap243/ontologies` | **ALIGNED** | params: `ontology`, `search` |
| 24 | `/api/ap243/ontologies/{name}` | GET | `/api/ap243/ontologies/{name}` | **ALIGNED** | |
| 25 | `/api/ap243/units` | GET | `/api/ap243/units` | **ALIGNED** | |
| 26 | `/api/ap243/units/{id}` | GET | `/api/ap243/units/{id}` | **ALIGNED** | |
| 27 | `/api/ap243/value-types` | GET | `/api/ap243/value-types` | **ALIGNED** | |
| 28 | `/api/ap243/classifications` | GET | `/api/ap243/classifications` | **ALIGNED** | params: `system` |
| 29 | `/api/ap243/statistics` | GET | `/api/ap243/statistics` | **ALIGNED** | |

### SMRL v1 — Backend: `smrl_v1_fastapi.py` → mounted at `/api/v1`

| # | Frontend Call | Method | Backend Endpoint | Status | Notes |
|---|---|---|---|---|---|
| 30 | `/api/v1/{type}/{uid}` | GET | `/api/v1/{resource_type}/{uid}` | **ALIGNED** | |
| 31 | `/api/v1/{type}` | GET | `/api/v1/{resource_type}` | **ALIGNED** | params: `limit`, `offset` |
| 32 | `/api/v1/{type}` | POST | `/api/v1/{resource_type}` | **ALIGNED** | |
| 33 | `/api/v1/{type}/{uid}` | PUT | `/api/v1/{resource_type}/{uid}` | **ALIGNED** | |
| 34 | `/api/v1/{type}/{uid}` | PATCH | `/api/v1/{resource_type}/{uid}` | **ALIGNED** | |
| 35 | `/api/v1/{type}/{uid}` | DELETE | `/api/v1/{resource_type}/{uid}` | **ALIGNED** | |

---

## 2. Graph Service (`graph.service.ts`)

### Backend: `graph_fastapi.py` → mounted at `/api/graph`

| # | Frontend Call | Method | Backend Endpoint | Status | Notes |
|---|---|---|---|---|---|
| 36 | `/api/graph/data` | GET | `/api/graph/data` | **ALIGNED** | params: `limit`, `node_types`, `ap_level` |
| 37 | `/api/graph/node-types` | GET | `/api/graph/node-types` | **ALIGNED** | |
| 38 | `/api/graph/relationship-types` | GET | `/api/graph/relationship-types` | **ALIGNED** | |
| 39 | `/api/graph/search` | GET | **— NONE —** | **MISSING_BACKEND** | Frontend sends `GET /api/graph/search?q=…&node_type=…&limit=…`. No such endpoint exists in `graph_fastapi.py`. A similar `GET /api/search` exists in `core_fastapi.py`, but the path doesn't match. |
| 40 | `/api/graph/relationships` | POST | **— NONE —** | **MISSING_BACKEND** | Frontend sends `POST /api/graph/relationships` with body `{source_id, target_id, relationship_type, properties}`. No such endpoint exists anywhere in the backend. |

### Backend: `hierarchy_fastapi.py` → mounted at `/api/hierarchy`

| # | Frontend Call | Method | Backend Endpoint | Status | Notes |
|---|---|---|---|---|---|
| 41 | `/api/hierarchy/navigate/{nodeType}/{nodeId}` | GET | `/api/hierarchy/navigate/{node_type}/{node_id}` | **ALIGNED** | params: `depth`, `direction` |
| 42 | `/api/hierarchy/traceability-matrix` | GET | `/api/hierarchy/traceability-matrix` | **ALIGNED** | |
| 43 | `/api/hierarchy/search` | GET | `/api/hierarchy/search` | **ALIGNED** | params: `q`, `levels` |
| 44 | `/api/hierarchy/impact/{nodeType}/{nodeId}` | GET | `/api/hierarchy/impact/{node_type}/{node_id}` | **ALIGNED** | |

---

## 3. Agents Service (`agents.service.ts`)

### Backend: `agents_fastapi.py` → mounted at `/api/agents`

| # | Frontend Call | Method | Backend Endpoint | Status | Notes |
|---|---|---|---|---|---|
| 45 | `/api/agents/orchestrator/run` | POST | `/api/agents/orchestrator/run` | **ALIGNED** | body: `{query, task_type}` |

---

## 4. Simulation Service (`simulation.service.ts`)

### Backend: `simulation_fastapi.py` → router prefix `/simulation`, app prefix `/api`

| # | Frontend Call | Method | Backend Endpoint | Status | Notes |
|---|---|---|---|---|---|
| 46 | `/api/simulation/models` | GET | `/api/simulation/models` | **ALIGNED** | |
| 47 | `/api/simulation/runs` | GET | `/api/simulation/runs` | **ALIGNED** | params: `dossier_id`, `run_status`, `sim_type`, `limit` |
| 48 | `/api/simulation/runs/{id}` | GET | `/api/simulation/runs/{id}` | **ALIGNED** | |
| 49 | `/api/simulation/runs` | POST | `/api/simulation/runs` | **ALIGNED** | |
| 50 | `/api/simulation/results` | GET | `/api/simulation/results` | **ALIGNED** | |
| 51 | `/api/simulation/parameters` | GET | `/api/simulation/parameters` | **ALIGNED** | params: `class_name`, `property_name`, `data_type`, `include_constraints`, `limit` |
| 52 | `/api/simulation/validate` | POST | `/api/simulation/validate` | **ALIGNED** | body: `{parameters}` |
| 53 | `/api/simulation/units` | GET | `/api/simulation/units` | **ALIGNED** | |

---

## 5. SDD (Simulation Data Dossier) Service (`sdd.service.ts`)

### Backend: `simulation_fastapi.py` (same router)

| # | Frontend Call | Method | Backend Endpoint | Status | Notes |
|---|---|---|---|---|---|
| 54 | `/api/simulation/dossiers` | GET | `/api/simulation/dossiers` | **ALIGNED** | |
| 55 | `/api/simulation/dossiers/{id}` | GET | `/api/simulation/dossiers/{id}` | **ALIGNED** | |
| 56 | `/api/simulation/dossiers` | POST | `/api/simulation/dossiers` | **ALIGNED** | |
| 57 | `/api/simulation/dossiers/{id}` | PATCH | `/api/simulation/dossiers/{id}` | **ALIGNED** | |
| 58 | `/api/simulation/artifacts` | GET | `/api/simulation/artifacts` | **ALIGNED** | |
| 59 | `/api/simulation/artifacts/{id}` | GET | `/api/simulation/artifacts/{id}` | **ALIGNED** | |
| 60 | `/api/simulation/statistics` | GET | `/api/simulation/statistics` | **ALIGNED** | |
| 61 | `/api/simulation/trace/{requirementId}` | GET | `/api/simulation/trace/{requirement_id}` | **ALIGNED** | |

---

## 6. Audit Service (`audit.service.ts`)

### Backend: `simulation_fastapi.py` — **NO matching endpoints**

| # | Frontend Call | Method | Backend Endpoint | Status | Notes |
|---|---|---|---|---|---|
| 62 | `/api/simulation/dossiers/{dossierId}/audit` | POST | **— NONE —** | **MISSING_BACKEND** | No audit trigger endpoint exists in `simulation_fastapi.py` or anywhere else. |
| 63 | `/api/simulation/dossiers/{dossierId}/audit` | GET | **— NONE —** | **MISSING_BACKEND** | No audit findings retrieval endpoint exists. |

---

## 7. Approval Service (`approval.service.ts`)

### Backend: `simulation_fastapi.py` — **NO matching endpoints**

| # | Frontend Call | Method | Backend Endpoint | Status | Notes |
|---|---|---|---|---|---|
| 64 | `/api/simulation/dossiers/{dossierId}/approve` | POST | **— NONE —** | **MISSING_BACKEND** | No approval submission endpoint exists. |
| 65 | `/api/simulation/dossiers/{dossierId}/approvals` | GET | **— NONE —** | **MISSING_BACKEND** | No approval history endpoint exists. |

---

## 8. OSLC Service (`oslc.service.ts`)

### TRS — Backend: `trs_fastapi.py` → router prefix `/oslc/trs`, app prefix `/api`

| # | Frontend Call | Method | Backend Endpoint | Status | Notes |
|---|---|---|---|---|---|
| 66 | `/api/oslc/trs/base?page=…` | GET | `/api/oslc/trs/base` | **ALIGNED** | |
| 67 | `/api/oslc/trs/changelog` | GET | `/api/oslc/trs/changelog` | **ALIGNED** | |
| 68 | `/api/oslc/trs` | GET | `/api/oslc/trs` | **ALIGNED** | (router GET `""`) |

### OSLC Client — Backend: `oslc_client_fastapi.py` → router prefix `/oslc/client`, app prefix `/api`

| # | Frontend Call | Method | Backend Endpoint | Status | Notes |
|---|---|---|---|---|---|
| 69 | `/api/oslc/client/connect` | POST | `/api/oslc/client/connect` | **MISALIGNED** | **Body shape mismatch.** Frontend sends `{root_url, auth_type, username, password}`. Backend `ConnectRequest` expects `{url, username, password}`. Field `root_url` ≠ `url`; `auth_type` is not accepted. |
| 70 | `/api/oslc/client/query` | POST | `/api/oslc/client/query` | **MISALIGNED** | **Body shape mismatch.** Frontend sends `{provider_url, resource_type, query}`. Backend `QueryRequest` expects `{query_capability_url, oslc_where, username, password}`. Fields are entirely different. |

### OSLC Discovery — Backend: `oslc_fastapi.py` → router prefix `/oslc`, **NO** app prefix

| # | Frontend Call | Method | Backend Endpoint | Status | Notes |
|---|---|---|---|---|---|
| 71 | `/api/oslc/rootservices` | GET | `/oslc/rootservices` | **MISALIGNED** | **Path mismatch.** Frontend sends to `/api/oslc/rootservices` (via `apiClient`). Backend mounts OSLC router **without** `/api` prefix, so the actual endpoint is `/oslc/rootservices`. The request will 404. |
| 72 | `/api/oslc/catalog` | GET | `/oslc/catalog` | **MISALIGNED** | Same issue — `/api/oslc/catalog` vs `/oslc/catalog`. |
| 73 | `/api/oslc/providers/{providerId}` | GET | **— NONE —** | **MISSING_BACKEND** | Backend has `/oslc/sp/{project_id}` instead. Even if the prefix matched, the path segment differs (`providers` vs `sp`). |

---

## 9. Upload Service (`upload.service.ts`)

### Backend: `upload_fastapi.py` → router prefix `/api/upload` (no app prefix)

| # | Frontend Call | Method | Backend Endpoint | Status | Notes |
|---|---|---|---|---|---|
| 74 | `/api/upload/` | POST | `/api/upload/` | **ALIGNED** | multipart file upload |
| 75 | `/api/upload/status/{jobId}` | GET | `/api/upload/status/{job_id}` | **ALIGNED** | |
| 76 | `/api/upload/jobs` | GET | `/api/upload/jobs` | **ALIGNED** | |

---

## 10. Validation Service (`validation.service.ts`)

### Backend: `shacl_fastapi.py` → router prefix `/api/validate` (no app prefix)

| # | Frontend Call | Method | Backend Endpoint | Status | Notes |
|---|---|---|---|---|---|
| 77 | `/api/validation/shacl` | POST | `/api/validate/shacl` | **MISALIGNED** | **Path mismatch.** Frontend calls `/api/validation/shacl`; backend is at `/api/validate/shacl`. Will 404. |

---

## 11. Ontology Service (`ontology.service.ts`)

### Backend: `ontology_ingest_fastapi.py` → router prefix `/api/ontology` (no app prefix)

| # | Frontend Call | Method | Backend Endpoint | Status | Notes |
|---|---|---|---|---|---|
| 78 | `/api/ontology/ingest` | POST | `/api/ontology/ingest` | **ALIGNED** | multipart file upload |
| 79 | `/api/ontology` | GET | **— NONE —** | **MISSING_BACKEND** | Frontend calls `GET /api/ontology` to list ontologies. Backend only has `POST /api/ontology/ingest`. No list endpoint. |

---

## 12. Export Service (`export.service.ts`)

### Backend: `export_fastapi.py` → router prefix `/export`, app prefix `/api`

| # | Frontend Call | Method | Backend Endpoint | Status | Notes |
|---|---|---|---|---|---|
| 80 | `/api/export/schema` | GET | `/api/export/schema` | **ALIGNED** | |
| 81 | `/api/export/graphml` | GET | `/api/export/graphml` | **ALIGNED** | |
| 82 | `/api/export/jsonld` | GET | `/api/export/jsonld` | **ALIGNED** | |
| 83 | `/api/export/csv` | GET | `/api/export/csv` | **ALIGNED** | |
| 84 | `/api/export/step` | GET | `/api/export/step` | **ALIGNED** | |
| 85 | `/api/export/plantuml` | GET | `/api/export/plantuml` | **ALIGNED** | |
| 86 | `/api/export/rdf` | GET | `/api/export/rdf` | **ALIGNED** | |
| 87 | `/api/export/cytoscape` | GET | `/api/export/cytoscape` | **ALIGNED** | |

---

## 13. EXPRESS Service (`express.service.ts`)

### Backend: `express_parser_fastapi.py` → router prefix `/express`, app prefix `/api`

| # | Frontend Call | Method | Backend Endpoint | Status | Notes |
|---|---|---|---|---|---|
| 88 | `/api/express/parse` | POST | `/api/express/parse/upload` | **MISALIGNED** | **Path mismatch.** Frontend POSTs multipart to `/api/express/parse`. Backend has `/parse/file`, `/parse/content`, `/parse/upload`, `/parse/directory` — but no bare `/parse`. Closest is `/parse/upload`. |
| 89 | `/api/express/query` | GET | `/api/express/query/entities` (POST) | **MISALIGNED** | **Method + path mismatch.** Frontend sends `GET /api/express/query?schema=…&entity=…`. Backend has `POST /api/express/query/entities` and `POST /api/express/query/types` — wrong HTTP method and wrong sub-path. |
| 90 | `/api/express/analyze` | POST | `/api/express/analyze/statistics` (POST) | **MISALIGNED** | **Path mismatch.** Frontend POSTs `{schema}` to `/api/express/analyze`. Backend has `/analyze/statistics`, `/analyze/inheritance`, `/analyze/type-usage`, `/analyze/select-usage` — no bare `/analyze`. |
| 91 | `/api/express/export/{schema}` | GET | `/api/express/export/json` (POST) | **MISALIGNED** | **Method + path mismatch.** Frontend sends `GET /api/express/export/{schema}`. Backend has `POST /api/express/export/json`, `POST /api/express/export/markdown`, `POST /api/express/export/graphml` — POST, not GET, and different path structure (`/export/{format}` not `/export/{schema}`). |

---

## 14. Query Service (`query.service.ts`)

### Backend: `core_fastapi.py` → mounted at `/api`

| # | Frontend Call | Method | Backend Endpoint | Status | Notes |
|---|---|---|---|---|---|
| 92 | `/api/cypher` | POST | `/api/cypher` | **ALIGNED** | body: `{query, params}` |
| 93 | `/api/artifacts` | GET | `/api/artifacts` | **ALIGNED** | |
| 94 | `/api/artifacts/{type}/{id}` | GET | `/api/artifacts/{artifact_type}/{artifact_id}` | **ALIGNED** | |
| 95 | `/api/health` | GET | `/api/health` | **ALIGNED** | Defined directly on `app` in `app_fastapi.py` |
| 96 | `/api/stats` | GET | `/api/stats` | **ALIGNED** | |

---

## 15. Auth Service (`auth.service.ts`)

### Backend: `auth_fastapi.py` → router prefix `/auth`, app prefix `/api`

| # | Frontend Call | Method | Backend Endpoint | Status | Notes |
|---|---|---|---|---|---|
| 97 | `/api/auth/login` | POST | `/api/auth/login` | **ALIGNED** | |
| 98 | `/api/auth/refresh` | POST | `/api/auth/refresh` | **ALIGNED** | |
| 99 | `/api/auth/logout` | POST | `/api/auth/logout` | **ALIGNED** | |
| 100 | `/api/auth/verify` | GET | `/api/auth/verify` | **ALIGNED** | |
| 101 | `/api/auth/change-password` | POST | `/api/auth/change-password` | **ALIGNED** | |
| 102 | `/api/auth/sessions` | GET | **— NONE —** | **MISALIGNED** | **Path mismatch.** Frontend calls `GET /api/auth/sessions`. Backend session listing is at `GET /api/sessions/me` (in `sessions_fastapi.py`). No endpoint at `/auth/sessions`. |
| 103 | `/api/auth/admin/sessions` | GET | **— NONE —** | **MISALIGNED** | **Path mismatch.** Frontend calls `GET /api/auth/admin/sessions`. Backend admin session endpoints are at `GET /api/sessions/stats` and `GET /api/sessions/user/{username}` (in `sessions_fastapi.py`). |
| 104 | `/api/auth/sessions/{sessionId}` | DELETE | **— NONE —** | **MISALIGNED** | **Path mismatch.** Frontend calls `DELETE /api/auth/sessions/{id}`. Backend equivalent is `DELETE /api/sessions/me/{session_id}`. |

---

## 16. Metrics Service (`metrics.ts`)

### Backend: `metrics_fastapi.py` → mounted at `/api/metrics`

| # | Frontend Call | Method | Backend Endpoint | Status | Notes |
|---|---|---|---|---|---|
| 105 | `/api/metrics/summary` | GET | `/api/metrics/summary` | **ALIGNED** | |
| 106 | `/api/metrics/history` | GET | `/api/metrics/history` | **ALIGNED** | |
| 107 | `/api/metrics/health` | GET | `/api/metrics/health` | **ALIGNED** | |

---

## 17. GraphQL Service (`graphql.ts`)

### Backend: `graphql_fastapi.py` → Strawberry `GraphQLRouter` mounted at `/api/graphql`

| # | Frontend Call | Method | Backend Endpoint | Status | Notes |
|---|---|---|---|---|---|
| 108 | `/api/graphql` | POST | `/api/graphql` | **ALIGNED** | Standard GraphQL POST with `{query, variables}` |

---

## 18. PLM Service (`plm.ts`)

### Backend: `plm_connectors_fastapi.py` → mounted at `/api/v1/plm`

| # | Frontend Call | Method | Backend Endpoint | Status | Notes |
|---|---|---|---|---|---|
| 109 | `/api/v1/plm/connectors` | GET | `/api/v1/plm/connectors` | **ALIGNED** | |
| 110 | `/api/v1/plm/connectors/{connectorId}/sync` | POST | `/api/v1/plm/connectors/{connector_id}/sync` | **ALIGNED** | |
| 111 | `/api/v1/plm/connectors/{connectorId}/status` | GET | `/api/v1/plm/connectors/{connector_id}/status` | **ALIGNED** | |

---

## 19. WebSocket Service (`websocket.ts`)

This service uses native `WebSocket`, not `apiClient`. It connects to `ws://…/ws` or similar. Backend WebSocket support needs separate verification (not REST-based), so it is **out of scope** for this REST audit.

---

## 20. Backend-Only Endpoints (MISSING_FRONTEND)

These backend routes have **no corresponding frontend service call**:

### `core_fastapi.py` → `/api`

| # | Endpoint | Method | Notes |
|---|---|---|---|
| F1 | `/api/packages` | GET | No frontend caller |
| F2 | `/api/package/{id}` | GET | No frontend caller |
| F3 | `/api/classes` | GET | No frontend caller |
| F4 | `/api/class/{id}` | GET | No frontend caller |
| F5 | `/api/search` | GET | Exists at `/api/search`; frontend graph.service calls `/api/graph/search` instead |
| F6 | `/api/search` | POST | Same issue — POST variant also unused by frontend |

### `smrl_v1_fastapi.py` → `/api/v1`

| # | Endpoint | Method | Notes |
|---|---|---|---|
| F7 | `/api/v1/health` | GET | |
| F8 | `/api/v1/traceability` | GET | |
| F9 | `/api/v1/parameters` | GET | |
| F10 | `/api/v1/constraints` | GET | |
| F11 | `/api/v1/composition/{node_id}` | GET | |
| F12 | `/api/v1/impact/{node_id}` | GET | |
| F13 | `/api/v1/versions/{node_id}` | GET | |
| F14 | `/api/v1/diff` | POST | |
| F15 | `/api/v1/history/{node_id}` | GET | |
| F16 | `/api/v1/checkpoint` | POST | |
| F17 | `/api/v1/match` | POST | |

### `hierarchy_fastapi.py` → `/api/hierarchy`

| # | Endpoint | Method | Notes |
|---|---|---|---|
| F18 | `/api/hierarchy/statistics` | GET | |

### `simulation_fastapi.py` → `/api/simulation`

(All simulation endpoints have frontend callers — none missing.)

### `sessions_fastapi.py` → `/api/sessions`

| # | Endpoint | Method | Notes |
|---|---|---|---|
| F19 | `/api/sessions/me` | GET | Frontend calls `/api/auth/sessions` instead |
| F20 | `/api/sessions/me/{session_id}` | DELETE | Frontend calls `/api/auth/sessions/{id}` instead |
| F21 | `/api/sessions/me/all` | DELETE | No frontend caller |
| F22 | `/api/sessions/stats` | GET | Frontend calls `/api/auth/admin/sessions` instead |
| F23 | `/api/sessions/user/{username}` | GET | No frontend caller |
| F24 | `/api/sessions/user/{username}` | DELETE | No frontend caller |
| F25 | `/api/sessions/cleanup` | POST | No frontend caller |

### `oslc_fastapi.py` → `/oslc`

| # | Endpoint | Method | Notes |
|---|---|---|---|
| F26 | `/oslc/sp/{project_id}` | GET | Frontend calls `/api/oslc/providers/{id}` instead |
| F27 | `/oslc/rm/requirements` | GET | No frontend caller |
| F28 | `/oslc/rm/requirements` | POST | No frontend caller |
| F29 | `/oslc/dialogs/rm/select` | GET | No frontend caller |

### `plm_fastapi.py` → `/api/plm`

| # | Endpoint | Method | Notes |
|---|---|---|---|
| F30 | `/api/plm/*` (5 endpoints) | GET | PLM integration router; frontend uses `/api/v1/plm/` (connectors), not `/api/plm/` |

### `express_parser_fastapi.py` → `/api/express`

| # | Endpoint | Method | Notes |
|---|---|---|---|
| F31 | `/api/express/parse/file` | POST | Frontend calls bare `/express/parse` |
| F32 | `/api/express/parse/content` | POST | No frontend caller |
| F33 | `/api/express/parse/directory` | POST | No frontend caller |
| F34 | `/api/express/query/types` | POST | No frontend caller |
| F35 | `/api/express/analyze/inheritance` | POST | No frontend caller |
| F36 | `/api/express/analyze/type-usage` | POST | No frontend caller |
| F37 | `/api/express/analyze/select-usage` | POST | No frontend caller |
| F38 | `/api/express/export/markdown` | POST | No frontend caller |
| F39 | `/api/express/export/graphml` | POST | No frontend caller |
| F40 | `/api/express/neo4j/cypher` | POST | No frontend caller |
| F41 | `/api/express/neo4j/graph` | POST | No frontend caller |
| F42 | `/api/express/info` | GET | No frontend caller |
| F43 | `/api/express/health` | GET | No frontend caller |
| F44 | `/api/express/` | GET | No frontend caller |

### `shacl_fastapi.py` → `/api/validate`

| # | Endpoint | Method | Notes |
|---|---|---|---|
| F45 | `/api/validate/shacl/inline` | POST | No frontend caller |

### `upload_fastapi.py` → `/api/upload`

| # | Endpoint | Method | Notes |
|---|---|---|---|
| F46 | `/api/upload/job/{job_id}` | DELETE | No frontend caller |
| F47 | `/api/upload/health` | GET | No frontend caller |

### `version_fastapi.py` → `/api/version`

| # | Endpoint | Method | Notes |
|---|---|---|---|
| F48 | `/api/version/*` | Various | No frontend caller |

### `cache_fastapi.py` → `/api/cache`

| # | Endpoint | Method | Notes |
|---|---|---|---|
| F49 | `/api/cache/*` | Various | No frontend caller |

### `admin_fastapi.py` → `/api/admin`

| # | Endpoint | Method | Notes |
|---|---|---|---|
| F50 | `/api/admin/*` | Various | No frontend caller |

### `step_ingest_fastapi.py` → `/api/step`

| # | Endpoint | Method | Notes |
|---|---|---|---|
| F51 | `/api/step/*` | Various | No frontend caller |

---

## Summary

### Counts

| Category | Count |
|---|---|
| **ALIGNED** | 82 |
| **MISALIGNED** | 11 |
| **MISSING_BACKEND** (frontend calls nonexistent endpoint) | 6 |
| **MISSING_FRONTEND** (backend endpoint with no frontend caller) | ~51 |

### Critical Issues (will cause runtime 404s or request failures)

| Priority | Issue | Frontend File | Fix Recommendation |
|---|---|---|---|
| **P0** | `GET /api/graph/search` → no backend | `graph.service.ts` | Either add `GET /search` to `graph_fastapi.py`, or change frontend to call `GET /api/search` (core). |
| **P0** | `POST /api/graph/relationships` → no backend | `graph.service.ts` | Add `POST /relationships` to `graph_fastapi.py`. |
| **P0** | `POST /api/simulation/dossiers/{id}/audit` → no backend | `audit.service.ts` | Implement audit endpoint in `simulation_fastapi.py`. |
| **P0** | `GET /api/simulation/dossiers/{id}/audit` → no backend | `audit.service.ts` | Implement audit findings endpoint in `simulation_fastapi.py`. |
| **P0** | `POST /api/simulation/dossiers/{id}/approve` → no backend | `approval.service.ts` | Implement approval endpoint in `simulation_fastapi.py`. |
| **P0** | `GET /api/simulation/dossiers/{id}/approvals` → no backend | `approval.service.ts` | Implement approval history endpoint in `simulation_fastapi.py`. |
| **P0** | `POST /api/validation/shacl` → should be `/api/validate/shacl` | `validation.service.ts` | Change frontend path from `/validation/shacl` to `/validate/shacl`. |
| **P0** | `GET /api/oslc/rootservices` → backend at `/oslc/rootservices` | `oslc.service.ts` | Either mount `oslc_router` with app prefix `/api`, or change frontend to not use `apiClient` for these calls. |
| **P0** | `GET /api/oslc/catalog` → backend at `/oslc/catalog` | `oslc.service.ts` | Same fix as above. |
| **P0** | `GET /api/oslc/providers/{id}` → no backend (closest: `/oslc/sp/{id}`) | `oslc.service.ts` | Rename backend to `/providers/{id}` + fix mount prefix; or update frontend. |
| **P1** | OSLC client `/connect` body: `root_url` vs `url` | `oslc.service.ts` | Align field names between frontend and `ConnectRequest` Pydantic model. |
| **P1** | OSLC client `/query` body: completely different fields | `oslc.service.ts` | Redesign one side to match the other. |
| **P1** | Auth sessions path: `/api/auth/sessions` vs `/api/sessions/me` | `auth.service.ts` | Change frontend to call `/sessions/me`, `/sessions/me/{id}`, etc. |
| **P1** | Auth admin sessions: `/api/auth/admin/sessions` vs `/api/sessions/stats` | `auth.service.ts` | Change frontend to call `/sessions/stats`. |
| **P1** | EXPRESS parse: `POST /api/express/parse` vs `/api/express/parse/upload` | `express.service.ts` | Change frontend to call `/express/parse/upload`. |
| **P1** | EXPRESS query: `GET /api/express/query` vs `POST /api/express/query/entities` | `express.service.ts` | Change frontend to POST to `/express/query/entities`. |
| **P1** | EXPRESS analyze: `POST /api/express/analyze` vs `/api/express/analyze/statistics` | `express.service.ts` | Change frontend to call `/express/analyze/statistics`. |
| **P1** | EXPRESS export: `GET /api/express/export/{schema}` vs `POST /api/express/export/json` | `express.service.ts` | Change frontend to POST to `/express/export/{format}`. |
| **P1** | Ontology list: `GET /api/ontology` → no backend | `ontology.service.ts` | Add `GET /` to `ontology_ingest_fastapi.py` or create separate list route. |

---

*End of audit.*
