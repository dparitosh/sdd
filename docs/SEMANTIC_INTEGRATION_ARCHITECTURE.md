# SDD-MOSSEC — Semantic Integration Architecture
**Version:** 1.0  
**Date:** 2026-03-02  
**Status:** Formal Plan — Implementation in Progress

---

## 1. System Overview

SDD-MOSSEC is a knowledge-graph-centric MBSE platform that integrates:
- **Teamcenter PLMXML / STEP** — product structure and 3D geometry from NX/TC
- **OWL Ontologies** — AP239 (PLCS), AP242 (MBx), AP243 (MoSSEC), OSLC Core/RM
- **SHACL Shapes** — constraint validation on graph instances
- **OpenSearch** — HNSW dense-vector index for semantic similarity
- **OSLC** — lifecycle interoperability protocol (TRS, RM, catalog)
- **LLM Agents** — LangGraph multi-agent orchestration via Ollama / OpenAI

---

## 2. Layer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  L5 — UI Layer                                                  │
│  Chat · GraphView · AI Insights · SmartAnalysis                 │
├─────────────────────────────────────────────────────────────────┤
│  L4 — Agentic Orchestration Layer                               │
│  OrchestratorAgent → [PLM · MBSE · Ontology · Step · OSLC ·    │
│                        Semantic · SHACL · Export]               │
├─────────────────────────────────────────────────────────────────┤
│  L3 — Knowledge Graph Layer                                     │
│  Neo4j: instances + ontology nodes + SHACL violation nodes      │
│  OpenSearch: HNSW kNN vector index (cosine, dim=768)            │
├─────────────────────────────────────────────────────────────────┤
│  L2 — Semantic Integration Layer                                │
│  CLASSIFIED_AS · SUBCLASS_OF · EQUIVALENT_CLASS                 │
│  SHACL validate-on-write · OSLC TRS broadcast                   │
├─────────────────────────────────────────────────────────────────┤
│  L1 — Ingestion Layer                                           │
│  PLMXML v4/v5/v6 · STEP AP214/AP242 · OWL/RDF/TTL · OSLC       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Ontology Stack

### 3.1 OSLC Protocol Layer (horizontal)
| Ontology | File | Purpose |
|---|---|---|
| OSLC Core | `data/seed/oslc/oslc-core.ttl` | ServiceProvider, Service, QueryCapability, CreationFactory |
| OSLC-RM | `data/seed/oslc/oslc-rm.ttl` | Requirement, RequirementCollection — base types |

### 3.2 AP Domain Ontologies (vertical hierarchy)
```
AP243 — MoSSEC Reference Data (TOP / Foundation)
  └─ Defines: ExternalOwlClass, ExternalUnit, Classification, ValueType
  └─ File: smrlv12/data/domain_models/mossec/ap243_v1.owl
  └─ OSLC: data/seed/oslc/oslc-ap243.ttl

  AP242 — Managed Model-Based 3D Engineering (MID / CAD)
    └─ Subclasses/uses AP243 concepts
    └─ Defines: Part, PartVersion, PartOccurrence, GeometryRepresentation
    └─ File: smrlv12/data/core_model/core_v4.owl
    └─ OSLC: data/seed/oslc/oslc-ap242.ttl
    └─ ← PLMXML items (Product/Part) map here

    AP239 / PLCS — Product Life Cycle Support (BOTTOM / Systems Engineering)
      └─ Subclasses/uses AP242 concepts
      └─ Defines: Requirement, Document, LifecycleEvent, Configuration
      └─ File: smrlv12/data/domain_models/product_life_cycle_support/4439_rd_v2.owl
      └─ OSLC: data/seed/oslc/oslc-ap239.ttl
      └─ ← OSLC-RM requirements map here
```

### 3.3 Cross-Ontology SUBCLASS_OF Edges (to be added — Task 2)

The three OSLC TTLs are currently disconnected islands. The following edges will be
declared to connect them into a traversable hierarchy:

```turtle
# oslc-ap242.ttl — connect up to AP243
ap242:Part           rdfs:subClassOf  ap243:Product .
ap242:PartVersion    rdfs:subClassOf  ap243:ProductVersion .
ap242:PartOccurrence rdfs:subClassOf  ap243:ProductOccurrence .
ap242:Drawing        rdfs:subClassOf  ap243:Document .

# oslc-ap239.ttl — connect up to AP242 and OSLC-RM
ap239:Requirement    rdfs:subClassOf  oslc_rm:Requirement .
ap239:Document       rdfs:subClassOf  ap242:Drawing .
ap239:BreakdownElement rdfs:subClassOf ap242:Part .
```

After re-ingestion, Neo4j will have connected `[:SUBCLASS_OF]` paths enabling
queries like:  
`MATCH (c:ExternalOwlClass)-[:SUBCLASS_OF*1..5]->(root) WHERE root.name = "Product"`

### 3.4 PLMXML-to-Ontology Mapping

