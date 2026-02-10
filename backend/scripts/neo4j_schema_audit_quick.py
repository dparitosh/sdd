#!/usr/bin/env python3
"""Quick Neo4j KG schema audit.

Focus:
- Labels / relationship types counts (summary)
- AP layering via ap_level / ap_schema
- Presence of core domain labels (Requirement/Part/ExternalOwlClass/etc.)
- Cross-level edges where ap_level differs

Reads Neo4j connection info from the same Config used by other scripts.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv


def _print_kv(title: str, rows: list[dict], key_cols: list[str]) -> None:
    print(f"\n=== {title} ===")
    if not rows:
        print("(no rows)")
        return
    for r in rows:
        parts = []
        for k in key_cols:
            parts.append(f"{k}={r.get(k)!r}")
        print("  " + ", ".join(parts))


def main() -> int:
    parser = argparse.ArgumentParser(description="Quick Neo4j KG schema audit")
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Default LIMIT for top-N sections (default: 50)",
    )
    parser.add_argument(
        "--missing-limit",
        type=int,
        default=25,
        help="LIMIT for missing-metadata sections (default: 25)",
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

    print("=" * 72)
    print("NEO4J SCHEMA AUDIT (QUICK)")
    print("=" * 72)

    limit = max(1, int(args.limit))
    missing_limit = max(1, int(args.missing_limit))

    # Totals
    totals = conn.execute_query(
        "MATCH (n) RETURN count(n) AS total_nodes"
    )
    rels = conn.execute_query(
        "MATCH ()-[r]->() RETURN count(r) AS total_relationships"
    )
    print(f"Total nodes: {totals[0]['total_nodes'] if totals else 'N/A'}")
    print(f"Total relationships: {rels[0]['total_relationships'] if rels else 'N/A'}")

    # AP layering distributions
    ap_level_counts = conn.execute_query(
        """
        MATCH (n)
        WHERE n.ap_level IS NOT NULL
        RETURN n.ap_level AS ap_level, count(*) AS count
        ORDER BY ap_level
        """
    )
    _print_kv("Nodes by ap_level", ap_level_counts, ["ap_level", "count"])

    ap_schema_counts = conn.execute_query(
        """
        MATCH (n)
        WHERE n.ap_schema IS NOT NULL
        RETURN n.ap_schema AS ap_schema, count(*) AS count
        ORDER BY count DESC
        LIMIT $limit
        """
        ,
        {"limit": limit},
    )
    _print_kv("Nodes by ap_schema", ap_schema_counts, ["ap_schema", "count"])

    # Missing metadata
    missing_ap_level = conn.execute_query(
        """
        MATCH (n)
        WHERE n.ap_level IS NULL
        UNWIND labels(n) AS label
        RETURN label, count(*) AS count
        ORDER BY count DESC
        LIMIT $limit
        """
        ,
        {"limit": missing_limit},
    )
    _print_kv("Top labels missing ap_level", missing_ap_level, ["label", "count"])

    missing_ap_schema = conn.execute_query(
        """
        MATCH (n)
        WHERE n.ap_level IS NOT NULL AND n.ap_schema IS NULL
        UNWIND labels(n) AS label
        RETURN n.ap_level AS ap_level, label, count(*) AS count
        ORDER BY ap_level, count DESC
        LIMIT $limit
        """
        ,
        {"limit": missing_limit},
    )
    _print_kv("Top labels with ap_level but missing ap_schema", missing_ap_schema, ["ap_level", "label", "count"])

    # Domain label presence checks
    domain_labels = [
        "Requirement",
        "RequirementVersion",
        "Part",
        "PartVersion",
        "Material",
        "MaterialProperty",
        "Assembly",
        "GeometricModel",
        "ExternalOwlClass",
        "ExternalUnit",
        "ValueType",
        "Classification",
        "Analysis",
        "Approval",
        "Document",
        # MoSSEC / SMRL-ish
        "ModelInstance",
        "Study",
        "ActualActivity",
    ]

    domain_counts = []
    for label in domain_labels:
        rows = conn.execute_query(
            f"MATCH (n:{label}) RETURN '{label}' AS label, count(n) AS count"
        )
        if rows:
            domain_counts.append(rows[0])

    # Sort descending by count
    domain_counts = sorted(domain_counts, key=lambda r: r.get("count", 0), reverse=True)
    _print_kv("Selected domain label counts", domain_counts, ["label", "count"])

    # Cross-level relationships
    cross_level = conn.execute_query(
        """
        MATCH (a)-[r]->(b)
        WHERE a.ap_level IS NOT NULL AND b.ap_level IS NOT NULL
          AND a.ap_level <> b.ap_level
        RETURN a.ap_level AS from_level,
               b.ap_level AS to_level,
               type(r) AS rel_type,
               count(*) AS count
        ORDER BY count DESC
        LIMIT $limit
        """
        ,
        {"limit": limit},
    )
    _print_kv("Cross-level relationships (by ap_level)", cross_level, ["from_level", "to_level", "rel_type", "count"])

    # Cross-level by label
    cross_level_labels = conn.execute_query(
        """
        MATCH (a)-[r]->(b)
        WHERE a.ap_level IS NOT NULL AND b.ap_level IS NOT NULL
          AND a.ap_level <> b.ap_level
        RETURN labels(a)[0] AS from_label,
               labels(b)[0] AS to_label,
               type(r) AS rel_type,
               count(*) AS count
        ORDER BY count DESC
        LIMIT $limit
        """
        ,
        {"limit": limit},
    )
    _print_kv("Cross-level relationships (by label)", cross_level_labels, ["from_label", "to_label", "rel_type", "count"])

    # Traceability sample path existence (Requirement -> Part -> ExternalOwlClass)
    traceability_sample = conn.execute_query(
        """
        MATCH (req:Requirement)
        WHERE req.ap_level = 1
        OPTIONAL MATCH (req)-[*1..3]->(part:Part)
        WHERE part.ap_level = 2
        OPTIONAL MATCH (part)-[*1..3]->(owl:ExternalOwlClass)
        WHERE owl.ap_level = 3
        RETURN count(DISTINCT req) AS requirements,
               count(DISTINCT part) AS parts,
               count(DISTINCT owl) AS ontologies
        """
    )
    _print_kv("Traceability path coverage (counts)", traceability_sample, ["requirements", "parts", "ontologies"])

    print("\nDone.")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
