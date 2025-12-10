# Implementation Plan: AP239/AP242/AP243 Hierarchical Integration

## Executive Summary

To enable the 3-level hierarchical schema architecture (AP239 → AP242 → AP243), we need changes across **frontend**, **backend**, and **Neo4j database**. This document outlines specific code changes required.

---

## 🎯 Current State vs. Target State

### **Current State** (Baseline)
```
Database (Neo4j):
├─ 7 node types (Class, Package, Property, Port, Association, Constraint, Comment)
├─ 2,158 nodes total
└─ UML/SysML structural model only

Backend (Flask):
├─ /api/packages, /api/classes, /api/properties
├─ /api/v1/{ResourceType} (SMRL v1)
└─ Basic CRUD operations

Frontend (React):
├─ Package browser, Class viewer
├─ Property inspector, Port connections
└─ No requirements, approvals, or CAD integration
```

### **Target State** (AP239/AP242/AP243)
```
Database (Neo4j):
├─ LEVEL 1: AP239 nodes (Requirement, Analysis, Approval, Document, Activity)
├─ LEVEL 2: AP242 nodes (Part, PartVersion, Assembly, Material, GeometricModel)
├─ LEVEL 3: AP243 nodes (ExternalOwlClass, ExternalUnit, ValueType)
└─ Cross-level relationships (SATISFIES, ANALYZES, USES_MATERIAL, etc.)

Backend (Flask):
├─ /api/v1/requirements, /api/v1/parts, /api/v1/materials
├─ /api/v1/approvals, /api/v1/analysis
└─ /api/v1/hierarchy (AP239 → AP242 → AP243 navigation)

Frontend (React):
├─ Requirements Dashboard
├─ CAD/BOM Explorer (AP242)
├─ Traceability Matrix (Requirement → Part)
└─ Approval Workflows
```

---

## 📋 Changes Required by Component

## 1️⃣ **NEO4J DATABASE CHANGES**

### **A. Extend Parser to Support AP239 Node Types**

**File**: `src/parsers/semantic_loader.py`

**Changes**:
```python
# ADD AP239 node types to NODE_TYPES set (around line 30)

NODE_TYPES = {
    # Existing types
    "uml:Model",
    "uml:Package",
    "uml:Class",
    # ... existing types ...
    
    # ===== ADD AP239 TYPES =====
    # Requirements Management
    "ap239:Requirement",
    "ap239:RequirementVersion",
    "ap239:RequirementSource",
    "ap239:RequirementRelationship",
    
    # Analysis & Simulation
    "ap239:Analysis",
    "ap239:AnalysisModel",
    "ap239:AnalysisVersion",
    "ap239:AnalysisRepresentationContext",
    
    # Approvals & Workflow
    "ap239:Approval",
    "ap239:ApprovalAssignment",
    "ap239:ApprovalRelationship",
    "ap239:Certification",
    "ap239:CertificationAssignment",
    
    # Documents & Evidence
    "ap239:Document",
    "ap239:DocumentDefinition",
    "ap239:DocumentVersion",
    "ap239:Evidence",
    
    # Lifecycle & Configuration
    "ap239:Activity",
    "ap239:ActivityMethod",
    "ap239:Effectivity",
    "ap239:DatedEffectivity",
    "ap239:BreakdownElement",
    "ap239:BreakdownVersion",
    
    # Events & Conditions
    "ap239:Event",
    "ap239:Condition",
    "ap239:ConditionEvaluation",
}

# ADD AP239 relationships (around line 75)

RELATIONSHIP_TYPES = {
    # ... existing types ...
    
    # ===== ADD AP239 RELATIONSHIPS =====
    "ap239:SATISFIES",          # Requirement → Design
    "ap239:VERIFIES",           # Test → Requirement
    "ap239:REFINES",            # Requirement → Sub-requirement
    "ap239:APPROVES",           # Approval → Artifact
    "ap239:ANALYZES",           # Analysis → Model
    "ap239:REQUIRES",           # Requirement → Requirement
    "ap239:DOCUMENTS",          # Document → Artifact
    "ap239:TRACES_TO",          # Traceability link
    "ap239:DECOMPOSES_INTO",    # Breakdown hierarchy
    "ap239:APPLIES_TO",         # Effectivity → Configuration
}
```

### **B. Add AP242 Node Types (CAD/Manufacturing)**

```python
NODE_TYPES = {
    # ... existing + AP239 types ...
    
    # ===== ADD AP242 TYPES =====
    # Product Structure
    "ap242:Part",
    "ap242:PartVersion",
    "ap242:PartView",
    "ap242:Assembly",
    "ap242:AssemblyRelationship",
    
    # Geometry & CAD
    "ap242:GeometricModel",
    "ap242:ShapeRepresentation",
    "ap242:GeometricRepresentationContext",
    "ap242:ComponentPlacement",
    
    # Materials & Properties
    "ap242:Material",
    "ap242:MaterialProperty",
    "ap242:PropertyValueRepresentation",
    
    # Manufacturing
    "ap242:MakeFrom",
    "ap242:PhysicalBreakdownElementViewAssociation",
}

RELATIONSHIP_TYPES = {
    # ... existing + AP239 types ...
    
    # ===== ADD AP242 RELATIONSHIPS =====
    "ap242:HAS_GEOMETRY",       # Part → GeometricModel
    "ap242:USES_MATERIAL",      # Part → Material
    "ap242:ASSEMBLES_WITH",     # Part → Part
    "ap242:PLACED_IN",          # Component → Assembly
    "ap242:HAS_REPRESENTATION", # Part → ShapeRepresentation
    "ap242:MAKES_FROM",         # Manufacturing → Part
}
```

