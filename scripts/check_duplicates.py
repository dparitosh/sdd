#!/usr/bin/env python3
"""
MBSE Knowledge Graph - Duplicate Check Script
Purpose: Check for duplicate nodes and relationships in the graph
Usage: python scripts/check_duplicates.py
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


def check_duplicates():
    """Check for duplicate nodes and relationships in the database."""
    load_dotenv()
    config = Config()

    print("\n=== Database Duplication Check ===\n")

    try:
        with Neo4jConnection(
            config.neo4j_uri, config.neo4j_user, config.neo4j_password
        ) as conn:
            conn.connect()

            # 1. Check for duplicate nodes based on id
            print("Checking for duplicate nodes by 'id' field...")
            query_dup_nodes = """
            MATCH (n)
            WHERE n.id IS NOT NULL
            WITH n.id as id, count(n) as c, collect(labels(n)) as lbls
            WHERE c > 1
            RETURN id, c, lbls
            LIMIT 10
            """
            dup_nodes = conn.execute_query(query_dup_nodes)

            if dup_nodes:
                print("❌ FOUND DUPLICATE NODES by id:")
                for d in dup_nodes:
                    print(f"   ID: {d['id']} | Count: {d['c']} | Labels: {d['lbls']}")
            else:
                print("✅ No duplicate nodes found based on id.")

            # 2. Check for duplicate relationships
            print("\nChecking for duplicate relationships...")
            query_dup_rels = """
            MATCH (a)-[r]->(b)
            WITH a, b, type(r) as t, count(r) as c
            WHERE c > 1
            RETURN labels(a)[0] as Source, labels(b)[0] as Target, t as Type, c as Count
            LIMIT 10
            """
            dup_rels = conn.execute_query(query_dup_rels)

            if dup_rels:
                print("❌ FOUND DUPLICATE RELATIONSHIPS:")
                for d in dup_rels:
                    print(
                        f"   {d['Source']} -[{d['Type']}]-> {d['Target']} : {d['Count']} times"
                    )
            else:
                print("✅ No duplicate relationships found.")

            # 3. Check for nodes with same Name and Label
            print("\nChecking for logical duplicates (Same Label + Name)...")
            query_logical_dup = """
            MATCH (n)
            WHERE n.name IS NOT NULL AND n.name <> ''
            WITH labels(n) as lbl, n.name as name, count(n) as c
            WHERE c > 1
            RETURN lbl, name, c
            ORDER BY c DESC
            LIMIT 5
            """
            logical_dups = conn.execute_query(query_logical_dup)

            if logical_dups:
                print(
                    "ℹ️  Found nodes with shared names (may be valid if in different packages):"
                )
                for d in logical_dups:
                    print(f"   {d['lbl']} '{d['name']}': {d['c']} occurrences")

                # Deep dive into the first one
                first_name = logical_dups[0]["name"]
                print(f"\n   Inspecting context for '{first_name}':")
                query_context = """
                MATCH (p)-[:CONTAINS]->(n)
                WHERE n.name = $name
                RETURN n.id as ID, labels(p)[0] as ParentType, p.name as ParentName
                """
                ctx = conn.execute_query(query_context, {"name": first_name})
                for c in ctx:
                    print(
                        f"     - ID: {c['ID']} | Parent: {c['ParentType']} '{c['ParentName']}'"
                    )
            else:
                print("✅ No name collisions found.")

            print("\n[OK] Duplication check complete!")

    except Exception as e:
        print(f"[ERROR] Check failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    check_duplicates()
