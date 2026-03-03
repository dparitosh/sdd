# SDD-MOSSEC — Semantic Integration Task Tracker
**Version:** 1.0  
**Date:** 2026-03-02  
**Architecture Reference:** [SEMANTIC_INTEGRATION_ARCHITECTURE.md](SEMANTIC_INTEGRATION_ARCHITECTURE.md)

---

## Status Legend
| Symbol | Meaning |
|---|---|
| ⬜ | Not started |
| 🔵 | In progress |
| ✅ | Complete |
| ❌ | Blocked |

---

## Phase 1 — Ontology Foundation

### Task 1 — PLMXML Parser v6 Fix
**Status:** ✅ Complete  
**File:** `backend/src/web/services/plmxml_ingest_service.py`  
**Depends on:** nothing  
**Complexity:** Small  
**Architecture ref:** Section 3.4

**Problem:**  
Current parser handles PLMXML v4 element names (`<Item>`, `<ItemRevision>`, `<BOMViewOccurrence>`).  
Real TC v13 exports use v6 names: `<Product subType="...">`, `<ProductRevision>`, `<ProductInstance>` inside `<InstanceGraph>`.

**Changes required:**
- [ ] `_iter_items()` — match `<Product>`, read `productId` as `item_id`, `subType` as `item_type`
- [ ] `_iter_revisions()` — match `<ProductRevision>`, read `productRevisionId` as `rev_id`
- [ ] `_iter_bom_lines()` — match `<ProductInstance>` inside `<InstanceGraph>`, read `partRef` (strip `#`) as `ref_uid`, `sequenceNumber` as `find_num`
- [ ] `_iter_datasets()` — verify `<DataSet>` element name unchanged
- [ ] Dry-run validation against 6 real TC v13 files in `d:\FileHistory\...\SPLM\`
- [ ] Confirm counts match expected (Items, Revisions, BOM lines, DataSets per file)

**Test files:**
```
d:\FileHistory\Paritosh\DESKTOP-6V68C8J\Data\D\graphdb\...\SPLM\
  000687_A_1inductionmotor (2023_02_05 08_36_29 UTC).xml
  000687_A_1-INDUCTIONMOTORASSY5 (2023_01_12 06_42_22 UTC).xml
  000687_A_1-INDUCTIONMOTORASSY5 (2023_02_05 08_36_29 UTC).xml
  000687_A_1-INDUCTIONMOTORASSY5HP (2022_12_27 07_33_35 UTC).xml
  000687_A_1-INDUCTIONMOTORASSY5HP (2023_02_05 08_36_29 UTC).xml
  000687_A_1inductionmotor (2022_12_17 01_44_39 UTC).xml
```

---

### Task 2 — Cross-Ontology SUBCLASS_OF Edges in TTL Files
**Status:** ✅ Complete  
**Files:** `backend/data/seed/oslc/oslc-ap242.ttl`, `oslc-ap239.ttl`  
**Depends on:** nothing  
**Complexity:** Small  
**Architecture ref:** Section 3.3

**Problem:**  
The three AP ontology TTLs (AP239, AP242, AP243) are disconnected — no `owl:imports` or `rdfs:subClassOf` cross-links between them. Graph traversal cannot cross ontology boundaries.

**Changes required:**
- [ ] Add to `oslc-ap242.ttl`:
  ```turtle
  ap242:Part            rdfs:subClassOf  ap243:Product .
  ap242:PartVersion     rdfs:subClassOf  ap243:ProductVersion .
  ap242:PartOccurrence  rdfs:subClassOf  ap243:ProductOccurrence .
  ap242:Drawing         rdfs:subClassOf  ap243:Document .
  ```
- [ ] Add to `oslc-ap239.ttl`:
  ```turtle
  ap239:Requirement     rdfs:subClassOf  oslc_rm:Requirement .
  ap239:Document        rdfs:subClassOf  ap242:Drawing .
  ap239:BreakdownElement rdfs:subClassOf ap242:Part .
  ```
- [ ] Re-run `OntologyAgent.ingest_standard_ontologies()` after edits
- [ ] Verify Neo4j has connected `[:SUBCLASS_OF]` path: `ap239:Requirement → oslc_rm:Requirement`

---

## Phase 2 — Semantic Linking Layer

### Task 3 — Post-ingest CLASSIFIED_AS Linker
**Status:** ✅ Complete  
**File:** `backend/src/web/services/plmxml_ingest_service.py` (add `_link_ontology_classes`)  
**Depends on:** Task 1, Task 2  
**Complexity:** Medium  
**Architecture ref:** Section 5, Step 3

**Changes required:**
- [ ] Add `_link_ontology_classes(self, result: PLMXMLIngestResult)` method to `PLMXMLIngestService`
- [ ] Strategy 1 — exact match: `cls.name = item.item_type`
- [ ] Strategy 2 — fuzzy fallback: `toLower(cls.name) CONTAINS toLower(item_type)`
- [ ] If no match: `SET item.unclassified = true`
- [ ] Call from `ingest_file()` after Neo4j write, wrapped in `try/except` (non-blocking)
- [ ] Add same hook to `StepIngestService` for `:StepFile` nodes
- [ ] Return `classified_count` and `unclassified_count` in `IngestResult`

**Cypher for linker:**
```cypher
MATCH (item:PLMXMLItem {uid: $uid})
MATCH (cls:ExternalOwlClass)
WHERE cls.name = $item_type
  AND cls.ap_level IN ['AP242', 'AP243']