### **C. Add AP243 Reference Data Types**

```python
NODE_TYPES = {
    # ... existing + AP239 + AP242 types ...
    
    # ===== ADD AP243 TYPES =====
    # Reference Ontologies
    "ap243:ExternalOwlClass",
    "ap243:ExternalOwlObject",
    "ap243:ExternalClassSystem",
    
    # Units & Measures
    "ap243:ExternalUnit",
    "ap243:ExternalTypeQualifier",
    
    # Value Types & Classifications
    "ap243:ValueType",
    "ap243:ExternalPropertyDefinition",
}

RELATIONSHIP_TYPES = {
    # ... existing + AP239 + AP242 types ...
    
    # ===== ADD AP243 RELATIONSHIPS =====
    "ap243:CLASSIFIED_AS",      # Any node → ExternalOwlClass
    "ap243:HAS_UNIT",           # Property → ExternalUnit
    "ap243:HAS_VALUE_TYPE",     # Property → ValueType
}
```

### **D. Add Cross-Level Relationships (Hierarchical Links)**

```python
RELATIONSHIP_TYPES = {
    # ... all existing types ...
    
    # ===== CROSS-LEVEL HIERARCHICAL RELATIONSHIPS =====
    # AP239 → AP242 (Top → Middle)
    "SATISFIED_BY_PART",        # AP239 Requirement → AP242 Part
    "ANALYZED_BY_MODEL",        # AP239 Analysis → AP242 GeometricModel
    "APPROVED_FOR_VERSION",     # AP239 Approval → AP242 PartVersion
    "DOCUMENTED_BY",            # AP239 Document → AP242 Part
    
    # AP242 → AP243 (Middle → Bottom)
    "MATERIAL_CLASSIFIED_AS",   # AP242 Material → AP243 ExternalOwlClass
    "USES_UNIT",                # AP242 Property → AP243 ExternalUnit
    "HAS_REFERENCE_TYPE",       # AP242 Any → AP243 ValueType
    
    # AP239 → AP243 (Top → Bottom, direct reference)
    "REQUIREMENT_VALUE_TYPE",   # AP239 Requirement → AP243 ValueType
    "ANALYSIS_USES_UNIT",       # AP239 Analysis → AP243 ExternalUnit
}
```

### **E. Create Cypher Migration Script**

**File**: `scripts/migrate_to_ap_hierarchy.cypher` (NEW)

```cypher
// ============================================================================
// Neo4j Migration: Add AP239/AP242/AP243 Hierarchical Structure
// ============================================================================

// 1. Add indexes for AP239 nodes
CREATE INDEX ap239_requirement_uid IF NOT EXISTS FOR (n:Requirement) ON (n.uid);
CREATE INDEX ap239_analysis_uid IF NOT EXISTS FOR (n:Analysis) ON (n.uid);
CREATE INDEX ap239_approval_uid IF NOT EXISTS FOR (n:Approval) ON (n.uid);
CREATE INDEX ap239_document_uid IF NOT EXISTS FOR (n:Document) ON (n.uid);

// 2. Add indexes for AP242 nodes
CREATE INDEX ap242_part_uid IF NOT EXISTS FOR (n:Part) ON (n.uid);
CREATE INDEX ap242_partversion_uid IF NOT EXISTS FOR (n:PartVersion) ON (n.uid);
CREATE INDEX ap242_material_uid IF NOT EXISTS FOR (n:Material) ON (n.uid);
CREATE INDEX ap242_geometricmodel_uid IF NOT EXISTS FOR (n:GeometricModel) ON (n.uid);

// 3. Add indexes for AP243 nodes
CREATE INDEX ap243_externalowl_uri IF NOT EXISTS FOR (n:ExternalOwlClass) ON (n.uri);
CREATE INDEX ap243_externalunit_symbol IF NOT EXISTS FOR (n:ExternalUnit) ON (n.symbol);

// 4. Add hierarchical metadata to existing nodes
MATCH (n)
WHERE n.uid IS NOT NULL
SET n.ap_level = CASE 
    WHEN labels(n)[0] IN ['Requirement', 'Analysis', 'Approval', 'Document', 'Activity'] THEN 'AP239'
    WHEN labels(n)[0] IN ['Part', 'PartVersion', 'Material', 'GeometricModel', 'Assembly'] THEN 'AP242'
    WHEN labels(n)[0] IN ['ExternalOwlClass', 'ExternalUnit', 'ValueType'] THEN 'AP243'
    ELSE 'Legacy'
END;

// 5. Sample data: Create AP239 requirement nodes
CREATE (:Requirement {
    uid: 'REQ-001',
    name: 'System Performance Requirement',
    text: 'System shall achieve 99.9% uptime',
    priority: 'Critical',
    status: 'Approved',
    ap_level: 'AP239',
    created_on: datetime(),
    href: 'http://standards.iso.org/iso/10303/-239/Requirement/REQ-001'
});

// 6. Sample data: Create AP242 part nodes
CREATE (:Part {
    uid: 'PART-001',
    name: 'Main Assembly',
    part_number: 'PN-12345',
    description: 'Primary structural assembly',
    ap_level: 'AP242',
    created_on: datetime(),
    href: 'http://standards.iso.org/iso/10303/-242/Part/PART-001'
});

// 7. Sample data: Create AP243 reference nodes
CREATE (:ExternalOwlClass {
    uri: 'http://standards.iso.org/iso/10303/-243/tech/refdata/ap243_v1#Material_Aluminum_7075',
    label: 'Aluminum 7075-T6',
    definition: 'High-strength aluminum alloy',
    ap_level: 'AP243'
});

// 8. Create hierarchical relationships
MATCH (req:Requirement {uid: 'REQ-001'})
MATCH (part:Part {uid: 'PART-001'})
CREATE (req)-[:SATISFIED_BY_PART {
    traced_on: datetime(),
    confidence: 1.0
}]->(part);

// 9. Verify hierarchy
MATCH (ap239)-[r]->(ap242)
WHERE ap239.ap_level = 'AP239' AND ap242.ap_level = 'AP242'
RETURN count(r) as ap239_to_ap242_links;

MATCH (ap242)-[r]->(ap243)
WHERE ap242.ap_level = 'AP242' AND ap243.ap_level = 'AP243'
RETURN count(r) as ap242_to_ap243_links;
```