| PLMXML Element (TC v13) | Neo4j Label | Maps to ExternalOwlClass |
|---|---|---|
| `<Product subType="Item">` | `:PLMXMLItem {item_type:"Item"}` | `ap242:Part` |
| `<Product subType="Document">` | `:PLMXMLItem {item_type:"Document"}` | `ap239:Document` |
| `<Product subType="Assembly">` | `:PLMXMLItem {item_type:"Assembly"}` | `ap242:Assembly` |
| `<ProductRevision>` | `:PLMXMLRevision` | `ap242:PartVersion` |
| `<ProductInstance>` in `<InstanceGraph>` | `:PLMXMLBOMLine` | `ap242:PartOccurrence` |
| `<DataSet format="UGMASTER">` | `:PLMXMLDataSet` | `ap242:GeometryRepresentation` |
| `<DataSet format="DirectModel">` | `:PLMXMLDataSet` | `ap242:ShapeRepresentation` |
| `:StepFile` | `:StepFile` | `ap242:ShapeRepresentation` |

---

## 4. Neo4j Graph Schema

### 4.1 Instance Node Labels
```
:PLMXMLFile       {file_uri, schema_version, tc_version, label, item_count, ...}
:PLMXMLItem       {uid, item_id, name, item_type, object_type, unclassified}
:PLMXMLRevision   {uid, rev_id, item_uid, name, sequence_no}
:PLMXMLBOMLine    {uid, find_num, quantity, ref_uid, transform}
:PLMXMLDataSet    {uid, name, type, format, member_files[]}
:StepFile         {uid, name, file_uri, ap_level, entity_count, source_file}
:StepInstance     {uid, entity_type, entity_id, raw_args}
```

### 4.2 Ontology Node Labels (loaded from OWL/TTL)
```
:ExternalOwlClass  {uri, name, description, ontology, ap_level}   ← also :OWLClass
:OWLProperty       {uri, name, domain_uri, range_uri, ontology}
:ExternalUnit      {uri, name, symbol, ontology}
:ValueType         {uri, name, datatype, ontology}
:Classification    {uri, name, description, ontology}
:Ontology          {uri, name, source_file, ap_level}
```

### 4.3 Semantic / Validation Node Labels
```
:SHACLViolation    {uid, target_uid, shape, severity, message, timestamp}
```

### 4.4 Relationship Inventory
```
Instance relations:
  (:PLMXMLFile)      -[:CONTAINS]->           (:PLMXMLItem)
  (:PLMXMLItem)      -[:HAS_REVISION]->        (:PLMXMLRevision)
  (:PLMXMLRevision)  -[:HAS_BOM_LINE]->        (:PLMXMLBOMLine)
  (:PLMXMLBOMLine)   -[:REFERENCES]->          (:PLMXMLItem)
  (:PLMXMLRevision)  -[:HAS_DATASET]->         (:PLMXMLDataSet)
  (:PLMXMLDataSet)   -[:LINKED_STEP_FILE]->    (:StepFile)

Semantic relations (post-ingest):
  (:PLMXMLItem)      -[:CLASSIFIED_AS {source, ap_level, confidence}]-> (:ExternalOwlClass)
  (:PLMXMLRevision)  -[:CLASSIFIED_AS]->       (:ExternalOwlClass)
  (:PLMXMLBOMLine)   -[:CLASSIFIED_AS]->       (:ExternalOwlClass)
  (:PLMXMLDataSet)   -[:CLASSIFIED_AS]->       (:ExternalOwlClass)
  (:StepFile)        -[:CLASSIFIED_AS]->       (:ExternalOwlClass)

Ontology relations:
  (:ExternalOwlClass)-[:SUBCLASS_OF]->         (:ExternalOwlClass)
  (:ExternalOwlClass)-[:EQUIVALENT_CLASS]->    (:ExternalOwlClass)
  (:Ontology)        -[:DEFINES_REFERENCE_DATA]->(:ExternalOwlClass)

SHACL relations:
  (:SHACLViolation)  -[:HAS_VIOLATION]->       (:PLMXMLItem | :PLMXMLRevision | ...)
```

---

## 5. Post-Ingest Pipeline

Every ingest service (`PLMXMLIngestService`, `StepIngestService`) executes the
following sequence. Each step is **non-blocking** — failures are logged but do not
roll back the Neo4j write.

```
Step 1: Parse source file
Step 2: MERGE nodes into Neo4j          ← system of record (blocking — must succeed)
Step 3: Link CLASSIFIED_AS              ← ontology classification (non-blocking)
        - Exact name match: cls.name = item.item_type
        - Fuzzy fallback: toLower(cls.name) CONTAINS toLower(item_type)
        - No match: item.unclassified = true, logged to reconcile queue
Step 4: SHACL validate_batch(label)     ← write :SHACLViolation nodes (non-blocking)
Step 5: Vectorize → OpenSearch upsert   ← embed text → HNSW index (non-blocking)
        - If OpenSearch down: write uid to data/vectorize_progress/{uid}.pending
Step 6: OSLC TRS broadcast              ← append change event to TRS changelog (non-blocking)

Return: IngestResult {
  items_written, violations, vectors_indexed,
  unclassified_count, trs_events
}
```

---

## 6. SHACL Validation

### 6.1 Shape Definitions
File: `backend/data/seed/shacl/plmxml_shapes.ttl`

