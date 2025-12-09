#!/bin/bash

###############################################################################
# MBSE Knowledge Graph - Database Diagnostics
# Purpose: Test Neo4j connectivity and performance
# Usage: bash deployment/diagnostics/test_database.sh
###############################################################################

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "=========================================="
echo "Neo4j Database Diagnostics"
echo "=========================================="
echo -e "${NC}"

# Load environment variables
if [ -f ".env" ]; then
    source .env
    echo -e "${GREEN}✓ Environment loaded from .env${NC}"
else
    echo -e "${RED}✗ .env file not found${NC}"
    exit 1
fi

# Check required variables
if [ -z "$NEO4J_URI" ] || [ -z "$NEO4J_USER" ] || [ -z "$NEO4J_PASSWORD" ]; then
    echo -e "${RED}✗ Missing Neo4j configuration in .env${NC}"
    echo "Required: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD"
    exit 1
fi

echo ""
echo "Configuration:"
echo "  URI: $NEO4J_URI"
echo "  User: $NEO4J_USER"
echo "  Database: ${NEO4J_DATABASE:-neo4j}"
echo ""

# Test 1: Python driver connectivity
echo -e "${BLUE}=== Test 1: Python Driver Connectivity ===${NC}"
python3 << EOF
import sys
from neo4j import GraphDatabase
import os

uri = os.getenv('NEO4J_URI')
user = os.getenv('NEO4J_USER')
password = os.getenv('NEO4J_PASSWORD')
database = os.getenv('NEO4J_DATABASE', 'neo4j')

try:
    driver = GraphDatabase.driver(uri, auth=(user, password))
    driver.verify_connectivity()
    print("✓ Connection successful")
    
    with driver.session(database=database) as session:
        result = session.run("RETURN 1 as test")
        record = result.single()
        if record['test'] == 1:
            print("✓ Query execution successful")
    
    driver.close()
    sys.exit(0)
except Exception as e:
    print(f"✗ Connection failed: {e}")
    sys.exit(1)
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Python driver test passed${NC}"
else
    echo -e "${RED}✗ Python driver test failed${NC}"
    exit 1
fi

echo ""

# Test 2: Database statistics
echo -e "${BLUE}=== Test 2: Database Statistics ===${NC}"
python3 << EOF
from neo4j import GraphDatabase
import os

uri = os.getenv('NEO4J_URI')
user = os.getenv('NEO4J_USER')
password = os.getenv('NEO4J_PASSWORD')
database = os.getenv('NEO4J_DATABASE', 'neo4j')

try:
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    with driver.session(database=database) as session:
        # Count nodes
        result = session.run("MATCH (n) RETURN count(n) as node_count")
        node_count = result.single()['node_count']
        print(f"  Total Nodes: {node_count}")
        
        # Count relationships
        result = session.run("MATCH ()-[r]->() RETURN count(r) as rel_count")
        rel_count = result.single()['rel_count']
        print(f"  Total Relationships: {rel_count}")
        
        # Node types
        result = session.run("""
            MATCH (n)
            RETURN labels(n)[0] as label, count(*) as count
            ORDER BY count DESC
            LIMIT 10
        """)
        print("\n  Top Node Types:")
        for record in result:
            print(f"    - {record['label']}: {record['count']}")
        
        # Relationship types
        result = session.run("""
            MATCH ()-[r]->()
            RETURN type(r) as type, count(*) as count
            ORDER BY count DESC
            LIMIT 10
        """)
        print("\n  Top Relationship Types:")
        for record in result:
            print(f"    - {record['type']}: {record['count']}")
    
    driver.close()
except Exception as e:
    print(f"✗ Failed to retrieve statistics: {e}")
EOF

echo ""

# Test 3: Query performance
echo -e "${BLUE}=== Test 3: Query Performance ===${NC}"
python3 << EOF
from neo4j import GraphDatabase
import os
import time

uri = os.getenv('NEO4J_URI')
user = os.getenv('NEO4J_USER')
password = os.getenv('NEO4J_PASSWORD')
database = os.getenv('NEO4J_DATABASE', 'neo4j')

try:
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    with driver.session(database=database) as session:
        # Test 1: Simple query
        start = time.time()
        session.run("MATCH (n) RETURN n LIMIT 1")
        elapsed = (time.time() - start) * 1000
        print(f"  Simple query: {elapsed:.2f}ms")
        
        # Test 2: Count query
        start = time.time()
        session.run("MATCH (n) RETURN count(n)")
        elapsed = (time.time() - start) * 1000
        print(f"  Count query: {elapsed:.2f}ms")
        
        # Test 3: Relationship traversal
        start = time.time()
        session.run("MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 10")
        elapsed = (time.time() - start) * 1000
        print(f"  Traversal query: {elapsed:.2f}ms")
    
    driver.close()
    
    if elapsed < 1000:
        print("\n✓ Performance: Excellent")
    elif elapsed < 5000:
        print("\n✓ Performance: Good")
    else:
        print("\n⚠ Performance: Consider optimization")
        
except Exception as e:
    print(f"✗ Performance test failed: {e}")
EOF

echo ""

# Test 4: Index verification
echo -e "${BLUE}=== Test 4: Index Verification ===${NC}"
python3 << EOF
from neo4j import GraphDatabase
import os

uri = os.getenv('NEO4J_URI')
user = os.getenv('NEO4J_USER')
password = os.getenv('NEO4J_PASSWORD')
database = os.getenv('NEO4J_DATABASE', 'neo4j')

try:
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    with driver.session(database=database) as session:
        result = session.run("SHOW INDEXES")
        indexes = list(result)
        
        if len(indexes) > 0:
            print(f"  Total Indexes: {len(indexes)}")
            print("\n  Index Details:")
            for idx in indexes[:10]:  # Show first 10
                name = idx.get('name', 'N/A')
                state = idx.get('state', 'N/A')
                print(f"    - {name}: {state}")
            
            if len(indexes) > 10:
                print(f"    ... and {len(indexes) - 10} more")
        else:
            print("  ⚠ No indexes found. Consider creating indexes for better performance.")
    
    driver.close()
except Exception as e:
    print(f"  ⚠ Could not retrieve indexes: {e}")
EOF

echo ""

# Summary
echo -e "${GREEN}"
echo "=========================================="
echo "Database Diagnostics Complete"
echo "=========================================="
echo -e "${NC}"
echo ""
echo "If all tests passed, your database is properly configured!"
echo "If any tests failed, check your .env configuration and Neo4j instance."
