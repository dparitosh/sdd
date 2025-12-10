###############################################################################
# MBSE Knowledge Graph - Database Diagnostics (Windows PowerShell)
# Purpose: Test Neo4j connectivity and performance
# Usage: .\test_database.ps1
###############################################################################

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Neo4j Database Diagnostics" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Load environment variables from .env file
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^([^=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            Set-Item -Path "env:$name" -Value $value
        }
    }
    Write-Host "[SUCCESS] Environment loaded from .env" -ForegroundColor Green
} else {
    Write-Host "[ERROR] .env file not found" -ForegroundColor Red
    exit 1
}

# Check required variables
if (-not $env:NEO4J_URI) {
    Write-Host "[ERROR] NEO4J_URI not set in .env" -ForegroundColor Red
    exit 1
}
if (-not $env:NEO4J_USER) {
    Write-Host "[ERROR] NEO4J_USER not set in .env" -ForegroundColor Red
    exit 1
}
if (-not $env:NEO4J_PASSWORD) {
    Write-Host "[ERROR] NEO4J_PASSWORD not set in .env" -ForegroundColor Red
    exit 1
}

if (-not $env:NEO4J_DATABASE) {
    $env:NEO4J_DATABASE = "neo4j"
}

Write-Host ""
Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  URI: $env:NEO4J_URI"
Write-Host "  User: $env:NEO4J_USER"
Write-Host "  Database: $env:NEO4J_DATABASE"
Write-Host ""

# Test 1: Python driver connectivity
Write-Host "=== Test 1: Python Driver Connectivity ===" -ForegroundColor Cyan
$testScript1 = @"
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
    print('[SUCCESS] Connection successful')
    
    with driver.session(database=database) as session:
        result = session.run('RETURN 1 as test')
        record = result.single()
        if record['test'] == 1:
            print('[SUCCESS] Query execution successful')
    
    driver.close()
    sys.exit(0)
except Exception as e:
    print(f'[ERROR] Connection failed: {e}')
    sys.exit(1)
"@

$testScript1 | python
if ($LASTEXITCODE -eq 0) {
    Write-Host "[SUCCESS] Python driver test passed" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Python driver test failed" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Test 2: Database statistics
Write-Host "=== Test 2: Database Statistics ===" -ForegroundColor Cyan
$testScript2 = @"
from neo4j import GraphDatabase
import os

uri = os.getenv('NEO4J_URI')
user = os.getenv('NEO4J_USER')
password = os.getenv('NEO4J_PASSWORD')
database = os.getenv('NEO4J_DATABASE', 'neo4j')

try:
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    with driver.session(database=database) as session:
        # Node count
        result = session.run('MATCH (n) RETURN count(n) as node_count')
        node_count = result.single()['node_count']
        print(f'Nodes: {node_count}')
        
        # Relationship count
        result = session.run('MATCH ()-[r]->() RETURN count(r) as rel_count')
        rel_count = result.single()['rel_count']
        print(f'Relationships: {rel_count}')
        
        # Labels
        result = session.run('CALL db.labels()')
        labels = [record['label'] for record in result]
        print(f'Labels: {len(labels)}')
        for label in labels[:10]:
            print(f'  - {label}')
        
        # Relationship types
        result = session.run('CALL db.relationshipTypes()')
        types = [record['relationshipType'] for record in result]
        print(f'Relationship Types: {len(types)}')
        for t in types[:10]:
            print(f'  - {t}')
    
    driver.close()
except Exception as e:
    print(f'[ERROR] Failed: {e}')
    exit(1)
"@

$testScript2 | python
if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "[SUCCESS] Database statistics retrieved" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Failed to retrieve statistics" -ForegroundColor Red
}

Write-Host ""

# Test 3: Query performance
Write-Host "=== Test 3: Query Performance ===" -ForegroundColor Cyan
$testScript3 = @"
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
        # Test query latency
        start = time.time()
        session.run('RETURN 1').consume()
        latency = (time.time() - start) * 1000
        
        print(f'Simple query latency: {latency:.2f}ms')
        
        if latency < 100:
            print('Status: GOOD')
        elif latency < 500:
            print('Status: SLOW')
        else:
            print('Status: CRITICAL')
    
    driver.close()
except Exception as e:
    print(f'[ERROR] Failed: {e}')
"@

$testScript3 | python

Write-Host ""

# Test 4: Check if database is populated
Write-Host "=== Test 4: Database Content Check ===" -ForegroundColor Cyan
$testScript4 = @"
from neo4j import GraphDatabase
import os

uri = os.getenv('NEO4J_URI')
user = os.getenv('NEO4J_USER')
password = os.getenv('NEO4J_PASSWORD')
database = os.getenv('NEO4J_DATABASE', 'neo4j')

try:
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    with driver.session(database=database) as session:
        result = session.run('MATCH (n) RETURN count(n) as count')
        count = result.single()['count']
        
        print(f'Total nodes: {count}')
        
        if count > 0:
            print('[SUCCESS] Database is populated')
        else:
            print('[WARNING] Database is empty')
    
    driver.close()
except Exception as e:
    print(f'[ERROR] Failed: {e}')
"@

$testScript4 | python

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Diagnostics Complete" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

Read-Host -Prompt "Press Enter to exit"