---

## 2️⃣ **BACKEND (FLASK) CHANGES**

### **A. Create AP239 Route Handler**

**File**: `src/web/routes/ap239.py` (NEW)

```python
"""
AP239 Product Life Cycle Support API Routes
Handles requirements, analysis, approvals, and documents
"""

from flask import Blueprint, jsonify, request
from src.web.services import get_neo4j_service

ap239_bp = Blueprint("ap239", __name__, url_prefix="/api/v1/ap239")


@ap239_bp.route("/requirements", methods=["GET"])
def get_requirements():
    """Get all requirements (AP239 Level 1)"""
    neo4j = get_neo4j_service()
    
    query = """
    MATCH (req:Requirement)
    OPTIONAL MATCH (req)-[:SATISFIED_BY_PART]->(part:Part)
    RETURN req.uid AS uid,
           req.name AS name,
           req.text AS text,
           req.priority AS priority,
           req.status AS status,
           req.ap_level AS ap_level,
           collect(part.name) AS satisfied_by_parts
    ORDER BY req.priority DESC, req.name
    """
    
    result = neo4j.execute_query(query)
    return jsonify([dict(r) for r in result])


@ap239_bp.route("/requirements/<uid>", methods=["GET"])
def get_requirement(uid):
    """Get specific requirement with traceability"""
    neo4j = get_neo4j_service()
    
    query = """
    MATCH (req:Requirement {uid: $uid})
    OPTIONAL MATCH (req)-[:SATISFIED_BY_PART]->(part:Part)
    OPTIONAL MATCH (req)-[:VERIFIES]->(test:Analysis)
    OPTIONAL MATCH (req)-[:APPROVED]->(approval:Approval)
    RETURN req,
           collect(DISTINCT part) AS satisfying_parts,
           collect(DISTINCT test) AS verifying_tests,
           collect(DISTINCT approval) AS approvals
    """
    
    result = neo4j.execute_query(query, {"uid": uid})
    if not result:
        return jsonify({"error": "Requirement not found"}), 404
    
    return jsonify({
        "requirement": dict(result[0]["req"]),
        "satisfying_parts": [dict(p) for p in result[0]["satisfying_parts"]],
        "verifying_tests": [dict(t) for t in result[0]["verifying_tests"]],
        "approvals": [dict(a) for a in result[0]["approvals"]]
    })


@ap239_bp.route("/analysis", methods=["GET"])
def get_analyses():
    """Get all analysis records"""
    neo4j = get_neo4j_service()
    
    query = """
    MATCH (analysis:Analysis)
    OPTIONAL MATCH (analysis)-[:ANALYZES]->(model:GeometricModel)
    RETURN analysis.uid AS uid,
           analysis.name AS name,
           analysis.type AS type,
           analysis.results AS results,
           analysis.timestamp AS timestamp,
           collect(model.name) AS analyzed_models
    ORDER BY analysis.timestamp DESC
    """
    
    result = neo4j.execute_query(query)
    return jsonify([dict(r) for r in result])


@ap239_bp.route("/approvals", methods=["GET"])
def get_approvals():
    """Get all approvals"""
    neo4j = get_neo4j_service()
    
    query = """
    MATCH (approval:Approval)
    OPTIONAL MATCH (approval)-[:APPROVES]->(artifact)
    RETURN approval.uid AS uid,
           approval.status AS status,
           approval.approver AS approver,
           approval.date AS date,
           collect({
               type: labels(artifact)[0],
               name: artifact.name,
               uid: artifact.uid
           }) AS approved_artifacts
    ORDER BY approval.date DESC
    """
    
    result = neo4j.execute_query(query)
    return jsonify([dict(r) for r in result])


@ap239_bp.route("/documents", methods=["GET"])
def get_documents():
    """Get all documents"""
    neo4j = get_neo4j_service()
    
    query = """
    MATCH (doc:Document)
    OPTIONAL MATCH (doc)-[:DESCRIBES]->(part:Part)
    RETURN doc.uid AS uid,
           doc.name AS name,
           doc.type AS type,
           doc.version AS version,
           doc.file_uri AS file_uri,
           collect(part.name) AS describes_parts
    ORDER BY doc.name
    """
    
    result = neo4j.execute_query(query)
    return jsonify([dict(r) for r in result])
```

