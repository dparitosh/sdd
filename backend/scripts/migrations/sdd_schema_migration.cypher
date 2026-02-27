// ============================================================================
// SDD SCHEMA MIGRATION - Simulation Data Dossier Integration
// ============================================================================
// Purpose: Create Neo4j schema for SDD entities (7 labels, 16 relationships)
// Created: February 24, 2026
// Phase: Sprint 1 - Schema Design
// Related: docs/SDD_INTEGRATION_TRACKER.md
// ============================================================================

// ----------------------------------------------------------------------------
// PART 1: CREATE CONSTRAINTS (Ensure data integrity)
// ----------------------------------------------------------------------------

// SimulationDossier constraints
CREATE CONSTRAINT simulation_dossier_id IF NOT EXISTS
FOR (d:SimulationDossier) REQUIRE d.id IS UNIQUE;

CREATE CONSTRAINT simulation_dossier_name IF NOT EXISTS
FOR (d:SimulationDossier) REQUIRE d.name IS NOT NULL;

// SimulationArtifact constraints
CREATE CONSTRAINT simulation_artifact_id IF NOT EXISTS
FOR (a:SimulationArtifact) REQUIRE a.id IS UNIQUE;

CREATE CONSTRAINT simulation_artifact_name IF NOT EXISTS
FOR (a:SimulationArtifact) REQUIRE a.name IS NOT NULL;

// SimulationRun constraints
CREATE CONSTRAINT simulation_run_id IF NOT EXISTS
FOR (r:SimulationRun) REQUIRE r.id IS UNIQUE;

CREATE CONSTRAINT simulation_run_timestamp IF NOT EXISTS
FOR (r:SimulationRun) REQUIRE r.timestamp IS NOT NULL;

// EvidenceCategory constraints
CREATE CONSTRAINT evidence_category_id IF NOT EXISTS
FOR (e:EvidenceCategory) REQUIRE e.id IS UNIQUE;

// ValidationCase constraints
CREATE CONSTRAINT validation_case_id IF NOT EXISTS
FOR (v:ValidationCase) REQUIRE v.id IS UNIQUE;

// ComplianceAudit constraints
CREATE CONSTRAINT compliance_audit_id IF NOT EXISTS
FOR (a:ComplianceAudit) REQUIRE a.id IS UNIQUE;

// DecisionLog constraints
CREATE CONSTRAINT decision_log_id IF NOT EXISTS
FOR (d:DecisionLog) REQUIRE d.id IS UNIQUE;

// ----------------------------------------------------------------------------
// PART 2: CREATE INDEXES (Performance optimization)
// ----------------------------------------------------------------------------

// Index on ap_level for AP243/AP239 filtering
CREATE INDEX simulation_dossier_ap_level IF NOT EXISTS
FOR (d:SimulationDossier) ON (d.ap_level);

CREATE INDEX simulation_artifact_ap_level IF NOT EXISTS
FOR (a:SimulationArtifact) ON (a.ap_level);

// Index on status for filtering
CREATE INDEX simulation_dossier_status IF NOT EXISTS
FOR (d:SimulationDossier) ON (d.status);

CREATE INDEX simulation_artifact_status IF NOT EXISTS
FOR (a:SimulationArtifact) ON (a.status);

// Index on type for categorization
CREATE INDEX simulation_artifact_type IF NOT EXISTS
FOR (a:SimulationArtifact) ON (a.type);

CREATE INDEX evidence_category_type IF NOT EXISTS
FOR (e:EvidenceCategory) ON (e.type);

// Index on created_at for temporal queries
CREATE INDEX simulation_dossier_created_at IF NOT EXISTS
FOR (d:SimulationDossier) ON (d.created_at);

CREATE INDEX simulation_run_timestamp IF NOT EXISTS
FOR (r:SimulationRun) ON (r.timestamp);

// ----------------------------------------------------------------------------
// PART 3: CREATE AP239 REQUIREMENT STUBS (8 requirements)
// ----------------------------------------------------------------------------

// REQ-01: Electromagnetic Performance
MERGE (r:Requirement {id: 'REQ-01'})
SET r.name = 'Electromagnetic Performance Specification',
    r.description = 'Motor shall achieve rated torque of 15,400 Nm ±2% at rated speed with 96.4% minimum efficiency',
    r.type = 'Performance',
    r.priority = 'Critical',
    r.status = 'Approved',
    r.verification_method = 'Electromagnetic FEA Simulation',
    r.standard = 'IEC 60034-30-1 IE4',
    r.ap_level = 'AP239',
    r.ap_schema = 'AP239',
    r.created_at = '2024-01-15'
RETURN r.id, r.name;

// REQ-02: Transient Start Behavior
MERGE (r:Requirement {id: 'REQ-02'})
SET r.name = 'Transient Start Current Limitation',
    r.description = 'Starting current shall not exceed 450A during direct-on-line start transient',
    r.type = 'Performance',
    r.priority = 'High',
    r.status = 'Approved',
    r.verification_method = 'Transient Electromagnetic Simulation',
    r.standard = 'IEC 60034-12',
    r.ap_level = 'AP239',
    r.ap_schema = 'AP239',
    r.created_at = '2024-01-15'
RETURN r.id, r.name;

