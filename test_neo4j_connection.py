#!/usr/bin/env python3
"""
Test Neo4j Connection - Validates connectivity to Neo4j Aura
"""

import os
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import after loading env
from src.web.services.neo4j_service import Neo4jService

def test_connection():
    """Test Neo4j connection with improved error handling"""
    
    print("=" * 60)
    print("Neo4j Connection Test")
    print("=" * 60)
    
    # Show configuration (hide password)
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")
    database = os.getenv("NEO4J_DATABASE", "neo4j")
    
    print(f"\nConfiguration:")
    print(f"  URI: {uri}")
    print(f"  User: {user}")
    print(f"  Password: {'*' * len(password) if password else 'Not set'}")
    print(f"  Database: {database}")
    print()
    
    try:
        # Create service
        print("Creating Neo4j service...")
        service = Neo4jService()
        
        # Verify connectivity
        print("Verifying connectivity...")
        start = time.time()
        service.verify_connectivity()
        latency = (time.time() - start) * 1000
        
        print(f"✓ Connected successfully in {latency:.2f}ms")
        print()
        
        # Test query
        print("Running test query...")
        start = time.time()
        result = service.execute_query("""
            MATCH (n)
            RETURN count(n) as node_count
            LIMIT 1
        """)
        query_time = (time.time() - start) * 1000
        
        node_count = result[0]["node_count"] if result else 0
        print(f"✓ Query executed in {query_time:.2f}ms")
        print(f"  Total nodes: {node_count:,}")
        print()
        
        # Test database statistics
        print("Fetching database statistics...")
        stats_query = """
            CALL apoc.meta.stats() YIELD nodeCount, relCount, labels, relTypesCount
            RETURN nodeCount, relCount, size(labels) as labelCount, relTypesCount
        """
        
        try:
            stats = service.execute_query(stats_query)
            if stats:
                print(f"  Nodes: {stats[0].get('nodeCount', 0):,}")
                print(f"  Relationships: {stats[0].get('relCount', 0):,}")
                print(f"  Labels: {stats[0].get('labelCount', 0)}")
                print(f"  Relationship Types: {stats[0].get('relTypesCount', 0)}")
        except Exception as e:
            print(f"  (APOC not available: {e})")
        
        print()
        print("=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        
        # Clean up
        service.close()
        return True
        
    except Exception as e:
        print(f"\n✗ Connection failed: {e}")
        print()
        print("Troubleshooting:")
        print("  1. Check NEO4J_URI is correct in .env")
        print("  2. Verify Neo4j Aura instance is running")
        print("  3. Check username and password")
        print("  4. Ensure firewall allows connections")
        print()
        return False

if __name__ == "__main__":
    success = test_connection()
    exit(0 if success else 1)
