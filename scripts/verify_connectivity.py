#!/usr/bin/env python3
"""
MBSE Knowledge Graph - Database Connectivity Verification
Purpose: Verify Neo4j connection and inspect graph structure
Usage: python scripts/verify_connectivity.py
"""

import os
import sys

# Add backend directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
backend_path = os.path.join(project_root, "backend")
sys.path.insert(0, backend_path)

from src.graph.connection import Neo4jConnection
from src.utils.config import Config
from dotenv import load_dotenv


def verify_connectivity():
    """Verify database connectivity and show graph statistics."""
    load_dotenv()
    config = Config()

    print("\n=== Neo4j Connectivity Check ===")
    print(f"URI: {config.neo4j_uri}")
    print(f"User: {config.neo4j_user}")
    print("")

    try:
        with Neo4jConnection(
            config.neo4j_uri, config.neo4j_user, config.neo4j_password
        ) as conn:
            conn.connect()
            print("[OK] Connected to Neo4j successfully!\n")

            # 1. Count Relationships by Type
            print("=== Relationship Types ===")
            query_types = """
            MATCH ()-[r]->()
            RETURN type(r) as type, count(r) as count
            ORDER BY count DESC
            """
            results_types = conn.execute_query(query_types)
            if results_types:
                for r in results_types:
                    print(f"  {r['type']}: {r['count']}")
            else:
                print("  No relationships found.")

            # 2. Sample Paths (Semantic)
            print("\n=== Sample Semantic Connections (Non-Containment) ===")
            query_paths = """
            MATCH (a)-[r]->(b)
            WHERE type(r) <> 'CONTAINS'
            RETURN labels(a)[0] as SourceLabel, a.name as SourceName, 
                   type(r) as RelType, labels(b)[0] as TargetLabel, b.name as TargetName
            LIMIT 5
            """
            results_paths = conn.execute_query(query_paths)
            if not results_paths:
                print("  No non-containment relationships found.")
            for r in results_paths:
                print(
                    f"  ({r['SourceLabel']} '{r['SourceName']}') "
                    f"-[:{r['RelType']}]-> "
                    f"({r['TargetLabel']} '{r['TargetName']}')"
                )

            # 3. Connectivity Health
            print("\n=== Connectivity Health ===")
            query_islands = "MATCH (n) WHERE NOT (n)--() RETURN count(n) as count"
            islands = conn.execute_query(query_islands)[0]["count"]

            query_dense = """
            MATCH (n)-[r]-()
            RETURN n.name as name, count(r) as degree
            ORDER BY degree DESC
            LIMIT 3
            """
            dense = conn.execute_query(query_dense)

            print(f"  Isolated Nodes: {islands}")
            print("  Most Connected Nodes:")
            for d in dense:
                print(f"    - {d['name']} ({d['degree']} connections)")

            print("\n[OK] Connectivity verification complete!")

    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    verify_connectivity()