// REQ-03: Loss Segregation & Efficiency
MERGE (r:Requirement {id: 'REQ-03'})
SET r.name = 'Loss Segregation and Efficiency Validation',
    r.description = 'Total losses shall not exceed 2.5 kW with segregation accuracy ±5% per loss component',
    r.type = 'Performance',
    r.priority = 'Critical',
    r.status = 'Approved',
    r.verification_method = 'Electromagnetic FEA with Loss Analysis',
    r.standard = 'IEC 60034-2-1',
    r.ap_level = 'AP239',
    r.ap_schema = 'AP239',
    r.created_at = '2024-01-16'
RETURN r.id, r.name;

// REQ-04: Cooling Performance (CFD)
MERGE (r:Requirement {id: 'REQ-04'})
SET r.name = 'Cooling System Performance Requirements',
    r.description = 'Hotspot temperature shall not exceed 155°C under continuous rated load with 45°C ambient',
    r.type = 'Thermal',
    r.priority = 'High',
    r.status = 'Approved',
    r.verification_method = 'CFD Thermal Simulation',
    r.standard = 'IEC 60034-1 Class F Insulation',
    r.ap_level = 'AP239',
    r.ap_schema = 'AP239',
    r.created_at = '2024-01-17'
RETURN r.id, r.name;

// REQ-05: Vibration & Modal Limits
MERGE (r:Requirement {id: 'REQ-05'})
SET r.name = 'Vibration and Modal Analysis Requirements',
    r.description = 'RMS vibration shall not exceed 2.8 mm/s with no resonance frequencies between 45-55 Hz',
    r.type = 'Mechanical',
    r.priority = 'Medium',
    r.status = 'Approved',
    r.verification_method = 'Modal FEA and Vibration Analysis',
    r.standard = 'ISO 20816-1 Category II',
    r.ap_level = 'AP239',
    r.ap_schema = 'AP239',
    r.created_at = '2024-01-18'
RETURN r.id, r.name;

// REQ-06: Insulation Life Requirements
MERGE (r:Requirement {id: 'REQ-06'})
SET r.name = 'Insulation Aging and Life Expectancy',
    r.description = 'Insulation system shall maintain dielectric strength >3 kV for 25 years under rated thermal stress',
    r.type = 'Reliability',
    r.priority = 'High',
    r.status = 'Approved',
    r.verification_method = 'Thermal Aging Simulation',
    r.standard = 'IEC 60034-18-31',
    r.ap_level = 'AP239',
    r.ap_schema = 'AP239',
    r.created_at = '2024-01-19'
RETURN r.id, r.name;

// REQ-07: Structural Integrity
MERGE (r:Requirement {id: 'REQ-07'})
SET r.name = 'Structural Integrity During Faults',
    r.description = 'Frame shall withstand 3x rated torque during electrical fault without permanent deformation',
    r.type = 'Mechanical',
    r.priority = 'High',
    r.status = 'Approved',
    r.verification_method = 'Structural FEA',
    r.standard = 'IEC 60034-1',
    r.ap_level = 'AP239',
    r.ap_schema = 'AP239',
    r.created_at = '2024-01-20'
RETURN r.id, r.name;

// REQ-V1: Validation Trace Link
MERGE (r:Requirement {id: 'REQ-V1'})
SET r.name = 'MOSSEC Validation Traceability',
    r.description = 'All simulations shall maintain complete MOSSEC trace from requirement to approval',
    r.type = 'Process',
    r.priority = 'Medium',
    r.status = 'Approved',
    r.verification_method = 'Graph Query Validation',
    r.standard = 'MOSSEC Internal',
    r.ap_level = 'AP239',
    r.ap_schema = 'AP239',
    r.created_at = '2024-01-21'
RETURN r.id, r.name;

// ----------------------------------------------------------------------------
// PART 4: VERIFICATION QUERIES
// ----------------------------------------------------------------------------

// Verify all requirements created
MATCH (r:Requirement)
WHERE r.id IN ['REQ-01', 'REQ-02', 'REQ-03', 'REQ-04', 'REQ-05', 'REQ-06', 'REQ-07', 'REQ-V1']
RETURN r.id AS RequirementID, r.name AS Name, r.priority AS Priority, r.standard AS Standard
ORDER BY r.id;

// Verify constraints created
SHOW CONSTRAINTS
YIELD name, type, entityType
WHERE name STARTS WITH 'simulation_' OR name STARTS WITH 'evidence_' OR name STARTS WITH 'validation_' OR name STARTS WITH 'compliance_' OR name STARTS WITH 'decision_'
RETURN name, type, entityType
ORDER BY name;

// Verify indexes created
SHOW INDEXES
YIELD name, type, entityType
WHERE name STARTS WITH 'simulation_' OR name STARTS WITH 'evidence_'
RETURN name, type, entityType
ORDER BY name;

// ============================================================================
// EXPECTED RESULTS
// ============================================================================
// - 8 Requirement nodes created (REQ-01 through REQ-V1)
// - 7 unique constraints created (one per label)
// - 10 indexes created (performance optimization)
// - All constraints: UNIQUENESS + NOT NULL
// - All requirements: ap_level = 'AP239', ap_schema = 'AP239'
// ============================================================================
