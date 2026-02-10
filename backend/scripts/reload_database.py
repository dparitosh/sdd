"""Reload database with enhanced Association properties.

This is a DESTRUCTIVE script (clears all nodes) and is intentionally guarded.
Safe for smoke testing: `--help` should not connect to Neo4j.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reload Neo4j database using SemanticXMILoader (DESTRUCTIVE: clears DB)"
    )
    parser.add_argument(
        "--xmi-file",
        default="data/raw/Domain_model.xmi",
        help="Path to XMI file to load (default: data/raw/Domain_model.xmi)",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm deletion of ALL nodes in the target database",
    )
    args = parser.parse_args()

    if not args.yes:
        logger.error("Refusing to reload database without --yes (safety guard).")
        return 2

    load_dotenv()

    from backend.src.graph.connection import Neo4jConnection
    from backend.src.parsers.semantic_loader import SemanticXMILoader
    from backend.src.utils.config import Config

    logger.info("Reloading database with enhanced Association properties...")

    config = Config()
    conn = Neo4jConnection(config.neo4j_uri, config.neo4j_user, config.neo4j_password)
    conn.connect()
    try:
        logger.warning("Clearing existing data (DETACH DELETE all nodes)...")
        conn.execute_query("MATCH (n) DETACH DELETE n")
        logger.info("Database cleared.")

        xmi_file = args.xmi_file
        logger.info(f"Loading XMI: {xmi_file}")

        loader = SemanticXMILoader(conn, enable_versioning=True)
        stats = loader.load_xmi_file(xmi_file)

        logger.success("Database reload complete.")
        logger.info("Statistics:")
        logger.info(f"  Nodes: {stats.get('nodes_created')}")
        logger.info(f"  Containment Relationships: {stats.get('containment_relationships')}")
        logger.info(f"  Semantic Relationships: {stats.get('semantic_relationships')}")
        logger.info(f"  Type Relationships: {stats.get('type_relationships')}")
        logger.info(f"  Metadata Attached: {stats.get('metadata_attached')}")

        total_rels = (
            (stats.get("containment_relationships") or 0)
            + (stats.get("semantic_relationships") or 0)
            + (stats.get("type_relationships") or 0)
        )
        logger.info(f"  Total Relationships: {total_rels}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
