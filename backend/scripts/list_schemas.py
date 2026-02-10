#!/usr/bin/env python3
"""List known schemas in the Neo4j knowledge graph."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv


def main() -> int:
    parser = argparse.ArgumentParser(description="List Schema nodes in Neo4j")
    parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Max rows to show (default: 200)",
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
        query = """
        MATCH (s:Schema)
        RETURN s.name AS name, s.version AS version, s.source AS source
        ORDER BY name, version
        LIMIT $limit
        """
        rows = conn.execute_query(query, {"limit": max(1, int(args.limit))})

        print("=== SCHEMAS ===")
        for r in rows:
            print(f"- {r.get('name')} {r.get('version')} ({r.get('source')})")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
