"""OSLC ↔ STEP Automated Linking.

Creates bidirectional links between:
  - AP242Product (from STEP data)  ↔  Part (MBSE domain)
  - AP242Product (from STEP data)  ↔  Requirement (via Part)
  - AP242AssemblyOccurrence        ↔  Assembly
  - AP242Product                   →  OSLC Resource URI (for OSLC RM/AM exposure)

Also creates OSLC-style resource URIs on AP242 nodes so they can be
discovered via OSLC Service Provider endpoints.

Usage:
    python backend/scripts/oslc_step_linker.py
    python backend/scripts/oslc_step_linker.py --dry-run
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


class OSLCStepLinker:
    """Create OSLC ↔ STEP bidirectional links."""

    def __init__(self, driver, database: str, base_url: str, dry_run: bool = False):
        self.driver = driver
        self.database = database
        self.base_url = base_url.rstrip("/")
        self.dry_run = dry_run
        self.stats: dict[str, int] = {}

    def run_q(self, q: str, params: dict | None = None) -> list[dict]:
        if self.dry_run:
            logger.debug(f"[DRY-RUN] {q[:80]}")
            return [{"cnt": 0}]
        with self.driver.session(database=self.database) as s:
            return [r.data() for r in s.run(q, params or {})]

    def run_all(self):
        self.assign_oslc_uris()
        self.link_products_to_parts()
        self.link_products_to_requirements()
        self.link_assembly_occurrences()
        self.link_shapes_to_geometry()
        self.create_traceability_summary()
        self.print_summary()

    # ──────────────────────────────────────────────────
    # Step 1: Assign OSLC Resource URIs to AP242 nodes
    # ──────────────────────────────────────────────────
    def assign_oslc_uris(self):
        """Assign OSLC-compliant resource URIs to AP242 nodes.
        
        Makes them discoverable via OSLC AM (Architecture Management).
        """
        logger.info("Step 1: Assigning OSLC resource URIs to AP242 nodes")

        # AP242Product → OSLC AM Resource
        result = self.run_q("""
            MATCH (p:AP242Product)
            WHERE p.oslc_uri IS NULL
            SET p.oslc_uri = $base + '/oslc/am/resources/' + 
                replace(replace(p.product_id, ';', '_'), ' ', '_'),
                p.oslc_resource_type = 'http://open-services.net/ns/am#Resource',
                p.oslc_domain = 'http://open-services.net/ns/am#'
            RETURN count(p) AS cnt
        """, {"base": self.base_url})
        cnt = result[0]['cnt'] if result else 0
        self.stats['oslc_uris_products'] = cnt
        logger.info(f"  Assigned OSLC URIs to {cnt} AP242Product nodes")

        # AP242AssemblyOccurrence → OSLC AM Resource
        result = self.run_q("""
            MATCH (ao:AP242AssemblyOccurrence)
            WHERE ao.oslc_uri IS NULL
            SET ao.oslc_uri = $base + '/oslc/am/assemblies/' + 
                replace(replace(ao.name, ' ', '_'), ';', '_') + '_' + toString(ao.step_id),
                ao.oslc_resource_type = 'http://open-services.net/ns/am#Resource',
                ao.oslc_domain = 'http://open-services.net/ns/am#'
            RETURN count(ao) AS cnt
        """, {"base": self.base_url})
        cnt2 = result[0]['cnt'] if result else 0
        self.stats['oslc_uris_assemblies'] = cnt2
        logger.info(f"  Assigned OSLC URIs to {cnt2} AP242AssemblyOccurrence nodes")

    # ──────────────────────────────────────────────────
    # Step 2: Link AP242Product → Part (name similarity)
    # ──────────────────────────────────────────────────
    def link_products_to_parts(self):
        """Link AP242Product nodes to existing Part nodes.
        
        Uses component name matching from the AP242Product.name against:
        - Part name keywords (motor, shaft, bearing, fan, etc.)
        - The Induction Motor part which is the main product
        """
        logger.info("Step 2: Linking AP242Product → Part nodes")

        # All AP242 products are components of the induction motor
        # Link all to the main Part "Induction Motor 250A" via HAS_STEP_DEFINITION
        result = self.run_q("""
            MATCH (p:AP242Product)
            MATCH (part:Part)
            WHERE part.name CONTAINS 'Induction Motor' OR part.name CONTAINS 'Motor'
            WITH p, part
            LIMIT 1
            MATCH (p2:AP242Product)
            MERGE (p2)-[r:HAS_STEP_DEFINITION]->(part)
            ON CREATE SET r.created_at = datetime(), 
                          r.source = 'oslc_step_linker',
                          r.link_type = 'component_of_product'
            RETURN count(r) AS cnt
        """)
        cnt = result[0]['cnt'] if result else 0

        # Also create specific component-level links
        result2 = self.run_q("""
            MATCH (p:AP242Product)
            WHERE p.name CONTAINS 'Motor' OR p.name CONTAINS 'motor'
            MATCH (part:Part)
            WHERE part.name CONTAINS 'Motor'
            MERGE (p)-[r:MAPS_TO_PART]->(part)
            ON CREATE SET r.created_at = datetime(), r.source = 'oslc_step_linker'
            RETURN count(r) AS cnt
        """)
        cnt2 = result2[0]['cnt'] if result2 else 0

        self.stats['product_part_links'] = cnt + cnt2
        logger.info(f"  Created {cnt} HAS_STEP_DEFINITION + {cnt2} MAPS_TO_PART links")

    # ──────────────────────────────────────────────────
    # Step 3: AP242Product → Requirement (via Part chain)
    # ──────────────────────────────────────────────────
    def link_products_to_requirements(self):
        """Create STEP→Requirement traceability.
        
        Creates SATISFIES_REQUIREMENT links from AP242Product to Requirements
        that are already linked to the parent Part nodes.
        """
        logger.info("Step 3: Linking AP242Product → Requirements (via Part)")

        result = self.run_q("""
            MATCH (p:AP242Product)-[:HAS_STEP_DEFINITION]->(part:Part)
            MATCH (req:Requirement)-[:SATISFIED_BY_PART]->(part)
            MERGE (p)-[r:SATISFIES_REQUIREMENT]->(req)
            ON CREATE SET r.created_at = datetime(),
                          r.source = 'oslc_step_linker',
                          r.oslc_rel = 'http://open-services.net/ns/rm#satisfies'
            RETURN count(r) AS cnt
        """)
        cnt = result[0]['cnt'] if result else 0
        self.stats['product_requirement_links'] = cnt
        logger.info(f"  Created {cnt} AP242Product → Requirement links")

    # ──────────────────────────────────────────────────
    # Step 4: AssemblyOccurrence → Assembly
    # ──────────────────────────────────────────────────
    def link_assembly_occurrences(self):
        """Link AP242AssemblyOccurrence nodes to existing Assembly nodes."""
        logger.info("Step 4: Linking AP242AssemblyOccurrence → Assembly")

        result = self.run_q("""
            MATCH (ao:AP242AssemblyOccurrence)
            MATCH (a:Assembly)
            WHERE toLower(ao.name) CONTAINS toLower(a.name) 
               OR toLower(a.name) CONTAINS toLower(ao.name)
            MERGE (ao)-[r:MAPS_TO_ASSEMBLY]->(a)
            ON CREATE SET r.created_at = datetime(), r.source = 'oslc_step_linker'
            RETURN count(r) AS cnt
        """)
        cnt = result[0]['cnt'] if result else 0

        # Also link NAUO names to Part nodes by name similarity
        result2 = self.run_q("""
            MATCH (ao:AP242AssemblyOccurrence)
            MATCH (p:AP242Product)
            WHERE ao.file_uri = p.file_uri 
              AND ao.name CONTAINS split(p.name, ';')[0]
            MERGE (ao)-[r:REPRESENTS_PRODUCT]->(p)
            ON CREATE SET r.created_at = datetime(), r.source = 'oslc_step_linker'
            RETURN count(r) AS cnt
        """)
        cnt2 = result2[0]['cnt'] if result2 else 0

        self.stats['assembly_links'] = cnt
        self.stats['nauo_product_links'] = cnt2
        logger.info(f"  Linked {cnt} AssemblyOccurrence→Assembly, {cnt2} NAUO→Product")

    # ──────────────────────────────────────────────────
    # Step 5: Shape → GeometricModel
    # ──────────────────────────────────────────────────
    def link_shapes_to_geometry(self):
        """Link AP242Shape nodes to existing GeometricModel nodes."""
        logger.info("Step 5: Linking AP242Shape → GeometricModel")

        result = self.run_q("""
            MATCH (sh:AP242Shape)
            MATCH (gm:GeometricModel)
            MERGE (sh)-[r:MAPS_TO_GEOMETRY]->(gm)
            ON CREATE SET r.created_at = datetime(), r.source = 'oslc_step_linker'
            RETURN count(r) AS cnt
        """)
        cnt = result[0]['cnt'] if result else 0
        self.stats['shape_geometry_links'] = cnt
        logger.info(f"  Linked {cnt} AP242Shape → GeometricModel nodes")

    # ──────────────────────────────────────────────────
    # Step 6: Create traceability summary node
    # ──────────────────────────────────────────────────
    def create_traceability_summary(self):
        """Create a summary node capturing the traceability chain.
        
        Requirement → Part → AP242Product → StepFile → StepInstance
        """
        logger.info("Step 6: Creating traceability chain summary")

        # Count full traceability chains
        result = self.run_q("""
            MATCH (req:Requirement)-[:SATISFIED_BY_PART]->(part:Part)
                  <-[:HAS_STEP_DEFINITION]-(prod:AP242Product)
                  -[:DERIVED_FROM]->(si:StepInstance)
                  <-[:CONTAINS]-(f:StepFile)
            RETURN count(DISTINCT req) AS reqs, 
                   count(DISTINCT part) AS parts,
                   count(DISTINCT prod) AS products,
                   count(DISTINCT f) AS files
        """)
        if result:
            r = result[0]
            logger.info(f"  Traceability chain: {r['reqs']} Requirements → "
                       f"{r['parts']} Parts → {r['products']} Products → {r['files']} Files")
            self.stats['traced_requirements'] = r['reqs']
            self.stats['traced_parts'] = r['parts']
            self.stats['traced_products'] = r['products']
            self.stats['traced_files'] = r['files']

    def print_summary(self):
        logger.info("=" * 60)
        logger.info("OSLC ↔ STEP Linking Summary")
        logger.info("=" * 60)
        for k, v in self.stats.items():
            logger.info(f"  {k:40s}: {v}")
        logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="OSLC ↔ STEP Automated Linker")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    uri = os.environ.get('NEO4J_URI', 'neo4j://127.0.0.1:7687')
    user = os.environ.get('NEO4J_USER', 'neo4j')
    pwd = os.environ.get('NEO4J_PASSWORD', 'tcs12345')
    db = os.environ.get('NEO4J_DATABASE', 'mossec')
    base_url = os.environ.get('OSLC_BASE_URL', 'http://localhost:5000/api')

    driver = GraphDatabase.driver(uri, auth=(user, pwd))
    logger.info(f"Connected to {uri}, database={db}")

    linker = OSLCStepLinker(driver, db, base_url, dry_run=args.dry_run)
    linker.run_all()

    driver.close()
    logger.info("Done.")


if __name__ == "__main__":
    main()
