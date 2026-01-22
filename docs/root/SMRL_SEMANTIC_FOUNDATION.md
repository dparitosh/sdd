# SMRL Semantic Foundation & Ontology Architecture

## 1. The Missing Semantic Layer
Previous architecture analysis focused on **OSLC Protocols** (Transport) and **MoSSEC Agents** (Process). This document addresses the **Semantic Payload** (Meaning).

To be a true MoSSEC/SMRL implementation, the system must not just "transport" data but "understand" it using the ISO 10303-4443 (SMRL) Ontology.

## 2. SMRL Ontology Components

### 2.1 The Ontology (TBox)
The `smrlv12` folder contains the EXPRESS schemas that define the SMRL universe. We must formalize this into an **RDFS/OWL Ontology** hosted by the platform.

*   **Core Model**: Defines identifying basics (`Identification`, `Name`, `Description`).
*   **Domain Models**: Defines the specific MBSE concepts (`Requirement`, `Activity`, `Interface`).
*   **Modules**: The modular building blocks (`Person`, `Organization`, `Date`).

**Implementation Strategy:**
*   **Ingestion**: Phase 2 must include a pipeline to parse the `smrlv12` resources (likely EXPRESS or XSD) and convert them to **OWL 2 RL** (Web Ontology Language).
*   **Hosting**: The platform must serve this ontology at a stable URI (e.g., `https://mbse-mossec.com/ontologies/smrl#`).

### 2.2 Data Dictionary & Vocabulary (SKOS)
ISO 10303 is heavy on "Classification" pattern (Reference Data). We will use **SKOS (Simple Knowledge Organization System)** to manage this.

*   **Thesaurus**: Handling synonyms (e.g., "FEM" vs "FEA" vs "Finite Element Analysis").
*   **Classification**: The `classification_schema` in SMRL maps directly to SKOS Concept Schemes.
    *   `skos:ConceptScheme`: E.g., "Analysis Types".
    *   `skos:Concept`: E.g., "Thermal Analysis", "Structural Analysis".
    *   `skos:broader/narrower`: Handling the hierarchy.

### 2.3 Semantic Validation (Data Dictionary Enforcement)
We cannot rely on loose "Strings" for types.
*   **Bad:** `Analysis.type = "Structural"` (String)
*   **Good:** `Analysis.type = <http://smrl.org/refdata#StructuralAnalysis>` (URI)

We will use **SHACL (Shapes Constraint Language)** to enforce that data ingested by Agents conforms to the Data Dictionary.

## 3. Revised Architecture Stack

| Layer | Technology | SMRL Component |
|:---|:---|:---|
| **Knowledge Graph** | Neo4j + Neosemantics (n10s) | The ABox (Instance Data) |
| **Ontology Layer** | **OWL 2 / RDFS** | The TBox (Classes/Properties from `smrlv12`) |
| **Reference Data** | **SKOS** | The Data Dictionary/Thesaurus |
| **Validation** | **SHACL** | The Rules (Constraints) |
| **Transport** | **OSLC** | The Protocol |

## 4. Specific Action Items for Phase 2

1.  **SMRL Ingester**: Create `scripts/ingest_smrl_ontology.py` to walk the `smrlv12` directory and build the OWL graph.
2.  **SKOS Service**: Add endpoints to query the vocabulary (`/api/vocab/search?q=thermal`).
3.  **Agent Vocabulary Awareness**: Update Agents to query the SKOS service to "Resolve" terms before writing to the graph (e.g., Agent searches for "Heat Sim", finds "Thermal Analysis" Concept).

## 5. Deployment of Reference Data
The `smrlv12` folder contains thousands of critical definitions (e.g., `measure_schema` for Units). These must be pre-loaded into the Graph as `ReferenceData` nodes, distinct from the user's operational data.