### **B. Create AP242 Route Handler**

**File**: `src/web/routes/ap242.py` (NEW)

```python
"""
AP242 Managed Model-Based 3D Engineering API Routes
Handles parts, assemblies, geometry, and materials
"""

from flask import Blueprint, jsonify, request
from src.web.services import get_neo4j_service

ap242_bp = Blueprint("ap242", __name__, url_prefix="/api/v1/ap242")


@ap242_bp.route("/parts", methods=["GET"])
def get_parts():
    """Get all parts (AP242 Level 2)"""
    neo4j = get_neo4j_service()
    
    query = """
    MATCH (part:Part)
    OPTIONAL MATCH (part)<-[:SATISFIED_BY_PART]-(req:Requirement)
    OPTIONAL MATCH (part)-[:HAS_GEOMETRY]->(geom:GeometricModel)
    OPTIONAL MATCH (part)-[:USES_MATERIAL]->(mat:Material)
    RETURN part.uid AS uid,
           part.name AS name,
           part.part_number AS part_number,
           part.description AS description,
           part.ap_level AS ap_level,
           collect(DISTINCT req.name) AS satisfies_requirements,
           collect(DISTINCT geom.file_uri) AS geometry_files,
           collect(DISTINCT mat.name) AS materials
    ORDER BY part.part_number
    """
    
    result = neo4j.execute_query(query)
    return jsonify([dict(r) for r in result])


@ap242_bp.route("/parts/<uid>", methods=["GET"])
def get_part(uid):
    """Get specific part with full hierarchy"""
    neo4j = get_neo4j_service()
    
    query = """
    MATCH (part:Part {uid: $uid})
    OPTIONAL MATCH (part)<-[:SATISFIED_BY_PART]-(req:Requirement)
    OPTIONAL MATCH (part)-[:HAS_GEOMETRY]->(geom:GeometricModel)
    OPTIONAL MATCH (part)-[:USES_MATERIAL]->(mat:Material)
    OPTIONAL MATCH (mat)-[:CLASSIFIED_AS]->(ref:ExternalOwlClass)
    OPTIONAL MATCH (part)-[:ASSEMBLES_WITH]->(other:Part)
    RETURN part,
           collect(DISTINCT req) AS requirements,
           collect(DISTINCT geom) AS geometry,
           collect(DISTINCT {material: mat, reference: ref}) AS materials,
           collect(DISTINCT other) AS assembly_parts
    """
    
    result = neo4j.execute_query(query, {"uid": uid})
    if not result:
        return jsonify({"error": "Part not found"}), 404
    
    r = result[0]
    return jsonify({
        "part": dict(r["part"]),
        "requirements": [dict(req) for req in r["requirements"]],
        "geometry": [dict(g) for g in r["geometry"]],
        "materials": r["materials"],
        "assembly_parts": [dict(p) for p in r["assembly_parts"]]
    })


@ap242_bp.route("/bom/<part_uid>", methods=["GET"])
def get_bom(part_uid):
    """Get Bill of Materials for a part"""
    neo4j = get_neo4j_service()
    
    query = """
    MATCH path = (root:Part {uid: $part_uid})-[:ASSEMBLES_WITH*1..5]->(component:Part)
    RETURN DISTINCT component.uid AS uid,
           component.name AS name,
           component.part_number AS part_number,
           length(path) AS level
    ORDER BY level, component.name
    """
    
    result = neo4j.execute_query(query, {"part_uid": part_uid})
    return jsonify([dict(r) for r in result])


@ap242_bp.route("/materials", methods=["GET"])
def get_materials():
    """Get all materials"""
    neo4j = get_neo4j_service()
    
    query = """
    MATCH (mat:Material)
    OPTIONAL MATCH (mat)<-[:USES_MATERIAL]-(part:Part)
    OPTIONAL MATCH (mat)-[:CLASSIFIED_AS]->(ref:ExternalOwlClass)
    RETURN mat.uid AS uid,
           mat.name AS name,
           mat.specification AS specification,
           count(DISTINCT part) AS used_in_parts,
           ref.label AS classification
    ORDER BY mat.name
    """
    
    result = neo4j.execute_query(query)
    return jsonify([dict(r) for r in result])
```

### **C. Create AP243 Route Handler**

**File**: `src/web/routes/ap243.py` (NEW)