| Shape | Target Class | Key Constraints |
|---|---|---|
| `PLMXMLItemShape` | `ap242:Part` | `item_id` required (minCount 1), ≥1 revision |
| `PLMXMLRevisionShape` | `ap242:PartVersion` | `rev_id` required, parent item must exist |
| `PLMXMLBOMLineShape` | `ap242:PartOccurrence` | `ref_uid` must resolve to existing `:PLMXMLItem` |
| `PLMXMLDataSetShape` | `ap242:GeometryRepresentation` | `name` required, `type` in allowed set |
| `StepFileShape` | `ap242:ShapeRepresentation` | `entity_count > 0` |
| `RequirementShape` | `ap239:Requirement` | `title` required, `oslc_rm:Requirement` subclass |

### 6.2 Validation Modes
- **Pre-write guard** — called before bulk ingest; blocks write on CRITICAL violations
- **Post-ingest audit** — called after write; stores all violations as `:SHACLViolation` nodes
- **On-demand** — `GET /api/shacl/validate/{label}` or agent-triggered

### 6.3 Violation Node Schema
```cypher
(:SHACLViolation {
  uid:        string,           // auto-generated
  target_uid: string,           // uid of violating node
  shape:      string,           // shape name
  severity:   "Violation"|"Warning"|"Info",
  message:    string,
  path:       string,           // sh:path value
  timestamp:  datetime
})
-[:HAS_VIOLATION]->(:PLMXMLItem | :PLMXMLRevision | ...)
```

---

## 7. Agent Architecture

### 7.1 Agent Roster and Responsibilities

| Agent | File | task_types | Single Responsibility |
|---|---|---|---|
| **OrchestratorAgent** | `orchestrator_workflow.py` | `route` | Intent classification → dispatch to specialist |
| **PLMAgent** | `plm_agent.py` | `plm_ingest`, `plm_query`, `plm_bom` | PLMXML/STEP ingest and BOM queries |
| **MBSEAgent** | `mbse_agent.py` | `kg_query`, `kg_expand` | General Neo4j graph queries and expansion |
| **OntologyAgent** | `ontology_agent.py` | `ont_ingest`, `ont_classify`, `ont_search` | OWL ingest, CLASSIFIED_AS linking, class search |
| **SHACLAgent** | `shacl_agent.py` | `shacl_validate`, `shacl_report` | Pre/post validation, violation queries |
| **SemanticAgent** | `semantic_agent.py` | `semantic_search`, `semantic_insight` | OpenSearch kNN + Neo4j expansion + LLM synthesis |
| **StepAgent** | `step_agent.py` | `step_ingest`, `step_query` | STEP AP214/AP242 parse and entity queries |
| **OSLCAgent** | `oslc_agent.py` (routes) | `oslc_sync`, `oslc_query` | TRS broadcast, OSLC RM operations |
| **ExportAgent** | `export_agent.py` | `export_rdf`, `export_csv`, `export_step` | Export graph subsets in requested format |

### 7.2 Agent Input / Output Contracts

```python
# OrchestratorAgent
Input:  { query: str, context: dict, session_id: str }
Output: { task_type: Literal[...], routed_to: str, payload: dict }

# PLMAgent
Input:  { file_path: str } | { item_id: str } | { query: str }
Output: { items: int, revisions: int, bom_lines: int, violations: int,
          vectors_indexed: int, trs_events: int }

# OntologyAgent
Input:  { file_path: str } | { keyword: str } | { uids: list[str] }
Output: { classes_linked: int, unclassified: int } | list[ClassInfo]

# SHACLAgent
Input:  { label: str } | { uid: str } | { shape: str }
Output: { violations: list[ViolationInfo], summary: str }

# SemanticAgent
Input:  { query: str, top_k: int, expand: bool, threshold: float }
Output: { hits: list[HitInfo], insight: str, sources: list[str] }

# ExportAgent
Input:  { query: str, format: "rdf"|"csv"|"step"|"json" }
Output: { file_path: str, record_count: int }
```

### 7.3 Orchestrator Routing Table (keyword + LLM fallback)

| Keywords | → Agent | task_type |
|---|---|---|
| plmxml, teamcenter, bom, induction motor, item revision | PLMAgent | `plm_ingest` / `plm_bom` |
| step, stp, entity, geometry, solid | StepAgent | `step_ingest` / `step_query` |
| ontology, owl, classify, class, subclass | OntologyAgent | `ont_classify` / `ont_search` |
| shacl, validate, violation, constraint | SHACLAgent | `shacl_validate` |
| similar, semantic, find related, vector | SemanticAgent | `semantic_search` |
| requirement, oslc, traceability, traces to | OSLCAgent / MBSEAgent | `oslc_query` / `kg_query` |
| export, download, rdf, csv | ExportAgent | `export_*` |
| (fallback) | MBSEAgent | `kg_query` |

---

## 8. Agentic Workflow — Full PLMXML Ingest Sequence