MERGE (item)-[:CLASSIFIED_AS {
  source: 'plmxml_ingest',
  ap_level: cls.ap_level,
  confidence: 'exact'
}]->(cls)
```

---

### Task 4 — Post-ingest OpenSearch Vectorization
**Status:** ✅ Complete  
**File:** `backend/src/web/services/plmxml_ingest_service.py` (add `_vectorize_nodes`)  
**Depends on:** Task 1  
**Complexity:** Medium  
**Architecture ref:** Section 5, Step 5

**Changes required:**
- [ ] Add `_vectorize_nodes(self, result: PLMXMLIngestResult)` method
- [ ] Text template: `"item_id: {item_id} name: {name} type: {item_type} revision: {rev_id}"`
- [ ] Call `OllamaEmbeddings.embed([text])` per item
- [ ] Call `ElasticsearchVectorStore.upsert(index, uid, text, embedding, metadata)`
- [ ] `metadata = {"labels": ["PLMXMLItem"], "item_type": item_type, "ap_level": "AP242"}`
- [ ] On OpenSearch failure: write `data/vectorize_progress/{uid}.pending`
- [ ] Call from `ingest_file()` after Neo4j write (non-blocking)
- [ ] Return `vectors_indexed` count in `IngestResult`
- [ ] Add same hook to `StepIngestService`

---

## Phase 3 — SHACL Validation

### Task 5 — SHACL Shape Definitions
**Status:** ✅ Complete  
**File:** `backend/data/seed/shacl/plmxml_shapes.ttl` (NEW)  
**Depends on:** Task 2  
**Complexity:** Small  
**Architecture ref:** Section 6

**Changes required:**
- [ ] Create `backend/data/seed/shacl/` directory
- [ ] Create `plmxml_shapes.ttl` with shapes:
  - [ ] `PLMXMLItemShape` — target `ap242:Part`, `item_id` minCount 1
  - [ ] `PLMXMLRevisionShape` — target `ap242:PartVersion`, `rev_id` required
  - [ ] `PLMXMLBOMLineShape` — target `ap242:PartOccurrence`, `ref_uid` resolves
  - [ ] `PLMXMLDataSetShape` — target `ap242:GeometryRepresentation`, `name` required
  - [ ] `StepFileShape` — target `ap242:ShapeRepresentation`, `entity_count > 0`
  - [ ] `RequirementShape` — target `ap239:Requirement`, `title` required

---

### Task 6 — SHACLValidationService + Route
**Status:** ✅ Complete  
**Files:**  
  - `backend/src/web/services/shacl_validation_service.py` (NEW)  
  - `backend/src/web/routes/shacl_fastapi.py` (NEW)  
  - `backend/src/web/app_fastapi.py` (register route)  
**Depends on:** Task 5  
**Complexity:** Medium  
**Architecture ref:** Section 6.2

**Changes required:**
- [ ] Create `SHACLValidationService` with:
  - [ ] `validate(node_uid, shape_name)` — single node validation
  - [ ] `validate_batch(label)` — all nodes of label
  - [ ] `get_violations(uid)` — query existing `:SHACLViolation` nodes
- [ ] Store violations as `(:SHACLViolation)-[:HAS_VIOLATION]->(node)`
- [ ] Create `shacl_fastapi.py` routes:
  - [ ] `GET /api/shacl/validate/{label}` — batch validate
  - [ ] `GET /api/shacl/violations/{uid}` — per-node violations
  - [ ] `GET /api/shacl/report` — summary (violation counts by label/severity)
- [ ] Register in `app_fastapi.py`
- [ ] Create `SHACLAgent` wrapper that calls `SHACLValidationService`

---

## Phase 4 — Agent Contracts & Routing

### Task 7 — Formalize Agent Contracts
**Status:** ✅ Complete  
**Files:** All agent `.py` files  
**Depends on:** Tasks 3, 4, 6  
**Complexity:** Medium  
**Architecture ref:** Section 7

**Changes required:**
- [ ] Add `INPUT_SCHEMA` and `OUTPUT_SCHEMA` class-level dicts to each agent
- [ ] Add `@property task_types: list[str]` to each agent
- [ ] Ensure all agents return consistent dict structure (no free-form strings)
- [ ] Create `backend/src/agents/contracts.py` with `AgentContract` base dataclass
- [ ] Register all agents in a `AGENT_REGISTRY: dict[str, AgentContract]` dict

---

### Task 8 — Orchestrator State Machine
**Status:** ✅ Complete  
**File:** `backend/src/agents/orchestrator_workflow.py`  
**Depends on:** Task 7  
**Complexity:** Large  
**Architecture ref:** Section 7.3, Section 8

**Changes required:**
- [ ] Extend `task_type` Literal with all new types: `shacl_validate`, `semantic_search`, `semantic_insight`, `ont_classify`, `export_rdf`, `export_csv`
- [ ] Add routing entries for SHACL, semantic, export keywords
- [ ] Wire post-ingest callbacks: after `plm_ingest` success → call ontology linker, SHACL validator, vectorizer, TRS broadcaster
- [ ] Add `kg_expand` task type → MBSEAgent with 2-hop expansion
- [ ] Ensure early-exit guard covers all specialized task types (no double-execution in MBSEAgent)

---

## Phase 5 — Query Layer

### Task 9 — Graph Query Registry
**Status:** ✅ Complete  
**File:** `backend/src/web/services/graph_query_registry.py` (NEW)  
**Depends on:** Task 3  
**Complexity:** Small  
**Architecture ref:** Section 12

**Changes required:**
- [ ] Create `QUERY_REGISTRY: dict[str, str]` with all named Cypher queries
- [ ] Implement `execute_named_query(name, params, limit)` helper
- [ ] Add `GET /api/graph/query/{name}` route exposing registry
- [ ] Views to register: `bom_tree`, `ontology_hierarchy`, `classification_web`, `traceability_chain`, `shacl_violations`, `semantic_neighbors`, `step_geometry`, `oslc_req_links`

---

## Phase 6 — Chat & AI

### Task 10 — Chat Agent RAG Pipeline
**Status:** ✅ Complete  
**File:** `backend/src/agents/semantic_agent.py` (NEW or extend)  
**Depends on:** Tasks 4, 8  
**Complexity:** Medium  
**Architecture ref:** Section 9

**Changes required:**
- [ ] Create `SemanticAgent` class (separate from `VectorStoreTool`)
- [ ] Implement `semantic_search(query, top_k, expand, threshold)`:
  - [ ] Step 1: Embed query via Ollama
  - [ ] Step 2: OpenSearch kNN search
  - [ ] Step 3: Neo4j 2-hop expansion per hit
  - [ ] Step 4: Assemble context dict
- [ ] Implement `semantic_insight(question, top_k)`:
  - [ ] Calls `semantic_search`
  - [ ] Assembles prompt with context
  - [ ] Calls LLM for synthesis
  - [ ] Returns markdown answer + source links
- [ ] Implement full-text fallback when OpenSearch unavailable
- [ ] Wire into chat endpoint (`POST /api/chat/message`)

---

### Task 11 — AI Insights + SmartAnalysis
**Status:** ✅ Complete  
**Files:** Frontend + backend services  
**Depends on:** Tasks 9, 10  
**Complexity:** Large  
**Architecture ref:** Sections 10, 11

**Changes required:**

**Backend:**
- [ ] `GET /api/insights/bom-completeness` — count unclassified + missing revisions
- [ ] `GET /api/insights/traceability-gaps` — requirements without TRACES_TO
- [ ] `GET /api/insights/classification-coverage` — % PLMXMLItem with CLASSIFIED_AS
- [ ] `GET /api/insights/semantic-duplicates` — kNN self-query, cosine > 0.95
- [ ] `GET /api/insights/shacl-compliance` — violations / total_nodes by label
- [ ] `POST /api/smart-analysis/{uid}` — per-node deep analysis (5-step pipeline)

**Frontend:**
- [ ] SmartAnalysis panel: tabs [Overview | Ontology | Similar | Violations | Graph]
- [ ] AI Insights dashboard: cards per insight type with refresh button
- [ ] Graph view: wire named queries from registry to graph renderer

---

## Phase 7 — OSLC TRS Sync

### Task 12 — OSLC TRS Sync Trigger
**Status:** ✅ Complete  
**File:** `backend/src/web/services/oslc_trs_service.py` (extend)  
**Depends on:** Task 8  
**Complexity:** Small  
**Architecture ref:** Section 13

**Changes required:**
- [ ] Add `append_change_event(resource_uri, change_type)` to `OSLCTRSService`
- [ ] Call from `PLMXMLIngestService` post-write (non-blocking)
- [ ] Call from `StepIngestService` post-write (non-blocking)
- [ ] Verify `GET /api/oslc/trs` returns valid TRS document after ingest
- [ ] Add `GET /api/oslc/trs/base` and `GET /api/oslc/trs/changelog` if not present

---

## Phase 8 — Infrastructure Setup (OpenSearch, Neo4j, Ollama)

### Task 13 — OpenSearch Index Setup & Health Verification
**Status:** ✅ Complete  
**File:** `backend/scripts/setup_opensearch.py` (NEW)  
**Depends on:** nothing  
**Complexity:** Small  
**Architecture ref:** Section 14

**Pre-conditions:**
- OpenSearch 3.3.1 installed at `D:\Software\opensearch-3.3.1`
- Security plugin disabled (`plugins.security.disabled: true`)
- Start: `.\scripts\start_opensearch.ps1 -Detach`

**Changes required:**
- [ ] Verify `GET http://localhost:9200` returns cluster info (green/yellow)
- [ ] Create `setup_opensearch.py` script that:
  - [ ] Checks cluster health
  - [ ] Creates `embeddings` index with HNSW mapping (dim=768, lucene, cosinesimil)
  - [ ] Verifies index exists: `GET /embeddings`
  - [ ] Prints count: `GET /embeddings/_count`
