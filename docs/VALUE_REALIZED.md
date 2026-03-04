# Functional Value Realized — MoSSEC MBSE Knowledge Graph Platform

> **MoSSEC** (Model-based Open Systems Engineering Collaboration) is a unified MBSE platform that ingests, connects, and queries multi-standard engineering data across the full product lifecycle — from requirements to simulation evidence — through an AI-enabled knowledge graph.

---

## 1. Ontology Management

**Why is this needed when COTS PLM tools already have data models?**
COTS PLM tools (Teamcenter, Windchill, ENOVIA) each have proprietary, closed data models. When a program uses three tools — one for requirements, one for CAD/BOM, one for simulation — there is no shared semantic layer: "Part" in Teamcenter and "Product" in an AP242 STEP file and "Component" in a SysML model are all the same engineering concept, but no COTS tool recognises them as equivalent. Engineers spend significant effort manually reconciling these differences in spreadsheets.

**What MoSSEC does differently:** The ontology (85+ OWL/SHACL-validated labels) acts as a universal schema that classifies every ingested artifact — from any tool or standard — into a common vocabulary. This enables cross-standard graph queries (AP239 ↔ AP242 ↔ AP243) without schema conflicts, and allows SHACL validation to flag data quality violations at ingestion time rather than during design reviews. The ontology is the enabler for every other capability on this platform — without it, the knowledge graph is just a collection of disconnected nodes.

---

## 2. OSLC (Open Services for Lifecycle Collaboration)

**Why is this needed when PLM tools already have APIs?**
Every major PLM vendor provides a proprietary REST API — but they are incompatible with each other. Integrating DOORS (requirements) with Teamcenter (BOM) with a custom simulation database requires bespoke point-to-point connectors. A 5-tool program needs up to 10 connectors; each costs months to build and breaks on every tool upgrade. This is the single most cited integration problem in complex systems engineering programs.

**What MoSSEC does differently:** OSLC is the ISO/OASIS-standardised protocol for lifecycle tool federation. By exposing full OSLC TRS (Tracked Resource Set) and OSLC client/server endpoints at `/oslc/`, MoSSEC acts as the neutral broker — any OSLC-compliant tool can push or pull lifecycle resources without a custom connector. Requirements from DOORS, CAD from Teamcenter, and simulation results from AP243 tools are all linked through a single standards-based interface, reducing integration effort from months to days and eliminating the upgrade-breakage cycle entirely.

---

## 3. STEP AP239 — Product Life Cycle Support Data

**Why is this needed when maintenance plans already exist in ERP/MRO systems?**
MRO (Maintenance, Repair & Overhaul) systems like SAP PM or IBM Maximo store maintenance plans operationally — but they are disconnected from the design data that caused the maintenance requirement. If a part is redesigned, the maintenance plan is not automatically updated because there is no traceable link between the design model and the support concept. This disconnect is a well-known source of in-service safety risk.

**What MoSSEC does differently:** AP239 (PLCS — Product Life Cycle Support) is the STEP standard that formally encodes the connection between design artifacts and support data. By ingesting AP239 nodes and linking them to the same `:AP242Product` parts in the knowledge graph, MoSSEC makes the design-to-maintenance traceability traversable in a single query. A lifecycle engineer can ask: *"which maintenance tasks are affected by this design change?"* and get an immediate answer — without switching tools or waiting for a manual impact assessment.

---

## 4. STEP AP242 — Managed Model Based 3D Engineering (BOM & Product Structure)

**Why is this needed when CAD tools already show the BOM?**
CAD tools (CATIA, NX, Creo) display the BOM — but only to licensed CAD users, only while the tool is open, and only in the context of the CAD session. A systems engineer, a requirements analyst, or a simulation engineer cannot query the BOM without a CAD seat. Exporting to Excel creates a static snapshot that is immediately out of date. There is no way to query the BOM alongside requirements or simulation data in a CAD tool.

**What MoSSEC does differently:** The platform parses the ISO 10303 AP242 STEP file directly — extracting `:AP242Product` nodes and `:AP242AssemblyOccurrence` nodes from NEXT_ASSEMBLY_USAGE_OCCURRENCE (NAUO) entities — and loads them into the knowledge graph as permanent, queryable nodes. Any engineer, in any role, can retrieve the full BOM (e.g. Induction Motor Assembly — 24 parts) as a formatted table in a browser in under 2 seconds, without a CAD licence, without opening the STEP file, and with the BOM joined to requirements and simulation evidence in the same query.

---

## 5. STEP AP243 — System Modelling and Simulation

**Why is this needed when simulation tools already manage their own results?**
Simulation tools (Ansys, Nastran, AMESim) store their own results in proprietary formats. When a V&V review asks *"which simulation dossiers have complete evidence for requirement REQ-045?"*, the answer requires manually opening each simulation tool, cross-referencing the results against the requirements database, and building a compliance table — typically a multi-day effort repeated for every milestone review.

**What MoSSEC does differently:** AP243 (System Modelling and Simulation integration) is the STEP standard that formalises the relationship between simulation models, runs, artifacts, and the evidence they produce. By ingesting AP243 data as `:SimulationDossier`, `:SimulationRun`, `:SimulationArtifact`, and `:EvidenceCategory` nodes, MoSSEC makes these relationships traversable in graph queries. A single AI panel prompt — *"list all simulation dossiers with their evidence category UIDs"* — returns the full joined table in seconds, replacing the multi-day manual compliance review.