```python
"""
AP243 Reference Data & Ontologies API Routes
Handles external ontologies, units, and value types
"""

from flask import Blueprint, jsonify, request
from src.web.services import get_neo4j_service

ap243_bp = Blueprint("ap243", __name__, url_prefix="/api/v1/ap243")


@ap243_bp.route("/ontologies", methods=["GET"])
def get_ontologies():
    """Get all external OWL classes (AP243 Level 3)"""
    neo4j = get_neo4j_service()
    
    query = """
    MATCH (owl:ExternalOwlClass)
    OPTIONAL MATCH (owl)<-[:CLASSIFIED_AS]-(entity)
    RETURN owl.uri AS uri,
           owl.label AS label,
           owl.definition AS definition,
           owl.ap_level AS ap_level,
           count(DISTINCT entity) AS usage_count,
           collect(DISTINCT labels(entity)[0]) AS used_by_types
    ORDER BY owl.label
    """
    
    result = neo4j.execute_query(query)
    return jsonify([dict(r) for r in result])


@ap243_bp.route("/units", methods=["GET"])
def get_units():
    """Get all external units"""
    neo4j = get_neo4j_service()
    
    query = """
    MATCH (unit:ExternalUnit)
    RETURN unit.symbol AS symbol,
           unit.name AS name,
           unit.conversion_factor AS conversion_factor,
           unit.base_unit AS base_unit
    ORDER BY unit.symbol
    """
    
    result = neo4j.execute_query(query)
    return jsonify([dict(r) for r in result])


@ap243_bp.route("/value-types", methods=["GET"])
def get_value_types():
    """Get all value type definitions"""
    neo4j = get_neo4j_service()
    
    query = """
    MATCH (vt:ValueType)
    RETURN vt.uri AS uri,
           vt.datatype AS datatype,
           vt.constraints AS constraints
    ORDER BY vt.datatype
    """
    
    result = neo4j.execute_query(query)
    return jsonify([dict(r) for r in result])
```

### **D. Create Hierarchical Navigation Endpoint**

**File**: `src/web/routes/hierarchy.py` (NEW)

```python
"""
Hierarchical Navigation API - AP239 → AP242 → AP243
"""

from flask import Blueprint, jsonify, request
from src.web.services import get_neo4j_service

hierarchy_bp = Blueprint("hierarchy", __name__, url_prefix="/api/v1/hierarchy")


@hierarchy_bp.route("/requirement-to-part/<req_uid>", methods=["GET"])
def requirement_to_part(req_uid):
    """Navigate from AP239 Requirement down to AP242 Parts"""
    neo4j = get_neo4j_service()
    
    query = """
    MATCH (req:Requirement {uid: $req_uid})
    MATCH (req)-[:SATISFIED_BY_PART]->(part:Part)
    OPTIONAL MATCH (part)-[:HAS_GEOMETRY]->(geom:GeometricModel)
    OPTIONAL MATCH (part)-[:USES_MATERIAL]->(mat:Material)
    OPTIONAL MATCH (mat)-[:CLASSIFIED_AS]->(ref:ExternalOwlClass)
    RETURN req.name AS requirement,
           part.name AS part_name,
           part.uid AS part_uid,
           geom.file_uri AS cad_file,
           mat.name AS material,
           ref.label AS material_classification
    """
    
    result = neo4j.execute_query(query, {"req_uid": req_uid})
    return jsonify([dict(r) for r in result])


@hierarchy_bp.route("/traceability-matrix", methods=["GET"])
def traceability_matrix():
    """Get full traceability matrix (AP239 → AP242 → AP243)"""
    neo4j = get_neo4j_service()
    
    query = """
    MATCH (req:Requirement)
    OPTIONAL MATCH (req)-[:SATISFIED_BY_PART]->(part:Part)
    OPTIONAL MATCH (part)-[:USES_MATERIAL]->(mat:Material)
    OPTIONAL MATCH (mat)-[:CLASSIFIED_AS]->(ref:ExternalOwlClass)
    RETURN req.uid AS requirement_uid,
           req.name AS requirement,
           req.priority AS priority,
           collect(DISTINCT {
               part: part.name,
               part_uid: part.uid,
               material: mat.name,
               reference: ref.label
           }) AS implementation
    ORDER BY req.priority DESC
    """
    
    result = neo4j.execute_query(query)
    return jsonify([dict(r) for r in result])


@hierarchy_bp.route("/levels", methods=["GET"])
def get_levels():
    """Get count of nodes at each AP level"""
    neo4j = get_neo4j_service()
    
    query = """
    MATCH (n)
    WHERE n.ap_level IS NOT NULL
    RETURN n.ap_level AS level,
           count(n) AS count,
           collect(DISTINCT labels(n)[0]) AS node_types
    ORDER BY level
    """
    
    result = neo4j.execute_query(query)
    return jsonify([dict(r) for r in result])
```

### **E. Register New Blueprints in Main App**

**File**: `src/web/app.py`

```python
# ADD IMPORTS at top
from src.web.routes.ap239 import ap239_bp
from src.web.routes.ap242 import ap242_bp
from src.web.routes.ap243 import ap243_bp
from src.web.routes.hierarchy import hierarchy_bp

# REGISTER BLUEPRINTS (around line 50, after existing blueprints)
app.register_blueprint(ap239_bp)
app.register_blueprint(ap242_bp)
app.register_blueprint(ap243_bp)
app.register_blueprint(hierarchy_bp)
```

---

## 3️⃣ **FRONTEND (REACT) CHANGES**