- [ ] Add `OPENSEARCH_HOME` to `.env` pointing to installation dir
- [ ] Add OpenSearch start to `deployment/scripts/` startup sequence
- [ ] Verify `GET /api/vector/stats` returns `{ "total_docs": 0 }` from running FastAPI

---

### Task 14 — Neo4j Schema: Constraints, Indexes & Full-Text
**Status:** ✅ Complete  
**File:** `backend/scripts/setup_neo4j_schema.py` (NEW)  
**Depends on:** Neo4j running with `mossec` database  
**Complexity:** Small  
**Architecture ref:** Section 15

**Changes required:**
- [ ] Create `setup_neo4j_schema.py` that runs all Cypher DDL statements:
  - [ ] Unique constraints: `PLMXMLItem.uid`, `PLMXMLRevision.uid`, `PLMXMLBOMLine.uid`, `PLMXMLDataSet.uid`, `StepFile.uid`, `ExternalOwlClass.uri`, `SHACLViolation.uid`
  - [ ] Index on `PLMXMLItem.item_type`, `PLMXMLItem.name`
  - [ ] Index on `ExternalOwlClass.name`, `ExternalOwlClass.ap_level`
  - [ ] Index on `SHACLViolation.target_uid`
  - [ ] Full-text index `plmxml_fulltext` on PLMXMLItem/Revision/DataSet name fields
  - [ ] Full-text index `ontology_fulltext` on ExternalOwlClass/OWLProperty name/description
