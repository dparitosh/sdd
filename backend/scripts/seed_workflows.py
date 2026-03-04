"""
seed_workflows.py
=================
Seeds WorkflowMethod, TaskElement, and ActionResource nodes in Neo4j for
the 5 existing SimulationRuns, following the STEP AP243/AP239 action_schema
and method_definition_schema patterns:

  action_method        →  :WorkflowMethod
  sequential_method    →  :TaskElement with [:NEXT_STEP] chain
  concurrent_action    →  [:PARALLEL_WITH] edges
  action_resource      →  :ActionResource
  executed_action      →  :SimulationRun [:CHOSEN_METHOD]→ :WorkflowMethod

Run:
  python backend/scripts/seed_workflows.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

from src.web.services.neo4j_service import Neo4jService

neo4j = Neo4jService()

# ---------------------------------------------------------------------------
# Workflow definitions
# ---------------------------------------------------------------------------
WORKFLOWS = [
    {
        "id": "WF-EM-001",
        "name": "Electromagnetic Analysis Workflow",
        "version": "1.0",
        "sim_type": "Electromagnetic",
        "purpose": "Full FEA electromagnetic field simulation per IEC 60034",
        "consequence": "Validated EM field distribution and loss maps",
        "status": "active",
        "steps": [
            {"seq": 1, "name": "Geometry & Mesh Setup",      "type": "prepare",  "description": "Import CAD, define mesh parameters, assign material regions"},
            {"seq": 2, "name": "Boundary Condition Config",   "type": "prepare",  "description": "Apply excitation sources, symmetry planes, and flux boundary conditions"},
            {"seq": 3, "name": "EM Solver Execution",         "type": "execute",  "description": "Run Maxwell 2D/3D FEA solver (ISO 17025 tool verification)"},
            {"seq": 4, "name": "Field Distribution Analysis", "type": "analyze",  "description": "Extract B-field, H-field, flux distribution and eddy current maps"},
            {"seq": 5, "name": "Loss Calculation",            "type": "analyze",  "description": "Compute iron loss, copper loss and efficiency metrics"},
            {"seq": 6, "name": "Report & Evidence Package",   "type": "report",   "description": "Generate AP243 conformant result artifact set with SHA-256 fingerprint"},
        ],
        "resources": [
            {"id": "RES-MAXWELL-001", "name": "ANSYS Maxwell 2D/3D", "resource_type": "solver"},
            {"id": "RES-MOTCAD-001",  "name": "Motor-CAD",           "resource_type": "solver"},
            {"id": "RES-HPC-EM",      "name": "EM HPC Cluster",      "resource_type": "compute"},
        ],
        "linked_runs": ["FEA-MAXWELL-2D", "FEA-MAXWELL-3D", "MOTOR-CAD-TRACTION"],
    },
    {
        "id": "WF-CFD-001",
        "name": "Computational Fluid Dynamics Workflow",
        "version": "1.0",
        "sim_type": "CFD",
        "purpose": "Incompressible/compressible CFD analysis of pump/fluid systems",
        "consequence": "Pressure distribution, velocity fields, efficiency curves",
        "status": "active",
        "steps": [
            {"seq": 1, "name": "Geometry Import & Cleanup",  "type": "prepare",  "description": "Import STEP geometry, repair topology defects"},
            {"seq": 2, "name": "Volume Mesh Generation",     "type": "prepare",  "description": "Generate polyhedral/hex mesh, refine boundary layer"},
            {"seq": 3, "name": "Physics & BC Setup",         "type": "prepare",  "description": "Define inlet/outlet BCs, turbulence model, fluid properties"},
            {"seq": 4, "name": "CFD Solver Execution",       "type": "execute",  "description": "Run ANSYS Fluent RANS solver to convergence"},
            {"seq": 5, "name": "Post-Processing",            "type": "analyze",  "description": "Extract pressure drop, velocity profiles, streamlines"},
            {"seq": 6, "name": "Performance Validation",     "type": "analyze",  "description": "Compare results to test data, compute CFD uncertainty"},
            {"seq": 7, "name": "Report Generation",          "type": "report",   "description": "Produce AP243-conformant CFD result dossier"},
        ],
        "resources": [
            {"id": "RES-FLUENT-001", "name": "ANSYS Fluent",   "resource_type": "solver"},
            {"id": "RES-HPC-CFD",    "name": "CFD HPC Cluster","resource_type": "compute"},
        ],
        "linked_runs": ["CFD-PUMP-FLUENT"],
    },
    {
        "id": "WF-STRUCT-001",
        "name": "Structural FEA Workflow",
        "version": "1.0",
        "sim_type": "Structural",
        "purpose": "Linear/nonlinear structural analysis of mechanical assemblies",
        "consequence": "Stress/strain distribution, factor of safety, fatigue life",
        "status": "active",
        "steps": [
            {"seq": 1, "name": "CAD Import & Simplification", "type": "prepare",  "description": "Import assembly, remove small features, assign material properties"},
            {"seq": 2, "name": "Mesh Generation",             "type": "prepare",  "description": "Generate tetrahedral/hexahedral FE mesh with refinement zones"},
            {"seq": 3, "name": "Boundary & Load Conditions",  "type": "prepare",  "description": "Apply supports, forces, pressures, and thermal loads"},
            {"seq": 4, "name": "FEA Solver Execution",        "type": "execute",  "description": "Run linear static or nonlinear FEA solver"},
            {"seq": 5, "name": "Stress & Deformation Analysis","type": "analyze", "description": "Extract von Mises stress, principal strains, deflections"},
            {"seq": 6, "name": "Factor of Safety Check",      "type": "validate", "description": "Evaluate FoS against material yield and ultimate limits"},
            {"seq": 7, "name": "Fatigue Assessment",          "type": "analyze",  "description": "Apply S-N curve analysis for cyclic loading"},
            {"seq": 8, "name": "Certification Report",        "type": "report",   "description": "AP243 structural result dossier with traceability to requirements"},
        ],
        "resources": [
            {"id": "RES-MECHANICAL-001", "name": "ANSYS Mechanical",  "resource_type": "solver"},
            {"id": "RES-NASTRAN-001",    "name": "NX Nastran",        "resource_type": "solver"},
            {"id": "RES-HPC-STRUCT",     "name": "Structural HPC",    "resource_type": "compute"},
        ],
        "linked_runs": ["FEA-CRANE-STRUCT"],
    },
]

# ---------------------------------------------------------------------------
# Helper: element uid
# ---------------------------------------------------------------------------
def step_uid(wf_id: str, seq: int) -> str:
    return f"{wf_id}-STEP-{seq:02d}"

# ---------------------------------------------------------------------------
# Cypher: create/merge workflow + steps
# ---------------------------------------------------------------------------
def seed_workflow(wf: dict):
    wid = wf["id"]
    print(f"  Seeding {wid}: {wf['name']} ({len(wf['steps'])} steps, {len(wf['linked_runs'])} runs)")

    # 1. Create WorkflowMethod node
    neo4j.execute_write("""
        MERGE (wm:WorkflowMethod:ActionMethod {id: $id})
        SET wm.name             = $name,
            wm.version          = $version,
            wm.sim_type         = $sim_type,
            wm.purpose          = $purpose,
            wm.consequence      = $consequence,
            wm.status           = $status,
            wm.step_count       = $step_count,
            wm.updated_at       = datetime()
    """, {
        "id": wid, "name": wf["name"], "version": wf["version"],
        "sim_type": wf["sim_type"], "purpose": wf["purpose"],
        "consequence": wf["consequence"], "status": wf["status"],
        "step_count": len(wf["steps"]),
    })

    # 2. Create TaskElement nodes + link to WorkflowMethod
    prev_uid = None
    for step in wf["steps"]:
        uid = step_uid(wid, step["seq"])
        neo4j.execute_write("""
            MERGE (te:TaskElement {uid: $uid})
            SET te.name            = $name,
                te.type            = $type,
                te.description     = $description,
                te.sequence_position = $seq,
                te.workflow_id     = $wf_id
            WITH te
            MATCH (wm:WorkflowMethod {id: $wf_id})
            MERGE (wm)-[:HAS_STEP]->(te)
        """, {
            "uid": uid, "name": step["name"], "type": step["type"],
            "description": step["description"], "seq": step["seq"], "wf_id": wid,
        })
        # Serial chain: NEXT_STEP
        if prev_uid:
            neo4j.execute_write("""
                MATCH (a:TaskElement {uid: $prev})
                MATCH (b:TaskElement {uid: $curr})
                MERGE (a)-[:NEXT_STEP]->(b)
            """, {"prev": prev_uid, "curr": uid})
        prev_uid = uid

    # 3. Create ActionResource nodes + link to WorkflowMethod
    for res in wf["resources"]:
        neo4j.execute_write("""
            MERGE (ar:ActionResource {id: $id})
            SET ar.name          = $name,
                ar.resource_type = $rtype
            WITH ar
            MATCH (wm:WorkflowMethod {id: $wf_id})
            MERGE (wm)-[:USES_RESOURCE]->(ar)
        """, {"id": res["id"], "name": res["name"], "rtype": res["resource_type"], "wf_id": wid})

    # 4. Link existing SimulationRuns to WorkflowMethod
    for run_id in wf["linked_runs"]:
        result = neo4j.execute_write("""
            MATCH (sr:SimulationRun {id: $run_id})
            MATCH (wm:WorkflowMethod {id: $wf_id})
            MERGE (sr)-[:CHOSEN_METHOD]->(wm)
            RETURN sr.id AS rid
        """, {"run_id": run_id, "wf_id": wid})
        if result:
            print(f"    Linked run {run_id} → {wid}")
        else:
            print(f"    [WARN] SimulationRun not found: {run_id}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Seeding STEP AP243/AP239 workflow nodes into Neo4j (mossec db)...")
    for wf in WORKFLOWS:
        seed_workflow(wf)
    print("\nVerifying...")
    counts = neo4j.execute_query("""
        MATCH (wm:WorkflowMethod) WITH count(wm) AS wms
        MATCH (te:TaskElement)    WITH wms, count(te) AS tes
        MATCH (ar:ActionResource) WITH wms, tes, count(ar) AS ars
        RETURN wms, tes, ars
    """, {})
    if counts:
        r = counts[0]
        print(f"  WorkflowMethod nodes : {r['wms']}")
        print(f"  TaskElement nodes    : {r['tes']}")
        print(f"  ActionResource nodes : {r['ars']}")
    print("\nDone.")
