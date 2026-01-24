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

def verify_connectivity():
    load_dotenv()
    config = Config()
    
    with Neo4jConnection(config.neo4j_uri, config.neo4j_user, config.neo4j_password) as conn:
        conn.connect()
        
        # 1. Count Relationships by Type
        print("\n=== Relationship Types ===")
        query_types = """
        MATCH ()-[r]->()
        RETURN type(r) as type, count(r) as count
        ORDER BY count DESC
        """
        results_types = conn.execute_query(query_types)
        for r in results_types:
            print(f"{r['type']}: {r['count']}")
            
        # 2. Sample Paths (Semantic)
        print("\n=== Sample Semantic Connections (Non-Containment) ===")
        # Exclude 'CONTAINS' to show interesting semantic links
        query_paths = """
        MATCH (a)-[r]->(b)
        WHERE type(r) <> 'CONTAINS'
        RETURN labels(a)[0] as SourceLabel, a.name as SourceName, type(r) as RelType, labels(b)[0] as TargetLabel, b.name as TargetName
        LIMIT 5
        """
        results_paths = conn.execute_query(query_paths)
        if not results_paths:
            print("No non-containment relationships found.")
        for r in results_paths:
            print(f"({r['SourceLabel']} '{r['SourceName']}') -[:{r['RelType']}]-> ({r['TargetLabel']} '{r['TargetName']}')")

        # 3. Connectivity Health
        print("\n=== Connectivity Health ===")
        # Check for islands (nodes with no relationships)
        query_islands = "MATCH (n) WHERE NOT (n)--() RETURN count(n) as count"
        islands = conn.execute_query(query_islands)[0]['count']
        
        # Check for densely connected nodes
        query_dense = """
        MATCH (n)-[r]-()
        RETURN n.name as names, count(r) as degree
        ORDER BY degree DESC
        LIMIT 3
        """
        dense = conn.execute_query(query_dense)
        
        print(f"Isolated Nodes: {islands}")
        print("Most Connected Nodes:")
        for d in dense:
             print(f"  - {d['names']} ({d['degree']} connections)")

if __name__ == "__main__":
    verify_connectivity()
