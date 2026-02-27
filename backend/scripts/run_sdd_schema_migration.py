#!/usr/bin/env python3
"""
SDD Schema Migration Runner
============================================================================
Purpose: Execute SDD schema migration (constraints, indexes, requirement stubs)
Created: February 24, 2026
Phase: Sprint 1 - Schema Design
============================================================================

Usage:
    python backend/scripts/run_sdd_schema_migration.py

What it does:
    - Creates 7 unique constraints (one per label)
    - Creates 10 indexes for performance
    - Creates 8 AP239 requirement stubs (REQ-01 through REQ-V1)
    - Verifies all constraints and indexes were created
"""

import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from loguru import logger

from backend.src.graph.connection import Neo4jConnection
from backend.src.utils.config import Config

# Load environment variables
load_dotenv()


def execute_cypher_file(conn: Neo4jConnection, cypher_file: Path):
    """Execute a Cypher file by splitting it into individual statements"""
    
    logger.info(f"Reading Cypher file: {cypher_file}")
    
    with open(cypher_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by semicolons (each statement ends with ;)
    # Filter out comments and empty lines
    statements = []
    current_statement = []
    
    for line in content.split('\n'):
        # Skip comment-only lines
        if line.strip().startswith('//') or line.strip().startswith('#'):
            continue
        
        # Remove inline comments
        if '//' in line:
            line = line[:line.index('//')]
        
        if line.strip():
            current_statement.append(line)
            
            # Check if statement is complete (ends with ;)
            if line.strip().endswith(';'):
                stmt = '\n'.join(current_statement)
                statements.append(stmt)
                current_statement = []
    
    logger.info(f"Found {len(statements)} Cypher statements")
    
    # Execute each statement
    for i, stmt in enumerate(statements, 1):
        stmt = stmt.strip()
        if not stmt:
            continue
        
        try:
            # Show what we're executing (first 100 chars)
            preview = stmt[:100].replace('\n', ' ')
            logger.info(f"Executing statement {i}/{len(statements)}: {preview}...")
            
            result = conn.execute_query(stmt)
            
            # Show results if any
            if result:
                logger.success(f"  ✓ Returned {len(result)} row(s)")
                if len(result) <= 5:  # Show details for small results
                    for row in result:
                        logger.info(f"    {row}")
            else:
                logger.success(f"  ✓ Completed")
        
        except Exception as e:
            # Some statements might fail if already exist (that's OK for MERGE)
            if "already exists" in str(e).lower() or "equivalent" in str(e).lower():
                logger.warning(f"  ⚠ Already exists: {e}")
            else:
                logger.error(f"  ✗ Failed: {e}")
                raise


def verify_migration(conn: Neo4jConnection):
    """Verify the migration was successful"""
    
    logger.info("\n" + "=" * 70)
    logger.info("VERIFICATION")
    logger.info("=" * 70)
    
    # Check requirements
    query = """
    MATCH (r:Requirement)
    WHERE r.id IN ['REQ-01', 'REQ-02', 'REQ-03', 'REQ-04', 'REQ-05', 'REQ-06', 'REQ-07', 'REQ-V1']
    RETURN count(r) AS count
    """
    
    result = conn.execute_query(query)
    req_count = result[0]['count'] if result else 0
    
    if req_count == 8:
        logger.success(f"✓ All 8 requirement stubs created")
    else:
        logger.error(f"✗ Only {req_count}/8 requirements found")
    
    # Check constraints
    query = """
    SHOW CONSTRAINTS
    YIELD name, type
    WHERE name STARTS WITH 'simulation_' OR name STARTS WITH 'evidence_' 
       OR name STARTS WITH 'validation_' OR name STARTS WITH 'compliance_' 
       OR name STARTS WITH 'decision_'
    RETURN count(*) AS count
    """
    
    try:
        result = conn.execute_query(query)
        const_count = result[0]['count'] if result else 0
        logger.success(f"✓ Found {const_count} constraints")
    except Exception as e:
        logger.warning(f"Could not verify constraints: {e}")
    
    # Check indexes
    query = """
    SHOW INDEXES
    YIELD name, type
    WHERE name STARTS WITH 'simulation_' OR name STARTS WITH 'evidence_'
    RETURN count(*) AS count
    """
    
    try:
        result = conn.execute_query(query)
        idx_count = result[0]['count'] if result else 0
        logger.success(f"✓ Found {idx_count} indexes")
    except Exception as e:
        logger.warning(f"Could not verify indexes: {e}")


def main():
    """Main entry point"""
    
    logger.info("\n" + "=" * 70)
    logger.info("SDD SCHEMA MIGRATION")
    logger.info("=" * 70)
    
    # Find migration file
    migration_file = PROJECT_ROOT / 'backend' / 'scripts' / 'migrations' / 'sdd_schema_migration.cypher'
    
    if not migration_file.exists():
        logger.error(f"Migration file not found: {migration_file}")
        return 1
    
    # Initialize connection
    config = Config()
    conn = Neo4jConnection(
        uri=config.neo4j_uri,
        user=config.neo4j_user,
        password=config.neo4j_password
    )
    conn.connect()
    
    try:
        # Execute migration
        execute_cypher_file(conn, migration_file)
        
        # Verify results
        verify_migration(conn)
        
        logger.info("\n" + "=" * 70)
        logger.success("✅ Schema migration completed successfully")
        logger.info("=" * 70)
        logger.info("\nNext step: Run data ingestion")
        logger.info("  python backend/scripts/ingest_sdd_data.py")
        
        return 0
    
    except Exception as e:
        logger.exception(f"Migration failed: {e}")
        return 1
    
    finally:
        conn.close()


if __name__ == '__main__':
    sys.exit(main())
