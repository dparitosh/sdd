#!/usr/bin/env python3
"""
SDD → Ontology Linker
============================================================================
Purpose: Wire SimulationDossier / SimulationArtifact / EvidenceCategory nodes
         into the broader knowledge graph by:

  1. Adding `uid` property (= `id`) to all SDD nodes so semantic search works
  2. Creating motor Part nodes per dossier and linking via VALIDATES_PART
  3. Linking each dossier directly to Requirements via VALIDATES_REQUIREMENT
  4. Distributing artifacts (clones per dossier) to all 5 dossiers
  5. Creating SimulationRun nodes per dossier
  6. Creating ValidationCase nodes per dossier
  7. Linking to relevant Study / Analysis nodes already in the graph
  8. Linking to OWL/Ontology class nodes (Simulation, Validation, AP243)
  9. Adding a name-resolution `name` property to every SDD node for graph display

Usage:
    python backend/scripts/link_sdd_to_ontology.py
    python backend/scripts/link_sdd_to_ontology.py --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

from neo4j import GraphDatabase
from loguru import logger

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

MOTOR_PARTS = {
    "DOS-2024-001": {
        "motor_id": "IM-250-A",
        "name": "Induction Motor 250A",
        "type": "InductionMotor",
        "rating_kw": 250,
        "description": "Three-phase induction motor, 250kW, used in Mudra Sugar Plant Expansion",
    },
    "DOS-2024-002": {
        "motor_id": "HD-EM-500",
        "name": "High-Duty Electric Motor 500",
        "type": "PermanentMagnetMotor",
        "rating_kw": 500,
        "description": "Heavy-duty permanent magnet motor for offshore wind platform",
    },
    "DOS-2024-003": {
        "motor_id": "EV-P-120",
        "name": "EV Powertrain Motor 120",
        "type": "TractionMotor",
        "rating_kw": 120,
        "description": "Compact traction motor for electric vehicle powertrain",
    },
    "DOS-2024-004": {
        "motor_id": "IND-CRANE-10",
        "name": "Industrial Crane Motor 10",
        "type": "InductionMotor",
        "rating_kw": 75,
        "description": "Heavy-lift gantry crane drive motor for industrial integration",
    },
    "DOS-2024-005": {
        "motor_id": "TX-PUMP-22",
        "name": "Transmission Pump Motor 22",
        "type": "SubmergedPumpMotor",
        "rating_kw": 22,
        "description": "Submersible pump motor for municipal water works",
    },
}

# All requirement IDs defined in sdd_schema_migration.cypher
ALL_REQUIREMENT_IDS = [
    "REQ-01", "REQ-02", "REQ-03", "REQ-04",
    "REQ-05", "REQ-06", "REQ-07", "REQ-V1",
]

# Evidence category codes (A1–H1, MoSSEC pipeline)
EVIDENCE_CODES = [
    ("A1", "Verification"),
    ("B1", "Validation"),
    ("C1", "Uncertainty Quantification"),
    ("D1", "Code Verification"),
    ("E1", "Solution Verification"),
    ("F1", "Model Calibration"),
    ("G1", "Prediction Assessment"),
    ("H1", "Adequacy Assessment"),
]

# Artifacts template — each dossier gets its own cloned set
ARTIFACT_TEMPLATES = [
    {"code": "A1", "type": "Report",       "req": "REQ-01", "name_suffix": "Electromagnetic Performance"},
    {"code": "A2", "type": "Report",       "req": "REQ-02", "name_suffix": "Transient Start Simulation"},
    {"code": "B1", "type": "Report",       "req": "REQ-03", "name_suffix": "Loss Segregation"},
    {"code": "C1", "type": "Report",       "req": "REQ-04", "name_suffix": "Cooling CFD Evidence"},
    {"code": "D1", "type": "Report",       "req": "REQ-05", "name_suffix": "Modal & Harmonic Analysis"},
    {"code": "E1", "type": "Certification","req": "REQ-06", "name_suffix": "Insulation Certification"},
    {"code": "F1", "type": "CSV",          "req": "REQ-07", "name_suffix": "Efficiency Test Data"},
    {"code": "G1", "type": "Certification","req": "REQ-V1", "name_suffix": "Type Test Certificate"},
    {"code": "H1", "type": "Report",       "req": None,     "name_suffix": "Final Credibility Evidence"},
]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

class Linker:
    def __init__(self, driver, database: str, dry_run: bool = False):
        self.driver = driver
        self.database = database
        self.dry_run = dry_run
        self.stats: dict = {k: 0 for k in [
            "uid_set", "parts_created", "dossier_part_links",
            "dossier_req_links", "artifacts_created", "artifact_dossier_links",
            "artifact_req_links", "sim_runs_created",
            "validation_cases_created", "study_links", "ontology_links",
        ]}

    def run(self, q: str, params: dict | None = None) -> list:
        if self.dry_run:
            logger.debug(f"[DRY-RUN] {q[:100]}")
            return []
        with self.driver.session(database=self.database) as s:
            result = s.run(q, params or {})
            return [r.data() for r in result]

    # ------------------------------------------------------------------
    # 1. Add uid property to all SDD nodes
    # ------------------------------------------------------------------
    def set_uid_properties(self):
        logger.info("Step 1: Setting uid property on SDD nodes...")
        for label in ["SimulationDossier", "SimulationArtifact", "EvidenceCategory",
                      "SimulationRun", "ValidationCase", "ComplianceAudit", "DecisionLog"]:
            res = self.run(f"""
                MATCH (n:{label})
                WHERE n.uid IS NULL
                SET n.uid = COALESCE(n.id, elementId(n))
                RETURN count(n) AS cnt
            """)
            cnt = res[0]["cnt"] if res else 0
            self.stats["uid_set"] += cnt
            if cnt:
                logger.info(f"  {label}: set uid on {cnt} nodes")

    # ------------------------------------------------------------------
    # 2. Create motor Part nodes and link to dossiers
    # ------------------------------------------------------------------
    def create_motor_parts(self):
        logger.info("Step 2: Creating motor Part nodes and VALIDATES_PART links...")
        for dos_id, m in MOTOR_PARTS.items():
            res = self.run("""
                MATCH (d:SimulationDossier {id: $dos_id})
                MERGE (p:Part {id: $motor_id})
                ON CREATE SET
                    p.name        = $name,
                    p.uid         = $motor_id,
                    p.part_type   = $type,
                    p.rating_kw   = $rating_kw,
                    p.description = $description,
                    p.ap_level    = 'AP243',
                    p.created_at  = datetime()
                ON MATCH SET
                    p.name        = $name,
                    p.uid         = $motor_id,
                    p.description = $description
                MERGE (d)-[r:VALIDATES_PART]->(p)
                ON CREATE SET r.created_at = datetime()
                RETURN p.id AS part_id, r IS NOT NULL AS linked
            """, {
                "dos_id": dos_id,
                "motor_id": m["motor_id"],
                "name": m["name"],
                "type": m["type"],
                "rating_kw": m["rating_kw"],
                "description": m["description"],
            })
            if res:
                self.stats["parts_created"] += 1
                self.stats["dossier_part_links"] += 1
                logger.info(f"  {dos_id} -> VALIDATES_PART -> {m['motor_id']}")

    # ------------------------------------------------------------------
    # 3. Link each dossier directly to all Requirements
    # ------------------------------------------------------------------
    def link_dossiers_to_requirements(self):
        logger.info("Step 3: Linking dossiers to Requirements via VALIDATES_REQUIREMENT...")
        for req_id in ALL_REQUIREMENT_IDS:
            res = self.run("""
                MATCH (d:SimulationDossier)
                MATCH (r:Requirement {id: $req_id})
                MERGE (d)-[lnk:VALIDATES_REQUIREMENT]->(r)
                ON CREATE SET lnk.created_at = datetime(), lnk.source = 'sdd_linker'
                RETURN count(lnk) AS cnt
            """, {"req_id": req_id})
            cnt = res[0]["cnt"] if res else 0
            self.stats["dossier_req_links"] += cnt
        logger.info(f"  Created {self.stats['dossier_req_links']} dossier-requirement links")

    # ------------------------------------------------------------------
    # 4. Distribute artifacts to all 5 dossiers
    # ------------------------------------------------------------------
    def distribute_artifacts(self):
        logger.info("Step 4: Creating & distributing artifacts to all dossiers...")
        for dos_id in MOTOR_PARTS.keys():
            for tmpl in ARTIFACT_TEMPLATES:
                art_id = f"{dos_id}_{tmpl['code']}"
                params: dict = {
                    "art_id": art_id,
                    "dos_id": dos_id,
                    "name": f"Artifact {tmpl['code']} – {tmpl['name_suffix']}",
                    "code": tmpl["code"],
                    "a_type": tmpl["type"],
                    "req_id": tmpl.get("req"),
                    "ap_level": "AP243",
                }
                res = self.run("""
                    MATCH (d:SimulationDossier {id: $dos_id})
                    MERGE (a:SimulationArtifact {id: $art_id})
                    ON CREATE SET
                        a.name     = $name,
                        a.uid      = $art_id,
                        a.code     = $code,
                        a.type     = $a_type,
                        a.status   = 'Validated',
                        a.ap_level = $ap_level,
                        a.created_at = datetime()
                    ON MATCH SET
                        a.uid = $art_id
                    MERGE (d)-[:CONTAINS_ARTIFACT]->(a)
                    RETURN a.id AS art_id
                """, params)
                if res:
                    self.stats["artifacts_created"] += 1

                if tmpl.get("req"):
                    link_res = self.run("""
                        MATCH (a:SimulationArtifact {id: $art_id})
                        MATCH (r:Requirement {id: $req_id})
                        MERGE (a)-[lnk:LINKED_TO_REQUIREMENT]->(r)
                        ON CREATE SET lnk.created_at = datetime()
                        RETURN count(lnk) AS c
                    """, {"art_id": art_id, "req_id": tmpl["req"]})
                    self.stats["artifact_req_links"] += (link_res[0]["c"] if link_res else 0)

        logger.info(f"  Created/updated {self.stats['artifacts_created']} artifacts")
        logger.info(f"  Created {self.stats['artifact_req_links']} artifact→requirement links")

    # ------------------------------------------------------------------
    # 5. Create SimulationRun per dossier
    # ------------------------------------------------------------------
    def create_simulation_runs(self):
        logger.info("Step 5: Creating SimulationRun nodes...")
        solver_map = {
            "DOS-2024-001": ("FEA-MAXWELL-2D", "ANSYS Maxwell 2D"),
            "DOS-2024-002": ("FEA-MAXWELL-3D", "ANSYS Maxwell 3D"),
            "DOS-2024-003": ("MOTOR-CAD-TRACTION", "Motor-CAD Traction"),
            "DOS-2024-004": ("FEA-CRANE-STRUCT", "ANSYS Structural FEA"),
            "DOS-2024-005": ("CFD-PUMP-FLUENT", "ANSYS Fluent CFD"),
        }
        for dos_id, (run_id, solver) in solver_map.items():
            # Create the SimulationRun and link to dossier
            res = self.run("""
                MATCH (d:SimulationDossier {id: $dos_id})
                MERGE (run:SimulationRun {id: $run_id})
                ON CREATE SET
                    run.uid        = $run_id,
                    run.name       = $solver + ' Run for ' + $dos_id,
                    run.solver     = $solver,
                    run.status     = 'Completed',
                    run.timestamp  = datetime(),
                    run.ap_level   = 'AP243',
                    run.created_at = datetime()
                MERGE (d)-[r:HAS_SIMULATION_RUN]->(run)
                ON CREATE SET r.created_at = datetime()
                RETURN run.id AS rid
            """, {"dos_id": dos_id, "run_id": run_id, "solver": solver})
            # Link SimulationRun to Part separately
            self.run("""
                MATCH (run:SimulationRun {id: $run_id})
                MATCH (d:SimulationDossier {id: $dos_id})-[:VALIDATES_PART]->(p:Part)
                MERGE (run)-[r:SIMULATES_PART]->(p)
                ON CREATE SET r.created_at = datetime()
                RETURN count(r) AS cnt
            """, {"run_id": run_id, "dos_id": dos_id})
            if res:
                self.stats["sim_runs_created"] += 1
        logger.info(f"  Created {self.stats['sim_runs_created']} SimulationRun nodes")

    # ------------------------------------------------------------------
    # 6. Create ValidationCase per dossier
    # ------------------------------------------------------------------
    def create_validation_cases(self):
        logger.info("Step 6: Creating ValidationCase nodes...")
        for dos_id, m in MOTOR_PARTS.items():
            vc_id = f"VC-{dos_id}"
            res = self.run("""
                MATCH (d:SimulationDossier {id: $dos_id})
                MERGE (vc:ValidationCase {id: $vc_id})
                ON CREATE SET
                    vc.uid        = $vc_id,
                    vc.name       = 'Validation Case: ' + $dos_id,
                    vc.status     = d.status,
                    vc.motor_id   = $motor_id,
                    vc.ap_level   = 'AP243',
                    vc.created_at = datetime()
                MERGE (d)-[r:HAS_VALIDATION_CASE]->(vc)
                ON CREATE SET r.created_at = datetime()
                RETURN vc.id AS vid
            """, {"dos_id": dos_id, "vc_id": vc_id, "motor_id": m["motor_id"]})
            if res:
                self.stats["validation_cases_created"] += 1
        logger.info(f"  Created {self.stats['validation_cases_created']} ValidationCase nodes")

    # ------------------------------------------------------------------
    # 7. Link dossiers to existing Study / Analysis nodes
    # ------------------------------------------------------------------
    def link_to_studies(self):
        logger.info("Step 7: Linking dossiers to Study/Analysis nodes in graph...")
        res = self.run("""
            MATCH (s) WHERE 'Study' IN labels(s) OR 'Analysis' IN labels(s)
            RETURN s.id AS id, s.name AS name, labels(s) AS lbls LIMIT 10
        """)
        if not res:
            logger.info("  No Study/Analysis nodes found — skipping")
            return
        for row in res:
            lbl = row["lbls"][0] if row["lbls"] else "Study"
            logger.info(f"  Found {lbl}: {row['id']} — {row['name']}")

        # Link all dossiers to all study/analysis nodes as RELATED_TO
        link_res = self.run("""
            MATCH (d:SimulationDossier)
            MATCH (s) WHERE 'Study' IN labels(s) OR 'Analysis' IN labels(s)
            MERGE (d)-[r:RELATED_TO_STUDY]->(s)
            ON CREATE SET r.created_at = datetime()
            RETURN count(r) AS cnt
        """)
        cnt = link_res[0]["cnt"] if link_res else 0
        self.stats["study_links"] = cnt
        logger.info(f"  Created {cnt} dossier→Study/Analysis links")

    # ------------------------------------------------------------------
    # 8. Link dossiers to relevant ontology class nodes
    # ------------------------------------------------------------------
    def link_to_ontology(self):
        logger.info("Step 8: Linking dossiers to ontology concept nodes...")
        # Find OWLClass / OntologyClass / ExternalOwlClass nodes matching simulation/validation/AP243
        res = self.run("""
            MATCH (oc)
            WHERE (
                'OWLClass' IN labels(oc) OR
                'OntologyClass' IN labels(oc) OR
                'ExternalOwlClass' IN labels(oc) OR
                'DomainConcept' IN labels(oc)
            )
            AND (
                toLower(COALESCE(oc.name, oc.label, '')) CONTAINS 'simulation' OR
                toLower(COALESCE(oc.name, oc.label, '')) CONTAINS 'validation' OR
                toLower(COALESCE(oc.name, oc.label, '')) CONTAINS 'analysis' OR
                toLower(COALESCE(oc.name, oc.label, '')) CONTAINS 'dossier' OR
                toLower(COALESCE(oc.name, oc.label, '')) CONTAINS 'digital' OR
                toLower(COALESCE(oc.name, oc.label, '')) CONTAINS 'test'
            )
            RETURN oc.id AS id, COALESCE(oc.name, oc.label) AS name, labels(oc) AS lbls
            LIMIT 20
        """)

        if not res:
            logger.info("  No matching ontology nodes found — skipping")
            return

        for row in res:
            logger.info(f"  Ontology match: {row['name']} [{row['lbls']}]")

        link_res = self.run("""
            MATCH (d:SimulationDossier)
            MATCH (oc)
            WHERE (
                'OWLClass' IN labels(oc) OR
                'OntologyClass' IN labels(oc) OR
                'ExternalOwlClass' IN labels(oc) OR
                'DomainConcept' IN labels(oc)
            )
            AND (
                toLower(COALESCE(oc.name, oc.label, '')) CONTAINS 'simulation' OR
                toLower(COALESCE(oc.name, oc.label, '')) CONTAINS 'validation' OR
                toLower(COALESCE(oc.name, oc.label, '')) CONTAINS 'analysis' OR
                toLower(COALESCE(oc.name, oc.label, '')) CONTAINS 'digital'
            )
            MERGE (d)-[r:INSTANCE_OF_CONCEPT]->(oc)
            ON CREATE SET r.created_at = datetime()
            RETURN count(r) AS cnt
        """)
        cnt = link_res[0]["cnt"] if link_res else 0
        self.stats["ontology_links"] = cnt
        logger.info(f"  Created {cnt} dossier→ontology concept links")

    # ------------------------------------------------------------------
    # 9. Ensure all SimulationDossier nodes have a `name` property
    #    (the current `project_name` field is what the front-end shows)
    # ------------------------------------------------------------------
    def ensure_name_property(self):
        logger.info("Step 9: Ensuring `name` property on all SDD nodes...")
        res = self.run("""
            MATCH (d:SimulationDossier)
            WHERE d.name IS NULL
            SET d.name = d.project_name
            RETURN count(d) AS cnt
        """)
        cnt = res[0]["cnt"] if res else 0
        if cnt:
            logger.info(f"  Back-filled name for {cnt} dossiers from project_name")

        # Also ensure EvidenceCategory has readable name
        self.run("""
            MATCH (e:EvidenceCategory)
            WHERE e.name IS NULL
            SET e.name = COALESCE(e.label, e.type, e.id)
            RETURN count(e) AS cnt
        """)

    # ------------------------------------------------------------------
    # Main
    # ------------------------------------------------------------------
    def run_all(self):
        self.set_uid_properties()
        self.create_motor_parts()
        self.link_dossiers_to_requirements()
        self.distribute_artifacts()
        self.create_simulation_runs()
        self.create_validation_cases()
        self.link_to_studies()
        self.link_to_ontology()
        self.ensure_name_property()

        logger.info("\n" + "=" * 60)
        logger.info("LINKING SUMMARY")
        logger.info("=" * 60)
        for k, v in self.stats.items():
            logger.info(f"  {k:<30}: {v}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Link SDD nodes into the ontology graph")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    args = parser.parse_args()

    uri      = os.getenv("NEO4J_URI")
    user     = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")
    database = os.getenv("NEO4J_DATABASE", "neo4j")

    if not all([uri, user, password]):
        logger.error("NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD must be set in .env")
        sys.exit(1)

    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        linker = Linker(driver, database, dry_run=args.dry_run)
        linker.run_all()
    finally:
        driver.close()

    logger.success("Done.")


if __name__ == "__main__":
    main()
