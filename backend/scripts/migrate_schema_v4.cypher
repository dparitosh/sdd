// ============================================================================
// SDD v4.0 SCHEMA MIGRATION — Governance Layer Node Types + Constraints
// ============================================================================
// Purpose: Creates all v4.0 uniqueness constraints, indexes, and reference
//          Standard nodes per SDD_MODULAR_ARCHITECTURE_PLAN.md Section 4.2-4.5.
// Created: February 26, 2026
// Phase:   Phase 2 — Neo4j Schema Evolution
//
// IMPORTANT: This migration is additive.  It does NOT delete existing nodes,
//            relationships, or constraints.  Safe to run multiple times
//            (all statements use IF NOT EXISTS / MERGE).
// ============================================================================


// ============================================================================
// PART 1: UNIQUENESS CONSTRAINTS (Section 4.5)
// ============================================================================

// -- Existing labels (ensure constraints exist) --
CREATE CONSTRAINT sdd_simulation_dossier_id IF NOT EXISTS
FOR (d:SimulationDossier) REQUIRE d.id IS UNIQUE;

CREATE CONSTRAINT sdd_simulation_run_id IF NOT EXISTS
FOR (r:SimulationRun) REQUIRE r.id IS UNIQUE;

CREATE CONSTRAINT sdd_simulation_model_id IF NOT EXISTS
FOR (m:SimulationModel) REQUIRE m.id IS UNIQUE;

// -- New governance labels --
CREATE CONSTRAINT sdd_approval_record_id IF NOT EXISTS
FOR (a:ApprovalRecord) REQUIRE a.id IS UNIQUE;

CREATE CONSTRAINT sdd_audit_finding_id IF NOT EXISTS
FOR (f:AuditFinding) REQUIRE f.id IS UNIQUE;

CREATE CONSTRAINT sdd_decision_log_id IF NOT EXISTS
FOR (dl:DecisionLog) REQUIRE dl.id IS UNIQUE;

CREATE CONSTRAINT sdd_standard_name IF NOT EXISTS
FOR (s:Standard) REQUIRE s.name IS UNIQUE;

CREATE CONSTRAINT sdd_vv_plan_id IF NOT EXISTS
FOR (v:VV_Plan) REQUIRE v.id IS UNIQUE;

CREATE CONSTRAINT sdd_product_spec_id IF NOT EXISTS
FOR (ps:ProductSpec) REQUIRE ps.id IS UNIQUE;


// ============================================================================
// PART 2: INDEXES (Performance)
// ============================================================================

// -- SimulationDossier queries --
CREATE INDEX idx_dossier_status IF NOT EXISTS
FOR (d:SimulationDossier) ON (d.status);

CREATE INDEX idx_dossier_engineer IF NOT EXISTS
FOR (d:SimulationDossier) ON (d.engineer);

CREATE INDEX idx_dossier_created_at IF NOT EXISTS
FOR (d:SimulationDossier) ON (d.created_at);

// -- ApprovalRecord queries --
CREATE INDEX idx_approval_record_status IF NOT EXISTS
FOR (a:ApprovalRecord) ON (a.status);

CREATE INDEX idx_approval_record_reviewer IF NOT EXISTS
FOR (a:ApprovalRecord) ON (a.reviewer);

CREATE INDEX idx_approval_record_timestamp IF NOT EXISTS
FOR (a:ApprovalRecord) ON (a.timestamp);

// -- AuditFinding queries --
CREATE INDEX idx_audit_finding_severity IF NOT EXISTS
FOR (f:AuditFinding) ON (f.severity);

CREATE INDEX idx_audit_finding_category IF NOT EXISTS
FOR (f:AuditFinding) ON (f.category);

// -- DecisionLog queries --
CREATE INDEX idx_decision_log_timestamp IF NOT EXISTS
FOR (dl:DecisionLog) ON (dl.timestamp);

CREATE INDEX idx_decision_log_reviewer IF NOT EXISTS
FOR (dl:DecisionLog) ON (dl.reviewer);

// -- SimulationRun queries --
CREATE INDEX idx_simulation_run_status IF NOT EXISTS
FOR (sr:SimulationRun) ON (sr.status);

CREATE INDEX idx_simulation_run_start IF NOT EXISTS
FOR (sr:SimulationRun) ON (sr.start_time);

// -- Standard queries --
CREATE INDEX idx_standard_version IF NOT EXISTS
FOR (s:Standard) ON (s.version);

// -- VV_Plan queries --
CREATE INDEX idx_vv_plan_status IF NOT EXISTS
FOR (v:VV_Plan) ON (v.status);

CREATE INDEX idx_vv_plan_type IF NOT EXISTS
FOR (v:VV_Plan) ON (v.type);


// ============================================================================
// PART 3: REFERENCE STANDARD NODES (Section 4.2)
// ============================================================================

MERGE (s:Standard {name: "ISO 17025"})
SET s.version   = "2017",
    s.domain    = "General requirements for the competence of testing and calibration laboratories",
    s.category  = "Quality",
    s.url       = "https://www.iso.org/standard/66912.html";

MERGE (s:Standard {name: "IEC 61508-3"})
SET s.version   = "2010",
    s.domain    = "Functional safety of electrical/electronic/programmable electronic safety-related systems — Part 3: Software requirements",
    s.category  = "Safety",
    s.url       = "https://webstore.iec.ch/publication/5517";

MERGE (s:Standard {name: "AP243 MoSSEC"})
SET s.version   = "1.0",
    s.domain    = "Model-based Simulation and Credibility Evidence — ISO 10303-243",
    s.category  = "Simulation",
    s.url       = "https://www.iso.org/standard/84667.html";

MERGE (s:Standard {name: "ISO 10303-4443 SMRL"})
SET s.version   = "1.0",
    s.domain    = "Simulation Modelling Resources Library — AP-4443 SMRL schema",
    s.category  = "Simulation",
    s.url       = "https://www.iso.org/standard/78592.html";

MERGE (s:Standard {name: "ISO 10303-239"})
SET s.version   = "2012",
    s.domain    = "Product Lifecycle Support — AP239 PLCS",
    s.category  = "PLM",
    s.url       = "https://www.iso.org/standard/48284.html";

MERGE (s:Standard {name: "ISO 10303-242"})
SET s.version   = "2020",
    s.domain    = "Managed model-based 3D engineering — AP242 MBD",
    s.category  = "CAD/CAE",
    s.url       = "https://www.iso.org/standard/57620.html";


// ============================================================================
// PART 4: VERIFICATION QUERIES
// ============================================================================

// Verify constraints
SHOW CONSTRAINTS
YIELD name, type, entityType, labelsOrTypes
WHERE name STARTS WITH 'sdd_'
RETURN name, type, entityType, labelsOrTypes
ORDER BY name;

// Verify indexes
SHOW INDEXES
YIELD name, type, entityType, labelsOrTypes
WHERE name STARTS WITH 'idx_'
RETURN name, type, entityType, labelsOrTypes
ORDER BY name;

// Verify Standard nodes
MATCH (s:Standard)
RETURN s.name AS StandardName, s.version AS Version, s.category AS Category
ORDER BY s.name;


// ============================================================================
// EXPECTED RESULTS
// ============================================================================
// - 9 uniqueness constraints (3 existing + 6 new)
// - 16 indexes (performance optimization)
// - 6 Standard reference nodes
// ============================================================================