```
User: POST /api/plmxml/upload  (file: induction_motor.xml)
  │
  ▼
OrchestratorAgent
  │  task_type = "plm_ingest"
  ▼
PLMAgent.ingest_plmxml(file_path)
  │
  ├── PLMXMLIngestService.ingest_file(path)
  │     ├── _PLMXMLParser.parse()
  │     │     ├── _iter_items()      → <Product subType="...">
  │     │     ├── _iter_revisions()  → <ProductRevision>
  │     │     ├── _iter_bom_lines()  → <ProductInstance> in <InstanceGraph>
  │     │     └── _iter_datasets()   → <DataSet>
  │     │
  │     └── _write_to_neo4j(result)  ← MERGE all nodes/edges
  │           RETURNS: {items_written, uids[]}
  │
  ├── [on success] OntologyAgent._link_ontology_classes(uids)
  │     ├── MATCH cls WHERE cls.name = item_type AND cls.ap_level IN ["AP242","AP243"]
  │     ├── MERGE (item)-[:CLASSIFIED_AS]->(cls)
  │     └── item.unclassified = true if no match
  │
  ├── [on success] SHACLAgent.validate_batch("PLMXMLItem")
  │     ├── pyshacl.validate(nodes_as_rdf, shapes_graph)
  │     └── MERGE (:SHACLViolation)-[:HAS_VIOLATION]->(item)
  │
  ├── [on success] SemanticAgent.vectorize_nodes(uids)
  │     ├── text = "item_id:{id} name:{name} type:{type} rev:{rev}"
  │     ├── embedding = OllamaEmbeddings.embed([text])
  │     └── ElasticsearchVectorStore.upsert(index, uid, text, embedding, metadata)
  │           → if OS down: write to data/vectorize_progress/{uid}.pending
  │
  └── [on success] OSLCAgent.trs_broadcast(uids, change_type="Creation")
        └── TRSChangelog.append_entry(resource_uri, order, timestamp)

RETURN: IngestResult {
  file: "induction_motor.xml",
  items:          42,
  revisions:      42,
  bom_lines:     156,
  datasets:       38,
  classified:     40,
  unclassified:    2,
  violations:      3,
  vectors_indexed: 42,
  trs_events:      42
}
```

---

## 9. Agentic Workflow — Semantic Query / Chat

```
User: "Find all parts related to thermal management in the induction motor BOM"
  │
  ▼
OrchestratorAgent → task_type = "semantic_search"
  │
  ▼
SemanticAgent.semantic_search(query, top_k=5, expand=True)
  │
  ├── Step 1: Embed query
  │     OllamaEmbeddings.embed(["Find all parts related to thermal management..."])
  │     → vector: float[768]
  │
  ├── Step 2: OpenSearch kNN
  │     POST /embeddings/_search { knn: { vector: { vector: [...], k: 5 } } }
  │     → hits: [{ id, score, text, metadata }]
  │
  ├── Step 3: Neo4j graph expansion (for each hit)
  │     MATCH (n {uid: $uid})-[:CLASSIFIED_AS|HAS_REVISION|REFERENCES|TRACES_TO*1..2]-(neighbor)
  │     → expanded context: {node_props, ontology_class, connected_nodes}
  │
  ├── Step 4: LLM synthesis
  │     system: "You are an MBSE assistant. Use graph context below."
  │     context: assembled from hits + expansion
  │     → insight: markdown paragraph with citations
  │
  └── RETURN: {
       hits: [...],
       insight: "The following components are classified as thermal...",
       sources: ["PLMXMLItem:uid-001", "ap242:HeatExchanger"]
     }
```

---

## 10. SmartAnalysis Workflow (per-node deep dive)

```
User selects node: PLMXMLItem uid="TC-000687-A"
  │
  ▼
OrchestratorAgent → task_type = "kg_expand"
  │
  ├── MBSEAgent.get_context(uid, hops=3)
  │     MATCH (n {uid:$uid})-[*1..3]-(neighbor)
  │     → node props + all connected nodes + rel types
  │
  ├── SemanticAgent.find_similar(uid, top_k=5)
  │     1. Fetch node's vector from OpenSearch
  │     2. kNN search using that vector
  │     → semantically closest items (score + text)
  │
  ├── SHACLAgent.get_violations(uid)
  │     MATCH (v:SHACLViolation)-[:HAS_VIOLATION]->(n {uid:$uid})
  │     → list of active violations with severity + message
  │
  ├── OntologyAgent.get_classification(uid)
  │     MATCH (n {uid:$uid})-[:CLASSIFIED_AS]->(cls)-[:SUBCLASS_OF*0..4]->(root)
  │     → classification chain up to root AP243 class
  │
  └── LLM synthesis → structured SmartAnalysis response:
      {
        summary:        "Assembly component, classified as ap242:Part, ...",
        classification: { class: "ap242:Part", chain: ["ap242:Part","ap243:Product"] },
        similar_items:  [{ name, score, type }],
        violations:     [{ shape, severity, message }],
        recommendations: ["Add missing revision", "Link to STEP dataset"]
      }

Frontend renders as tabbed panel:
  [Overview] [Ontology] [Similar] [Violations] [Graph]
```

---

## 11. AI Insights (Scheduled + On-demand)