- [ ] Run script and verify with `SHOW INDEXES`
- [ ] Add script to `deployment/DEPLOYMENT_CHECKLIST.md`

---

### Task 15 — Ollama Model Pull & Embedding Verification
**Status:** ✅ Complete  
**File:** `backend/scripts/verify_ollama.py` (NEW)  
**Depends on:** Ollama installed and `ollama serve` running  
**Complexity:** Small  
**Architecture ref:** Section 16

**Changes required:**
- [ ] Pull required models:
  ```bash
  ollama pull nomic-embed-text   # 768-dim embeddings
  ollama pull llama3             # chat/synthesis
  ```
- [ ] Create `verify_ollama.py` that:
  - [ ] `GET http://localhost:11434` — verify server up
  - [ ] `POST /api/embeddings` with `nomic-embed-text` — verify returns `float[768]`  
  - [ ] `POST /api/chat` with `llama3` + short prompt — verify response
  - [ ] Prints model list from `GET /api/tags`
- [ ] Verify `OllamaEmbeddings.embed(["test"])` returns non-empty vector in Python
- [ ] Add `OLLAMA_BASE_URL`, `OLLAMA_EMBED_MODEL`, `OLLAMA_CHAT_MODEL` to `.env`

---

## Phase 9 — Frontend: AI Studio Wiring

