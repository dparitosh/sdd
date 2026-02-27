#!/usr/bin/env python3
"""
SimulationRun Workflow Migration Script
============================================================================
Purpose: Execute SimulationRun schema migration with verification
Created: February 24, 2026
Phase: Sprint 2 - SimulationRun Workflow
Related: backend/scripts/migrations/sdd_simulation_run_migration.cypher
============================================================================

Usage:
    python backend/scripts/run_simulation_run_migration.py
    
Prerequisites:
    - Sprint 1 schema migration completed
    - SimulationDossier and SimulationArtifact nodes exist
    
Expected Results:
    - 2 constraints created
    - 4 indexes created
    - 3 SimulationRun nodes created
    - 4 GENERATED relationships
    - 3 HAS_SIMULATION_RUN relationships
"""

import sys
from pathlib import Path
from loguru import logger

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.src.graph.connection import Neo4jConnection
from backend.src.utils.config import Config


def run_migration():
    """Execute SimulationRun migration"""
    
    config = Config()
    conn = Neo4jConnection(
        uri=config.neo4j_uri,
        user=config.neo4j_user,
        password=config.neo4j_password
    )
    conn.connect()
    
    # Read migration file
    migration_file = PROJECT_ROOT / 'backend' / 'scripts' / 'migrations' / 'sdd_simulation_run_migration.cypher'
    
    if not migration_file.exists():
        logger.error(f"Migration file not found: {migration_file}")
        return False
    
    with open(migration_file, 'r', encoding='utf-8') as f:
        cypher_script = f.read()
    
    logger.info("=" * 70)
    logger.info("SPRINT 2: SimulationRun Workflow Migration")
    logger.info("=" * 70)
    
    # Split into statements (filter out comments and empty lines)
    statements = []
    current_stmt = []
    
    for line in cypher_script.split('\n'):
        stripped = line.strip()
        
        # Skip comments and empty lines
        if stripped.startswith('//') or not stripped:
            continue
        
        current_stmt.append(line)
        
        # End of statement
        if stripped.endswith(';'):
            stmt = '\n'.join(current_stmt)
            statements.append(stmt)
            current_stmt = []
    
    logger.info(f"\nFound {len(statements)} Cypher statements to execute")
    
    # Execute each statement
    success_count = 0
    error_count = 0
    
    for i, stmt in enumerate(statements, 1):
        try:
            # Show what we're executing (first 80 chars)
            preview = stmt.strip()[:80].replace('\n', ' ')
            logger.info(f"\n[{i}/{len(statements)}] Executing: {preview}...")
            
            result = conn.execute_query(stmt)
            success_count += 1
            
            # Show result if available
            if result and len(result) > 0:
                logger.success(f"  → Result: {result}")
            else:
                logger.success(f"  → Executed successfully")
                
        except Exception as e:
            # Some errors are expected (e.g., constraint already exists)
            error_msg = str(e)
            if 'already exists' in error_msg or 'constraint already created' in error_msg.lower():
                logger.warning(f"  → Already exists (skipping): {error_msg[:100]}")
                success_count += 1
            else:
                logger.error(f"  → Error: {e}")
                error_count += 1
    
    # Verification
    logger.info("\n" + "=" * 70)
    logger.info("VERIFICATION")
    logger.info("=" * 70)
    
    # Count SimulationRun nodes
    run_count = conn.execute_query("MATCH (sr:SimulationRun) RETURN count(sr) AS count")
    logger.info(f"\n✓ SimulationRun nodes: {run_count[0]['count']}")
    
    # Count GENERATED relationships
    gen_count = conn.execute_query("MATCH ()-[r:GENERATED]->() RETURN count(r) AS count")
    logger.info(f"✓ GENERATED relationships: {gen_count[0]['count']}")
    
    # Count HAS_SIMULATION_RUN relationships
    has_run_count = conn.execute_query("MATCH ()-[r:HAS_SIMULATION_RUN]->() RETURN count(r) AS count")
    logger.info(f"✓ HAS_SIMULATION_RUN relationships: {has_run_count[0]['count']}")
    
    # Show sample run
    sample = conn.execute_query("""
        MATCH (sr:SimulationRun)-[r:GENERATED]->(a:SimulationArtifact)
        WITH sr, collect(a.id) AS artifacts
        RETURN sr.id AS run_id, sr.sim_type AS sim_type, sr.status AS status, 
               sr.solver_version AS solver, artifacts
        LIMIT 3
    """)
    
    logger.info("\n✓ Sample SimulationRuns:")
    for s in sample:
        logger.info(f"  - {s['run_id']} ({s['sim_type']}, {s['status']})")
        logger.info(f"    Solver: {s['solver']}")
        logger.info(f"    Generated: {s['artifacts']}")
    
    conn.close()
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("MIGRATION SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Statements executed: {success_count}/{len(statements)}")
    if error_count > 0:
        logger.warning(f"Errors: {error_count}")
    else:
        logger.success("✅ Migration completed successfully!")
    logger.info("=" * 70 + "\n")
    
    return error_count == 0


if __name__ == '__main__':
    success = run_migration()
    sys.exit(0 if success else 1)