| Insight | Trigger | Query / Method |
|---|---|---|
| **BOM Completeness** | After PLMXML ingest | Count `PLMXMLItem.unclassified = true` + missing revisions |
| **Traceability Gaps** | On demand | `MATCH (r:Requirement) WHERE NOT (r)-[:TRACES_TO]->()` |
| **Classification Coverage** | Scheduled daily | `% of PLMXMLItem nodes with [:CLASSIFIED_AS]` |
| **Semantic Duplicates** | After vectorization | kNN self-query, cosine > 0.95 between two different uid vectors |
| **SHACL Compliance Score** | After validate_batch | violations / total_nodes per label |
| **AP Standard Alignment** | On demand | CLASSIFIED_AS target ap_level distribution |

---

## 12. GraphView Queries (Registry)

File: `backend/src/web/services/graph_query_registry.py`

| View Name | Cypher Pattern | Frontend Use |
|---|---|---|
| `bom_tree` | `(:PLMXMLItem)-[:HAS_REVISION]->(:PLMXMLRevision)-[:HAS_BOM_LINE*1..5]->(b)` | BOM explorer |
| `ontology_hierarchy` | `(:ExternalOwlClass)-[:SUBCLASS_OF*1..4]->(p)` | Class hierarchy tree |
| `classification_web` | `(n)-[:CLASSIFIED_AS]->(c:ExternalOwlClass)` | What's classified where |
| `traceability_chain` | `(r:Requirement)-[:TRACES_TO|REALIZES|VERIFIED_BY*1..3]-()` | SE traceability |
| `shacl_violations` | `(:SHACLViolation)-[:HAS_VIOLATION]->(n)` | Quality dashboard |
| `semantic_neighbors` | `(n {uid:$uid})-[*1..2]-(neighbor)` | Node context panel |
| `step_geometry` | `(:StepFile)-[:LINKED_STEP_FILE]->(:StepInstance)` | Geometry browser |
| `oslc_req_links` | `(r:Requirement)-[:OSLC_LINK]->(target)` | OSLC requirement map |

---

## 13. OSLC TRS Integration

After every successful write in any ingest or mutation:

```python
OSLCTRSService.append_change_event(
    resource_uri = f"http://localhost:5000/api/oslc/rm/requirements/{uid}",
    change_type  = "Creation" | "Modification" | "Deletion",
)
```

**TRS Endpoints:**
- `GET /api/oslc/trs` — full TRS document (base + changelog)
- `GET /api/oslc/trs/base` — snapshot of all current resource URIs
- `GET /api/oslc/trs/changelog` — ordered list of change events

OSLC-compliant tools (Doors Next, Jira OSLC adapters, Polarion) can poll `GET /api/oslc/trs` to sync their resource indexes.

---

## 14. OpenSearch Infrastructure

### 14.1 Installation
- **Version:** OpenSearch 3.3.1
- **Location:** `D:\Software\opensearch-3.3.1`
- **Start script:** `scripts/start_opensearch.ps1` (interactive or `-Detach` background)
- **Port:** `9200` (HTTP), `9300` (transport)
- **Security:** disabled for local dev (`plugins.security.disabled: true` in `opensearch.yml`)

### 14.2 Index Configuration

```json
// Index: embeddings
{
  "settings": { "knn": true },
  "mappings": {
    "properties": {
      "text":     { "type": "text" },
      "vector":   {
        "type":      "knn_vector",
        "dimension": 768,
        "method": {
          "name":       "hnsw",
          "engine":     "lucene",
          "space_type": "cosinesimil"
        }
      },
      "metadata": { "type": "object", "enabled": true }
    }
  }
}
```

### 14.3 Index Management

| Operation | Endpoint | Notes |
|---|---|---|
| Create index | `PUT /embeddings` (via `ElasticsearchVectorStore.create_index`) | Auto-called on first upsert |
| Upsert doc | `PUT /embeddings/_doc/{uid}` | doc_id = Neo4j uid |
| kNN search | `POST /embeddings/_search` | HNSW approximate |
| Doc count | `GET /embeddings/_count` | Used by `/api/vector/stats` |
| Reconcile gap | `GET /api/vector/reconcile` | Neo4j indexable nodes − OpenSearch docs |
| Back-fill pending | Re-run vectorize on `data/vectorize_progress/*.pending` files | After OpenSearch recovery |

### 14.4 Health Checks
```bash
GET http://localhost:9200/          # cluster info
GET http://localhost:9200/_cat/health?v   # green/yellow/red
GET http://localhost:9200/embeddings/_count  # doc count
```

### 14.5 OpenSearch ↔ Neo4j Reconciliation Flow
```
GET /api/vector/reconcile
  1. Count Neo4j nodes with .uid property (indexable)
  2. Count OpenSearch docs in 'embeddings' index
  3. Return: { neo4j_indexable_nodes, opensearch_docs, indexable_gap }
  4. Gap > 0 → trigger back-fill via POST /api/vector/index for each pending uid
```

---

## 15. Neo4j Schema & Indexes

### 15.1 Connection
- **URI:** `neo4j://127.0.0.1:7687`
- **Database:** `mossec`
- **Driver:** `neo4j` Python driver (sync)

