#!/usr/bin/env python3
"""
MBSE Knowledge Graph - Database Reload Script
Purpose: Clear and reload the Neo4j database from XMI source data
Usage:
    python scripts/reload_database.py            # legacy path
    python scripts/reload_database.py --engine    # modular engine pipeline
    python scripts/reload_database.py --engine --store spark  # Spark Connector
"""

import argparse
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


# ---------------------------------------------------------------------------
# New engine-based reload
# ---------------------------------------------------------------------------

def _reload_via_engine(store_type: str = "neo4j") -> None:
    """Run the full reload using the modular IngestionPipeline."""
    from src.engine import IngestionPipeline, Neo4jGraphStore, SparkCypherGraphStore, registry

    # Build the store
    if store_type == "spark":
        logger.info("Using SparkCypherGraphStore (Neo4j Spark Connector)")
        store = SparkCypherGraphStore()
    else:
        logger.info("Using Neo4jGraphStore (bolt)")
        config = Config()
        store = Neo4jGraphStore(
            uri=config.neo4j_uri,
            user=config.neo4j_user,
            password=config.neo4j_password,
        )

    xmi_file = os.path.join(project_root, "data", "raw", "Domain_model.xmi")
    oslc_dir = os.path.join(backend_path, "data", "seed", "oslc")

    if not os.path.exists(xmi_file):
        logger.error(f"❌ XMI file not found: {xmi_file}")
        sys.exit(1)

    pipeline = IngestionPipeline(store=store, registry=registry)
    results = pipeline.run(
        sources={"xmi": xmi_file, "oslc": oslc_dir},
        clear_first=True,
    )

    # Summary
    logger.info("\n✅ Engine pipeline complete!")
    for r in results:
        status = "OK" if r.ok else f"ERRORS: {r.errors}"
        logger.info(f"  [{r.ingester_name}] nodes={r.nodes_created} rels={r.relationships_created} {status}")

    store.close()


# ---------------------------------------------------------------------------
# Legacy reload (unchanged logic)
# ---------------------------------------------------------------------------

def _reload_legacy() -> None:
    """Original reload path (direct Neo4jConnection + SemanticXMILoader)."""
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

        # Step 1: Create uniqueness constraints and indexes BEFORE loading
        logger.info("\n📐 Creating constraints and indexes...")
        loader.create_constraints_and_indexes()

        logger.info(f"Loading {xmi_file}...")
        stats = loader.load_xmi_file(xmi_file)

        logger.info("\n✅ XMI load complete!")
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

        # --- OSLC Seeding (OntologyIngestService for ExternalOntology/ExternalOwlClass) ---
        logger.info("\n🔗 Seeding OSLC ontologies...")
        try:
            from src.web.services.ontology_ingest_service import OntologyIngestService, OntologyIngestConfig

            oslc_dir = os.path.join(backend_path, "data", "seed", "oslc")

            oslc_files = [
                ("oslc-core.ttl", "OSLC-Core"),
                ("oslc-rm.ttl", "OSLC-RM"),
                ("oslc-ap239.ttl", "OSLC-AP239"),
                ("oslc-ap242.ttl", "OSLC-AP242"),
                ("oslc-ap243.ttl", "OSLC-AP243"),
            ]

            svc = OntologyIngestService(OntologyIngestConfig())

            for fname, oname in oslc_files:
                fpath = os.path.join(oslc_dir, fname)
                if os.path.exists(fpath):
                    logger.info(f"Seeding {oname} from {fname}...")
                    stats_oslc = svc.ingest_file(fpath, ontology_name=oname)
                    logger.info(f"  Loaded {oname}: {stats_oslc.classes_upserted} classes")
                else:
                    logger.warning(f"  Skipping {oname}: File not found at {fpath}")

        except Exception as e:
            logger.error(f"Error seeding OSLC ontologies: {e}")
            logger.info("  (Proceeding, as the main graph load was successful.)")

        # --- Also load OSLC seed via load_oslc_seed for OntologyClass/OntologyProperty nodes ---
        logger.info("\n📚 Loading OSLC seed vocabulary (OntologyClass/OntologyProperty)...")
        try:
            seed_dir = os.path.join(backend_path, "data", "seed", "oslc")
            sys.path.insert(0, backend_path)
            from scripts.load_oslc_seed import load_turtle_file, ingest_graph
            from src.web.services import get_neo4j_service
            neo4j_svc = get_neo4j_service()

            for filename in sorted(os.listdir(seed_dir)):
                if not filename.endswith(".ttl"):
                    continue
                filepath = os.path.join(seed_dir, filename)
                g = load_turtle_file(filepath)
                seed_stats = ingest_graph(neo4j_svc, g, source_label=filename)
                logger.info(f"  {filename}: {seed_stats}")
        except Exception as e:
            logger.error(f"Error loading OSLC seed vocabulary: {e}")

        # --- Cross-Schema Linking ---
        logger.info("\n🌐 Creating cross-schema links (XMI ↔ XSD ↔ OSLC)...")
        try:
            cross_links = loader.create_cross_schema_links()
            logger.info(f"  Cross-schema links created: {cross_links}")
        except Exception as e:
            logger.error(f"Error creating cross-schema links: {e}")

        logger.info("\n✅ Full database reload complete!")


def main():
    """Reload the database with data from XMI file."""
    load_dotenv()
    logger.info("🔄 Reloading database...")

    parser = argparse.ArgumentParser(description="MBSE KG Database Reload")
    parser.add_argument(
        "--engine",
        action="store_true",
        help="Use the modular engine pipeline (GraphStore + IngesterRegistry)",
    )
    parser.add_argument(
        "--store",
        choices=["neo4j", "spark"],
        default="neo4j",
        help="Which GraphStore backend to use (default: neo4j)",
    )
    args = parser.parse_args()

    if args.engine:
        _reload_via_engine(store_type=args.store)
    else:
        _reload_legacy()


if __name__ == "__main__":
    main()