### Task 16 — ModelChat & Chatbot: Semantic Response Wiring
**Status:** ✅ Complete  
**Files:**  
  - `frontend/src/features/ai-studio/components/ModelChat.jsx`  
  - `frontend/src/features/ai-studio/components/Chatbot.tsx`  
**Depends on:** Task 10 (Chat RAG pipeline backend)  
**Complexity:** Medium  
**Architecture ref:** Section 17.2

**Current state:** Chat UI renders, `runOrchestrator()` sends query, markdown response renders.  

**Changes required:**
- [ ] Parse `result.data.hits` from `semantic_search` response — render as source citations below answer
- [ ] Render `result.data.sources` as clickable node links (click \u2192 open SmartAnalysis panel)
- [ ] Add "Search mode" toggle: `general` (kg_query) vs `semantic` (semantic_search)
- [ ] `Chatbot.tsx`: inject selected graph node uid as `context.uid` in orchestrator payload
- [ ] Add SSE streaming support (`EventSource` \u2192 `POST /api/orchestrate/stream`) — optional
- [ ] Show spinner while awaiting response; show "Searching graph + OpenSearch..." status text
- [ ] Add `agents.service.ts`: `semanticSearch(query, topK)` calling `POST /api/vector/search`

---

### Task 17 — AIInsights: Backend Endpoints + Frontend Wiring
**Status:** ✅ Complete  
**Files:**  
  - `frontend/src/features/ai-studio/components/AIInsights.jsx`  
  - `backend/src/web/routes/insights_fastapi.py` (NEW)  
  - `backend/src/web/app_fastapi.py` (register route)  
**Depends on:** Tasks 3, 4, 6  
**Complexity:** Large  
**Architecture ref:** Sections 11, 17.2

**Backend — 6 insight endpoints to create:**
- [ ] `GET /api/insights/bom-completeness`
  - Query: Count `PLMXMLItem` total vs `unclassified=true` + count items with 0 revisions
  - Returns: `{ total, classified, unclassified, missing_revision_count }`
- [ ] `GET /api/insights/traceability-gaps`
  - Query: `MATCH (r:Requirement) WHERE NOT (r)-[:TRACES_TO]->() RETURN r`
  - Returns: `{ gap_count, requirements: [{uid, title}] }`
