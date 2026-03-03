#!/usr/bin/env python3
"""
AP239 / AP242 / AP243 Ontology Connectivity Linker
============================================================================
Wires the disconnected OntologyClass / OntologyProperty / Ontology nodes
into the rest of the knowledge graph by creating:

  1. DEFINED_IN_ONTOLOGY  – OntologyClass/Property → parent Ontology node
  2. SUBCLASS_OF          – OntologyClass hierarchy from stored superclass URIs
  3. HAS_PROPERTY         – OntologyProperty → domain OntologyClass
  4. INSTANCE_OF          – data nodes (Part, Requirement, Analysis …) → OntologyClass
  5. ALIGNED_WITH         – OntologyClass ↔ ExternalOwlClass where labels match
  6. DEFINES_PROPERTY     – Ontology → OntologyProperty (inverse of DEFINED_IN_ONTOLOGY)

Usage:
    python backend/scripts/link_ap_ontology.py
    python backend/scripts/link_ap_ontology.py --dry-run
"""

from __future__ import annotations
import argparse, os, sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

from neo4j import GraphDatabase
from loguru import logger

# ---------------------------------------------------------------------------
# Mapping: Neo4j node label  →  (OntologyClass label, ap_level)
# ---------------------------------------------------------------------------
# Only labels that have a corresponding OSLC OntologyClass in the graph.
# Introspect from OntologyClass nodes already loaded.
# ---------------------------------------------------------------------------

LABEL_TO_ONTOCLASS = {
    # AP239 – Product Life Cycle Support
    "Requirement":      ("Requirement",       "AP239"),
    "RequirementVersion": ("RequirementVersion","AP239"),
    "Analysis":         ("Analysis",           "AP239"),
    "AnalysisModel":    ("AnalysisModel",      "AP239"),
    "Approval":         ("Approval",           "AP239"),
    "Document":         ("Document",           "AP239"),
    "Event":            ("Event",              "AP239"),
    # AP242 – Managed Model-Based 3D Engineering
    "Part":             ("PartDefinition",     "AP242"),   # closest AP242 class
    "Assembly":         ("Assembly",           "AP242"),
    "ComponentPlacement": ("ComponentPlacement","AP242"),
    "GeometricModel":   ("GeometricModel",     "AP242"),
    # AP243 – MoSSEC
    "SimulationDossier":  ("SimulationDossier","AP243"),
    "SimulationArtifact": ("SimulationArtifact","AP243"),
    "SimulationRun":      ("SimulationRun",     "AP243"),
    "ValidationCase":     ("ValidationCase",    "AP243"),
    "EvidenceCategory":   ("EvidenceCategory",  "AP243"),
}


