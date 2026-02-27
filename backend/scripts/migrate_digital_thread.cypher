// ============================================================================
// SDD v4.0 DIGITAL THREAD — Relationship Types + Sample Links
// ============================================================================
// Purpose: Creates the 11 governance relationship types from
//          SDD_MODULAR_ARCHITECTURE_PLAN.md Section 4.3.
//          Also links existing test data (SimulationDossier, SimulationRun,
//          SimulationModel, Requirement, Part) when nodes are present.
//
// Created: February 26, 2026
// Phase:   Phase 2 — Neo4j Schema Evolution
//
// IMPORTANT: Additive only.  Uses MERGE, never DELETE.
//            Safe to run multiple times.
// ============================================================================


// ============================================================================
// PART 1: DIGITAL THREAD RELATIONSHIPS (Section 4.3)
// ============================================================================
//
// The following 11 relationship types form the governance digital thread:
//
//   [:GENERATED_FROM]        Dossier → SimulationRun
//   [:USES_MODEL]            SimulationRun → SimulationModel
//   [:REPRESENTS]            SimulationModel → CADModel
//   [:PROVES_COMPLIANCE_TO]  Dossier → Requirement
//   [:GOVERNS]               Dossier → Part
//   [:HAS_APPROVAL]          Dossier → ApprovalRecord
//   [:HAS_FINDING]           Dossier → AuditFinding
//   [:HAS_DECISION]          Dossier → DecisionLog
//   [:GOVERNED_BY]           Dossier → Standard
//   [:VALIDATED_BY]          SimulationRun → VV_Plan
//   [:SPEC_FOR]              ProductSpec → Part
//
// The relationships below are created on existing sample data ONLY if the
// referenced nodes already exist (WHERE clauses guard each statement).
// ============================================================================


// --------------------------------------------------------------------------
// 1. [:GENERATED_FROM] — Dossier → SimulationRun
//    Links a dossier to the simulation run(s) that produced its evidence.
// --------------------------------------------------------------------------
MATCH (d:SimulationDossier)
MATCH (sr:SimulationRun)
WHERE EXISTS((d)-[:HAS_SIMULATION_RUN]->(sr))
  AND NOT EXISTS((d)-[:GENERATED_FROM]->(sr))
MERGE (d)-[:GENERATED_FROM]->(sr);


// --------------------------------------------------------------------------
// 2. [:USES_MODEL] — SimulationRun → SimulationModel
//    Links a simulation run to the model it executed.
// --------------------------------------------------------------------------
MATCH (sr:SimulationRun)-[:BELONGS_TO_MODEL]->(m:SimulationModel)
WHERE NOT EXISTS((sr)-[:USES_MODEL]->(m))
MERGE (sr)-[:USES_MODEL]->(m);


// --------------------------------------------------------------------------
// 3. [:REPRESENTS] — SimulationModel → CADModel
//    Links AP243 simulation models to their AP242 CAD geometry.
//    Uses matching by name substring if direct link does not exist.
// --------------------------------------------------------------------------
MATCH (sm:SimulationModel), (cm:CADModel)
WHERE sm.name CONTAINS cm.name OR cm.name CONTAINS sm.name
  AND NOT EXISTS((sm)-[:REPRESENTS]->(cm))
MERGE (sm)-[:REPRESENTS]->(cm);


// --------------------------------------------------------------------------
// 4. [:PROVES_COMPLIANCE_TO] — Dossier → Requirement
//    Links a dossier to the requirements it satisfies.
//    Derives from existing artifact→requirement traces.
// --------------------------------------------------------------------------
MATCH (d:SimulationDossier)-[:CONTAINS_ARTIFACT]->(a:SimulationArtifact)-[:LINKED_TO_REQUIREMENT]->(r:Requirement)
WHERE NOT EXISTS((d)-[:PROVES_COMPLIANCE_TO]->(r))
MERGE (d)-[:PROVES_COMPLIANCE_TO]->(r);


// --------------------------------------------------------------------------
// 5. [:GOVERNS] — Dossier → Part
//    Links a dossier to the physical part(s) it governs.
//    Uses product_id or matching name.
// --------------------------------------------------------------------------
MATCH (d:SimulationDossier), (p:Part)
WHERE (d.product_id IS NOT NULL AND d.product_id = p.id)
   OR (d.name CONTAINS p.name)
  AND NOT EXISTS((d)-[:GOVERNS]->(p))
MERGE (d)-[:GOVERNS]->(p);


// --------------------------------------------------------------------------
// 6. [:HAS_APPROVAL] — Dossier → ApprovalRecord
//    Already created by approval_service at runtime.
//    This ensures any orphaned ApprovalRecord nodes are linked.
// --------------------------------------------------------------------------
MATCH (d:SimulationDossier), (ar:ApprovalRecord)
WHERE ar.dossier_id = d.id
  AND NOT EXISTS((d)-[:HAS_APPROVAL]->(ar))