### **A. Add AP239/AP242/AP243 Type Definitions**

**File**: `frontend/src/types/api.ts`

```typescript
// ADD after existing interfaces

// ============================================================================
// AP239 - Product Life Cycle Support Types
// ============================================================================

export interface Requirement extends Artifact {
  type: 'Requirement';
  text: string;
  priority: 'Critical' | 'High' | 'Medium' | 'Low';
  status: 'Draft' | 'Approved' | 'Implemented' | 'Verified';
  ap_level: 'AP239';
  satisfied_by_parts?: string[];
  verifying_tests?: Analysis[];
  approvals?: Approval[];
}

export interface Analysis extends Artifact {
  type: 'Analysis';
  analysis_type: string;
  results: string;
  timestamp: string;
  ap_level: 'AP239';
  analyzed_models?: string[];
}

export interface Approval extends Artifact {
  type: 'Approval';
  status: 'Pending' | 'Approved' | 'Rejected';
  approver: string;
  date: string;
  ap_level: 'AP239';
  approved_artifacts?: Array<{
    type: string;
    name: string;
    uid: string;
  }>;
}

export interface Document extends Artifact {
  type: 'Document';
  document_type: string;
  version: string;
  file_uri: string;
  ap_level: 'AP239';
  describes_parts?: string[];
}

// ============================================================================
// AP242 - Managed Model-Based 3D Engineering Types
// ============================================================================

export interface Part extends Artifact {
  type: 'Part';
  part_number: string;
  description: string;
  ap_level: 'AP242';
  satisfies_requirements?: string[];
  geometry_files?: string[];
  materials?: string[];
  assembly_parts?: Part[];
}

export interface PartVersion extends Artifact {
  type: 'PartVersion';
  version: string;
  part_uid: string;
  ap_level: 'AP242';
}

export interface Material extends Artifact {
  type: 'Material';
  specification: string;
  ap_level: 'AP242';
  used_in_parts?: number;
  classification?: string;
}

export interface GeometricModel extends Artifact {
  type: 'GeometricModel';
  file_uri: string;
  format: 'STEP' | 'IGES' | 'STL' | 'OBJ';
  ap_level: 'AP242';
}

// ============================================================================
// AP243 - Reference Data & Ontologies Types
// ============================================================================

export interface ExternalOwlClass {
  uri: string;
  label: string;
  definition: string;
  ap_level: 'AP243';
  usage_count?: number;
  used_by_types?: string[];
}

export interface ExternalUnit {
  symbol: string;
  name: string;
  conversion_factor?: number;
  base_unit?: string;
}

export interface ValueType {
  uri: string;
  datatype: string;
  constraints?: string;
}

// ============================================================================
// Hierarchical Navigation Types
// ============================================================================

export interface TraceabilityLink {
  requirement_uid: string;
  requirement: string;
  priority: string;
  implementation: Array<{
    part: string;
    part_uid: string;
    material: string;
    reference: string;
  }>;
}

export interface LevelStatistics {
  level: 'AP239' | 'AP242' | 'AP243';
  count: number;
  node_types: string[];
}
```

### **B. Create Requirements Dashboard Component**

**File**: `frontend/src/pages/RequirementsDashboard.tsx` (NEW)

```typescript
import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Requirement, TraceabilityLink } from '@/types/api';

export default function RequirementsDashboard() {
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [traceability, setTraceability] = useState<TraceabilityLink[]>([]);

  useEffect(() => {
    // Fetch requirements
    fetch('/api/v1/ap239/requirements')
      .then(res => res.json())
      .then(data => setRequirements(data));

    // Fetch traceability matrix
    fetch('/api/v1/hierarchy/traceability-matrix')
      .then(res => res.json())
      .then(data => setTraceability(data));
  }, []);

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'Critical': return 'destructive';
      case 'High': return 'default';
      case 'Medium': return 'secondary';
      case 'Low': return 'outline';
      default: return 'default';
    }
  };

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-3xl font-bold">Requirements Dashboard (AP239)</h1>

      {/* Requirements List */}
      <div className="grid gap-4">
        {requirements.map((req) => (
          <Card key={req.uid}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>{req.name}</CardTitle>
                <div className="flex gap-2">
                  <Badge variant={getPriorityColor(req.priority)}>
                    {req.priority}
                  </Badge>
                  <Badge variant="outline">{req.status}</Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-4">{req.text}</p>
              {req.satisfied_by_parts && req.satisfied_by_parts.length > 0 && (
                <div className="text-sm">
                  <span className="font-semibold">Satisfied by: </span>
                  {req.satisfied_by_parts.join(', ')}
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Traceability Matrix */}
      <Card>
        <CardHeader>
          <CardTitle>Traceability Matrix (AP239 → AP242 → AP243)</CardTitle>
        </CardHeader>
        <CardContent>
          <table className="w-full">
            <thead>
              <tr className="border-b">
                <th className="text-left p-2">Requirement</th>
                <th className="text-left p-2">Priority</th>
                <th className="text-left p-2">Part</th>
                <th className="text-left p-2">Material</th>
                <th className="text-left p-2">Reference (AP243)</th>
              </tr>
            </thead>
            <tbody>
              {traceability.map((trace) =>
                trace.implementation.map((impl, idx) => (
                  <tr key={`${trace.requirement_uid}-${idx}`} className="border-b">
                    <td className="p-2">{trace.requirement}</td>
                    <td className="p-2">
                      <Badge variant={getPriorityColor(trace.priority)}>
                        {trace.priority}
                      </Badge>
                    </td>
                    <td className="p-2">{impl.part}</td>
                    <td className="p-2">{impl.material}</td>
                    <td className="p-2 text-sm text-muted-foreground">
                      {impl.reference}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
```