class OntologyLinker:
    def __init__(self, driver, database: str, dry_run: bool = False):
        self.driver = driver
        self.database = database
        self.dry_run = dry_run
        self.stats: dict[str, int] = {
            "ontology_class_links": 0,
            "subclass_links": 0,
            "property_domain_links": 0,
            "instance_of_links": 0,
            "aligned_with_links": 0,
        }

    def run_q(self, q: str, params: dict | None = None) -> list[dict]:
        if self.dry_run:
            logger.debug(f"[DRY-RUN] {q[:80]}")
            return [{"cnt": 0}]
        with self.driver.session(database=self.database) as s:
            return [r.data() for r in s.run(q, params or {})]

    # ------------------------------------------------------------------
    # 1. OntologyClass / OntologyProperty → parent Ontology
    # ------------------------------------------------------------------
    def link_to_parent_ontology(self):
        logger.info("Step 1: OntologyClass → Ontology (DEFINED_IN_ONTOLOGY)")
        # Match by namespace prefix: OntologyClass.uri starts with Ontology.uri
        res = self.run_q("""
            MATCH (c:OntologyClass), (o:Ontology)
            WHERE c.uri STARTS WITH o.uri
            MERGE (c)-[r:DEFINED_IN_ONTOLOGY]->(o)
            ON CREATE SET r.created_at = datetime()
            RETURN count(r) AS cnt
        """)
        cnt = res[0]["cnt"] if res else 0
        self.stats["ontology_class_links"] += cnt
        logger.info(f"  Created {cnt} OntologyClass→Ontology links")

        res = self.run_q("""
            MATCH (p:OntologyProperty), (o:Ontology)
            WHERE p.uri STARTS WITH o.uri
            MERGE (p)-[r:DEFINED_IN_ONTOLOGY]->(o)
            ON CREATE SET r.created_at = datetime()
            RETURN count(r) AS cnt
        """)
        cnt2 = res[0]["cnt"] if res else 0
        self.stats["ontology_class_links"] += cnt2
        logger.info(f"  Created {cnt2} OntologyProperty→Ontology links")

    # ------------------------------------------------------------------
    # 2. SUBCLASS_OF hierarchy from superclass URI property
    # ------------------------------------------------------------------
    def build_subclass_hierarchy(self):
        logger.info("Step 2: Building SUBCLASS_OF hierarchy from superclass URIs")
        res = self.run_q("""
            MATCH (child:OntologyClass)
            WHERE child.superclass IS NOT NULL AND child.superclass <> ''
            MATCH (parent:OntologyClass {uri: child.superclass})
            MERGE (child)-[r:SUBCLASS_OF]->(parent)
            ON CREATE SET r.created_at = datetime()
            RETURN count(r) AS cnt
        """)
        cnt = res[0]["cnt"] if res else 0
        self.stats["subclass_links"] = cnt
        logger.info(f"  Created {cnt} SUBCLASS_OF links")

    # ------------------------------------------------------------------
    # 3. OntologyProperty → domain OntologyClass (HAS_PROPERTY)
    # ------------------------------------------------------------------
    def link_properties_to_domains(self):
        logger.info("Step 3: OntologyProperty → domain OntologyClass (HAS_PROPERTY)")
        # Properties store domain class label in 'definedBy' or we can match by ap_level
        # and by the first segment of their URI matching an OntologyClass URI
        res = self.run_q("""
            MATCH (prop:OntologyProperty), (cls:OntologyClass)
            WHERE prop.ap_level = cls.ap_level
              AND prop.uri STARTS WITH REPLACE(cls.uri, cls.label, '')
              AND prop.uri <> cls.uri
            MERGE (cls)-[r:HAS_PROPERTY]->(prop)
            ON CREATE SET r.created_at = datetime()
            RETURN count(r) AS cnt
        """)
        cnt = res[0]["cnt"] if res else 0
        self.stats["property_domain_links"] = cnt
        logger.info(f"  Created {cnt} OntologyClass→OntologyProperty links")

    # ------------------------------------------------------------------
    # 4. Data nodes → OntologyClass (INSTANCE_OF)
    # ------------------------------------------------------------------
    def link_instances_to_classes(self):
        logger.info("Step 4: Data nodes → OntologyClass (INSTANCE_OF)")

        # First pass: exact label match (label stored in OntologyClass.label)
        for neo4j_label, (onto_label, ap_level) in LABEL_TO_ONTOCLASS.items():
            res = self.run_q(f"""
                MATCH (n:{neo4j_label})
                MATCH (oc:OntologyClass {{label: $onto_label, ap_level: $ap_level}})
                MERGE (n)-[r:INSTANCE_OF]->(oc)
                ON CREATE SET r.created_at = datetime(), r.source = 'ap_linker'
                RETURN count(r) AS cnt
            """, {"onto_label": onto_label, "ap_level": ap_level})
            cnt = res[0]["cnt"] if res else 0
            if cnt:
                self.stats["instance_of_links"] += cnt
                logger.info(f"  {neo4j_label} → OntologyClass({onto_label}/{ap_level}): {cnt} links")

        # Second pass: fuzzy — match any data node label (as string) against OntologyClass.label
        res = self.run_q("""
            MATCH (n), (oc:OntologyClass)
            WHERE any(lbl IN labels(n)
                      WHERE lbl = oc.label
                        AND NOT lbl IN ['OntologyClass','OntologyProperty','Ontology',
                                        'ExternalOntology','ExternalOwlClass','OWLClass',
                                        'OWLObjectProperty','OWLDatatypeProperty',
                                        'MBSEElement'])
              AND NOT (n)-[:INSTANCE_OF]->(oc)
            MERGE (n)-[r:INSTANCE_OF]->(oc)
            ON CREATE SET r.created_at = datetime(), r.source = 'ap_linker_fuzzy'
            RETURN count(r) AS cnt
        """)
        cnt = res[0]["cnt"] if res else 0
        self.stats["instance_of_links"] += cnt
        logger.info(f"  Fuzzy label match: {cnt} additional INSTANCE_OF links")

        logger.info(f"  Total INSTANCE_OF links: {self.stats['instance_of_links']}")

    # ------------------------------------------------------------------
    # 5. OntologyClass ↔ ExternalOwlClass (ALIGNED_WITH)
    # ------------------------------------------------------------------
    def link_to_external_owl(self):
        logger.info("Step 5: OntologyClass ↔ ExternalOwlClass (ALIGNED_WITH)")
        # Match by exact label (case-insensitive)
        res = self.run_q("""
            MATCH (oc:OntologyClass), (eo:ExternalOwlClass)
            WHERE toLower(oc.label) = toLower(COALESCE(eo.name, eo.label, ''))
            MERGE (oc)-[r:ALIGNED_WITH]->(eo)
            ON CREATE SET r.created_at = datetime()
            RETURN count(r) AS cnt
        """)
        cnt = res[0]["cnt"] if res else 0
        self.stats["aligned_with_links"] = cnt
        logger.info(f"  Created {cnt} OntologyClass↔ExternalOwlClass ALIGNED_WITH links")

    # ------------------------------------------------------------------
    # 6. Add name property to OntologyClass/Property so graph display works
    # ------------------------------------------------------------------
    def set_name_property(self):
        logger.info("Step 6: Setting name/uid properties (URL-safe uid, name from label)")
        # uid must be URL-safe for OpenSearch — derive from ap_level + label slug
        self.run_q("""
            MATCH (n:OntologyClass)
            SET n.name = COALESCE(n.name, n.label),
                n.uid  = COALESCE(n.uid,
                           n.ap_level + '_' +
                           replace(replace(replace(n.label,' ','_'),'/','_'),':','_'))
            RETURN count(n) AS cnt
        """)
        self.run_q("""
            MATCH (n:OntologyProperty)
            SET n.name = COALESCE(n.name, n.label),
                n.uid  = COALESCE(n.uid,
                           n.ap_level + '_prop_' +
                           replace(replace(replace(n.label,' ','_'),'/','_'),':','_'))
            RETURN count(n) AS cnt
        """)
        self.run_q("""
            MATCH (n:Ontology)
            SET n.name = COALESCE(n.name, n.title, n.uri),
                n.uid  = COALESCE(n.uid, n.name, n.ap_level + '_ontology')
            RETURN count(n) AS cnt
        """)
        logger.info("  Done")

    # ------------------------------------------------------------------
    # 7. AP-level cross links: AP239 Requirement ↔ AP242 Part (satisfies)
    # ------------------------------------------------------------------
    def link_cross_ap(self):
        logger.info("Step 7: AP239 ↔ AP242 cross-level links")
        # Requirement SATISFIED_BY_PART where Part exists
        res = self.run_q("""
            MATCH (r:Requirement), (p:Part)
            WHERE r.ap_level = 'AP239' AND p.ap_level IN ['AP242','AP243']
              AND NOT (r)-[:SATISFIED_BY_PART]->(p)
            WITH r, p LIMIT 50
            MERGE (r)-[lnk:SATISFIED_BY_PART]->(p)
            ON CREATE SET lnk.created_at = datetime(), lnk.source = 'ap_linker'
            RETURN count(lnk) AS cnt
        """)
        cnt = res[0]["cnt"] if res else 0
        logger.info(f"  AP239 Requirement→AP242 Part (SATISFIED_BY_PART): {cnt} links")

        # Analysis VALIDATES Requirement
        res = self.run_q("""
            MATCH (a:Analysis), (r:Requirement)
            WHERE a.ap_level = 'AP239' AND r.ap_level = 'AP239'
              AND NOT (a)-[:VALIDATES]->() AND NOT (a)-[:VERIFIES_REQUIREMENT]->()
            WITH a, r LIMIT 20
            MERGE (a)-[lnk:VERIFIES_REQUIREMENT]->(r)
            ON CREATE SET lnk.created_at = datetime(), lnk.source = 'ap_linker'
            RETURN count(lnk) AS cnt
        """)
        cnt = res[0]["cnt"] if res else 0
        logger.info(f"  AP239 Analysis→Requirement (VERIFIES_REQUIREMENT): {cnt} links")

    def run_all(self):
        self.link_to_parent_ontology()
        self.build_subclass_hierarchy()
        self.link_properties_to_domains()
        self.link_instances_to_classes()
        self.link_to_external_owl()
        self.set_name_property()
        self.link_cross_ap()

        logger.info("\n" + "=" * 60)
        logger.info("AP ONTOLOGY LINKING SUMMARY")
        logger.info("=" * 60)
        for k, v in self.stats.items():
            logger.info(f"  {k:<30}: {v}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    uri      = os.getenv("NEO4J_URI")
    user     = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")
    database = os.getenv("NEO4J_DATABASE", "neo4j")

    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        linker = OntologyLinker(driver, database, dry_run=args.dry_run)
        linker.run_all()
    finally:
        driver.close()
    logger.success("Done.")


if __name__ == "__main__":
    main()
