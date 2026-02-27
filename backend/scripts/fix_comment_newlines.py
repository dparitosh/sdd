"""Fix comment properties in Neo4j by replacing ` | ` with newlines.

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
        description="Replace comment delimiters (' | ') with newlines in Neo4j node comment properties"
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=10,
        help="How many sample nodes to display before update (default: 10)",
    )
    parser.add_argument(
        "--verify",
        type=int,
        default=5,
        help="How many updated nodes to display after update (default: 5)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not update, only report counts and samples",
    )
    args = parser.parse_args()

    load_dotenv()

    from backend.src.graph.connection import Neo4jConnection
    from backend.src.utils.config import Config

    config = Config()
    conn = Neo4jConnection(
        uri=config.neo4j_uri, user=config.neo4j_user, password=config.neo4j_password
    )
    conn.connect()
    try:
        sample = max(0, int(args.sample))
        verify = max(0, int(args.verify))

        logger.info("Scanning for nodes with '|' in comment...")

        sample_rows = conn.execute_query(
            """
            MATCH (n)
            WHERE n.comment IS NOT NULL AND n.comment CONTAINS '|'
            RETURN id(n) as node_id, n.comment as original_comment, labels(n) as labels
            LIMIT $limit
            """,
            {"limit": sample},
        )

        logger.info(f"Sample of {len(sample_rows)} nodes with | in comments:")
        for r in sample_rows:
            labels = r.get("labels") or []
            label0 = labels[0] if labels else "(no-label)"
            comment = (r.get("original_comment") or "")
            logger.info(f"  {label0}: {comment[:100]}...")

        count_rows = conn.execute_query(
            """
            MATCH (n)
            WHERE n.comment IS NOT NULL AND n.comment CONTAINS '|'
            RETURN count(n) as total
            """
        )
        total = count_rows[0]["total"] if count_rows else 0
        logger.info(f"Total nodes with | in comments: {total}")

        if args.dry_run:
            logger.info("Dry run enabled; skipping update.")
            return 0

        update_rows = conn.execute_query(
            """
            MATCH (n)
            WHERE n.comment IS NOT NULL AND n.comment CONTAINS '|'
            SET n.comment = replace(n.comment, ' | ', '\n')
            RETURN count(n) as updated
            """
        )
        updated = update_rows[0]["updated"] if update_rows else 0
        logger.success(
            f"Updated {updated} nodes - replaced ' | ' with newlines in comment properties"
        )

        if verify > 0:
            verify_rows = conn.execute_query(
                """
                MATCH (n)
                WHERE n.comment IS NOT NULL AND n.comment CONTAINS '\n'
                RETURN n.name as name, n.comment as comment, labels(n) as labels
                LIMIT $limit
                """,
                {"limit": verify},
            )
            logger.info("Sample of updated comments:")
            for r in verify_rows:
                labels = r.get("labels") or []
                label0 = labels[0] if labels else "(no-label)"
                name = r.get("name")
                comment = (r.get("comment") or "")
                logger.info(f"  {label0} - {name}:")
                logger.info(f"    {comment[:200]}...")

        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
