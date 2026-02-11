#!/usr/bin/env python3
"""
MBSE Knowledge Graph - Database Reload Script
Purpose: Clear and reload the Neo4j database from XMI source data
Usage: python scripts/reload_database.py
"""

import os
import sys

# Add backend directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
backend_path = os.path.join(project_root, "backend")
sys.path.insert(0, backend_path)

from loguru import logger
from dotenv import load_dotenv
from src.graph.connection import Neo4jConnection
from src.parsers.semantic_loader import SemanticXMILoader
from src.utils.config import Config


def main():
    """Reload the database with data from XMI file."""
    load_dotenv()
    logger.info("🔄 Reloading database...")

    config = Config()

    # Default XMI file location
    xmi_file = os.path.join(project_root, "data", "raw", "Domain_model.xmi")
    
    if not os.path.exists(xmi_file):
        logger.error(f"❌ XMI file not found: {xmi_file}")
        logger.info("   Run the install script first to copy the sample data.")
        sys.exit(1)

    with Neo4jConnection(
        config.neo4j_uri, config.neo4j_user, config.neo4j_password
    ) as conn:
        conn.connect()

        # Clear existing data
        logger.info("Clearing existing data...")
        conn.execute_query("MATCH (n) DETACH DELETE n")
        logger.info("Database cleared.")

        # Load with enhanced semantic loader
        loader = SemanticXMILoader(conn, enable_versioning=True)

        logger.info(f"Loading {xmi_file}...")
        stats = loader.load_xmi_file(xmi_file)

        logger.info("\n✅ Database reload complete!")
        logger.info(f"Statistics:")
        logger.info(f"  Nodes: {stats['nodes_created']}")
        logger.info(f"  Containment Relationships: {stats['containment_relationships']}")
        logger.info(f"  Semantic Relationships: {stats['semantic_relationships']}")
        logger.info(f"  Type Relationships: {stats['type_relationships']}")
        logger.info(f"  Metadata Attached: {stats['metadata_attached']}")

        total_rels = (
            stats["containment_relationships"]
            + stats["semantic_relationships"]
            + stats["type_relationships"]
        )
        logger.info(f"  Total Relationships: {total_rels}")

        # --- OSLC Seeding ---
        logger.info("\nChecking for OSLC schemas to seed...")
        try:
            # We import specific services here to avoid circular deps or verify path availability
            from src.web.services.ontology_ingest_service import OntologyIngestService, OntologyIngestConfig
            
            # Re-verify backend path relative to this script
            # script_dir = ...scripts/
            # backend_path = ...backend/
            # data/seed/oslc is inside backend/
            oslc_dir = os.path.join(backend_path, "data", "seed", "oslc")
            
            oslc_files = [
                ("oslc-core.ttl", "OSLC-Core"),
                ("oslc-rm.ttl", "OSLC-RM")
            ]
            
            # Since OntologyIngestService uses the global Neo4jService (singleton),
            # we ensure it's initialized or just let it initialize itself from env vars.
            # load_dotenv() was called at start of main.
            
            svc = OntologyIngestService(OntologyIngestConfig())
            
            for fname, oname in oslc_files:
                fpath = os.path.join(oslc_dir, fname)
                if os.path.exists(fpath):
                    logger.info(f"Seeding {oname} from {fname}...")
                    # ingest_file expects a Path object or string
                    stats = svc.ingest_file(fpath, ontology_name=oname)
                    logger.info(f"  Loaded {oname}: {stats.classes_upserted} classes")
                else:
                    logger.warning(f"  Skipping {oname}: File not found at {fpath}")

        except Exception as e:
            logger.error(f"Error validating/seeding OSLC ontologies: {e}")
            logger.info("  (Proceeding, as the main graph load was successful.)")


if __name__ == "__main__":
    main()
