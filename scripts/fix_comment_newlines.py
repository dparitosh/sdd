"""Fix comment properties in Neo4j by replacing | with newlines"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from loguru import logger

from graph.connection import Neo4jConnection

# Use the Neo4j Aura connection (same as used in web app)
NEO4J_URI = "neo4j+s://2cccd05b.databases.neo4j.io"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "tcs12345"


def fix_comment_newlines():
    """Replace | with newlines in all comment properties"""

    with Neo4jConnection(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD) as db:
        db.connect()

        # Query to find all nodes with comment properties containing |
        query = """
        MATCH (n)
        WHERE n.comment IS NOT NULL AND n.comment CONTAINS '|'
        RETURN id(n) as node_id, n.comment as original_comment, labels(n) as labels
        LIMIT 10
        """

        with db._driver.session() as session:
            # First, check how many nodes need updating
            result = session.run(query)
            samples = list(result)

            logger.info(f"Sample of {len(samples)} nodes with | in comments:")
            for record in samples:
                logger.info(f"  {record['labels'][0]}: {record['original_comment'][:100]}...")

            # Count all nodes that need updating
            count_query = """
            MATCH (n)
            WHERE n.comment IS NOT NULL AND n.comment CONTAINS '|'
            RETURN count(n) as total
            """
            result = session.run(count_query)
            total = result.single()["total"]
            logger.info(f"Total nodes with | in comments: {total}")

            # Update all comment properties to replace | with newline
            update_query = """
            MATCH (n)
            WHERE n.comment IS NOT NULL AND n.comment CONTAINS '|'
            SET n.comment = replace(n.comment, ' | ', '\n')
            RETURN count(n) as updated
            """

            result = session.run(update_query)
            updated = result.single()["updated"]
            logger.success(
                f"Updated {updated} nodes - replaced | with newlines in comment properties"
            )

            # Verify a few updated records
            verify_query = """
            MATCH (n)
            WHERE n.comment IS NOT NULL AND n.comment CONTAINS '\n'
            RETURN n.name as name, n.comment as comment, labels(n) as labels
            LIMIT 5
            """
            result = session.run(verify_query)
            logger.info("Sample of updated comments:")
            for record in result:
                logger.info(f"  {record['labels'][0]} - {record['name']}:")
                logger.info(f"    {record['comment'][:200]}...")


if __name__ == "__main__":
    logger.info("Starting comment newline fix...")
    fix_comment_newlines()
    logger.info("Fix complete!")