- [ ] `GET /api/insights/classification-coverage`
  - Query: `% of PLMXMLItem/Revision/StepFile with at least one [:CLASSIFIED_AS]`
  - Returns: `{ coverage_pct, by_label: {PLMXMLItem: pct, ...} }`
- [ ] `GET /api/insights/semantic-duplicates`
  - For each vectorized item: kNN self-query, flag pairs with cosine > 0.95 and different uid
  - Returns: `{ duplicate_pairs: [{uid_a, uid_b, score, name_a, name_b}] }`
- [ ] `GET /api/insights/shacl-compliance`
  - Query: `violation count / total nodes` per label/severity
  - Returns: `{ compliance_pct, violations_by_label: {...}, violations_by_severity: {...} }`
- [ ] `GET /api/insights/ap-alignment`
  - Query: distribution of `[:CLASSIFIED_AS].ap_level` across all instance nodes
  - Returns: `{ AP239: n, AP242: n, AP243: n, unclassified: n }`

**Frontend — AIInsights.jsx:**
- [ ] Replace mock data with API calls to all 6 endpoints
- [ ] Render each as a card: title, number metric, mini bar chart, "View details" link
- [ ] Add "Refresh all" button + per-card refresh
- [ ] Auto-refresh every 60s (configurable)
- [ ] Add `insights.service.ts` in `frontend/src/services/`

---

### Task 18 — SmartAnalysis: Backend Endpoint + Frontend Wiring
**Status:** ✅ Complete  
**Files:**  
  - `frontend/src/features/ai-studio/components/SmartAnalysis.jsx`  
  - `backend/src/web/routes/smart_analysis_fastapi.py` (NEW)  
  - `backend/src/web/app_fastapi.py` (register route)  
**Depends on:** Tasks 3, 6, 10  
**Complexity:** Large  
**Architecture ref:** Sections 10, 17.2

**Backend — `POST /api/smart-analysis/{uid}`:**
- [ ] Step 1: `MBSEAgent.get_context(uid, hops=3)` — node props + 3-hop neighbors
- [ ] Step 2: `SemanticAgent.find_similar(uid, top_k=5)` — kNN using node's stored vector
- [ ] Step 3: `SHACLAgent.get_violations(uid)` — active `:SHACLViolation` nodes
- [ ] Step 4: `OntologyAgent.get_classification_chain(uid)` — `CLASSIFIED_AS` \u2192 `SUBCLASS_OF*` to root
- [ ] Step 5: LLM synthesis \u2192 structured JSON response
- [ ] Returns: `{ summary, classification_chain, similar_items, violations, recommendations }`

**Frontend — SmartAnalysis.jsx:**
- [ ] Wire tab [Overview] to `summary` field from API
- [ ] Wire tab [Ontology] to `classification_chain` — render as breadcrumb + AP level badge
- [ ] Wire tab [Similar] to `similar_items` — list with score + type + click-to-navigate
- [ ] Wire tab [Violations] to `violations` — severity-colored list with shape + message
- [ ] Wire tab [Graph] to `GET /api/graph/query/semantic_neighbors?uid={uid}` — mini graph
- [ ] Node uid input: accept from URL param `?uid=`, from graph click event, or manual input
- [ ] Add `smart-analysis.service.ts` in `frontend/src/services/`

---

## Phase 10 — Frontend: Graph Explorer Wiring

### Task 19 — GraphBrowser: Named Query Registry Integration
**Status:** ✅ Complete  
**Files:**  
  - `frontend/src/features/graph-explorer/components/GraphBrowser.jsx`  
  - `frontend/src/services/query.service.ts`  
**Depends on:** Task 9 (graph_query_registry backend)  
**Complexity:** Medium  
**Architecture ref:** Sections 12, 17.3

