
#!/usr/bin/env python3
"""Check entity property coverage in Neo4j.

Designed to be safe for smoke testing: `--help` must not connect to Neo4j.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Neo4j entity property coverage")
    parser.add_argument(
        "--label",
        help="Optional label to inspect (e.g., ExternalOwlClass). If omitted, checks top labels.",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=20,
        help="How many labels/properties to show (default: 20)",
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
        top = max(1, int(args.top))
        print("=== ENTITY PROPERTY CHECK ===")

        if args.label:
            # Count properties on a given label.
            query = """
            MATCH (n:`%s`)
            WITH n, keys(n) AS k
            UNWIND k AS key
            RETURN key, count(*) AS occurrences
            ORDER BY occurrences DESC, key ASC
            LIMIT $limit
            """ % (args.label.replace("`", ""))
            rows = conn.execute_query(query, {"limit": top})
            if not rows:
                print(f"No nodes found for label: {args.label}")
                return 0
            print(f"Label: {args.label}")
            for r in rows:
                print(f"- {r.get('key')}: {r.get('occurrences')}")
            return 0

        # Show top labels by node count.
        rows = conn.execute_query(
            """
            CALL db.labels() YIELD label
            CALL {
              WITH label
              MATCH (n)
              WHERE label IN labels(n)
              RETURN count(n) AS count
            }
            RETURN label, count
            ORDER BY count DESC, label ASC
            LIMIT $limit
            """,
            {"limit": top},
        )
        for r in rows:
            print(f"- {r.get('label')}: {r.get('count')}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
