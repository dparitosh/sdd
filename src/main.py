"""
MBSE Neo4j Knowledge Graph Builder
Main application entry point
"""

from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

from graph.connection import Neo4jConnection
from parsers.semantic_loader import SemanticXMILoader
from utils.config import Config
from utils.logger import setup_logger


def main():
    """Main application entry point"""
    # Load environment variables
    load_dotenv()

    # Setup logging
    setup_logger()
    logger.info("Starting MBSE Neo4j Knowledge Graph Builder")

    # Load configuration
    config = Config()

    try:
        # Test Neo4j connection
        logger.info(f"Connecting to Neo4j at {config.neo4j_uri}")
        with Neo4jConnection(
            uri=config.neo4j_uri, user=config.neo4j_user, password=config.neo4j_password
        ) as conn:
            # Verify connection
            if conn.verify_connection():
                logger.info("✓ Successfully connected to Neo4j")

                # Initialize Semantic loader
                loader = SemanticXMILoader(conn)

                # Check for XMI files in smrlv12/data/domain_models/mossec first
                mossec_dir = Path("smrlv12/data/domain_models/mossec")
                if mossec_dir.exists():
                    xmi_files = list(mossec_dir.glob("*.xmi"))
                    if xmi_files:
                        logger.info(f"Found {len(xmi_files)} XMI file(s) in {mossec_dir}")
                        for xmi_file in xmi_files:
                            logger.info(f"Loading: {xmi_file}")
                            stats = loader.load_xmi_file(xmi_file)
                            logger.success(f"✓ Loaded {xmi_file.name}: {stats}")
                        logger.success("Processing complete!")
                        sys.exit(0)

                # Fallback to data/raw directory
                data_dir = Path(config.data_dir) / "raw"
                xmi_files = list(data_dir.glob("*.xmi"))

                if not xmi_files:
                    logger.warning(f"No XMI files found")
                    logger.info(
                        "Place XMI files in data/raw/ or smrlv12/data/domain_models/mossec/"
                    )
                else:
                    logger.info(f"Found {len(xmi_files)} XMI file(s) to process")

                    for xmi_file in xmi_files:
                        logger.info(f"Loading: {xmi_file}")
                        stats = loader.load_xmi_file(xmi_file)
                        logger.success(f"✓ Loaded {xmi_file.name}: {stats}")

                logger.success("Processing complete!")
            else:
                logger.error("Failed to connect to Neo4j")
                sys.exit(1)

    except Exception as e:
        logger.exception(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
