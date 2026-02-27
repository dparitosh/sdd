#!/usr/bin/env python3
"""Check knowledge graph status (verify what's been ingested).

Safe to run with `--help` without attempting Neo4j connections.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Knowledge Graph status")
    parser.add_argument("--top", type=int, default=20, help="Top labels to show")
    parser.add_argument("--sample", type=int, default=10, help="Sample rows to show")
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
        print("=" * 60)
        print("KNOWLEDGE GRAPH STATUS")
        print("=" * 60)
        print()

        total = conn.execute_query("MATCH (n) RETURN count(n) as count")
        rels = conn.execute_query("MATCH ()-[r]->() RETURN count(r) as count")
        print(f"Total Nodes: {total[0]['count']}")
        print(f"Total Relationships: {rels[0]['count']}")
        print()

        xmi = conn.execute_query("MATCH (n:XMIElement) RETURN count(n) as count")
        print(f"XMI Elements: {xmi[0]['count']}")

        xsd = conn.execute_query("MATCH (n:XSDElement) RETURN count(n) as count")
        print(f"XSD Elements: {xsd[0]['count']}")
        print()

        print("=== NODES BY LABEL ===")
        labels = conn.execute_query(
            """
            MATCH (n)
            UNWIND labels(n) AS label
            RETURN label, count(*) as count
            ORDER BY count DESC
            LIMIT $top
            """,
            {"top": max(0, int(args.top))},
        )
        for r in labels:
            print(f"  {r['label']}: {r['count']}")

        print()
        print("=== SAMPLE XMI DATA ===")
        samples = conn.execute_query(
            """
            MATCH (n:XMIElement)
            WHERE n.name <> ''
            RETURN labels(n) as labels, n.name as name
            LIMIT $sample
            """,
            {"sample": max(0, int(args.sample))},
        )
        for s in samples:
            lbl = (
                [l for l in s["labels"] if l != "XMIElement"][0]
                if len(s["labels"]) > 1
                else s["labels"][0]
            )
            print(f"  [{lbl}] {s['name']}")

        print()
        print("=== SAMPLE XSD DATA ===")
        samples = conn.execute_query(
            """
            MATCH (n:XSDElement)
            WHERE n.name <> ''
            RETURN labels(n) as labels, n.name as name
            LIMIT $sample
            """,
            {"sample": max(0, int(args.sample))},
        )
        for s in samples:
            lbl = (
                [l for l in s["labels"] if l != "XSDElement"][0]
                if len(s["labels"]) > 1
                else s["labels"][0]
            )
            print(f"  [{lbl}] {s['name']}")

        print()
        print("=" * 60)
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