### **C. Create Parts/BOM Explorer Component**

**File**: `frontend/src/pages/PartsExplorer.tsx` (NEW)

```typescript
import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Part } from '@/types/api';

export default function PartsExplorer() {
  const [parts, setParts] = useState<Part[]>([]);
  const [selectedPart, setSelectedPart] = useState<Part | null>(null);

  useEffect(() => {
    fetch('/api/v1/ap242/parts')
      .then(res => res.json())
      .then(data => setParts(data));
  }, []);

  const fetchPartDetails = (uid: string) => {
    fetch(`/api/v1/ap242/parts/${uid}`)
      .then(res => res.json())
      .then(data => setSelectedPart(data.part));
  };

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-3xl font-bold">Parts & BOM Explorer (AP242)</h1>

      <div className="grid grid-cols-2 gap-6">
        {/* Parts List */}
        <Card>
          <CardHeader>
            <CardTitle>All Parts</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {parts.map((part) => (
                <div
                  key={part.uid}
                  className="p-3 border rounded cursor-pointer hover:bg-accent"
                  onClick={() => fetchPartDetails(part.uid)}
                >
                  <div className="font-semibold">{part.name}</div>
                  <div className="text-sm text-muted-foreground">
                    {part.part_number}
                  </div>
                  <div className="flex gap-2 mt-2">
                    <Badge variant="secondary">AP242</Badge>
                    {part.satisfies_requirements && part.satisfies_requirements.length > 0 && (
                      <Badge variant="outline">
                        {part.satisfies_requirements.length} Requirements
                      </Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Part Details */}
        <Card>
          <CardHeader>
            <CardTitle>Part Details</CardTitle>
          </CardHeader>
          <CardContent>
            {selectedPart ? (
              <div className="space-y-4">
                <div>
                  <h3 className="font-semibold">{selectedPart.name}</h3>
                  <p className="text-sm text-muted-foreground">
                    {selectedPart.part_number}
                  </p>
                </div>

                {selectedPart.satisfies_requirements && (
                  <div>
                    <h4 className="font-semibold mb-2">Satisfies Requirements:</h4>
                    <ul className="list-disc list-inside">
                      {selectedPart.satisfies_requirements.map((req, idx) => (
                        <li key={idx} className="text-sm">{req}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {selectedPart.materials && selectedPart.materials.length > 0 && (
                  <div>
                    <h4 className="font-semibold mb-2">Materials:</h4>
                    <div className="flex gap-2">
                      {selectedPart.materials.map((mat, idx) => (
                        <Badge key={idx} variant="secondary">{mat}</Badge>
                      ))}
                    </div>
                  </div>
                )}

                {selectedPart.geometry_files && selectedPart.geometry_files.length > 0 && (
                  <div>
                    <h4 className="font-semibold mb-2">CAD Files:</h4>
                    <ul className="text-sm space-y-1">
                      {selectedPart.geometry_files.map((file, idx) => (
                        <li key={idx} className="truncate">{file}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-muted-foreground">Select a part to view details</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
```

### **D. Update Navigation to Include New Pages**

**File**: `frontend/src/components/layout/Layout.tsx`

```typescript
// ADD to navigation items (around line 30)
const navGroups = [
  // ... existing groups ...
  {
    title: "AP239 - Lifecycle",
    description: "Requirements, Analysis, Approvals",
    items: [
      { href: "/requirements", label: "Requirements", icon: FileCheck, badge: "AP239" },
      { href: "/analysis", label: "Analysis", icon: LineChart, badge: "AP239" },
      { href: "/approvals", label: "Approvals", icon: CheckCircle, badge: "AP239" },
      { href: "/documents", label: "Documents", icon: FileText, badge: "AP239" },
    ]
  },
  {
    title: "AP242 - CAD/BOM",
    description: "Parts, Assemblies, Materials",
    items: [
      { href: "/parts", label: "Parts & BOM", icon: Box, badge: "AP242" },
      { href: "/assemblies", label: "Assemblies", icon: Boxes, badge: "AP242" },
      { href: "/materials", label: "Materials", icon: Layers, badge: "AP242" },
      { href: "/cad", label: "CAD Models", icon: Cube, badge: "AP242" },
    ]
  },
  {
    title: "AP243 - References",
    description: "Ontologies, Units, Standards",
    items: [
      { href: "/ontologies", label: "Ontologies", icon: Database, badge: "AP243" },
      { href: "/units", label: "Units", icon: Ruler, badge: "AP243" },
    ]
  },
  {
    title: "Hierarchy",
    description: "Cross-level Navigation",
    items: [
      { href: "/traceability", label: "Traceability Matrix", icon: Network, badge: "ALL" },
      { href: "/hierarchy", label: "AP Hierarchy", icon: GitBranch, badge: "ALL" },
    ]
  }
];
```