### 15.2 Required Constraints (idempotency keys)
```cypher
CREATE CONSTRAINT plmxml_item_uid     IF NOT EXISTS FOR (n:PLMXMLItem)     REQUIRE n.uid IS UNIQUE;
CREATE CONSTRAINT plmxml_rev_uid      IF NOT EXISTS FOR (n:PLMXMLRevision)  REQUIRE n.uid IS UNIQUE;
CREATE CONSTRAINT plmxml_bom_uid      IF NOT EXISTS FOR (n:PLMXMLBOMLine)   REQUIRE n.uid IS UNIQUE;
CREATE CONSTRAINT plmxml_ds_uid       IF NOT EXISTS FOR (n:PLMXMLDataSet)   REQUIRE n.uid IS UNIQUE;
CREATE CONSTRAINT stepfile_uid        IF NOT EXISTS FOR (n:StepFile)        REQUIRE n.uid IS UNIQUE;
CREATE CONSTRAINT owl_class_uri       IF NOT EXISTS FOR (n:ExternalOwlClass) REQUIRE n.uri IS UNIQUE;
CREATE CONSTRAINT shacl_viol_uid      IF NOT EXISTS FOR (n:SHACLViolation)   REQUIRE n.uid IS UNIQUE;
```

### 15.3 Required Indexes (query performance)
```cypher
CREATE INDEX plmxml_item_type   IF NOT EXISTS FOR (n:PLMXMLItem)      ON (n.item_type);
CREATE INDEX plmxml_item_name   IF NOT EXISTS FOR (n:PLMXMLItem)      ON (n.name);
CREATE INDEX owl_class_name     IF NOT EXISTS FOR (n:ExternalOwlClass) ON (n.name);
CREATE INDEX owl_class_aplevel  IF NOT EXISTS FOR (n:ExternalOwlClass) ON (n.ap_level);
CREATE INDEX shacl_target_uid   IF NOT EXISTS FOR (n:SHACLViolation)   ON (n.target_uid);
CREATE INDEX stepfile_name      IF NOT EXISTS FOR (n:StepFile)         ON (n.name);
```

### 15.4 Full-Text Search Indexes (fallback when OpenSearch unavailable)
```cypher
CREATE FULLTEXT INDEX plmxml_fulltext IF NOT EXISTS
  FOR (n:PLMXMLItem|PLMXMLRevision|PLMXMLDataSet)
  ON EACH [n.name, n.item_id, n.item_type];

CREATE FULLTEXT INDEX ontology_fulltext IF NOT EXISTS
  FOR (n:ExternalOwlClass|OWLProperty|Classification)
  ON EACH [n.name, n.description];
```

### 15.5 Schema Setup Script
Script: `backend/scripts/setup_neo4j_schema.py`  
Run once after Neo4j database is created:
```bash
python backend/scripts/setup_neo4j_schema.py
```

### 15.6 Node Count Baseline (current)
| Label | Count (2026-03-02) |
|---|---|
| Total nodes | ~4,199+ |
| ExternalOwlClass | TBD after ontology re-ingest |
| PLMXMLItem | 0 (ingest pending) |
| StepFile | TBD |
| SHACLViolation | 0 (validation pending) |

---

## 16. Ollama LLM Infrastructure

### 16.1 Setup
- **Server:** `http://localhost:11434`
- **Start:** `ollama serve` (runs as background service on Windows)
- **Python wrapper:** `backend/src/agents/embeddings_ollama.py` — `OllamaEmbeddings` class

### 16.2 Required Models
```bash
ollama pull nomic-embed-text    # 768-dim embeddings — REQUIRED for vector pipeline
ollama pull llama3              # chat/synthesis — used by SemanticAgent, SmartAnalysis
ollama pull mistral             # optional alternate chat model
```

### 16.3 Model Usage Map
| Model | Used by | Purpose |
|---|---|---|
| `nomic-embed-text` | `OllamaEmbeddings`, `VectorStoreTool`, `SemanticAgent` | Query + document embedding (768-dim) |
| `llama3` | `SemanticAgent.semantic_insight`, SmartAnalysis, Chat | Answer synthesis, insight generation |
| `llama3` | `OrchestratorAgent` intent router | LLM fallback for intent classification |

### 16.4 Embedding Pipeline
```
OllamaEmbeddings.embed([text])
  POST http://localhost:11434/api/embeddings
  { "model": "nomic-embed-text", "prompt": text }
  → { "embedding": float[768] }
```

### 16.5 Fallback Behavior
- If Ollama unavailable: `VectorStoreTool.index_document` logs warning, writes uid to `data/vectorize_progress/{uid}.pending`
- Chat endpoints fall back to Neo4j full-text search with no LLM synthesis
- `GET /api/vector/reconcile` shows gap so back-fill can be triggered when Ollama recovers

### 16.6 Environment Config
```
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBED_MODEL=nomic-embed-text
OLLAMA_CHAT_MODEL=llama3
```

---

## 17. Frontend Application Map

All frontend code lives in `frontend/src/`.

### 17.1 Feature Modules

