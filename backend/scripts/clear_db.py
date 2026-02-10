#!/usr/bin/env python3
"""Clear the Neo4j database.

This script is intentionally guarded to prevent accidental destructive runs.
Use `--yes` to confirm.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv


def main() -> int:
    parser = argparse.ArgumentParser(description="Clear ALL nodes and relationships from Neo4j")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5000,
        help="Deletion batch size (default: 5000)",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm you want to delete ALL nodes and relationships",
    )
    args = parser.parse_args()

    if not args.yes:
        print("Refusing to clear database without --yes (safety guard).")
        return 2

    load_dotenv()

    from backend.src.graph.connection import Neo4jConnection
    from backend.src.utils.config import Config

    config = Config()
    conn = Neo4jConnection(
        uri=config.neo4j_uri, user=config.neo4j_user, password=config.neo4j_password
    )
    conn.connect()

    try:
        batch_size = max(1, int(args.batch_size))

        print("=== CLEARING ALL NODES ===")
        deleted_total = 0
        while True:
            result = conn.execute_query(
                "MATCH (n) WITH n LIMIT $limit DETACH DELETE n RETURN count(n) as deleted",
                {"limit": batch_size},
            )
            deleted = result[0]["deleted"] if result else 0
            deleted_total += deleted
            print(f"  Deleted batch: {deleted}")
            if deleted == 0:
                break

        print(f"Total deleted: {deleted_total}")

        remaining = conn.execute_query("MATCH (n) RETURN count(n) as count")
        print(f"Remaining nodes: {remaining[0]['count'] if remaining else 'unknown'}")
        print("Database cleared!")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