MERGE (d)-[:HAS_APPROVAL]->(ar);


// --------------------------------------------------------------------------
// 7. [:HAS_FINDING] — Dossier → AuditFinding
//    Already created by audit_service at runtime.
//    This ensures any orphaned AuditFinding nodes are linked.
// --------------------------------------------------------------------------
MATCH (d:SimulationDossier), (af:AuditFinding)
WHERE af.dossier_id = d.id
  AND NOT EXISTS((d)-[:HAS_FINDING]->(af))
MERGE (d)-[:HAS_FINDING]->(af);


// --------------------------------------------------------------------------
// 8. [:HAS_DECISION] — Dossier → DecisionLog
//    Already created by approval_service at runtime.
//    This ensures any orphaned DecisionLog nodes are linked.
// --------------------------------------------------------------------------
MATCH (d:SimulationDossier), (dl:DecisionLog)
WHERE dl.dossier_id = d.id
  AND NOT EXISTS((d)-[:HAS_DECISION]->(dl))
MERGE (d)-[:HAS_DECISION]->(dl);


// --------------------------------------------------------------------------
// 9. [:GOVERNED_BY] — Dossier → Standard
//    Links every dossier to the AP243 MoSSEC standard by default.
//    Additional standard links can be added manually.
// --------------------------------------------------------------------------
MATCH (d:SimulationDossier), (s:Standard {name: "AP243 MoSSEC"})
WHERE NOT EXISTS((d)-[:GOVERNED_BY]->(s))
MERGE (d)-[:GOVERNED_BY]->(s);


// --------------------------------------------------------------------------
// 10. [:VALIDATED_BY] — SimulationRun → VV_Plan
//     Placeholder: will be linked when VV_Plan nodes are created.
//     If any VV_Plan nodes already exist, link runs by type match.
// --------------------------------------------------------------------------
MATCH (sr:SimulationRun), (vp:VV_Plan)
WHERE sr.sim_type = vp.type OR vp.type = 'Verification'
  AND NOT EXISTS((sr)-[:VALIDATED_BY]->(vp))
MERGE (sr)-[:VALIDATED_BY]->(vp);


// --------------------------------------------------------------------------
// 11. [:SPEC_FOR] — ProductSpec → Part
//     Links product specifications to their physical parts.
// --------------------------------------------------------------------------
MATCH (ps:ProductSpec), (p:Part)
WHERE ps.part_id = p.id
  AND NOT EXISTS((ps)-[:SPEC_FOR]->(p))
MERGE (ps)-[:SPEC_FOR]->(p);


// ============================================================================
// PART 2: SAMPLE VV_Plan + ProductSpec NODES
// ============================================================================

MERGE (vp:VV_Plan {id: "VVP-001"})
SET vp.name   = "Electromagnetic FEA Verification Plan",
    vp.status = "Active",
    vp.type   = "Verification",
    vp.description = "Verification plan for electromagnetic finite element analysis simulations per IEC 60034-30-1";

MERGE (vp:VV_Plan {id: "VVP-002"})
SET vp.name   = "Thermal CFD Validation Plan",
    vp.status = "Active",
    vp.type   = "Validation",
    vp.description = "Validation plan for CFD thermal simulations per IEC 60034-1 Class F";

MERGE (ps:ProductSpec {id: "SPEC-001"})
SET ps.name        = "Industrial Motor 500kW Specification",
    ps.model       = "IM-500-4P",
    ps.parameters  = "{\"power_kw\": 500, \"poles\": 4, \"voltage_v\": 6600, \"frequency_hz\": 50}",
    ps.constraints = "{\"max_temp_c\": 155, \"min_efficiency\": 0.964, \"max_vibration_mm_s\": 2.8}";


// ============================================================================
// PART 3: VERIFICATION QUERIES
// ============================================================================

// Count all v4.0 digital thread relationships
MATCH ()-[r:GENERATED_FROM|USES_MODEL|REPRESENTS|PROVES_COMPLIANCE_TO|GOVERNS|HAS_APPROVAL|HAS_FINDING|HAS_DECISION|GOVERNED_BY|VALIDATED_BY|SPEC_FOR]->()
RETURN type(r) AS RelType, COUNT(*) AS Count
ORDER BY RelType;

// Verify VV_Plan nodes
MATCH (vp:VV_Plan)
RETURN vp.id AS PlanID, vp.name AS Name, vp.type AS Type, vp.status AS Status
ORDER BY vp.id;

// Verify ProductSpec nodes
MATCH (ps:ProductSpec)
RETURN ps.id AS SpecID, ps.name AS Name, ps.model AS Model
ORDER BY ps.id;


// ============================================================================
// EXPECTED RESULTS
// ============================================================================
// - 11 relationship types created (where source/target nodes exist)
// - 2 VV_Plan nodes
// - 1 ProductSpec node
// - All MERGE-based: idempotent, safe to re-run
// ============================================================================