```
frontend/src/
├── features/
│   ├── ai-studio/          ← ModelChat, AIInsights, SmartAnalysis, Chatbot
│   ├── graph-explorer/     ← GraphBrowser, OntologyGraph, AP239/242/243 graphs, OSLCGraph
│   ├── semantic-web/       ← OntologyManager, SHACLValidator, TRSFeed, OSLCBrowser, RDFExporter
│   ├── sdd/                ← SDD data views
│   ├── systems-engineering/← SE artifacts
│   ├── simulation/         ← Simulation data
│   ├── telemetry/          ← Telemetry views
│   └── auth/               ← Login/session
├── services/
│   ├── agents.service.ts   ← runOrchestrator() → POST /api/orchestrate
│   ├── graph.service.ts    ← graph queries → GET /api/graph/*
│   ├── ontology.service.ts ← ontology ops → GET/POST /api/ontology/*
│   ├── oslc.service.ts     ← OSLC ops → GET /api/oslc/*
│   ├── validation.service.ts← SHACL → GET /api/shacl/*  [STUB — needs wiring]
│   ├── query.service.ts    ← named queries → GET /api/graph/query/*
│   └── upload.service.ts   ← file upload → POST /api/plmxml/upload
└── apps/
    ├── engineer/           ← main engineer workspace
    ├── quality/            ← quality + SHACL dashboard
    └── admin/              ← admin panel
```

### 17.2 AI Studio Components

#### `ModelChat.jsx`
- **Purpose:** Main chat interface — sends queries to `OrchestratorAgent`
- **API:** `POST /api/orchestrate` via `agents.service.ts → runOrchestrator()`
- **Current state:** Renders response, markdown support ✅
- **Needs wiring:** `semantic_search` / `semantic_insight` task types in orchestrator response
- **Missing:** Source citation links, graph node click-through, streaming SSE support

#### `Chatbot.tsx`
- **Purpose:** Embedded floating chat widget (context-aware)
- **API:** Same as ModelChat
- **Current state:** Renders markdown ✅
- **Needs wiring:** Context injection (selected node uid → query context)

#### `AIInsights.jsx`
- **Purpose:** Scheduled + on-demand insight cards (BOM completeness, traceability gaps, etc.)
- **API:** `GET /api/insights/*` (endpoints NOT YET CREATED)
- **Current state:** UI shell exists, cards render static mock data
- **Needs wiring:** 6 backend insight endpoints (Task 11)

#### `SmartAnalysis.jsx`
- **Purpose:** Per-node deep analysis panel (5-step: context + similar + violations + ontology + LLM)
- **API:** `POST /api/smart-analysis/{uid}` (endpoint NOT YET CREATED)
- **Current state:** UI shell exists, tabs render
- **Needs wiring:** Backend `POST /api/smart-analysis/{uid}` (Task 11), node uid passed from graph click

### 17.3 Graph Explorer Components

#### `GraphBrowser.jsx`
- **Purpose:** Interactive force-directed graph of Neo4j nodes/relationships
- **API:** `GET /api/graph/*` queries via `graph.service.ts`
- **Current state:** Renders graph, hover tooltips, pointer events ✅
- **Needs wiring:** Named query registry (`GET /api/graph/query/{name}`) for BOM, ontology, traceability views
- **Missing:** Node click → SmartAnalysis panel integration; `CLASSIFIED_AS` edge rendering; SHACL violation highlight

#### `OntologyGraph.jsx`
- **Purpose:** Visualizes `ExternalOwlClass` hierarchy (`SUBCLASS_OF` tree)
- **API:** `GET /api/ontology/classes` via `ontology.service.ts`
- **Needs wiring:** Cross-ontology edges once Task 2 is done; `ap_level` color coding (AP239/242/243)

#### `AP239Graph.jsx` / `AP242Graph.jsx` / `AP243Graph.jsx`
- **Purpose:** AP-level-specific graph views (filtered by `ap_level`)
- **API:** Named query `ontology_hierarchy` with `ap_level` filter
- **Current state:** Stub components
- **Needs wiring:** Query registry integration + `CLASSIFIED_AS` instance overlay

#### `OSLCGraph.jsx`
- **Purpose:** OSLC requirement links and TRS resource graph
- **API:** `GET /api/oslc/catalog`, `GET /api/oslc/trs`
- **Needs wiring:** TRS changelog feed from Task 12

### 17.4 Semantic Web Components

#### `OntologyManager.jsx`
- **Purpose:** Browse, search, and ingest ontologies; view class hierarchies
- **API:** `GET/POST /api/ontology/*` via `ontology.service.ts`
- **Current state:** Functional for listing/searching ✅
- **Needs wiring:** CLASSIFIED_AS link count per class; cross-ontology traversal (Task 2)

#### `SHACLValidator.jsx`
- **Purpose:** Run SHACL validation, browse violations, see compliance score
- **API:** `GET /api/shacl/*` via `validation.service.ts` [STUB — backend not yet created]
- **Current state:** UI exists, calls unimplemented endpoints
- **Needs wiring:** Task 6 (SHACLValidationService + shacl_fastapi.py)