---

## 4️⃣ **TESTING & VALIDATION**

### **A. Database Migration Test Script**

**File**: `scripts/test_ap_hierarchy.py` (NEW)

```python
"""Test script to validate AP239/AP242/AP243 hierarchical implementation"""

from src.graph.connection import Neo4jConnection
from src.utils.config import Config

def test_ap_hierarchy():
    config = Config()
    conn = Neo4jConnection(config.neo4j_uri, config.neo4j_user, config.neo4j_password)
    conn.connect()

    print("=" * 80)
    print("AP239/AP242/AP243 HIERARCHY VALIDATION")
    print("=" * 80)

    # Test 1: Check AP level distribution
    query = """
    MATCH (n)
    WHERE n.ap_level IS NOT NULL
    RETURN n.ap_level AS level, count(n) AS count
    ORDER BY level
    """
    result = conn.execute_query(query)
    print("\n1. AP Level Distribution:")
    for r in result:
        print(f"   {r['level']}: {r['count']} nodes")

    # Test 2: Check hierarchical relationships
    query = """
    MATCH (ap239)-[r]->(ap242)
    WHERE ap239.ap_level = 'AP239' AND ap242.ap_level = 'AP242'
    RETURN type(r) AS relationship, count(r) AS count
    """
    result = conn.execute_query(query)
    print("\n2. AP239 → AP242 Relationships:")
    for r in result:
        print(f"   {r['relationship']}: {r['count']} links")

    # Test 3: Check AP242 → AP243 links
    query = """
    MATCH (ap242)-[r]->(ap243)
    WHERE ap242.ap_level = 'AP242' AND ap243.ap_level = 'AP243'
    RETURN type(r) AS relationship, count(r) AS count
    """
    result = conn.execute_query(query)
    print("\n3. AP242 → AP243 Relationships:")
    for r in result:
        print(f"   {r['relationship']}: {r['count']} links")

    # Test 4: Sample traceability chain
    query = """
    MATCH (req:Requirement)-[:SATISFIED_BY_PART]->(part:Part)-[:USES_MATERIAL]->(mat:Material)-[:CLASSIFIED_AS]->(ref:ExternalOwlClass)
    RETURN req.name AS requirement,
           part.name AS part,
           mat.name AS material,
           ref.label AS reference
    LIMIT 5
    """
    result = conn.execute_query(query)
    print("\n4. Sample Traceability Chains (AP239 → AP242 → AP243):")
    for r in result:
        print(f"   {r['requirement']} → {r['part']} → {r['material']} → {r['reference']}")

    conn.close()
    print("\n" + "=" * 80)
    print("VALIDATION COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    test_ap_hierarchy()
```

---

## 📊 Summary of Changes

| Component | Files to Create | Files to Modify | Lines of Code |
|-----------|----------------|-----------------|---------------|
| **Neo4j Database** | `scripts/migrate_to_ap_hierarchy.cypher` | `src/parsers/semantic_loader.py` | ~500 |
| **Backend (Flask)** | `src/web/routes/ap239.py`<br>`src/web/routes/ap242.py`<br>`src/web/routes/ap243.py`<br>`src/web/routes/hierarchy.py` | `src/web/app.py` | ~800 |
| **Frontend (React)** | `frontend/src/pages/RequirementsDashboard.tsx`<br>`frontend/src/pages/PartsExplorer.tsx` | `frontend/src/types/api.ts`<br>`frontend/src/components/layout/Layout.tsx` | ~600 |
| **Testing** | `scripts/test_ap_hierarchy.py` | None | ~100 |
| **Total** | 9 new files | 4 modified files | **~2,000 lines** |

---

## 🚀 Implementation Steps

1. **Phase 1: Database (1-2 days)**
   - Update `semantic_loader.py` with AP239/AP242/AP243 node types
   - Run `migrate_to_ap_hierarchy.cypher` script
   - Verify indexes and hierarchical relationships

2. **Phase 2: Backend (2-3 days)**
   - Create AP239, AP242, AP243 route handlers
   - Create hierarchical navigation endpoints
   - Register blueprints in main app
   - Test all new endpoints

3. **Phase 3: Frontend (2-3 days)**
   - Update TypeScript types
   - Create Requirements Dashboard
   - Create Parts/BOM Explorer
   - Update navigation menu
   - Test UI components

4. **Phase 4: Integration Testing (1 day)**
   - Run `test_ap_hierarchy.py`
   - Test end-to-end traceability
   - Verify cross-level navigation
   - Performance testing

---

## ✅ Success Criteria

- ✅ Neo4j contains AP239, AP242, AP243 nodes with `ap_level` property
- ✅ Hierarchical relationships (SATISFIED_BY_PART, USES_MATERIAL, CLASSIFIED_AS) exist
- ✅ Backend API endpoints return AP239/AP242/AP243 data correctly
- ✅ Frontend displays Requirements Dashboard with traceability
- ✅ Frontend displays Parts/BOM Explorer with materials and references
- ✅ Traceability Matrix shows complete AP239 → AP242 → AP243 chains
- ✅ All tests pass in `test_ap_hierarchy.py`

Ready to proceed with implementation?