---

## 6. Simulation Dossier Compliance

**Why is this needed when programmes already have V&V matrices in Excel?**
V&V matrices in Excel (or DOORS/Polarion modules) are manually maintained, statically updated, and disconnected from the actual simulation tool outputs. They answer the question "what should be verified?" but not "what has actually been verified, with what artifact, from which simulation run?" The gap between the two is where compliance failures hide — and where auditors spend the most time during milestone reviews.

**What MoSSEC does differently:** By traversing the live graph — `SimulationDossier → SimulationRun → SimulationArtifact → EvidenceCategory` — MoSSEC computes compliance status dynamically at query time, not from a manually updated matrix. Dossiers with missing evidence chains are flagged immediately. The result is a real-time compliance view that reflects the actual state of the simulation data, reducing audit preparation from days to minutes and eliminating the risk of the V&V matrix being out of sync with the simulation outputs.

---

## 7. AI Panel Chat (GraphBrowser)

**Why is this needed when engineers can already run database queries?**
Neo4j Cypher is a powerful query language — but it requires database expertise, knowledge of the schema, and time to construct multi-hop queries. Less than 5% of systems engineers on a programme have this skill. The remaining 95% — requirements analysts, systems architects, test engineers — cannot access the knowledge graph directly and depend on database specialists to answer their questions, creating a bottleneck that slows every design review and compliance check.

**What MoSSEC does differently:** The AI panel at `/engineer/graph` detects MBSE intent from plain-language prompts and routes them to pre-built, validated Cypher queries that execute directly against Neo4j — bypassing OpenSearch and LLM inference entirely for structured queries. Responses are streamed as formatted markdown in under 2 seconds. Any engineer, without database training, can now directly query 483,000+ knowledge graph nodes in their natural working vocabulary — turning the knowledge graph from a specialist tool into a daily-use engineering assistant.

---

## 8. AI Insights — Smart Analysis (`/engineer/ai/analysis`)

**Why is this needed when engineers already know their design?**
Engineers know their own subsystem well — but complex systems engineering programs span hundreds of requirements, thousands of parts, and dozens of simulation dossiers across multiple organisations. No individual engineer has visibility of the full cross-domain picture. Hidden dependencies (a requirement linked to a part with no simulation dossier), coverage gaps (an evidence category with no associated artifacts), and anomalies (a simulation run with no linked requirement) are invisible in document-centric workflows and only surface during late-stage reviews when they are expensive to fix.

**What MoSSEC does differently:** The Smart Analysis page provides per-node AI-powered graph analysis: select any node and `POST /api/insights/smart-analysis/{uid}` returns contextual insights — related nodes, coverage gaps, anomaly flags, and suggested next actions — derived from live graph traversal. This turns the knowledge graph from a passive data store into an active engineering advisor that surfaces cross-domain gaps early, when they are cheap to address, rather than at milestone reviews when they cause schedule impact.

---

## 9. Digital Thread — MoSSEC End-to-End Traceability

**Why is this needed when traceability already exists in requirements tools?**
Requirements tools (DOORS, Polarion) provide forward and backward traceability within the requirements domain — but they cannot trace beyond their own data boundary. They cannot answer: *"Is this requirement covered by a simulation run? Does that run have a completed evidence artifact? Is the artifact linked to a dossier that is approved?"* Answering that question today means exporting from three to five different tools, joining the data in Excel, and repeating for every requirement. On a large programme this is a full-time role.

**What MoSSEC does differently:** The MoSSEC digital thread connects the full engineering lifecycle as a single traversable graph chain: **Requirement → Part/Design Element → Simulation Dossier → Simulation Run → Simulation Artifact → Evidence Category**. A single AI panel prompt — *"trace the full digital thread from requirements to evidence"* — returns up to 30 multi-hop chains directly from Neo4j, each showing requirement ID, design element, dossier UID, run UID, and evidence name, with verified/unverified status computed at query time. This replaces days of manual cross-tool data joining with a sub-2-second graph traversal — and it reflects the live state of all connected data, not a static export.

---

## Summary — Productivity & Complexity Impact

| Capability | Why COTS Tools Fall Short | MoSSEC Advantage | Time Impact |
|------------|--------------------------|-----------------|-------------|
| Ontology | Proprietary, incompatible data models per tool | Universal semantic layer across all standards | Months of integration → built-in |
| OSLC | 10+ bespoke point-to-point connectors needed | Single standards-based federation hub | Connector build: months → days |
| AP239 | Design-to-maintenance link not visible in ERP | PLCS data joined to BOM in one graph query | Impact assessment: days → seconds |
| AP242 BOM | CAD licence required; static Excel exports | Live BOM queryable by any role in browser | BOM access: licence-gated → open |
| AP243 Simulation | Results siloed per simulation tool | Dossier/evidence joined in single Cypher query | Compliance table: days → seconds |
| Dossier Compliance | V&V matrix manually maintained | Real-time compliance from live graph traversal | Audit prep: days → minutes |
| AI Panel Chat | Cypher expertise required | Plain-language → validated Cypher, <2s response | Query access: 5% → 100% of team |
| Smart Analysis | Cross-domain gaps invisible until reviews | Per-node AI gap detection at any time | Gap discovery: late → early |
| Digital Thread | 3–5 tool exports + manual Excel joining | Single traversal: Req → Evidence in one query | Cross-domain trace: days → <2s |
