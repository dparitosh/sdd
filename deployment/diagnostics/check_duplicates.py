import os
import sys

# Add backend directory to path
# Script is in deployment/diagnostics, so we go up two levels to root, then into backend
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
backend_path = os.path.join(project_root, "backend")
sys.path.insert(0, backend_path)

from src.graph.connection import Neo4jConnection
from src.utils.config import Config
from dotenv import load_dotenv

def check_duplicates():
    load_dotenv()
    config = Config()
    
    with Neo4jConnection(config.neo4j_uri, config.neo4j_user, config.neo4j_password) as conn:
        conn.connect()
        
        print("\n=== Duplication Check ===")
        
        # 1. Check for duplicate nodes based on id
        print(f"Checking for duplicate nodes using field: 'id'")
        query_dup_nodes = f"""
        MATCH (n)
        WHERE n.id IS NOT NULL
        WITH n.id as id, count(n) as c, collect(labels(n)) as lbls
        WHERE c > 1
        RETURN id, c, lbls
        LIMIT 10
        """
        dup_nodes = conn.execute_query(query_dup_nodes)
        
        if dup_nodes:
            print(f"❌ FOUND DUPLICATE NODES by id:")
            for d in dup_nodes:
                print(f"  ID: {d['id']} | Count: {d['c']} | Labels: {d['lbls']}")
        else:
            print(f"✅ No duplicate nodes found based on id.")

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
                print(f"  {d['Source']} -[{d['Type']}]-> {d['Target']} : {d['Count']} times")
        else:
            print("✅ No duplicate relationships found.")
            
        # 3. Check for multiple nodes with same Name and Label (Logical Duplication)
        print("\nChecking for logical duplicates (Same Label + Name)...")
        # Just checking top labels to avoid massive scan
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
             print("ℹ️  Found nodes with shared names (May be valid if in different packages/containers):")
             for d in logical_dups:
                 print(f"  {d['lbl']} '{d['name']}': {d['c']} occurrences")
             
             # Deep dive into the first one
             first_name = logical_dups[0]['name']
             print(f"  -> Inspecting context for '{first_name}':")
             query_context = """
             MATCH (p)-[:CONTAINS]->(n)
             WHERE n.name = $name
             RETURN n.id as ID, labels(p)[0] as ParentType, p.name as ParentName
             """
             ctx = conn.execute_query(query_context, {'name': first_name})
             for c in ctx:
                 print(f"     - ID: {c['ID']} | Parent: {c['ParentType']} '{c['ParentName']}'")

        else:
             print("✅ No name collisions found.")

if __name__ == "__main__":
    check_duplicates()
