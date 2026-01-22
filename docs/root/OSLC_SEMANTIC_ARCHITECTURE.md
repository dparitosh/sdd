# MBSE/MOSSEC OSLC & Semantic Web Architecture (Phase 2)

## 1. Executive Summary
This document outlines the architecture for transforming the MBSE-MOSSEC platform into a fully compliant **OSLC (Open Services for Lifecycle Collaboration)** node. This transition enables the platform to act as both a **Server** (provider of semantic data) and a **Client** (consumer of external PLM/ALM data), leveraging the existing Neo4j graph for "Smart Linking."

## 2. Core Technologies
- **RDFLib**: For parsing, serializing, and querying RDF (Turtle, JSON-LD, RDF/XML).
- **PyOSLC** (or Custom FastAPI Implementation): For handling OSLC REST protocols, headers, and shape validation.
- **Neo4j Neosemantics (n10s)**: (Optional) For native graph-RDF mapping, though we will primarily handle this at the application layer for flexibility.

## 3. Architecture Components

### 3.1 OSLC Server (Provider)
The server exposes internal Neo4j entities (Requirements, Parts, Analyses) as standard OSLC Resources.

#### 3.1.1 Domain Mapping
| Neo4j Entity | OSLC Domain | Resource Type | URI Pattern |
|:---|:---|:---|:---|
| `Requirement` (AP239) | OSLC RM | `oslc_rm:Requirement` | `/oslc/rm/requirements/{id}` |
| `Part` (AP242) | OSLC AM | `oslc_am:Resource` | `/oslc/am/parts/{id}` |
| `Analysis` | OSLC QM | `oslc_qm:TestResult` | `/oslc/qm/analyses/{id}` |
| `Approval` | OSLC CM | `oslc_cm:ChangeRequest` | `/oslc/cm/approvals/{id}` |

#### 3.1.2 Endpoints Structure
- **Root Services** (`/oslc/rootservices`): Entry point discovery.
- **Service Provider Catalog** (`/oslc/catalog`): Grouping of services.
- **Service Provider** (`/oslc/sp/{projectId}`): Project-specific services.
- **Services**:
  - **Selection Dialog**: UI for external tools to pick resources.
  - **Creation Dialog**: UI for external tools to create resources.
  - **Query Capability**: OSLC Simple Query Syntax support.

#### 3.1.3 Serialization
All endpoints must support content negotiation:
- `application/ld+json` (JSON-LD) - **Primary**
- `application/rdf+xml`
- `text/turtle`

### 3.2 OSLC Client (Consumer)
The client enables the platform to fetch and link against remote repositories (e.g., DOORS Next, Windchill, Teamcenter).

#### 3.2.1 Capabilities
- **Discovery**: Parsing remote `rootservices` and Catalog.
- **OAuth 1.0a / 2.0**: Handling the complex auth flows of legacy PLM tools.
- **Delegated UI**: Rendering remote Selection Dialogs within the React frontend (via `iframe`).

### 3.3 Semantic Data Processing & Ontology
To support AP243 (Ontologies), we will verify data against SHACL shapes before ingestion.

- **Ontology Store**: Load standard ontologies (Dublin Core, FOAF, OSLC Core) into memory specifically for validation.
- **Inference**: Use RDFS semantic reasoning to infer relationships (e.g., if `Engine` is a subclass of `Part`, it inherits `Part` properties).

### 3.4 Smart Link Data Services
Refactoring the `link_ap_hierarchy.py` script into a continuous background service (using OSLC TRS).

- **TRS (Tracked Resource Set) Provider**:
  - **Base**: Initial dump of all resources.
  - **ChangeLog**: Stream of `Create`, `Update`, `Delete` events.
- **Link Indexer**:
  - Listens to internal Neo4j changes.
  - Listens to external TRS feeds.
  - "Smart Links" created automatically based on semantic rules (e.g., exact name match, property correlation).

## 4. Implementation Plan

### Phase 2.1: Foundation
1. Install `rdflib`, `pydantic-xml`, `isodate`.
2. Define Pydantic models for OSLC Core Resources (`Link`, `Property`).
3. Implement `JSON-LD` context generator for Neo4j nodes.

### Phase 2.2: Server Implementation
1. Create `OSLCService` class to handle content negotiation.
2. Implement `RootServices` and `ServiceProviderCatalog`.
3. Expose `Requirement` API with RDF serialization.

### Phase 2.3: Smart Linking
1. Refactor `APHierarchyLinker` to use RDF graphs instead of raw dictionaries.
2. Implement simple TRS ChangeLog endpoint.