#### `TRSFeed.jsx`
- **Purpose:** Live feed of OSLC TRS change events
- **API:** `GET /api/oslc/trs/changelog` (polling or SSE)
- **Current state:** Stub
- **Needs wiring:** Task 12 (OSLCTRSService.append_change_event)

#### `OSLCBrowser.jsx`
- **Purpose:** Browse OSLC service providers, catalogs, and requirements
- **API:** `GET /api/oslc/rootservices`, `GET /api/oslc/catalog`, `GET /api/oslc/rm/requirements`
- **Current state:** Uses `oslc.service.ts` ✅

#### `RDFExporter.jsx`
- **Purpose:** Export graph subsets as RDF/Turtle, CSV, or STEP
- **API:** `POST /api/export/*` via `export.service.ts`
- **Current state:** Stub
- **Needs wiring:** ExportAgent (future Task)

---

## 18. Service Dependency Map

```
Frontend Service         Backend Route              Agent / Service
─────────────────────────────────────────────────────────────────────
agents.service.ts    →  POST /api/orchestrate    → OrchestratorAgent
graph.service.ts     →  GET  /api/graph/*        → MBSEAgent / graph_query_registry
ontology.service.ts  →  GET  /api/ontology/*     → OntologyAgent / OntologyIngestService
validation.service.ts→  GET  /api/shacl/*        → SHACLAgent / SHACLValidationService  [PENDING T6]
oslc.service.ts      →  GET  /api/oslc/*         → OSLCAgent / OSLCService
upload.service.ts    →  POST /api/plmxml/upload  → PLMAgent / PLMXMLIngestService
query.service.ts     →  GET  /api/graph/query/*  → graph_query_registry              [PENDING T9]
(no service yet)     →  GET  /api/insights/*     → insight queries                   [PENDING T11]
(no service yet)     →  POST /api/smart-analysis → SmartAnalysis pipeline            [PENDING T11]
(no service yet)     →  GET  /api/vector/*       → VectorStoreTool / OpenSearch      ← COMPLETE
```

---

## 19. Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `NEO4J_URI` | `neo4j://127.0.0.1:7687` | Neo4j connection |
| `NEO4J_DATABASE` | `mossec` | Database name |
| `VECTORSTORE_HOST` | `http://localhost:9200` | OpenSearch / Elasticsearch |
| `VECTORSTORE_INDEX` | `embeddings` | Primary vector index |
| `NEO4J_EMBEDDING_ENABLED` | `false` | Mirror embeddings to Neo4j node property |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama LLM server |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Embedding model |
| `OLLAMA_CHAT_MODEL` | `llama3` | Chat / synthesis model |
| `SHACL_STRICT_MODE` | `false` | Blocks write on CRITICAL violations if true |

---

## 15. File Map

```
SDD_MOSSEC/
├── backend/
│   ├── data/
│   │   ├── seed/
│   │   │   ├── oslc/
│   │   │   │   ├── oslc-core.ttl
│   │   │   │   ├── oslc-rm.ttl
│   │   │   │   ├── oslc-ap239.ttl         ← add SUBCLASS_OF edges (Task 2)
│   │   │   │   ├── oslc-ap242.ttl         ← add SUBCLASS_OF edges (Task 2)
│   │   │   │   └── oslc-ap243.ttl
│   │   │   └── shacl/
│   │   │       └── plmxml_shapes.ttl      ← NEW (Task 5)
│   │   └── vectorize_progress/            ← pending OpenSearch upserts
│   └── src/
│       ├── agents/
│       │   ├── orchestrator_workflow.py   ← extend routing (Task 8)
│       │   ├── plm_agent.py               ← add post-ingest hooks (Tasks 3,4,6)
│       │   ├── ontology_agent.py          ← add link_classes() method (Task 3)
│       │   ├── shacl_agent.py             ← NEW (Task 6)
│       │   ├── semantic_agent.py          ← NEW (Task 10)
│       │   ├── mbse_agent.py              ← add kg_expand (Task 9)
│       │   ├── step_agent.py              ← add post-ingest vectorize (Task 4)
│       │   ├── export_agent.py            ← NEW (future)
│       │   ├── vectorstore_es.py          ← COMPLETE
│       │   └── agent_tools.py             ← COMPLETE
│       └── web/
│           ├── services/
│           │   ├── plmxml_ingest_service.py  ← fix v6 parser (Task 1), add hooks (Tasks 3,4)
│           │   ├── ontology_ingest_service.py ← COMPLETE
│           │   ├── shacl_validation_service.py ← NEW (Task 6)
│           │   ├── graph_query_registry.py     ← NEW (Task 9)
│           │   └── oslc_trs_service.py         ← extend (Task 12)
│           └── routes/
│               ├── plmxml_ingest_fastapi.py  ← COMPLETE
│               ├── vector_fastapi.py          ← COMPLETE
│               ├── shacl_fastapi.py           ← NEW (Task 6)
│               └── oslc_fastapi.py            ← extend TRS (Task 12)
└── docs/
    ├── SEMANTIC_INTEGRATION_ARCHITECTURE.md  ← THIS FILE
    └── SEMANTIC_INTEGRATION_TRACKER.md       ← task tracker
```
