"""Check augmented KG relationships including semantic layer.

Safe for smoke testing: `--help` should not connect to Neo4j.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze relationship and semantic-layer stats in Neo4j"
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="How many rows to show for top lists (default: 10)",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=5,
        help="How many sample cross-links to show (default: 5)",
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
        sample = max(0, int(args.sample))

        print("=" * 60)
        print("AUGMENTED KNOWLEDGE GRAPH - RELATIONSHIP ANALYSIS")
        print("=" * 60)

        result = conn.execute_query(
            """
            MATCH ()-[r]->()
            RETURN type(r) as rel_type, count(*) as count
            ORDER BY count DESC
            """
        )

        print("\n=== ALL RELATIONSHIPS BY TYPE ===")
        for row in result:
            print(f"  {row.get('rel_type')}: {row.get('count'):,}")

        nodes = conn.execute_query("MATCH (n) RETURN count(n) as c")[0]["c"]
        rels = conn.execute_query("MATCH ()-[r]->() RETURN count(r) as c")[0]["c"]
        print(f"\nTOTAL: {nodes:,} nodes, {rels:,} relationships")

        print("\n" + "=" * 60)
        print("SEMANTIC LAYER DETAILS")
        print("=" * 60)

        doc_stats = conn.execute_query(
            """
            MATCH (d:Documentation)
            RETURN d.doc_type as type, count(*) as count
            ORDER BY count DESC
            LIMIT $limit
            """,
            {"limit": top},
        )
        print("\n=== DOCUMENTATION BY TYPE ===")
        for row in doc_stats:
            print(f"  {row.get('type')}: {row.get('count')}")

        concept_stats = conn.execute_query(
            """
            MATCH (c:DomainConcept)
            RETURN c.category as category, count(*) as count
            ORDER BY count DESC
            LIMIT $limit
            """,
            {"limit": top},
        )
        print("\n=== DOMAIN CONCEPTS BY CATEGORY ===")
        for row in concept_stats:
            print(f"  {row.get('category')}: {row.get('count')}")

        top_concepts = conn.execute_query(
            """
            MATCH (c:DomainConcept)
            RETURN c.name as name, c.category as category, c.frequency as freq
            ORDER BY c.frequency DESC
            LIMIT $limit
            """,
            {"limit": top},
        )
        print(f"\n=== TOP {top} DOMAIN CONCEPTS ===")
        for row in top_concepts:
            print(
                f"  {row.get('name')} ({row.get('category')}): {row.get('freq')} refs"
            )

        ext_models = conn.execute_query(
            """
            MATCH (m:ExternalModel)<-[:REFERENCES_EXTERNAL]-(n)
            RETURN m.name as model, count(n) as ref_count
            ORDER BY ref_count DESC
            LIMIT $limit
            """,
            {"limit": top},
        )
        print("\n=== EXTERNAL MODEL REFERENCES ===")
        for row in ext_models:
            print(f"  {row.get('model')}: {row.get('ref_count')} references")

        same_as_rows = conn.execute_query(
            """
            MATCH (xmi:MBSEElement)-[r:SAME_AS]->(xsd)
            RETURN count(r) as count
            """
        )
        same_as = same_as_rows[0]["count"] if same_as_rows else 0
        print(f"\n=== CROSS-SCHEMA LINKS (XMI ↔ XSD) ===")
        print(f"  SAME_AS relationships: {same_as}")

        if sample > 0:
            print("\n  Sample matches:")
            samples = conn.execute_query(
                """
                MATCH (xmi:MBSEElement)-[r:SAME_AS]->(xsd)
                RETURN xmi.name as xmi_name, labels(xsd)[0] as xsd_type, r.matched_name as matched
                LIMIT $limit
                """,
                {"limit": sample},
            )
            for row in samples:
                print(
                    f"    {row.get('xmi_name')} ↔ {row.get('xsd_type')} ({row.get('matched')})"
                )

        print("\n" + "=" * 60)
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
