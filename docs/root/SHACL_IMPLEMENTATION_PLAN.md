# SMRL Semantic Implementation Plan (SHACL + AP Domains)

## 1. Domain-Specific Validation Strategy
Implementation of strict semantic validation for ISO 10303 domains using W3C SHACL.

### 1.1 AP239 (Product Life Cycle Support) Validation
**Focus:** Requirements, Approvals, and Documents.
- **Constraints**:
  - IDs must match regex patterns (e.g., `REQ-\d+`).
  - Creation dates are mandatory (OSLC Compliance).
  - Relationships to AP242 Parts must be explicitly typed.

### 1.2 AP242 (Managed Model-Based 3D Engineering) Validation
**Focus:** Parts, Assemblies, Geometric Models.
- **Constraints**:
  - `lifecycleState` restricted to strictly controlled vocabulary (e.g., "IN_WORK", "RELEASED").
  - Physical properties (Mass, Volume) must be non-negative.
  - Versions must be string-sortable.

## 2. Technical Component: `SHACLValidator`
A new service created at `backend/src/web/services/shacl_validator.py`.
- **Function**: Loads semantic shapes from disk (`backend/src/models/shapes/`).
- **Input**: `rdflib.Graph` (The semantic payload).
- **Output**: Boolean (Conforms) + Validation Report text.

## 3. Workflow Integration
1.  **Ingest**: Agent receives data (e.g., from Excel or PLM Tool).
2.  **Convert**: Agent converts data to ephemeral RDF Graph.
3.  **Validate**: `SHACLValidator` checks RDF against `ap239_requirement.ttl`.
4.  **Persist**: Only if valid, data is successfully written to Neo4j.

## 4. Future Extensions
- **Custom constraints**: Allow users to add project-specific SHACL rules via UI.
- **Real-time feedback**: Frontend indicates specific constraint violations (e.g., "Mass cannot be -10kg").
