# SDD-MOSSEC — Full Code Audit Report

**Date:** 2 March 2026  
**Scope:** 100% review — backend (240 .py), frontend (148 .jsx/.tsx/.ts), config, tests, **19 documentation files (.md, .csv, .cypher)**  
**Stats:** ~102 API endpoints · 17 route files · 16 services · 17 agent modules · 17 feature components · 20 frontend services · 19 docs

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Critical Bugs (Must Fix)](#2-critical-bugs-must-fix)
3. [High-Severity Bugs](#3-high-severity-bugs)
4. [Medium-Severity Issues](#4-medium-severity-issues)
5. [Security Vulnerabilities](#5-security-vulnerabilities)
6. [Frontend Component Status Map](#6-frontend-component-status-map)
7. [Backend Route Audit Table](#7-backend-route-audit-table)
8. [Backend Service Audit Table](#8-backend-service-audit-table)
9. [Agent Layer Audit Table](#9-agent-layer-audit-table)
10. [Compile / Lint Errors](#10-compile--lint-errors)
11. [Dead Code Inventory](#11-dead-code-inventory)
12. [Stub / Mock Implementations](#12-stub--mock-implementations)
13. [Pending Tasks Summary](#13-pending-tasks-summary)
14. [Recommended Fix Priority](#14-recommended-fix-priority)
15. [Documentation Audit (19 .md / .csv / .cypher files)](#15-documentation-audit)
16. [Cross-Document Contradictions](#16-cross-document-contradictions)
17. [Documentation Fix Priority](#17-documentation-fix-priority)

---

## 1. Executive Summary

| Category | Count |
|---|---|
| **CRITICAL bugs** | 8 |
| **HIGH-severity bugs** | 18 |
| **MEDIUM issues** | 25+ |
| **Security vulnerabilities** | 29 across routes + 6 in services/agents |
| **Compile/lint errors** | 239 (50 unique, most are `Unable to import` due to PYTHONPATH) |
| **Completely broken components** | 6 (5 graph wrappers + SHACLValidator) |
| **Pure stub components** | 1 (AIInsights) |
| **Dead code files/blocks** | 5 major blocks |
| **Unimplemented features** | 23 tracker tasks |
| **Documentation files audited** | 19 |
| **Docs rated MISLEADING** | 4 (README, SECURITY, mcp-server/README, mcp-server/INTEGRATION) |
| **Docs rated OUTDATED** | 2 (UI_DESIGN_PATTERNS, PHASE_PROMPTS) |
| **Docs rated PARTIALLY ACCURATE** | 11 |
| **Broken links in docs** | 10+ |
| **Cross-doc contradictions** | 7 major |

---

## 2. Critical Bugs (Must Fix)

### BUG-001: `neo4j_service.py` — Invalid Cypher in `list_nodes` / `count_nodes`
- **File:** `backend/src/web/services/neo4j_service.py` L387–425
- **Impact:** ANY filtered node listing or counting crashes with Cypher syntax error
- **Root cause:** `where_clause` is `" AND n.key = $filter_0"` — no `WHERE` keyword prepended. The generated Cypher is `MATCH (n:Label) AND n.key = ...` instead of `MATCH (n:Label) WHERE n.key = ...`
- **Affects:** All graph browsing, statistics, and filter operations

### BUG-002: `cache_service.py` — No thread safety despite "Thread-safe" docstring
- **File:** `backend/src/web/services/cache_service.py` L16–26
- **Impact:** `RuntimeError: dictionary changed size during iteration` under concurrent requests
- **Root cause:** No `threading.Lock` on `self.cache`, `self.timestamps`, `self.custom_ttls`. Concurrent reads/writes from multiple threads race.

### BUG-003: `dependencies.py` — Auth bypass when `API_KEY` env var unset
- **File:** `backend/src/web/dependencies.py` L23–25
- **Impact:** If `API_KEY` is not in environment (e.g., forgotten in production), `get_api_key()` returns `"development"` — entire API is unprotected
- **Root cause:** Fallback `os.getenv("API_KEY", "development")` provides a default instead of raising

### BUG-004: `auth_fastapi.py` — Hardcoded JWT secret & admin credentials
- **File:** `backend/src/web/routes/auth_fastapi.py` L43–48
- **Impact:** Anyone can forge JWT tokens. Admin account has well-known password `admin123`
- **Details:** `SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")`, `ADMIN_PASSWORD = "admin123"`

### BUG-005: `upload_fastapi.py` — Variable shadowing crashes `.parse_time_ms`
- **File:** `backend/src/web/routes/upload_fastapi.py` L248
- **Impact:** EXP file upload crashes with `AttributeError`
- **Root cause:** Loop `result = neo4j_service.execute_query(stmt)` shadows the `ParseResult` object. Then `result.parse_time_ms` accesses a list-of-dicts

### BUG-006: `vector_fastapi.py` — Module-level OpenSearch instantiation
- **File:** `backend/src/web/routes/vector_fastapi.py` L18–19
- **Impact:** If OpenSearch is unavailable at import time, the ENTIRE FastAPI app fails to start (all 30 route modules fail cascade)
- **Root cause:** `_vector = VectorStoreTool()` and `_es = ElasticsearchVectorStore()` at module scope

### BUG-007: `oslc_client.py` — SSL verification disabled
- **File:** `backend/src/web/services/oslc_client.py` L48
- **Impact:** Man-in-the-middle attacks on all OSLC outbound connections
- **Root cause:** `httpx.AsyncClient(verify=False)` hardcoded

### BUG-008: `adapters.py` — Async methods called synchronously
- **File:** `backend/src/agentic/adapters.py` L53–96
- **Impact:** `MBSEToolsAdapter.call()` returns coroutine objects instead of actual results
- **Root cause:** `self.tools_api.search_artifacts(...)` etc. are `async def` but invoked without `await`

---

## 3. High-Severity Bugs

### BUG-009: `neo4j_service.py` — Write operations through read path
- **File:** L347, L500, L520
- `create_node()`, `update_node()`, `delete_node()` all use `execute_query()` (read) instead of `execute_write()`. Bypasses write-transaction semantics and cache invalidation.

### BUG-010: `export_fastapi.py` — Cypher injection via `node_types`
- **File:** L200–204, L280
- `node_types` from query parameter interpolated directly into Cypher via f-string in GraphML and JSON-LD exports. No whitelist validation.

### BUG-011: `oslc_client_fastapi.py` — SSRF vulnerability
- **File:** L56, L76
- Unauthenticated endpoint makes HTTP requests to arbitrary user-supplied URLs. Can probe internal network.

### BUG-012: `orchestrator_workflow.py` — Hardcoded test part IDs in production
- **File:** L740
- `plm_agent_node` uses `["000123", "000456"]` — placeholder test data in live code path

### BUG-013: `orchestrator.py` — Double tool execution
- **File:** `backend/src/agentic/orchestrator.py` L60–75
- `BaselineOrchestrator.run()` executes all tools twice: once in `agent.run()`, once for reflection. Doubles Neo4j load, API calls, and latency.

### BUG-014: `langgraph_agent.py` — `_execute_tool` ignores arguments
- **File:** L303–304
- `matched_tool.run({})` always passes empty dict. Tool arguments from LLM response are never parsed.

### BUG-015: `langgraph_agent.py` — `httpx.AsyncClient` never closed
- **File:** L114
- Connection/file-descriptor leak. No `close()` or context manager.

### BUG-016: `simulation_agent.py` — `time.sleep()` blocks async event loop
- **File:** L89
- `run_simulation` is `async` but uses synchronous `time.sleep(1)`. Should be `await asyncio.sleep(1)`.

### BUG-017: `ontology_ingest_fastapi.py` — Path traversal bypass
- **File:** L102
- `str(p).startswith(str(ar))` for path restriction. A path like `...smrlv12_malicious/` bypasses. Should use `p.relative_to(ar)`.

### BUG-018: `graph_fastapi.py` — Sync Neo4j in async endpoints
- **File:** L218, L271, L330
- `neo4j.execute_query()` is synchronous but called from `async def` endpoints — blocks event loop.

### BUG-019: `SHACLValidator.jsx` — Call signature mismatch (BROKEN)
- **File:** `frontend/src/features/semantic-web/components/SHACLValidator.jsx` L28
- Calls `validate(rdfInput.trim(), shapeName)` but `useSHACL` expects `validate({ data, shapeName })`. Validation is completely non-functional.

### BUG-020: GraphBrowser — Ignores all wrapper props
- **File:** `frontend/src/features/graph-explorer/components/GraphBrowser.jsx` L170
- Does NOT destructure `fixedNodeTypes`, `apLevel`, `title`, `emptyMessage`. All 5 wrapper components (OntologyGraph, AP239Graph, AP242Graph, AP243Graph, OSLCGraph) pass those props but they are silently discarded. Every graph view shows the default ENTERPRISE view.

### BUG-021: GraphBrowser — Stale closure in `handleNodeClick`
- **File:** L630
- `useCallback` deps are `[currentViewId, normalizedGraph]` but reads `selectedNode`. Missing dep → stale closure on rapid clicks.

### BUG-022: `export_fastapi.py` — `generated_at: "now"` literal
- **File:** L79
- Returns the string `"now"` instead of `datetime.now().isoformat()`.

### BUG-023: `job_store.py` / `upload_job_store.py` — Key prefix collision
- **File:** Both use Redis key prefix `"upload_job:"` — data collision between two separate stores.

### BUG-024: `simulation_service.py` — `max_depth` parameter ignored
- **File:** L340–347
- Cypher hardcodes `[*1..7]` instead of using `$max_depth`.

### BUG-025: `step_agent.py` — `label` kwarg doesn't exist on `StepIngestConfig`
- **File:** L61
- Compile error: `Unexpected keyword argument "label" for "StepIngestConfig"`.

### BUG-026: `TRSFeed.jsx` — Destructures non-existent `trsError`
- **File:** `frontend/src/features/semantic-web/components/TRSFeed.jsx` L32
- `trsError` is always `undefined`. TRS errors are invisible to users.

---

## 4. Medium-Severity Issues

| # | File | Issue |
|---|---|---|
| M-01 | `plmxml_ingest_service.py` L576 | `session.run(cypher, **params)` — kwargs could conflict with `session.run()` internal args |
| M-02 | `plmxml_ingest_service.py` L500–507 | Orphan revisions with empty `parent_item_uid` silently dropped |
| M-03 | `plmxml_ingest_service.py` L266 | `rev_uid_set` parameter unused in `_iter_bom_lines` |
| M-04 | `ontology_ingest_service.py` L292 | `_ensure_ontology_node` uses `execute_query()` for write |
| M-05 | `plmxml_ingest_fastapi.py` L152 | `limit` kwarg passed separately from `params` — potential conflict |
| M-06 | `oslc_fastapi.py` L96–103 | `oslc.where` parameter accepted but completely ignored |
| M-07 | `oslc_fastapi.py` L176 | `CREATE` used instead of `MERGE` — duplicate keys possible |
| M-08 | `shacl_fastapi.py` L22–23 | `regex=` on `Query()` deprecated in Pydantic v2 — use `pattern=` |
| M-09 | `oslc_trs_service.py` L127 | Millisecond-resolution URIs can collide |
| M-10 | `oslc_trs_service.py` L77 | `record['labels'][0]` — potential `IndexError` |
| M-11 | `upload_job_store.py` L49–57 | If Redis unavailable at first connect, never retries |
| M-12 | `job_store.py` L141 | `key.decode()` may fail if `decode_responses=True` |
| M-13 | `job_store.py` L108–116 | Read-then-write without atomicity — lost-update race |
| M-14 | `export_service.py` L167–180 | Turtle output has no value escaping — invalid RDF |
| M-15 | `export_service.py` L135–157 | GraphML missing `<key>` declarations — invalid format |
| M-16 | `export_service.py` L159–165 | Uses Neo4j internal `id(n)` for URIs — not stable |
| M-17 | `container.py` L131–136 | `Neo4jConnection` created via `__new__`, bypassing `__init__` |
| M-18 | `vectorstore_es.py` L75–82 | Doubly-nested `knn.vector.vector` — may fail on some OpenSearch versions |
| M-19 | `RDFExporter.jsx` L20 | `selectedTypes` filter state never sent to API — type filter panel is decorative |
| M-20 | `ExpressExplorer.jsx` L47, L51 | `analyzeMutation.mutate()` and `exportExpress()` receive string instead of object |
| M-21 | `GraphBrowser.jsx` L1282 | Duplicate `<Checkbox>` elements per uncategorized type |
| M-22 | `ontology_agent.py` L139 | `depth` parameter ignored — hardcoded `[:SUBCLASS_OF*1..3]` |
| M-23 | `step_agent.py` L111 | `depth` parameter ignored — hardcoded `[:STEP_REF*1..2]` |
| M-24 | `neo4j_service.py` L200–208 | Async context never caches — silent performance degradation |
| M-25 | `dependencies.py` L37–40 | String comparison not constant-time — timing attack on API key |

---

## 5. Security Vulnerabilities

### 5.1 Authentication & Secrets

| # | File | Line | Severity | Issue |
|---|---|---|---|---|
| S-01 | `auth_fastapi.py` | L43 | **CRITICAL** | Default JWT secret `"your-secret-key-change-in-production"` |
| S-02 | `auth_fastapi.py` | L48 | **CRITICAL** | Hardcoded `ADMIN_PASSWORD = "admin123"` |
| S-03 | `auth_fastapi.py` | L188 | **HIGH** | Plaintext password comparison — no hashing |
| S-04 | `auth_fastapi.py` | L66 | **MEDIUM** | In-memory token blacklist — revoked tokens valid after restart |
| S-05 | `auth_fastapi.py` | L426 | **MEDIUM** | Logout with `verify_signature=False` — arbitrary session revocation |
| S-06 | `dependencies.py` | L23 | **CRITICAL** | Auth bypass when `API_KEY` env unset |
| S-07 | `dependencies.py` | L37 | **MEDIUM** | Timing attack on API key comparison |
| S-08 | `dependencies.py` | L40 | **LOW** | Logs partial API key in error message |
| S-09 | `plm_agent.py` | L37–39 | **HIGH** | Default credentials `admin`/`password` |
| S-10 | `oslc_client.py` | L48 | **CRITICAL** | SSL verification disabled (`verify=False`) |

### 5.2 Injection

| # | File | Line | Severity | Issue |
|---|---|---|---|---|
| S-11 | `export_fastapi.py` | L200 | **HIGH** | Cypher injection via `node_types` in GraphML export |
| S-12 | `export_fastapi.py` | L280 | **HIGH** | Same in JSON-LD export |
| S-13 | `graph_fastapi.py` | L259 | **MEDIUM** | Relationship type interpolated — mitigated by regex |
| S-14 | `agent_tools.py` | L41 | **HIGH** | `label` interpolated into Cypher f-string |
| S-15 | `core_fastapi.py` | L558 | **MEDIUM** | `POST /cypher` fragile regex blacklist for writes |

### 5.3 Path Traversal / SSRF

| # | File | Line | Severity | Issue |
|---|---|---|---|---|
| S-16 | `oslc_client_fastapi.py` | L56,L76 | **HIGH** | SSRF — requests to arbitrary URLs |
| S-17 | `express_parser_fastapi.py` | L97,L154,L178 | **HIGH** | 3× arbitrary filesystem read |
| S-18 | `plmxml_ingest_fastapi.py` | L79–89 | **HIGH** | No path restriction on ingest |
| S-19 | `ontology_ingest_fastapi.py` | L102 | **MEDIUM** | `startswith()` bypass |
| S-20 | `orchestrator_workflow.py` | L778–793 | **HIGH** | User-supplied file paths from chat query |
| S-21 | `ontology_agent.py` | L32–37 | **MEDIUM** | `_ALLOWED_OWL_DIRS` defined but never enforced |

### 5.4 Missing Authentication

12 of 17 route files have endpoints with ZERO authentication. Affected routes:
`agents`, `vector`, `ontology_ingest`, `shacl`, `plmxml_ingest`, `oslc`, `trs`, `oslc_client`, `upload`, `export`, `simulation`, `express_parser`

### 5.5 XSS

| # | File | Issue |
|---|---|---|
| S-22 | `SmartAnalysis.jsx` L166 | `dangerouslySetInnerHTML` with `marked.parse()` on LLM output |
| S-23 | `ModelChat.jsx` L131 | Same |
| S-24 | `Chatbot.tsx` L174 | Same |

---

## 6. Frontend Component Status Map

### AI Studio

| Component | File | Lines | Status | Issues |
|---|---|---|---|---|
| **AIInsights** | `ai-studio/components/AIInsights.jsx` | 52 | ❌ STUB | Zero API calls. All data hardcoded. |
| **SmartAnalysis** | `ai-studio/components/SmartAnalysis.jsx` | 280 | ⚠️ WORKING | ~85 lines dead code after closing `}`. XSS risk. |
| **ModelChat** | `ai-studio/components/ModelChat.jsx` | 290 | ⚠️ WORKING | ~110 lines dead code. XSS risk. Unstable key. |
| **Chatbot** | `ai-studio/components/Chatbot.tsx` | 210 | ✅ WORKING | XSS risk. Unstable key. |

### Graph Explorer

| Component | File | Lines | Status | Issues |
|---|---|---|---|---|
| **GraphBrowser** | `graph-explorer/components/GraphBrowser.jsx` | 1898 | ⚠️ WORKING | Stale closure. Duplicate checkbox. 1898-line monolith. |
| **OntologyGraph** | `graph-explorer/components/OntologyGraph.jsx` | 12 | ❌ BROKEN | Props ignored by GraphBrowser |
| **AP239Graph** | `graph-explorer/components/AP239Graph.jsx` | 10 | ❌ BROKEN | Props ignored |
| **AP242Graph** | `graph-explorer/components/AP242Graph.jsx` | 10 | ❌ BROKEN | Props ignored |
| **AP243Graph** | `graph-explorer/components/AP243Graph.jsx` | 10 | ❌ BROKEN | Props ignored |
| **OSLCGraph** | `graph-explorer/components/OSLCGraph.jsx` | 12 | ❌ BROKEN | Props ignored |

### Semantic Web

| Component | File | Lines | Status | Issues |
|---|---|---|---|---|
| **SHACLValidator** | `semantic-web/components/SHACLValidator.jsx` | 105 | ❌ BROKEN | Call signature mismatch — validation non-functional |
| **TRSFeed** | `semantic-web/components/TRSFeed.jsx` | 130 | ⚠️ PARTIAL | `trsError` undefined. TRS errors invisible. |
| **OntologyManager** | `semantic-web/components/OntologyManager.jsx` | 166 | ✅ WORKING | No significant bugs |
| **OSLCBrowser** | `semantic-web/components/OSLCBrowser.jsx` | 145 | ✅ WORKING | Minor: native `<select>` breaks theme consistency |
| **RDFExporter** | `semantic-web/components/RDFExporter.jsx` | 128 | ⚠️ PARTIAL | `selectedTypes` filter panel is decorative — never sent to API |
| **ExpressExplorer** | `semantic-web/components/ExpressExplorer.jsx` | 205 | ❌ BROKEN | Analyze/export receive string instead of object. Silent error swallow. |
| **GraphQLPlayground** | `semantic-web/components/GraphQLPlayground.jsx` | 130 | ✅ WORKING | No significant bugs |

### Summary: 4 working, 4 partial, 6 broken, 1 stub = 15 total audited

---

## 7. Backend Route Audit Table

| # | File | Lines | Endpoints | Bugs | Stubs | No Auth | Sync-in-Async |
|---|---|---|---|---|---|---|---|
| 1 | `agents_fastapi.py` | 81 | 1 | 1 | 0 | ✗ | 0 |
| 2 | `graph_fastapi.py` | 798 | 5 | 1 | 0 | partial | 3 |
| 3 | `vector_fastapi.py` | 135 | 4 | 2 | 0 | ✗ | 0 |
| 4 | `ontology_ingest_fastapi.py` | 147 | 2 | 0 | 0 | ✗ | 1 |
| 5 | `shacl_fastapi.py` | 75 | 2 | 2 | 0 | ✗ | 2 |
| 6 | `step_ingest_fastapi.py` | 99 | 1 | 0 | 0 | ✓ | 1 |
| 7 | `plmxml_ingest_fastapi.py` | 214 | 6 | 1 | 0 | ✗ | 0 |
| 8 | `oslc_fastapi.py` | 213 | 6 | 2 | 2 | ✗ | 2 |
| 9 | `trs_fastapi.py` | 68 | 3 | 0 | 0 | ✗ | 0 |
| 10 | `oslc_client_fastapi.py` | 85 | 2 | 1 | 0 | ✗ | 0 |
| 11 | `upload_fastapi.py` | 866 | 5 | 2 | 0 | ✗ | 0 |
| 12 | `export_fastapi.py` | 639 | 8 | 1 | 0 | ✗ | 0 |
| 13 | `auth_fastapi.py` | 638 | 8 | 1 | 0 | n/a | 0 |
| 14 | `simulation_fastapi.py` | 1306 | 20 | 1 | 0 | ✗ | many |
| 15 | `core_fastapi.py` | 681 | 10 | 0 | 0 | partial | 0 |
| 16 | `express_parser_fastapi.py` | 389 | 18 | 0 | 0 | ✗ | 0 |
| 17 | `admin_fastapi.py` | 71 | 1 | 0 | 0 | ✓ | 0 |
| | **TOTAL** | **6505** | **102** | **15** | **2** | **12 unprotected** | **9+** |

---

## 8. Backend Service Audit Table

| # | Service | Lines | Critical | High | Medium | Key Issues |
|---|---|---|---|---|---|---|
| 1 | `neo4j_service.py` | 749 | 2 | 3 | 1 | Invalid WHERE clause, writes via read path |
| 2 | `plmxml_ingest_service.py` | 627 | 0 | 0 | 3 | kwargs unpacking, orphan drop, unused arg |
| 3 | `ontology_ingest_service.py` | 773 | 0 | 0 | 1 | Write via read path |
| 4 | `shacl_validator.py` | 110 | 0 | 0 | 1 | Static shapes only, no dynamic discovery |
| 5 | `step_ingest_service.py` | 248 | 0 | 1 | 1 | Expensive full-graph scan per batch |
| 6 | `oslc_service.py` | 138 | 0 | 0 | 0 | Hardcoded single provider, incomplete spec |
| 7 | `oslc_trs_service.py` | 138 | 0 | 0 | 3 | Millis URI collision, IndexError, paging gaps |
| 8 | `oslc_client.py` | 182 | 1 | 1 | 1 | SSL off, no timeout, infinite recursion risk |
| 9 | `cache_service.py` | 203 | 1 | 2 | 1 | No thread safety, cleanup unstoppable |
| 10 | `simulation_service.py` | 658 | 0 | 1 | 1 | max_depth ignored, unsanitized SET |
| 11 | `upload_job_store.py` | 254 | 0 | 0 | 1 | No Redis retry after initial failure |
| 12 | `job_store.py` | 169 | 0 | 1 | 1 | decode crash, key prefix collision |
| 13 | `export_service.py` | 280 | 0 | 1 | 2 | Invalid RDF Turtle, invalid GraphML |
| 14 | `container.py` | 216 | 0 | 1 | 0 | `__new__` bypass of `__init__` |
| 15 | `dependencies.py` | 54 | 1 | 1 | 1 | Auth bypass, timing attack, log leak |

---

## 9. Agent Layer Audit Table

| # | Agent | Lines | Status | Key Issues |
|---|---|---|---|---|
| 1 | `agent_tools.py` | 83 | ⚠️ | Cypher injection in `index_document`, `search_artifacts` |
| 2 | `embeddings_ollama.py` | 50 | ⚠️ | No batching, no retry. Single POST for all texts. |
| 3 | `langgraph_agent.py` | 509 | ⚠️ | httpx leak, tool args always `{}`, 7 dead methods |
| 4 | `ontology_agent.py` | 258 | ⚠️ | depth ignored, path restriction not enforced |
| 5 | `orchestrator_workflow.py` | 1003 | ⚠️ | Hardcoded part IDs, async main uncalled, path traversal |
| 6 | `plm_agent.py` | 172 | ⚠️ | `calculate_impact` is 100% mock, default creds |
| 7 | `simulation_agent.py` | 128 | ❌ **MOCK** | All 3 methods return hardcoded test data |
| 8 | `step_agent.py` | 185 | ⚠️ | depth ignored, `label` kwarg invalid |
| 9 | `vectorstore_es.py` | 86 | ⚠️ | Doubly-nested kNN, HEAD check without retry |
| 10 | `adapters.py` | 102 | ❌ **BROKEN** | Async called without await — returns coroutines |
| 11 | `contracts.py` | 91 | ✅ | Clean protocol definitions |
| 12 | `orchestrator.py` | 87 | ⚠️ | Double execution, no multi-agent routing |
| 13 | `planning.py` | 60 | ⚠️ | Always single-step, context ignored, wrong tool for impact |
| 14 | `reflection.py` | 37 | ⚠️ | Only checks if output starts with "error" |
| 15 | `retrieval.py` | 46 | ⚠️ | `AzureAISearchRetriever` raises NotImplementedError |
| 16 | `tool_registry.py` | 38 | ✅ | Clean, no exception handling in call() |

---

## 10. Compile / Lint Errors

**239 total errors** across workspace. Key categories:

### Import Errors (most frequent)

| Module | Count | Cause |
|---|---|---|
| `src.agents.agent_tools` | 2 | PYTHONPATH not set outside web server |
| `src.web.services` | 5 | Same — scripts need `cd backend && PYTHONPATH=.` |
| `src.web.services.*` | 3 | Same |
| `src.graph.connection` | 1 | Script-level import |
| `src.parsers.*` | 1 | Script-level import |
| `src.engine` | 1 | Script-level import |

**Root cause:** Scripts under `backend/scripts/` and agents import via `from src.xxx` but are run without `PYTHONPATH=backend/` or `cd backend`. The web server sets this correctly, but standalone execution fails.

### Type Errors (MBSEsmrl workspace)

| File | Issue |
|---|---|
| `agents/tools/__init__.py` L76–83 | `str | None` passed where `str` expected (7 occurrences) |
| `agents/tools/graph_tool.py` L111 | `dict[str, object]` incompatible with `params` type |
| `agents/tools/dossier_tool.py` L111 | Same |
| `agents/tools/semantic_tool.py` L209 | Same |

### Code Quality

| Category | Count | Example |
|---|---|---|
| `Catching too general exception` | 8+ | Bare `except Exception` |
| Unused imports | 4 | `Tuple`, `groupby`, `json`, `Any` |
| Unused arguments | 3 | `depth`, `rev_uid_set` |
| Deprecated patterns | 2 | `regex=` → `pattern=`, `.dict()` → `.model_dump()` |
| f-string no interpolation | 1 | `f"Statistics:"` |

---

## 11. Dead Code Inventory

| File | Lines | Description |
|---|---|---|
| `SmartAnalysis.jsx` | ~L195–280 | Old version of component after closing `}` |
| `ModelChat.jsx` | ~L175–290 | Old version without location context |
| `Layout_old.jsx` | entire file | Old layout — `Layout.jsx` is the live version |
| `index.css.backup` | entire file | Backup CSS |
| `langgraph_agent.py` | L217–358 | 7 methods (`_understand_task`, `_plan_steps`, etc.) never called — `create_react_agent` has its own loop |

---

## 12. Stub / Mock Implementations

| Component | Type | What's Mock |
|---|---|---|
| **AIInsights.jsx** | Frontend | 100% static. "23 requirements", "15 components" — no API. |
| **SimulationAgent** | Backend | `get_simulation_parameters()` returns hardcoded mass/stress. `run_simulation()` returns mock FEA/CFD. `validate_results()` body is `pass`. |
| **PLMAgent.calculate_impact** | Backend | Returns hardcoded `"ASM-001"`, `"ASM-002"`. |
| **OSLC Service** | Backend | Catalog hardcodes "Default Project". No AM/QM/CM domains. No Resource Shapes. |
| **OSLCFastAPI dialogs** | Backend | `/dialogs/rm/select` returns hardcoded HTML placeholder. |
| **AzureAISearchRetriever** | Backend | `retrieve()` raises `NotImplementedError`. |
| **KeywordPlanner** | Backend | Always produces single-step plan. Context ignored. |
| **SimpleReflector** | Backend | Only checks `output.lower().startswith("error")`. |

---

## 13. Pending Tasks Summary

From `SEMANTIC_INTEGRATION_TRACKER.md` — 23 tasks across 11 phases:

| Phase | Tasks | Status |
|---|---|---|
| 1 — Ontology Foundation | Tasks 1-2 | ⬜ Not started |
| 2 — Semantic Linking | Tasks 3-4 | ⬜ Not started |
| 3 — SHACL Validation | Tasks 5-6 | ⬜ Not started |
| 4 — Agent Contracts | Tasks 7-8 | ⬜ Not started |
| 5 — Query Layer | Task 9 | ⬜ Not started |
| 6 — Chat & AI | Tasks 10-11 | ⬜ Not started |
| 7 — OSLC TRS | Task 12 | ⬜ Not started |
| 8 — Infrastructure | Tasks 13-15 | ⬜ Not started |
| 9 — Frontend: AI Studio | Tasks 16-18 | ⬜ Not started |
| 10 — Frontend: Graph Explorer | Tasks 19-20 | ⬜ Not started |
| 11 — Frontend: Semantic Web | Tasks 21-23 | ⬜ Not started |

---

## 14. Recommended Fix Priority

### P0 — Fix Immediately (blocks normal operation)

| # | Bug | Effort | Impact |
|---|---|---|---|
| 1 | BUG-001: `list_nodes`/`count_nodes` missing WHERE | 5 min | Crashes filtered queries |
| 2 | BUG-005: `upload_fastapi.py` variable shadowing | 5 min | Crashes EXP upload |
| 3 | BUG-006: Module-level OpenSearch instantiation | 10 min | App won't start without OpenSearch |
| 4 | BUG-019: SHACLValidator call signature | 5 min | SHACL validation non-functional |
| 5 | BUG-025: `step_agent.py` invalid `label` kwarg | 5 min | Compile error |
| 6 | BUG-008: `adapters.py` async/sync mismatch | 15 min | Agentic tools return coroutine objects |

### P1 — Fix Before Any User Access

| # | Bug | Effort | Impact |
|---|---|---|---|
| 7 | BUG-003: Auth bypass when env unset | 5 min | Full API unprotected |
| 8 | BUG-004: Hardcoded JWT secret + admin creds | 15 min | Token forgery possible |
| 9 | S-03: Plaintext password comparison | 30 min | No password hashing |
| 10 | S-07: Timing attack on API key | 5 min | API key leakable |
| 11 | BUG-010: Cypher injection in exports | 15 min | Data theft/mutation |
| 12 | BUG-011: SSRF in OSLC client | 10 min | Internal network probing |
| 13 | S-17: Path traversal in EXPRESS parser | 15 min | Arbitrary file read |
| 14 | S-18: Path traversal in PLMXML ingest | 10 min | Arbitrary file read |
| 15 | BUG-007: SSL verification disabled | 5 min | MITM attacks |

### P2 — Fix Before Production

| # | Bug | Effort | Impact |
|---|---|---|---|
| 16 | BUG-002: Cache service thread safety | 30 min | Crashes under load |
| 17 | BUG-009: Write ops through read path | 15 min | Cache/tx issues |
| 18 | BUG-013: Double tool execution | 20 min | 2× resource usage |
| 19 | BUG-020: GraphBrowser ignores wrapper props | 30 min | 5 views all show same data |
| 20 | BUG-016: time.sleep blocks event loop | 5 min | Server hangs |
| 21 | BUG-018: Sync Neo4j in async endpoints | 1 hr | Throughput bottleneck |
| 22 | BUG-015: httpx client leak | 10 min | FD exhaustion |
| 23 | Dead code cleanup (ModelChat, SmartAnalysis, etc.) | 30 min | Maintenance burden |

### P3 — Improve Quality

| # | Item | Effort |
|---|---|---|
| 24 | Add auth to 12 unprotected route files | 2 hr |
| 25 | Replace all mock data in SimulationAgent | 4 hr |
| 26 | Fix export formats (RDF, GraphML) | 2 hr |
| 27 | Add React error boundaries to all 17 components | 1 hr |
| 28 | Sanitize `dangerouslySetInnerHTML` (DOMPurify) | 30 min |
| 29 | Fix RDFExporter filter panel | 15 min |
| 30 | Fix ExpressExplorer argument types | 15 min |

---

## 15. Documentation Audit

**Files audited:** 19 total (17 `.md`, 1 `.csv`, 1 `.cypher`)

### 15.1 Per-File Rating Table

| # | File | Lines | Rating | Key Issues |
|---|---|---|---|---|
| 1 | `README.md` | 467 | ⛔ **MISLEADING** | References Flask (actual: FastAPI), says "50+ endpoints" (actual: ~162), shows `src/web/app.py` (actual: `app_fastapi.py`), 10 broken links, Linux commands for Windows project, references `start_all.ps1` which doesn't exist |
| 2 | `SECURITY.md` | 27 | ⛔ **MISLEADING** | Generic GitHub Inc. template referencing GitHub Bug Bounty — not project-specific at all |
| 3 | `mcp-server/README.md` | 280 | ⛔ **MISLEADING** | Says "Flask REST API" (actual: FastAPI), uses `neo4j+s://...databases.neo4j.io` (actual: `neo4j://127.0.0.1:7687`), references repo `mbse-neo4j-graph-rep` (actual: `SDD_MOSSEC`), `dist/` referenced but never built |
| 4 | `mcp-server/INTEGRATION.md` | 291 | ⛔ **MISLEADING** | Pervasively references "Flask REST API", architecture diagram shows "GPT-4" as MCP client (should be Claude), entry point `app.py` (actual: `app_fastapi.py`), claims "No authentication" (auth IS implemented), Aura Neo4j URIs, broken link |
| 5 | `frontend/UI_DESIGN_PATTERNS.md` | 254 | ⚠️ **OUTDATED** | All references to `frontend/src/pages/*.tsx` — no `pages/` directory exists (actual: `features/`), shows flat `<Route>` routing (actual: role-based layouts), wrong extensions (.tsx vs actual .jsx) |
| 6 | `docs/PHASE_PROMPTS.md` | 696 | ⚠️ **OUTDATED** | All phases appear already executed, no completion status markers, references `routers/` (actual: `routes/`) |
| 7 | `sdd---simulation-data-dossier/README.md` | 15 | ⛔ **MISLEADING** | Unedited Google AI Studio scaffold, references `GEMINI_API_KEY` (not used), app has mock data only |
| 8 | `INSTALL.md` | 633 | 🔶 **PARTIAL** | Python version inconsistency (3.10+ here vs 3.12 in deployment), hardcoded Neo4j password in example, otherwise thorough |
| 9 | `docs/SDD_MODULAR_ARCHITECTURE_PLAN.md` | 709 | 🔶 **PARTIAL** | Says 27 routers (actual: 29, missing `vector_fastapi.py` + `plmxml_ingest_fastapi.py`), frontend section outdated (pages/ → features/ already done) |
| 10 | `docs/API_ALIGNMENT_AUDIT.md` | ~450 | 🔶 **PARTIAL** | From Jan 2025 — several findings already fixed, missing 2 new routers |
| 11 | `docs/NEO4J_SCHEMA_AUDIT.cypher` | 137 | 🔶 **PARTIAL** | Queries for `:Part`, `:Requirement` labels that don't exist in actual schema (should be `:PLMXMLItem`, etc.), missing PLMXML-specific, SDD-specific, and SHACL label queries |
| 12 | `deployment/README.md` | ~200 | 🔶 **PARTIAL** | Version inconsistencies (Python 3.10+ vs 3.12 elsewhere, Node 18+ vs 20), references `start_all.ps1` which doesn't exist |
| 13 | `deployment/INDEX.md` | ~80 | 🔶 **PARTIAL** | Links to files that exist but have version conflicts |
| 14 | `deployment/DEPLOYMENT_SUMMARY.md` | ~150 | 🔶 **PARTIAL** | References Python 3.12 (conflicts with README's 3.10+) |
| 15 | `deployment/DEPLOYMENT_CHECKLIST.md` | ~120 | 🔶 **PARTIAL** | Missing actual commands for OpenSearch/Ollama setup |
| 16 | `.github/pull_request_template.md` | ~40 | 🔶 **PARTIAL** | Minor: wrong paths for lint commands |
| 17 | `.github/GIT_WORKFLOW.md` | ~80 | 🔶 **PARTIAL** | Missing frontend lint hooks |
| 18 | `docs/SEMANTIC_INTEGRATION_ARCHITECTURE.md` | ~700 | 🔶 **PARTIAL** | Duplicate section 15 numbering, TBD placeholder values, planned files not clearly marked as "(planned)" |
| 19 | `docs/SEMANTIC_INTEGRATION_TRACKER.md` | ~200 | ✅ **ACCURATE** | Well-structured, correctly represents planned work state |

### 15.2 Broken Links Inventory

All links below appear in documentation but the target files **do not exist** anywhere in the workspace:

| Source File | Broken Link / Reference |
|---|---|
| `README.md` | `docs/REST_API_GUIDE.md` |
| `README.md` | `docs/API_SCHEMA_ALIGNMENT.md` |
| `README.md` | `docs/SERVICE_LAYER_GUIDE.md` |
| `README.md` | `docs/CYPHER_QUERIES.md` |
| `README.md` | `docs/ARCHITECTURE.md` |
| `README.md` | `docs/DEPLOYMENT.md` (should be `deployment/README.md`) |
| `README.md` | `docs/TESTING.md` |
| `README.md` | `docs/CONTRIBUTING.md` |
| `README.md` | `scripts/start_all.ps1` |
| `README.md` | `docs/SECURITY.md` (should be `SECURITY.md` at root) |
| `mcp-server/INTEGRATION.md` | `docs/REST_API_GUIDE.md` |
| `mcp-server/README.md` | `dist/` directory |

### 15.3 README.md Specific Errors (Highest Priority)

The project `README.md` (467 lines) is the most visible documentation file and has the most errors:

1. **Framework wrong:** Says Flask throughout — actual framework is FastAPI
2. **Endpoint count wrong:** "50+ REST endpoints" — actual count is ~162
3. **Entry point wrong:** Shows `src/web/app.py` — actual is `backend/src/web/app_fastapi.py`
4. **Requirements path wrong:** Shows `requirements.txt` at root — actual is `backend/requirements.txt`
5. **Setup path wrong:** Shows `setup.py` at root — actual is `backend/setup.py`
6. **OS commands wrong:** Uses `source venv/bin/activate` — project runs on Windows (`.\venv\Scripts\activate`)
7. **Start script missing:** References `scripts/start_all.ps1` — file doesn't exist
8. **10 broken doc links:** See §15.2 above
9. **Missing major features:** No mention of OpenSearch, Redis, Ollama, vector search, PLMXML ingestion pipeline, dataloader sub-app
10. **Architecture diagram wrong:** Shows `app.py → routers/ → services/` — actual is `app_fastapi.py → routes/ → services/`

### 15.4 MCP Server Documentation Errors

Both `mcp-server/README.md` (280 lines) and `mcp-server/INTEGRATION.md` (291 lines) contain pervasive errors:

1. **"Flask REST API"** appears throughout both files — should be FastAPI
2. **Neo4j connection string** uses `neo4j+s://xxxx.databases.neo4j.io` (Aura cloud) — actual is `neo4j://127.0.0.1:7687` (local)
3. **Repository name** shown as `mbse-neo4j-graph-rep` — actual is `SDD_MOSSEC`
4. **Entry point** shown as `src/web/app.py` — actual is `backend/src/web/app_fastapi.py`
5. **Authentication claim** in INTEGRATION.md says "No authentication required" — JWT auth IS implemented
6. **Architecture diagram** shows "GPT-4" as MCP client — should reference Claude/Claude Desktop
7. **`dist/` directory** referenced in README but has never been built
8. **Database name** not mentioned — actual is `mossec`

---

## 16. Cross-Document Contradictions

| Topic | Source A | Source B | Actual |
|---|---|---|---|
| **Web framework** | README, MCP docs: "Flask" | Architecture doc: "FastAPI" | **FastAPI** (`app_fastapi.py`) |
| **Neo4j connection** | MCP docs: `neo4j+s://...neo4j.io` | INSTALL.md: `neo4j://localhost:7687` | **`neo4j://127.0.0.1:7687`** (local, db `mossec`) |
| **Python version** | README: "3.9+" | INSTALL.md: "3.10+" | Deployment: "3.12" |
| **Node.js version** | INSTALL.md: "18+" | deployment/DEPLOYMENT_SUMMARY: "20" | Untested — likely **20** |
| **API entry point** | README, MCP docs: `src/web/app.py` | Code: `backend/src/web/app_fastapi.py` | **`backend/src/web/app_fastapi.py`** |
| **Authentication** | INTEGRATION.md: "No authentication" | Code: JWT + API key auth | **Auth implemented** (JWT secret + optional API key) |
| **Frontend routing** | UI_DESIGN_PATTERNS: `pages/*.tsx`, flat routes | Code: `features/*.jsx`, role-based layouts | **`features/` + role-based** |
| **Router directory** | PHASE_PROMPTS: `routers/` | Code: `routes/` | **`routes/`** |
| **Router count** | SDD_MODULAR_ARCHITECTURE_PLAN: 27 | Code: 29 files in `routes/` | **29** (missing `vector_fastapi.py`, `plmxml_ingest_fastapi.py`) |
| **Endpoint count** | README: "50+" | Code audit: 102 in routes + 60 in sub-apps | **~162** |

---

## 17. Documentation Fix Priority

### D-P0 — Fix Immediately (misleading to any reader)

| # | File | Action | Effort |
|---|---|---|---|
| 1 | `README.md` | **Complete rewrite**: Fix Flask→FastAPI, entry point, paths, links, add missing features (OpenSearch, Redis, Ollama, vector search, PLMXML), fix OS commands, update architecture diagram | 2 hr |
| 2 | `SECURITY.md` | Replace GitHub template with project-specific security policy (contact info, supported versions, disclosure process) | 30 min |
| 3 | `mcp-server/README.md` | Fix Flask→FastAPI, Neo4j URI, repo name, entry point, build instructions | 1 hr |
| 4 | `mcp-server/INTEGRATION.md` | Fix Flask→FastAPI throughout, fix architecture diagram (GPT-4→Claude), fix auth claims, fix Neo4j URI, fix broken link | 1 hr |
| 5 | `sdd---simulation-data-dossier/README.md` | Either write real README or delete scaffold | 15 min |

### D-P1 — Update Soon (outdated, causes confusion)

| # | File | Action | Effort |
|---|---|---|---|
| 6 | `frontend/UI_DESIGN_PATTERNS.md` | Update all `pages/*.tsx` refs to `features/*.jsx`, update routing patterns to role-based layouts | 1 hr |
| 7 | `docs/PHASE_PROMPTS.md` | Add completion status markers to each phase, fix `routers/` → `routes/` | 30 min |
| 8 | `docs/SDD_MODULAR_ARCHITECTURE_PLAN.md` | Add 2 missing routers, update frontend section from pages/ to features/ | 30 min |
| 9 | `docs/NEO4J_SCHEMA_AUDIT.cypher` | Replace `:Part`/`:Requirement` with actual PLMXML labels, add SDD + SHACL queries | 1 hr |
| 10 | Deployment docs (all 4) | Reconcile Python/Node version requirements, remove `start_all.ps1` reference | 30 min |

### D-P2 — Nice to Have

| # | File | Action | Effort |
|---|---|---|---|
| 11 | `docs/API_ALIGNMENT_AUDIT.md` | Mark already-fixed items, add 2 new routers | 30 min |
| 12 | `docs/SEMANTIC_INTEGRATION_ARCHITECTURE.md` | Fix duplicate §15, replace TBD placeholders, mark planned files | 15 min |
| 13 | `.github/pull_request_template.md` | Fix lint command paths | 10 min |
| 14 | `.github/GIT_WORKFLOW.md` | Add frontend lint hooks | 15 min |
| 15 | Create missing docs | `REST_API_GUIDE.md`, `CONTRIBUTING.md`, `TESTING.md` (linked from README but don't exist) | 4 hr |

---

*End of Report*