**Changes required:**
- [ ] Add query picker dropdown: `[BOM Tree | Ontology Hierarchy | Classification Web | Traceability | SHACL Violations | Semantic Neighbors | STEP Geometry]`
- [ ] On selection: call `GET /api/graph/query/{name}?{params}` via `query.service.ts`
- [ ] Render result nodes/edges into existing force-directed canvas
- [ ] Color-code nodes by label: PLMXMLItem=blue, ExternalOwlClass=green, SHACLViolation=red, StepFile=orange
- [ ] `CLASSIFIED_AS` edges: render as dashed purple arrows
- [ ] `SUBCLASS_OF` edges: render as solid green arrows
- [ ] Node click event: emit `uid` to parent \u2192 open SmartAnalysis panel sidebar
- [ ] Add `query.service.ts`: `executeNamedQuery(name, params)` \u2192 `GET /api/graph/query/{name}`

---

### Task 20 — OntologyGraph & AP-Level Graphs Wiring
**Status:** ✅ Complete  
**Files:**  
  - `frontend/src/features/graph-explorer/components/OntologyGraph.jsx`  
  - `frontend/src/features/graph-explorer/components/AP239Graph.jsx`  
  - `frontend/src/features/graph-explorer/components/AP242Graph.jsx`  
  - `frontend/src/features/graph-explorer/components/AP243Graph.jsx`  
**Depends on:** Task 2 (cross-ontology edges), Task 14  
**Complexity:** Medium  
**Architecture ref:** Section 17.3

**Changes required:**
- [ ] `OntologyGraph.jsx`: call `GET /api/graph/query/ontology_hierarchy` — render SUBCLASS_OF tree
- [ ] Add ap_level color filter toggle (AP239=purple, AP242=blue, AP243=gold)
- [ ] `AP243Graph.jsx`: filter to `ap_level=AP243` nodes only \u2014 shows reference data layer
- [ ] `AP242Graph.jsx`: filter to `ap_level=AP242` — shows CAD/product structure layer
- [ ] `AP239Graph.jsx`: filter to `ap_level=AP239` — shows systems engineering layer
- [ ] Add `CLASSIFIED_AS` instance count badge on each class node
- [ ] Click class node \u2192 list all `:PLMXMLItem` nodes classified under it

---

## Phase 11 — Frontend: Semantic Web Components Wiring

### Task 21 — SHACLValidator Component Wiring
**Status:** ✅ Complete  
**File:** `frontend/src/features/semantic-web/components/SHACLValidator.jsx`  
**Depends on:** Task 6 (SHACLValidationService backend)  
**Complexity:** Medium  
**Architecture ref:** Section 17.4

**Changes required:**
- [ ] Wire "Run Validation" button \u2192 `GET /api/shacl/validate/{label}`
- [ ] Render violation list: severity badge (red/orange/yellow) + shape name + message
- [ ] Add compliance score gauge: `violations / total_nodes`
- [ ] Add per-node violation lookup: input uid \u2192 `GET /api/shacl/violations/{uid}`
- [ ] Wire "Summary Report" button \u2192 `GET /api/shacl/report`
- [ ] Add `validation.service.ts`: `validateLabel(label)`, `getViolations(uid)`, `getReport()`
- [ ] Link violation rows to GraphBrowser (click uid \u2192 navigate to node)

---

### Task 22 — TRSFeed Component Wiring
**Status:** ✅ Complete  
**File:** `frontend/src/features/semantic-web/components/TRSFeed.jsx`  
**Depends on:** Task 12 (OSLC TRS sync trigger)  
**Complexity:** Small  
**Architecture ref:** Section 13, 17.4

**Changes required:**
- [ ] Wire to `GET /api/oslc/trs/changelog` — poll every 10s
- [ ] Render change events: timestamp, change_type (Creation/Modification/Deletion), resource_uri
- [ ] Color-code by type: green=Creation, amber=Modification, red=Deletion
- [ ] Show total event count from `GET /api/oslc/trs/base`
- [ ] Add `oslc.service.ts`: `getTRSChangelog()`, `getTRSBase()`

---

### Task 23 — OntologyManager: CLASSIFIED_AS Count + Cross-Ontology View
**Status:** ✅ Complete  
**File:** `frontend/src/features/semantic-web/components/OntologyManager.jsx`  
**Depends on:** Tasks 2, 3  
**Complexity:** Small  
**Architecture ref:** Section 17.4

