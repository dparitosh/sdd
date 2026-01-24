"""Reload database with enhanced Association properties"""

import os
import sys

# Add backend directory to path so we can import src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from loguru import logger

from dotenv import load_dotenv
from src.graph.connection import Neo4jConnection
from src.parsers.semantic_loader import SemanticXMILoader
from src.utils.config import Config


def main():
    load_dotenv()
    logger.info("🔄 Reloading database with enhanced Association properties...")

    # Load config
    config = Config()

    # Connect to Neo4j
    with Neo4jConnection(config.neo4j_uri, config.neo4j_user, config.neo4j_password) as conn:
        conn.connect()

        # Clear existing data
        logger.info("Clearing existing data...")
        conn.execute_query("MATCH (n) DETACH DELETE n")
        logger.info("Database cleared.")

        # Load with enhanced semantic loader
        loader = SemanticXMILoader(conn, enable_versioning=True)
        xmi_file = "data/raw/Domain_model.xmi"

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


if __name__ == "__main__":
    main()
