#!/usr/bin/env python3
"""
Master Ingestion Controller
============================================================================
Orchestrate ingestion from multiple schema formats into Neo4j Knowledge Graph.

Supports:
    - XMI: UML/SysML Domain Models (primary MoSSEC/AP243 source)
    - XSD: XML Schema Definitions (STEP, ISO 10303)

Usage:
    # Ingest all schema types
    python backend/scripts/ingest_schemas.py --all
    
    # Ingest specific formats
    python backend/scripts/ingest_schemas.py --xmi
    python backend/scripts/ingest_schemas.py --xsd
    
    # Clear and re-ingest
    python backend/scripts/ingest_schemas.py --all --clear

Configuration:
    Uses .env for Neo4j connection settings (NEO4J_DATABASE, etc.)
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from loguru import logger

from backend.src.graph.connection import Neo4jConnection
from backend.src.utils.config import Config


def clear_database(conn: Neo4jConnection, node_types: List[str] = None):
    """Clear nodes from the database"""
    if node_types:
        for node_type in node_types:
            logger.warning(f"Clearing {node_type} nodes...")
            conn.execute_query(f"MATCH (n:{node_type}) DETACH DELETE n")
    else:
        logger.warning("Clearing ALL nodes from database...")
        result = conn.execute_query("MATCH (n) DETACH DELETE n")
        logger.info("Database cleared")


def ingest_xmi(conn: Neo4jConnection, clear: bool = False) -> Dict[str, Any]:
    """Run XMI ingestion"""
    from backend.scripts.ingest_xmi import XMIIngester
    
    logger.info("\n" + "=" * 70)
    logger.info("STARTING XMI INGESTION")
    logger.info("=" * 70)
    
    ingester = XMIIngester(connection=conn)
    
    if clear:
        clear_database(conn, ['XMIElement'])
    
    # Default XMI sources
    xmi_dir = PROJECT_ROOT / 'smrlv12' / 'data' / 'domain_models'
    if xmi_dir.exists():
        ingester.ingest_directory(xmi_dir, pattern="*.xmi")
    
    xmi_dir2 = PROJECT_ROOT / 'backend' / 'data' / 'raw'
    if xmi_dir2.exists():
        ingester.ingest_directory(xmi_dir2, pattern="*.xmi")
    
    ingester.print_summary()
    return ingester.stats


def ingest_xsd(conn: Neo4jConnection, clear: bool = False) -> Dict[str, Any]:
    """Run XSD ingestion"""
    from backend.scripts.ingest_xsd import XSDIngester
    
    logger.info("\n" + "=" * 70)
    logger.info("STARTING XSD INGESTION")
    logger.info("=" * 70)
    
    ingester = XSDIngester(connection=conn)
    
    if clear:
        clear_database(conn, ['XSDElement'])
    
    # Default XSD sources
    xsd_dir = PROJECT_ROOT / 'smrlv12' / 'data'
    if xsd_dir.exists():
        ingester.ingest_directory(xsd_dir, pattern="*.xsd")
    
    ingester.print_summary()
    return ingester.stats


def print_database_summary(conn: Neo4jConnection):
    """Print summary of database contents"""
    logger.info("\n" + "=" * 70)
    logger.info("DATABASE SUMMARY")
    logger.info("=" * 70)
    
    # Count by label (APOC-free query)
    result = conn.execute_query("""
        MATCH (n)
        RETURN labels(n)[0] AS label, count(*) AS count
        ORDER BY count DESC
    """)
    
    if result:
        for record in result:
            logger.info(f"  {record['label']}: {record['count']} nodes")
    
    # Total counts
    total = conn.execute_query("MATCH (n) RETURN count(n) as count")
    rel_count = conn.execute_query("MATCH ()-[r]->() RETURN count(r) as count")
    
    logger.info("-" * 40)
    logger.info(f"  TOTAL NODES: {total[0]['count'] if total else 0}")
    logger.info(f"  TOTAL RELATIONSHIPS: {rel_count[0]['count'] if rel_count else 0}")
    logger.info("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Orchestrate schema ingestion into Neo4j Knowledge Graph"
    )
    parser.add_argument(
        '--all', '-a',
        action='store_true',
        help='Ingest all schema types (XMI, XSD)'
    )
    parser.add_argument(
        '--xmi',
        action='store_true',
        help='Ingest XMI domain models'
    )
    parser.add_argument(
        '--xsd',
        action='store_true',
        help='Ingest XSD schema files'
    )
    parser.add_argument(
        '--clear',
        action='store_true',
        help='Clear existing nodes before ingestion'
    )
    parser.add_argument(
        '--clear-all',
        action='store_true',
        help='Clear entire database before ingestion'
    )
    parser.add_argument(
        '--summary',
        action='store_true',
        help='Just print database summary'
    )
    
    args = parser.parse_args()
    
    # If no specific format selected, default to --all
    if not any([args.all, args.xmi, args.xsd, args.summary]):
        args.all = True
    
    # Initialize connection
    load_dotenv(PROJECT_ROOT / ".env")
    config = Config()
    conn = Neo4jConnection(
        uri=config.neo4j_uri,
        user=config.neo4j_user,
        password=config.neo4j_password
    )
    conn.connect()
    
    try:
        if args.summary:
            print_database_summary(conn)
            return
        
        if args.clear_all:
            clear_database(conn)
        
        results = {}
        
        if args.all or args.xmi:
            results['xmi'] = ingest_xmi(conn, clear=args.clear)
        
        if args.all or args.xsd:
            results['xsd'] = ingest_xsd(conn, clear=args.clear)
        
        # Print final summary
        print_database_summary(conn)
        
    finally:
        conn.close()


if __name__ == "__main__":
    main()
