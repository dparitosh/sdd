# Backend API Route Audit Report

**Application:** `D:\MBSEsmrl\backend\src\web`  
**Entry Point:** `app_fastapi.py` (546 lines)  
**Service Container:** `container.py` (236 lines)  
**Total Route Files:** 27  
**Date:** Auto-generated audit

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Route Registration (app_fastapi.py)](#2-route-registration)
3. [Per-File Endpoint Inventory](#3-per-file-endpoint-inventory)
4. [Consolidated Issue Summary](#4-consolidated-issue-summary)

---

## 1. Architecture Overview

| Component | Technology |
|-----------|-----------|
| Framework | FastAPI |
| Database | Neo4j (graph) |
| Cache | Redis (optional async) |
| Auth | JWT (PyJWT) |
| Rate Limiting | slowapi (per-IP) |
| GraphQL | Strawberry |
| Standards | OSLC (RDF/Turtle/JSON-LD), ISO 10303 (AP239/AP242/AP243), SMRL |

**ServiceContainer** (`container.py`): Thread-safe singleton sharing a Neo4j driver between the web layer and engine `GraphStore`. Exposes `Services.neo4j()`, `Services.graph_store()`, `Services.redis()`, etc. as FastAPI `Depends` callables.

---

## 2. Route Registration

All routers are registered in `app_fastapi.py`. Some routers define their own prefix internally while also receiving an `app.include_router(prefix=...)` — the effective path is the concatenation.

| Router File | App Prefix | Router Prefix | Effective Base | Tags |
|-------------|-----------|---------------|----------------|------|
| `core_fastapi.py` | `/api` | — | `/api` | Core |
| `graph_fastapi.py` | `/api/graph` | — | `/api/graph` | Graph |
| `metrics_fastapi.py` | `/api/metrics` | — | `/api/metrics` | Metrics |
| `hierarchy_fastapi.py` | `/api/hierarchy` | — | `/api/hierarchy` | Hierarchy & Traceability |
| `auth_fastapi.py` | `/api` | `/auth` | `/api/auth` | Authentication |
| `sessions_fastapi.py` | `/api` | `/sessions` | `/api/sessions` | Session Management |
| `ap239_fastapi.py` | `/api/ap239` | — | `/api/ap239` | AP239 |
| `ap242_fastapi.py` | `/api/ap242` | — | `/api/ap242` | AP242 |
| `ap243_fastapi.py` | `/api/ap243` | — | `/api/ap243` | AP243 |
| `smrl_v1_fastapi.py` | `/api/v1` | — | `/api/v1` | SMRL v1 |
| `plm_connectors_fastapi.py` | `/api/v1/plm` | — | `/api/v1/plm` | PLM Connectors |
| `plm_fastapi.py` | `/api` | `/plm` | `/api/plm` | PLM Integration |
| `simulation_fastapi.py` | `/api` | `/simulation` | `/api/simulation` | Simulation |
| `export_fastapi.py` | `/api` | `/export` | `/api/export` | Data Export |
| `version_fastapi.py` | `/api` | `/version` | `/api/version` | Version Control |
| `cache_fastapi.py` | `/api` | `/cache` | `/api/cache` | Cache Management |
| `agents_fastapi.py` | `/api` | `/agents` | `/api/agents` | AI Agents |
| `upload_fastapi.py` | — | `/api/upload` | `/api/upload` | File Upload |
| `graphql_fastapi.py` | `/api/graphql` | — | `/api/graphql` | GraphQL |
| `oslc_fastapi.py` | — | `/oslc` | `/oslc` | OSLC |
| `trs_fastapi.py` | `/api` | `/oslc/trs` | `/api/oslc/trs` | OSLC TRS |
| `oslc_client_fastapi.py` | `/api` | `/oslc/client` | `/api/oslc/client` | OSLC Client |
| `express_parser_fastapi.py` | `/api` | `/express` | `/api/express` | EXPRESS Parser |
| `ontology_ingest_fastapi.py` | — | `/api/ontology` | `/api/ontology` | Ontology Ingestion |
| `shacl_fastapi.py` | — | `/api/validate` | `/api/validate` | SHACL Validation |
| `step_ingest_fastapi.py` | — | `/api/step` | `/api/step` | STEP Ingestion |
| `admin_fastapi.py` | — | `/api/admin` | `/api/admin` | Admin |

> **⚠️ DUPLICATE REGISTRATION:** `smrl_v1_fastapi.py` internally includes sub-routers for hierarchy, PLM, simulation, export, and version. These same routers are **also** registered directly in `app_fastapi.py`, creating duplicate routes under both `/api` and `/api/v1` prefixes.

---

## 3. Per-File Endpoint Inventory

### 3.1 `core_fastapi.py` (669 lines) — `/api`

| Method | Full Path | Parameters | Cypher Snippet | Issues |
|--------|-----------|-----------|----------------|--------|
| GET | `/api/packages` | — | `MATCH (p:Package) OPTIONAL MATCH (p)-[:CONTAINS]->(child) RETURN p, count(child)` | None |
| GET | `/api/package/{package_id}` | `package_id: str` | `MATCH (p:Package {id: $id})-[:CONTAINS]->(child) RETURN child, labels(child)[0]` | None |
| GET | `/api/classes` | — | `MATCH (c:Class) RETURN c LIMIT 100` | Hardcoded LIMIT 100 |
| GET | `/api/class/{class_id}` | `class_id: str` | `MATCH (c:Class {id: $id}) OPTIONAL MATCH (c)-[:HAS_ATTRIBUTE]->(p) ...` | None |
| GET | `/api/search` | `q: str`, `type: str`, `limit: int` | `MATCH (n) WHERE any(lbl...) AND any(prop IN keys(n) WHERE toString(n[prop]) =~ $pattern)` | Rate-limited 60/min. API key required. Regex pattern from user input — no escaping of regex metacharacters. |
| POST | `/api/search` | Body: `query`, `type`, `limit` | Same as above | Same as GET search |
| GET | `/api/artifacts` | — | `MATCH (n) WHERE NOT n:Package RETURN labels(n)[0], toString(id(n)), n` | **⚠️ Uses deprecated `id(n)` — should be `elementId(n)`** |
| GET | `/api/stats` | — | Multiple `MATCH (n) RETURN count(n)` queries | Cached 60s. API key required. |
| POST | `/api/cypher` | Body: `query`, `params` | User-supplied Cypher | Rate-limited 30/min. Blocks `DELETE`, `CREATE`, `SET`, `REMOVE`, `MERGE`, `CALL`, `DROP`. Auto-appends `LIMIT 1000`. |
| GET | `/api/artifacts/{artifact_type}/{artifact_id}` | `artifact_type: str`, `artifact_id: str` | `MATCH (n:{artifact_type} {id: $id})` | `artifact_type` is validated against a whitelist. F-string label injection is safe due to whitelist. |

---

### 3.2 `graph_fastapi.py` (~350 lines) — `/api/graph`

| Method | Full Path | Parameters | Cypher Snippet | Issues |
|--------|-----------|-----------|----------------|--------|
| GET | `/api/graph/data` | `node_types: List[str]`, `limit: int (500, max 1000)`, `depth: int (1–3)`, `ap_level: str`, `include_metadata: bool` | `MATCH (n) WHERE ... WITH n LIMIT $limit OPTIONAL MATCH (n)-[r]-(m) RETURN elementId(n), n, ...` | Uses `elementId(n)` ✅. Node types validated against whitelist. |
| GET | `/api/graph/node-types` | — | `CALL db.labels() YIELD label ... CALL { WITH label MATCH (n) WHERE label IN labels(n) RETURN count(n) }` | Uses `CALL db.labels()` procedure |
| GET | `/api/graph/relationship-types` | — | `CALL db.relationshipTypes() YIELD relationshipType ...` | Uses `CALL db.relationshipTypes()` procedure |

---

### 3.3 `metrics_fastapi.py` (~260 lines) — `/api/metrics`

| Method | Full Path | Parameters | Cypher Snippet | Issues |
|--------|-----------|-----------|----------------|--------|
| GET | `/api/metrics/summary` | — | `MATCH (n) RETURN count(n)` + `MATCH ()-[r]->() RETURN count(r)` for DB metrics | **⚠️ `get_cache_metrics()` returns HARDCODED mock values** (hit_rate: 0.87, etc.). **⚠️ `get_api_metrics()` returns hardcoded `avg_response_time_ms: 127.5`** |
| GET | `/api/metrics/history` | `hours: int (default 24)` | None (all mock) | **⚠️ Entirely HARDCODED/mock time-series data generation** |
| GET | `/api/metrics/health` | — | `MATCH (n) RETURN count(n) LIMIT 1` (connectivity test) | Uses psutil for system metrics. No auth required. |

---

### 3.4 `hierarchy_fastapi.py` (~400 lines) — `/api/hierarchy`

| Method | Full Path | Parameters | Cypher Snippet | Issues |
|--------|-----------|-----------|----------------|--------|
| GET | `/api/hierarchy/traceability-matrix` | `source_level: str`, `target_level: str`, `limit: int` | `MATCH path = (source)-[*1..4]-(target) WHERE any(lbl IN labels(source) WHERE lbl IN $source_types) ...` | Complex variable-length path query |
| GET | `/api/hierarchy/navigate/{node_type}/{node_id}` | `node_type: str`, `node_id: str`, `depth: int (1–5)`, `direction: str` | `MATCH (start:{node_type} {id: $node_id}) MATCH path = (start)-[*1..{depth}]-() ...` | `node_type` validated against `VALID_NODE_TYPES` whitelist ✅. `depth` injected as f-string int. |
| GET | `/api/hierarchy/search` | `query: str`, `levels: List[str]`, `limit: int` | `MATCH (n) WHERE any(lbl IN labels(n) WHERE lbl IN $labels) AND any(prop ... =~ $pattern)` | None |
| GET | `/api/hierarchy/statistics` | — | Multiple count queries per AP level | None |
| GET | `/api/hierarchy/impact/{node_type}/{node_id}` | `node_type: str`, `node_id: str`, `depth: int (1–3)` | `MATCH (source:{node_type} {id: $node_id})-[r*1..{depth}]-(impacted) ...` | **⚠️ `node_type` injected into Cypher f-string with NO whitelist validation** (unlike `/navigate` which has `VALID_NODE_TYPES` check) |

---

### 3.5 `auth_fastapi.py` (528 lines) — `/api/auth`

| Method | Full Path | Parameters | Cypher Snippet | Issues |
|--------|-----------|-----------|----------------|--------|
| POST | `/api/auth/login` | Body: `username`, `password` | None (credential check in Python) | **⚠️ Hardcoded `ADMIN_PASSWORD = "admin123"`**. **⚠️ Hardcoded `SECRET_KEY = "your-secret-key-change-in-production"`** |
| POST | `/api/auth/refresh` | Header: `Authorization` | None | None |
| POST | `/api/auth/logout` | Header: `Authorization` | None | **⚠️ `TOKEN_BLACKLIST = set()` — in-memory, lost on restart** |
| GET | `/api/auth/verify` | Header: `Authorization` | None | None |
| POST | `/api/auth/change-password` | Body: `current_password`, `new_password` | None | **⚠️ Does NOT actually change password** — returns success with comment "In production: verify current password, update in database" |

---

### 3.6 `ap239_fastapi.py` (749 lines) — `/api/ap239`

| Method | Full Path | Parameters | Cypher Snippet | Issues |
|--------|-----------|-----------|----------------|--------|
| GET | `/api/ap239/requirements` | `status: str`, `priority: str`, `search: str`, `skip: int`, `limit: int` | `MATCH (r:Requirement) WHERE ... RETURN r ORDER BY r.name SKIP $skip LIMIT $limit` | None |
| GET | `/api/ap239/requirements/{req_id}` | `req_id: str` | `MATCH (r:Requirement {id: $id}) OPTIONAL MATCH (r)-[rel]-(related) ...` | None |
| GET | `/api/ap239/requirements/{req_id}/traceability` | `req_id: str`, `depth: int (1–5)` | `MATCH path = (r:Requirement {id: $id})-[*1..{depth}]-(connected) ...` | `depth` injected as f-string int (validated range) |
| POST | `/api/ap239/requirements/traceability/bulk` | Body: `requirement_ids: List[str]` | `MATCH (r:Requirement) WHERE r.id IN $req_ids OPTIONAL MATCH (r)-[rel]-(related) ...` | Solves N+1 pattern ✅ |
| GET | `/api/ap239/analyses` | `search: str`, `limit: int` | `MATCH (a:Analysis) ...` | None |
| GET | `/api/ap239/approvals` | `status: str`, `limit: int` | `MATCH (a:Approval) ...` | None |
| GET | `/api/ap239/documents` | `type: str`, `search: str`, `limit: int` | `MATCH (d:Document) ...` | None |
| GET | `/api/ap239/statistics` | — | Multiple count queries grouped by status | None |

---

### 3.7 `ap242_fastapi.py` (707 lines) — `/api/ap242`

| Method | Full Path | Parameters | Cypher Snippet | Issues |
|--------|-----------|-----------|----------------|--------|
| GET | `/api/ap242/parts` | `material: str`, `search: str`, `skip: int`, `limit: int` | `MATCH (p:Part) WHERE ... RETURN p` | Escapes regex metacharacters ✅ |
| GET | `/api/ap242/parts/{part_id}` | `part_id: str` | `MATCH (p:Part {id: $id}) OPTIONAL MATCH (p)-[rel]-(related) ...` | None |
| GET | `/api/ap242/parts/{part_id}/bom` | `part_id: str`, `depth: int (1–5)` | `MATCH path = (root:Part {id: $id})-[:HAS_COMPONENT*1..{depth}]->(child) ...` | `depth` injected as f-string int |
| GET | `/api/ap242/assemblies` | `search: str`, `limit: int` | `MATCH (a:Assembly) ...` | None |
| GET | `/api/ap242/materials` | `search: str`, `limit: int` | `MATCH (m:Material) ...` | Uses double-brace `{{` in f-string Cypher — correct Python but may confuse readers |
| GET | `/api/ap242/materials/{material_name}` | `material_name: str` | `MATCH (m:Material) WHERE m.name =~ $pattern ...` | None |
| GET | `/api/ap242/geometry` | `type: str`, `search: str`, `limit: int` | `MATCH (g:GeometryModel) ...` | None |
| GET | `/api/ap242/statistics` | — | Multiple count queries | None |

---

### 3.8 `ap243_fastapi.py` (796 lines) — `/api/ap243`

| Method | Full Path | Parameters | Cypher Snippet | Issues |
|--------|-----------|-----------|----------------|--------|
| GET | `/api/ap243/overview` | — | Multiple count queries for MoSSEC classes | None |
| GET | `/api/ap243/domain-classes` | `domain: str`, `stereotype: str`, `search: str`, `skip: int`, `limit: int` | `MATCH (n) WHERE any(lbl IN labels(n) WHERE lbl IN $mossec_labels) ...` | None |
| GET | `/api/ap243/domain-classes/{class_name}` | `class_name: str` | `MATCH (n) WHERE n.name = $name AND any(lbl IN labels(n) WHERE lbl IN $mossec_labels) ...` | None |
| GET | `/api/ap243/domain-search` | `q: str`, `node_type: str`, `limit: int` | `MATCH (n{label_filter}) WHERE any(lbl IN labels(n) WHERE lbl IN $mossec_labels) ...` | **⚠️ `node_type` injected as f-string label** `(n:{node_type})` — relies on the `WHERE any(lbl...)` clause but the label is still injected into the Cypher string |
| GET | `/api/ap243/packages` | `search: str`, `limit: int` | `MATCH (p:Package) ...` | None |
| GET | `/api/ap243/stereotypes` | — | `MATCH (n) WHERE n.stereotype IS NOT NULL RETURN DISTINCT n.stereotype` | None |
| GET | `/api/ap243/ontologies` | `search: str`, `limit: int` | `MATCH (n) WHERE any(lbl IN labels(n) WHERE lbl IN [...]) ...` | None |
| GET | `/api/ap243/ontologies/{ontology_name}` | `ontology_name: str` | `MATCH (n) WHERE n.name = $name ...` | None |
| GET | `/api/ap243/units` | `search: str`, `limit: int` | `MATCH (u:Unit) ...` | None |
| GET | `/api/ap243/value-types` | `search: str`, `limit: int` | `MATCH (v:ValueType) ...` | None |
| GET | `/api/ap243/classifications` | `search: str`, `limit: int` | `MATCH (c:Classification) ...` | None |
| GET | `/api/ap243/statistics` | — | Multiple count queries grouped by category | None |

---

### 3.9 `smrl_v1_fastapi.py` (697 lines) — `/api/v1`

| Method | Full Path | Parameters | Cypher Snippet | Issues |
|--------|-----------|-----------|----------------|--------|
| GET | `/api/v1/health` | — | None | Health check |
| GET | `/api/v1/traceability` | (forwards to plm) | — | Compatibility forward |
| GET | `/api/v1/parameters` | (forwards to plm) | — | Compatibility forward |
| GET | `/api/v1/constraints` | (forwards to plm) | — | Compatibility forward |
| GET | `/api/v1/composition/{node_id}` | (forwards to plm) | — | Compatibility forward |
| GET | `/api/v1/impact/{node_id}` | (forwards to plm) | — | Compatibility forward |
| GET | `/api/v1/versions/{node_id}` | (forwards to version) | — | Compatibility forward |
| GET | `/api/v1/history/{node_id}` | (forwards to version) | — | Compatibility forward |
| POST | `/api/v1/diff` | (forwards to version) | — | Compatibility forward |
| POST | `/api/v1/checkpoint` | (forwards to version) | — | Compatibility forward |
| GET | `/api/v1/{resource_type}` | `resource_type: str`, query params | `MATCH (n:{neo4j_label}) RETURN n` (label from SMRLAdapter mapping) | Generic SMRL list |
| GET | `/api/v1/{resource_type}/{uid}` | `resource_type: str`, `uid: str` | `MATCH (n:{label} {id: $uid}) RETURN n` | Single resource |
| POST | `/api/v1/{resource_type}` | `resource_type: str`, Body: properties | `CREATE (n:{label} $properties) SET n.id = $uid RETURN n` | Creates node + TRS notification |
| PUT | `/api/v1/{resource_type}/{uid}` | `resource_type: str`, `uid: str`, Body | `MATCH (n:{label} {id: $uid}) SET n = $properties SET n.id = $uid RETURN n` | Full replacement |
| PATCH | `/api/v1/{resource_type}/{uid}` | `resource_type: str`, `uid: str`, Body | `MATCH (n:{label} {id: $uid}) SET n += $properties RETURN n` | Partial update |
| DELETE | `/api/v1/{resource_type}/{uid}` | `resource_type: str`, `uid: str` | `MATCH (n:{label} {id: $uid}) DETACH DELETE n RETURN count(n)` | Destructive |
| POST | `/api/v1/match` | Body: `resource_type`, `filters`, `limit` | `MATCH (n:{label}) WHERE ... RETURN n` | Advanced query |

**⚠️ ISSUE:** This file internally includes sub-routers (`hierarchy_router`, `plm_router`, `simulation_router`, `export_router`, `version_router`) that are **also** registered directly from `app_fastapi.py`, creating duplicate route registrations under both `/api` and `/api/v1` prefixes.

---

### 3.10 `plm_connectors_fastapi.py` (~230 lines) — `/api/v1/plm`

| Method | Full Path | Parameters | Cypher Snippet | Issues |
|--------|-----------|-----------|----------------|--------|
| GET | `/api/v1/plm/connectors` | — | None | **⚠️ Returns entirely HARDCODED mock connectors** (Teamcenter, Windchill, SAP — all "disconnected") |
| POST | `/api/v1/plm/connectors/{connector_id}/sync` | `connector_id: str` | None | **⚠️ Mock — does not actually sync** |
| GET | `/api/v1/plm/connectors/{connector_id}/status` | `connector_id: str` | None | **⚠️ Mock status with hardcoded history** |

---

### 3.11 `plm_fastapi.py` (665 lines) — `/api/plm`

| Method | Full Path | Parameters | Cypher Snippet | Issues |
|--------|-----------|-----------|----------------|--------|
| GET | `/api/plm/traceability` | `node_types: List[str]`, `relationship_types: List[str]`, `depth: int (1–5)`, `limit: int` | `MATCH path = (source)-[r*1..{depth}]-(target) WHERE source <> target ...` | Has whitelist for node/rel types (includes `None`). Variable-depth paths. |
| GET | `/api/plm/composition/{node_id}` | `node_id: str`, `depth: int (1–5)` | `MATCH (root {id: $node_id}) OPTIONAL MATCH path = (root)-[:HAS_COMPONENT\|CONTAINS*1..{depth}]->(child)` | `depth` injected as f-string int (validated) |
| GET | `/api/plm/impact/{node_id}` | `node_id: str`, `depth: int (1–3)`, `relationship_types: List[str]` | `MATCH (source {id: $node_id})-[r*1..{depth}]-(impacted) WHERE type(r[0]) IN [...]` | **⚠️ `type(r[0])` only checks the FIRST relationship** in variable-length path — not all relationships |
| GET | `/api/plm/parameters` | `search: str`, `owner_type: str`, `limit: int` | `MATCH (p:Property) OPTIONAL MATCH (p)-[:TYPED_BY]->(type) ...` | None |
| GET | `/api/plm/constraints` | `type: str`, `limit: int` | `MATCH (c:Constraint) ...` | None |

---

### 3.12 `simulation_fastapi.py` (651 lines) — `/api/simulation`

| Method | Full Path | Parameters | Cypher Snippet | Issues |
|--------|-----------|-----------|----------------|--------|
| GET | `/api/simulation/parameters` | `search: str`, `owner_type: str`, `limit: int` | `MATCH (p:Property) ... RETURN ..., toString(id(p)), toString(id(type)), toString(id(owner))` | **⚠️ Uses deprecated `id()` in 3 places**: `toString(id(p))`, `toString(id(type))`, `toString(id(owner))` |
| POST | `/api/simulation/validate` | Body: `parameters: List[dict]` | None (validation logic in Python) | Checks multiplicity and constraint bodies |
| GET | `/api/simulation/models` | `search: str`, `has_parameters: bool`, `limit: int` | `MATCH (c:Class) ... RETURN ..., toString(id(c))` | **⚠️ Uses deprecated `toString(id(c))`** |
| GET | `/api/simulation/results` | `model_id: str`, `limit: int` | `MATCH (r) WHERE ... RETURN ..., toString(id(r))` | **⚠️ Uses deprecated `toString(id(r))`** |
| GET | `/api/simulation/units` | `search: str`, `limit: int` | `MATCH (u:Unit) ...` | Clean — no deprecated functions |

---

### 3.13 `version_fastapi.py` (506 lines) — `/api/version`

| Method | Full Path | Parameters | Cypher Snippet | Issues |
|--------|-----------|-----------|----------------|--------|
| GET | `/api/version/versions/{node_id}` | `node_id: str` | `MATCH (n {id: $node_id}) RETURN n, labels(n)` | **⚠️ No actual version tracking** — returns current state as a single "version" |
| POST | `/api/version/diff` | Body: `node_id_1`, `node_id_2` | `MATCH (n {id: $id}) RETURN n, labels(n)` (x2) | Property-level diff comparison |
| GET | `/api/version/history/{node_id}` | `node_id: str` | `MATCH (n {id: $node_id}) RETURN n` | Limited to creation/modification timestamps |
| POST | `/api/version/checkpoint` | Body: `label`, `description` | `MATCH (n) RETURN labels(n)[0], count(n)` | **⚠️ Only captures label statistics, NOT actual graph snapshot** — comment says "Full graph snapshot would require additional storage mechanism" |

---

### 3.14 `export_fastapi.py` (632 lines) — `/api/export`

| Method | Full Path | Parameters | Cypher Snippet | Issues |
|--------|-----------|-----------|----------------|--------|
| GET | `/api/export/schema` | — | `CALL db.schema.nodeTypeProperties()` with fallback to sampling query | Uses two-phase approach with fallback ✅ |
| GET | `/api/export/graphml` | `node_types: List[str]`, `limit: int` | `MATCH (n)-[r]->(m) RETURN elementId(n), n, type(r), elementId(m), m` | Uses `elementId()` ✅ |
| GET | `/api/export/jsonld` | `limit: int` | `MATCH (n) OPTIONAL MATCH (n)-[r]->(m) ...` | None |
| GET | `/api/export/csv` | `node_type: str`, `limit: int` | `MATCH (n:{node_type}) RETURN n LIMIT {limit}` | **⚠️ CYPHER INJECTION: `node_type` injected directly into f-string with NO whitelist validation** |
| GET | `/api/export/step` | `limit: int` | `MATCH (c:Class) OPTIONAL MATCH (c)-[:HAS_ATTRIBUTE]->(p:Property) ...` | None |
| GET | `/api/export/plantuml` | `package: str` | Delegated to `ExportService.export_plantuml()` | None |
| GET | `/api/export/rdf` | — | Delegated to `ExportService.export_rdf()` | None |
| GET | `/api/export/cytoscape` | — | Delegated to `ExportService.export_cytoscape()` | None |

**⚠️ No API key or auth dependency on ANY export endpoint.**

---

### 3.15 `cache_fastapi.py` (~300 lines) — `/api/cache`

| Method | Full Path | Parameters | Cypher Snippet | Issues |
|--------|-----------|-----------|----------------|--------|
| GET | `/api/cache/stats` | — | None | Returns QueryCache statistics |
| POST | `/api/cache/stats/reset` | — | None | Resets statistics counters |
| POST | `/api/cache/clear` | — | None | **⚠️ Clears ALL cached queries — no auth** |
| POST | `/api/cache/invalidate/{pattern}` | `pattern: str` | None | **⚠️ Pattern-based cache invalidation — no auth** |
| GET | `/api/cache/config` | — | None | Returns cache config |
| GET | `/api/cache/health` | — | None | Cache health check |

**⚠️ No API key or auth on ANY cache endpoint including destructive operations (clear, invalidate).**

---

### 3.16 `agents_fastapi.py` (~85 lines) — `/api/agents`

| Method | Full Path | Parameters | Cypher Snippet | Issues |
|--------|-----------|-----------|----------------|--------|
| POST | `/api/agents/orchestrator/run` | Body: `goal: str`, `context: dict` | None (delegates to agent orchestrator) | **⚠️ No API key or auth** — multi-agent workflow exposed without authentication |

---

### 3.17 `upload_fastapi.py` (794 lines) — `/api/upload`

| Method | Full Path | Parameters | Cypher Snippet | Issues |
|--------|-----------|-----------|----------------|--------|
| POST | `/api/upload/` | `file: UploadFile` | Various per file type (XMI, CSV, EXPRESS, STEP, XSD) | File validation with extension whitelist. Max 100MB. |
| GET | `/api/upload/status/{job_id}` | `job_id: str` | None | Job status from Redis |
| GET | `/api/upload/jobs` | — | None | Lists all active jobs |
| DELETE | `/api/upload/job/{job_id}` | `job_id: str` | None | Deletes job record |
| GET | `/api/upload/health` | — | None | Upload service health |

**CSV processing issue:** `label` derived from filename stem is injected into Cypher: `MERGE (n:\`{label}\`...)` — backtick-escaped but a crafted filename could still be problematic.

**⚠️ No API key or auth on upload endpoints.**

---

### 3.18 `sessions_fastapi.py` (~350 lines) — `/api/sessions`

| Method | Full Path | Parameters | Cypher Snippet | Issues |
|--------|-----------|-----------|----------------|--------|
| GET | `/api/sessions/me` | JWT token | None (Redis lookup) | JWT auth required ✅ |
| DELETE | `/api/sessions/me/{session_id}` | `session_id: str`, JWT token | None | JWT auth required ✅ |
| DELETE | `/api/sessions/me/all` | JWT token | None | JWT auth required ✅ |
| GET | `/api/sessions/stats` | JWT token | None | Admin-only ✅ |
| GET | `/api/sessions/user/{username}` | `username: str`, JWT token | None | Admin-only ✅ |
| DELETE | `/api/sessions/user/{username}` | `username: str`, JWT token | None | Admin-only ✅ |
| POST | `/api/sessions/cleanup` | JWT token | None | Admin-only ✅ |

Auth properly implemented on all session endpoints.

---

### 3.19 `oslc_fastapi.py` (~250 lines) — `/oslc`

| Method | Full Path | Parameters | Cypher Snippet | Issues |
|--------|-----------|-----------|----------------|--------|
| GET | `/oslc/rootservices` | — | None | RDF/XML OSLC entry point |
| GET | `/oslc/catalog` | — | None | Service Provider Catalog (RDF/XML) |
| GET | `/oslc/sp/{project_id}` | `project_id: str` | None | Service Provider details |
| GET | `/oslc/rm/requirements` | `oslc.where: str`, `oslc.pageSize: int`, `oslc.pageNo: int` | `MATCH (r:Requirement) ... SKIP ... LIMIT ...` | Paged Cypher query |
| GET | `/oslc/dialogs/rm/select` | — | None | HTML selection dialog stub |
| POST | `/oslc/rm/requirements` | RDF body | `CREATE (r:Requirement $props) RETURN r` | Creates Requirement + TRS event |

**⚠️ No auth on ANY OSLC endpoint.**

---

### 3.20 `trs_fastapi.py` (~70 lines) — `/api/oslc/trs`

| Method | Full Path | Parameters | Cypher Snippet | Issues |
|--------|-----------|-----------|----------------|--------|
| GET | `/api/oslc/trs` | — | None | TRS resource set |
| GET | `/api/oslc/trs/base` | `page: int` | None | Paged TRS base |
| GET | `/api/oslc/trs/changelog` | — | None | TRS change log |

**⚠️ No auth on any TRS endpoint.**

---

### 3.21 `oslc_client_fastapi.py` (~80 lines) — `/api/oslc/client`

| Method | Full Path | Parameters | Cypher Snippet | Issues |
|--------|-----------|-----------|----------------|--------|
| POST | `/api/oslc/client/connect` | Body: `url: str`, `username: str`, `password: str` | None | Connects to external OSLC provider |
| POST | `/api/oslc/client/query` | Body: `provider_url: str`, `resource_type: str`, `query: str` | None | Executes OSLC query on remote |

**⚠️ No auth — could be abused for SSRF** (server-side request forgery to internal services).

---

### 3.22 `express_parser_fastapi.py` (~400 lines) — `/api/express`

| Method | Full Path | Parameters | Cypher Snippet | Issues |
|--------|-----------|-----------|----------------|--------|
| POST | `/api/express/parse/file` | Body: `file_path: str` | None | **⚠️ Accepts arbitrary filesystem path — path traversal risk** |
| POST | `/api/express/parse/content` | Body: `content: str`, `schema_name: str` | None | Parses EXPRESS from string |
| POST | `/api/express/parse/upload` | `file: UploadFile` | None | Parses uploaded .exp file |
| POST | `/api/express/parse/directory` | Body: `directory_path: str` | None | **⚠️ Accepts arbitrary directory path** |
| GET | `/api/express/info` | `file_path: str` | None | **⚠️ Accepts arbitrary file path** |
| POST | `/api/express/query/entities` | Body | None | Query entities from parsed schema |
| POST | `/api/express/query/types` | Body | None | Query types |
| POST | `/api/express/analyze/statistics` | Body | None | Schema statistics |
| POST | `/api/express/analyze/inheritance` | Body: `entity_name: str` | None | Inheritance tree |
| POST | `/api/express/analyze/type-usage` | Body: `type_name: str` | None | Type references |
| POST | `/api/express/analyze/select-usage` | Body | None | SELECT type usage |
| POST | `/api/express/export/json` | Body | None | JSON export of parsed schema |
| POST | `/api/express/export/markdown` | Body | None | Markdown export |
| POST | `/api/express/export/graphml` | Body | None | GraphML export |
| POST | `/api/express/neo4j/cypher` | Body | Generated Cypher statements | Cypher generation from schema |
| POST | `/api/express/neo4j/graph` | Body | None | Nodes/edges format |
| GET | `/api/express/health` | — | None | Health check |
| GET | `/api/express/` | — | None | API info |

**⚠️ No auth on ANY EXPRESS endpoint. Path traversal risk on 3 endpoints.**

---

### 3.23 `ontology_ingest_fastapi.py` (~120 lines) — `/api/ontology`

| Method | Full Path | Parameters | Cypher Snippet | Issues |
|--------|-----------|-----------|----------------|--------|
| POST | `/api/ontology/ingest` | Body: `file_path: str`, `format: str`, `graph_name: str` | Delegated to `OntologyIngestService` | API key required ✅. Path restricted to allowed roots (`smrlv12`, `data/uploads`, `data/raw`) ✅ |

---

### 3.24 `shacl_fastapi.py` (~80 lines) — `/api/validate`

| Method | Full Path | Parameters | Cypher Snippet | Issues |
|--------|-----------|-----------|----------------|--------|
| POST | `/api/validate/shacl` | `file: UploadFile`, `shapes_file: UploadFile (optional)` | None (rdflib validation) | **⚠️ No auth required** |
| POST | `/api/validate/shacl/inline` | Body: `data: str`, `shapes: str`, `format: str` | None | **⚠️ No auth required** |

---

### 3.25 `step_ingest_fastapi.py` (~100 lines) — `/api/step`

| Method | Full Path | Parameters | Cypher Snippet | Issues |
|--------|-----------|-----------|----------------|--------|
| POST | `/api/step/ingest` | Body: `file_path: str`, `batch_size: int`, `include_geometry: bool` | Delegated to `StepIngestService` | API key required ✅. Path restricted to allowed roots ✅ |

---

### 3.26 `admin_fastapi.py` (~70 lines) — `/api/admin`

| Method | Full Path | Parameters | Cypher Snippet | Issues |
|--------|-----------|-----------|----------------|--------|
| POST | `/api/admin/clear-db` | `confirm: bool` | `MATCH (n) DETACH DELETE n` | API key required ✅. Requires `confirm=true` ✅. Returns count of deleted nodes. |

---

### 3.27 `graphql_fastapi.py` (~80 lines) — `/api/graphql`

| Method | Full Path | Parameters | Cypher Snippet | Issues |
|--------|-----------|-----------|----------------|--------|
| POST | `/api/graphql` | GraphQL body | `statistics` query: count queries; `cypher_read` field: user-supplied Cypher | API key required ✅. Read-only Cypher validation via regex (blocks CREATE/DELETE/SET/MERGE/REMOVE/DROP/CALL). |

---

## 4. Consolidated Issue Summary

### 4.1 Critical: Security

| # | Issue | Files | Severity |
|---|-------|-------|----------|
| S1 | **Hardcoded admin password** `"admin123"` | `auth_fastapi.py` | 🔴 Critical |
| S2 | **Hardcoded JWT secret** `"your-secret-key-change-in-production"` (default) | `auth_fastapi.py` | 🔴 Critical |
| S3 | **Cypher injection** — `node_type` injected directly into f-string with no validation | `export_fastapi.py` (CSV endpoint) | 🔴 Critical |
| S4 | **Cypher injection** — `node_type` injected as label in f-string | `ap243_fastapi.py` (domain-search), `hierarchy_fastapi.py` (impact endpoint) | 🟠 High |
| S5 | **Path traversal** — accepts arbitrary filesystem paths with no restriction | `express_parser_fastapi.py` (3 endpoints: parse/file, parse/directory, info) | 🔴 Critical |
| S6 | **SSRF risk** — unauthenticated endpoint allows server to make requests to arbitrary URLs | `oslc_client_fastapi.py` | 🟠 High |
| S7 | **In-memory token blacklist** — lost on server restart, allowing revoked tokens to work | `auth_fastapi.py` | 🟠 High |

### 4.2 High: Missing Authentication

| # | Endpoint Group | File | Impact |
|---|---------------|------|--------|
| A1 | All export endpoints (schema, graphml, jsonld, csv, step, plantuml, rdf, cytoscape) | `export_fastapi.py` | Data exfiltration |
| A2 | All cache endpoints including clear/invalidate | `cache_fastapi.py` | DoS via cache flush |
| A3 | Agent orchestrator | `agents_fastapi.py` | Arbitrary agent execution |
| A4 | All OSLC endpoints | `oslc_fastapi.py` | Data read/write |
| A5 | All TRS endpoints | `trs_fastapi.py` | Data read |
| A6 | OSLC client connect/query | `oslc_client_fastapi.py` | SSRF |
| A7 | All EXPRESS parser endpoints | `express_parser_fastapi.py` | Path traversal + data |
| A8 | All upload endpoints | `upload_fastapi.py` | Arbitrary file upload |
| A9 | SHACL validation | `shacl_fastapi.py` | Resource abuse |

### 4.3 Medium: Deprecated Neo4j Functions

| # | Deprecated Usage | Replacement | File | Lines |
|---|-----------------|-------------|------|-------|
| D1 | `toString(id(n))` in artifacts query | `elementId(n)` | `core_fastapi.py` | artifacts endpoint |
| D2 | `toString(id(p))` | `elementId(p)` | `simulation_fastapi.py` | parameters endpoint |
| D3 | `toString(id(type))` | `elementId(type)` | `simulation_fastapi.py` | parameters endpoint |
| D4 | `toString(id(owner))` | `elementId(owner)` | `simulation_fastapi.py` | parameters endpoint |
| D5 | `toString(id(c))` | `elementId(c)` | `simulation_fastapi.py` | models endpoint |
| D6 | `toString(id(r))` | `elementId(r)` | `simulation_fastapi.py` | results endpoint |

> `id()` was deprecated in Neo4j 5.0 and will be removed in a future version. Use `elementId()` instead.

### 4.4 Medium: Hardcoded / Mock Data

| # | Description | File |
|---|-------------|------|
| M1 | `get_cache_metrics()` returns hardcoded `hit_rate: 0.87`, `avg_response_time_ms: 12.3` | `metrics_fastapi.py` |
| M2 | `get_api_metrics()` returns hardcoded `avg_response_time_ms: 127.5` | `metrics_fastapi.py` |
| M3 | `/metrics/history` endpoint generates entirely fake time-series data | `metrics_fastapi.py` |
| M4 | All PLM connector endpoints return hardcoded mock data | `plm_connectors_fastapi.py` |
| M5 | Change-password endpoint is a no-op (returns success without changing anything) | `auth_fastapi.py` |

### 4.5 Medium: Incomplete Implementations

| # | Description | File |
|---|-------------|------|
| I1 | Version checkpoint only captures label statistics — no actual graph snapshot | `version_fastapi.py` |
| I2 | Version history returns only current state as a single "version" | `version_fastapi.py` |
| I3 | PLM connectors are all mock with no real integration | `plm_connectors_fastapi.py` |

### 4.6 Low: Architectural Issues

| # | Description | Files |
|---|-------------|-------|
| R1 | **Duplicate route registration** — smrl_v1_fastapi.py includes sub-routers (hierarchy, plm, simulation, export, version) that are also registered independently in app_fastapi.py | `smrl_v1_fastapi.py`, `app_fastapi.py` |
| R2 | Search endpoints don't escape regex metacharacters in user input (ap239, core) while ap242 does | `core_fastapi.py`, `ap239_fastapi.py` vs `ap242_fastapi.py` |
| R3 | `type(r[0])` in impact analysis only checks first relationship in variable-length path | `plm_fastapi.py` |
| R4 | Cypher endpoint blocks `CALL` keyword but `graph_fastapi.py` uses `CALL db.labels()` / `CALL db.relationshipTypes()` internally | `core_fastapi.py`, `graph_fastapi.py` |

### 4.7 Issue Count Summary

| Category | Count |
|----------|-------|
| 🔴 Critical Security | 3 |
| 🟠 High Security | 3 |
| Missing Authentication | 9 endpoint groups |
| Deprecated Neo4j `id()` | 6 occurrences |
| Hardcoded / Mock Data | 5 |
| Incomplete Implementations | 3 |
| Architectural Issues | 4 |
| **Total** | **33** |

---

*End of audit report.*
