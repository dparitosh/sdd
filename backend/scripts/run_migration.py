#!/usr/bin/env python3
"""
Execute AP239/AP242/AP243 migration script using Python Neo4j driver
"""

import sys
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

# Ensure `import src...` works when running from repo root.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

load_dotenv(REPO_ROOT / ".env")

from src.web.services import get_neo4j_service


def execute_migration():
    """Execute Cypher migration script."""
    logger.info("Starting AP239/AP242/AP243 migration...")
    
    neo4j = get_neo4j_service()
    
    # Read migration script
    with open(BACKEND_ROOT / 'scripts' / 'migrate_to_ap_hierarchy.cypher', 'r', encoding='utf-8') as f:
        migration_script = f.read()
    
    # Split into individual statements (separated by semicolons)
    statements = [stmt.strip() for stmt in migration_script.split(';') if stmt.strip()]
    
    # Filter out comments-only statements
    statements = [stmt for stmt in statements if not all(
        line.strip().startswith('//') or line.strip() == '' 
        for line in stmt.split('\n')
    )]
    
    logger.info(f"Found {len(statements)} Cypher statements to execute")
    
    executed = 0
    failed = 0
    
    for i, statement in enumerate(statements, 1):
        # Skip comment-only lines
        clean_stmt = '\n'.join(line for line in statement.split('\n') 
                               if not line.strip().startswith('//'))
        
        if not clean_stmt.strip():
            continue
            
        try:
            # Show progress
            first_line = clean_stmt.split('\n')[0][:60]
            logger.info(f"[{i}/{len(statements)}] Executing: {first_line}...")
            
            result = neo4j.execute_query(clean_stmt)
            executed += 1
            
            if i % 10 == 0:
                logger.info(f"Progress: {executed}/{len(statements)} statements executed")
                
        except Exception as e:
            logger.error(f"Failed to execute statement {i}: {e}")
            logger.debug(f"Statement: {clean_stmt[:200]}")
            failed += 1
            
            # Continue with other statements
            continue
    
    logger.info("=" * 80)
    logger.info("MIGRATION SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Statements executed successfully: {executed}")
    logger.info(f"Statements failed: {failed}")
    logger.info("=" * 80)
    
    if failed > 0:
        logger.warning(f"{failed} statements failed - review logs above")
        return 1
    else:
        logger.success("✓ Migration completed successfully!")
        return 0


if __name__ == '__main__':
    sys.exit(execute_migration())
