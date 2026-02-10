#!/usr/bin/env python3
"""Quick script to check knowledge graph status.

This is intentionally a lightweight CLI and is safe to run with `--help`
without requiring Neo4j connectivity.
"""

from __future__ import annotations

import argparse
import os

from dotenv import load_dotenv
from neo4j import GraphDatabase


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Neo4j knowledge graph status")
    parser.add_argument(
        "--database",
        default=None,
        help="Neo4j database name (defaults to NEO4J_DATABASE or 'neo4j')",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Top relationship types to show",
    )
    args = parser.parse_args()

    load_dotenv()

    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")
    database = args.database or os.getenv("NEO4J_DATABASE", "neo4j")

    if not uri or not user:
        raise SystemExit(
            "Missing Neo4j configuration: NEO4J_URI and NEO4J_USER are required (set in .env or env vars)."
        )

    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        with driver.session(database=database) as session:
            total = session.run("MATCH (n) RETURN count(n) as total").single()["total"]
            print(f"\n=== Knowledge Graph Status (database: {database}) ===")
            print(f"Total nodes: {total}")

            print("\nNode Types:")
            result = session.run(
                "MATCH (n) RETURN DISTINCT labels(n) as labels, count(*) as count ORDER BY count DESC"
            )
            for r in result:
                print(f"  {r['labels']}: {r['count']} nodes")

            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as total").single()[
                "total"
            ]
            print(f"\nTotal relationships: {rel_count}")

            if rel_count > 0:
                print("\nRelationship Types:")
                rels = session.run(
                    "MATCH ()-[r]->() RETURN DISTINCT type(r) as type, count(*) as count "
                    "ORDER BY count DESC LIMIT $top",
                    top=max(0, int(args.top)),
                )
                for r in rels:
                    print(f"  {r['type']}: {r['count']}")
    finally:
        driver.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