**Changes required:**
- [ ] After Task 3 complete: add `classified_count` column to class list (how many instances link to this class)
- [ ] Add cross-ontology filter: show SUBCLASS_OF chain for a class across AP239/242/243
- [ ] Add "Ingest Standard Ontologies" button \u2192 `POST /api/ontology/ingest-standard`
- [ ] Show last-ingested timestamp per ontology
- [ ] Add unclassified items count \u2192 link to `GET /api/insights/bom-completeness`

---

## Progress Summary

| Phase | Tasks | Done | In Progress | Not Started |
|---|---|---|---|---|
| 1 — Ontology Foundation | 2 | 2 | 0 | 0 |
| 2 — Semantic Linking | 2 | 2 | 0 | 0 |
| 3 — SHACL Validation | 2 | 2 | 0 | 0 |
| 4 — Agent Contracts | 2 | 2 | 0 | 0 |
| 5 — Query Layer | 1 | 1 | 0 | 0 |
| 6 — Chat & AI | 2 | 2 | 0 | 0 |
| 7 — OSLC TRS | 1 | 1 | 0 | 0 |
| 8 — Infrastructure | 3 | 3 | 0 | 0 |
| 9 — Frontend: AI Studio | 3 | 3 | 0 | 0 |
| 10 — Frontend: Graph Explorer | 2 | 2 | 0 | 0 |
| 11 — Frontend: Semantic Web | 3 | 3 | 0 | 0 |
| **Total** | **23** | **23** | **0** | **0** |

---

## Already Complete (Pre-existing)

| Component | File | Notes |
|---|---|---|
| ElasticsearchVectorStore | `agents/vectorstore_es.py` | HNSW kNN, cosine, raw REST |
| VectorStoreTool | `agents/agent_tools.py` | embed + upsert + search wrapper |
| Vector REST API | `routes/vector_fastapi.py` | index, search, stats, reconcile |
| OntologyIngestService | `services/ontology_ingest_service.py` | OWL/RDF → ExternalOwlClass, SUBCLASS_OF |
| OntologyAgent | `agents/ontology_agent.py` | ingest, find_classes, hierarchy, resolve |
| PLMXMLIngestService | `services/plmxml_ingest_service.py` | v4/v5 parser ✅ — v6 fix pending |
| PLMXML REST API | `routes/plmxml_ingest_fastapi.py` | 6 routes complete |
| PLMAgent | `agents/plm_agent.py` | ingest_plmxml, list_items, get_bom |
| OSLC Service | `services/oslc_service.py` | rootservices, catalog, RM |
| OSLC TRS Service | `services/oslc_trs_service.py` | base TRS (extend for triggers) |
| OSLC Seed TTLs | `data/seed/oslc/*.ttl` | 5 files — cross-links missing |
| StepAgent | `agents/step_agent.py` | step_ingest, step_query |
| MBSEAgent | `agents/mbse_agent.py` | kg_query |
| Orchestrator | `agents/orchestrator_workflow.py` | route + early-exit guard |

---

## Decision Log

| Date | Decision | Rationale |
|---|---|---|
| 2026-03-02 | Post-ingest order: Neo4j → CLASSIFIED_AS → SHACL → OpenSearch → TRS | Neo4j is system of record; all downstream steps are non-blocking |
| 2026-03-02 | Ontology merge key: `{uri: row.uri}` (not name) | URIs are globally unique; name collisions across AP ontologies are possible |
| 2026-03-02 | CLASSIFIED_AS by `cls.name = item.item_type` first, then fuzzy | TC exports use plain English type names (Part, Document) matching AP242 rdfs:labels |
| 2026-03-02 | AP243 is top-most for classification; OSLC Core is top-most for protocol | Different axes: AP243 = semantic/reference; OSLC = interoperability protocol |
| 2026-03-02 | No `owl:imports` in TTLs — use explicit SUBCLASS_OF edges instead | Keeps ingest deterministic; `owl:imports` would require recursive RDF parsing |
| 2026-03-02 | OpenSearch failure → write pending file, do not fail ingest | Ingest must be reliable; vectors are supplementary, back-fillable via reconcile |
| 2026-03-02 | SHACL pre-write guard only in STRICT_MODE; default is audit-only | Avoid blocking ingest during initial data loading phase |
