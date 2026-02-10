#!/usr/bin/env python3
"""
Master Knowledge Graph Ingestion Orchestrator
============================================================================
Orchestrates ingestion of all STEP EXPRESS schemas into Neo4j Knowledge Graph.

Purpose:
    Run all schema ingesters (AP239, AP242, AP243) in sequence or parallel
    to build a comprehensive MBSE Knowledge Graph.

Schemas Ingested:
    - AP239: Product Life Cycle Support (Requirements, Documents, Approvals)
    - AP242: Managed Model-Based 3D Engineering (CAD, Geometry, PMI)
    - AP243: MoSSEC Systems Engineering (Systems, Functions, Interfaces)

Knowledge Graph Structure:
    ┌─────────────────────────────────────────────────────────────────┐
    │                    MBSE Knowledge Graph                         │
    ├─────────────────────────────────────────────────────────────────┤
    │  AP239 Layer          AP242 Layer          AP243 Layer          │
    │  ├─ Requirement       ├─ Shape             ├─ System            │
    │  ├─ Document          ├─ Product           ├─ Function          │
    │  ├─ Approval          ├─ Assembly          ├─ Interface         │
    │  ├─ Activity          ├─ Annotation        ├─ Behavior          │
    │  └─ Effectivity       └─ Geometry          └─ Parameter         │
    │                                                                 │
    │  Cross-Layer Relationships:                                     │
    │  - Requirement ─VERIFIED_BY─> Analysis                         │
    │  - System ─REALIZED_BY─> Product                               │
    │  - Function ─ALLOCATED_TO─> Component                          │
    └─────────────────────────────────────────────────────────────────┘

Usage:
    # Run all ingesters
    python backend/scripts/ingest_all.py
    
    # Dry run (parse only)
    python backend/scripts/ingest_all.py --dry-run
    
    # Select specific schemas
    python backend/scripts/ingest_all.py --schemas ap239 ap242
    
    # Clear database first
    python backend/scripts/ingest_all.py --clear

Configuration:
    Uses .env for Neo4j connection settings
"""

import os
import sys
import argparse
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from loguru import logger

from backend.src.graph.connection import Neo4jConnection
from backend.src.utils.config import Config

# Import ingesters
from backend.scripts.ingest_ap239_v2 import AP239Ingester
from backend.scripts.ingest_ap242 import AP242Ingester
from backend.scripts.ingest_ap243 import AP243Ingester


class KnowledgeGraphOrchestrator:
    """
    Master orchestrator for Knowledge Graph ingestion.
    
    Coordinates multiple ingesters and provides:
    - Sequential or parallel execution
    - Cross-schema relationship creation
    - Statistics aggregation
    - Error handling and recovery
    """
    
    # Available ingesters
    INGESTERS = {
        "ap239": AP239Ingester,
        "ap242": AP242Ingester,
        "ap243": AP243Ingester,
    }
    
    def __init__(
        self,
        smrl_root: Path,
        schemas: Optional[List[str]] = None,
        dry_run: bool = False,
        clear_first: bool = False,
        verbose: bool = True
    ):
        """
        Initialize the orchestrator.
        
        Args:
            smrl_root: Path to SMRL root directory
            schemas: List of schema names to ingest (default: all)
            dry_run: If True, parse but don't write to Neo4j
            clear_first: If True, clear database before ingestion
            verbose: Enable verbose logging
        """
        self.smrl_root = smrl_root
        self.schemas = schemas or list(self.INGESTERS.keys())
        self.dry_run = dry_run
        self.clear_first = clear_first
        self.verbose = verbose
        
        # Shared connection for all ingesters
        self.conn: Optional[Neo4jConnection] = None
        
        # Aggregated statistics
        self.stats: Dict[str, Any] = {
            "start_time": None,
            "end_time": None,
            "total_schemas_parsed": 0,
            "total_entities_found": 0,
            "total_types_found": 0,
            "total_nodes_created": 0,
            "total_relationships_created": 0,
            "by_ap": {},
            "errors": [],
        }
    
    def run(self) -> Dict[str, Any]:
        """
        Run the complete ingestion workflow.
        
        Returns:
            Dictionary with aggregated statistics
        """
        self.stats["start_time"] = datetime.now(timezone.utc)
        
        logger.info("=" * 70)
        logger.info("MBSE Knowledge Graph Orchestrator")
        logger.info("=" * 70)
        logger.info(f"SMRL Root: {self.smrl_root}")
        logger.info(f"Schemas: {', '.join(self.schemas)}")
        logger.info(f"Dry Run: {self.dry_run}")
        logger.info(f"Clear First: {self.clear_first}")
        logger.info("=" * 70)
        
        try:
            # Initialize connection
            if not self.dry_run:
                self._init_connection()
                
                # Clear database if requested
                if self.clear_first:
                    self._clear_database()
            
            # Run each ingester
            for schema_name in self.schemas:
                if schema_name in self.INGESTERS:
                    self._run_ingester(schema_name)
                else:
                    logger.warning(f"Unknown schema: {schema_name}")
            
            # Create cross-schema relationships
            if not self.dry_run and self.conn:
                self._create_cross_schema_relationships()
                self._create_graph_metadata()
            
        except Exception as e:
            logger.error(f"Orchestration error: {e}")
            self.stats["errors"].append(str(e))
        finally:
            self._close_connection()
        
        self.stats["end_time"] = datetime.now(timezone.utc)
        self._print_final_summary()
        
        return self.stats
    
    def _init_connection(self):
        """Initialize shared Neo4j connection"""
        load_dotenv()
        config = Config()
        self.conn = Neo4jConnection(
            uri=config.neo4j_uri,
            user=config.neo4j_user,
            password=config.neo4j_password
        )
        self.conn.connect()  # Establish the actual connection
        logger.info("Neo4j connection established")
    
    def _close_connection(self):
        """Close Neo4j connection"""
        if self.conn:
            self.conn.close()
            logger.info("Neo4j connection closed")
    
    def _clear_database(self):
        """Clear all nodes and relationships from database"""
        logger.warning("Clearing database...")
        
        # Delete in batches to handle large graphs
        batch_cypher = """
        MATCH (n)
        WITH n LIMIT 10000
        DETACH DELETE n
        RETURN count(*) as deleted
        """
        
        total_deleted = 0
        while True:
            result = self.conn.execute_query(batch_cypher)
            deleted = result[0]["deleted"] if result else 0
            total_deleted += deleted
            if deleted == 0:
                break
        
        logger.info(f"Cleared {total_deleted} nodes from database")
    
    def _run_ingester(self, schema_name: str):
        """Run a single ingester"""
        logger.info(f"\n{'='*70}")
        logger.info(f"Running {schema_name.upper()} Ingester")
        logger.info("=" * 70)
        
        ingester_class = self.INGESTERS[schema_name]
        
        try:
            # Create ingester with shared connection
            ingester = ingester_class(
                smrl_root=self.smrl_root,
                connection=self.conn,
                dry_run=self.dry_run,
                verbose=self.verbose
            )
            
            # Run ingestion
            stats = ingester.ingest()
            
            # Aggregate statistics
            self.stats["by_ap"][schema_name] = stats
            self.stats["total_schemas_parsed"] += stats.get("schemas_parsed", 0)
            self.stats["total_entities_found"] += stats.get("entities_found", 0)
            self.stats["total_types_found"] += stats.get("types_found", 0)
            self.stats["total_nodes_created"] += stats.get("nodes_created", 0)
            self.stats["total_relationships_created"] += stats.get("relationships_created", 0)
            
            if stats.get("errors"):
                self.stats["errors"].extend(stats["errors"])
                
        except Exception as e:
            logger.error(f"Error running {schema_name} ingester: {e}")
            self.stats["errors"].append(f"{schema_name}: {str(e)}")
    
    def _create_cross_schema_relationships(self):
        """Create relationships between entities from different APs"""
        logger.info("\n" + "=" * 70)
        logger.info("Creating Cross-Schema Relationships")
        logger.info("=" * 70)
        
        relationships = [
            # AP239 Requirements to AP243 Systems
            {
                "name": "Requirement to System allocation",
                "cypher": """
                MATCH (r:AP239Entity:Requirement)
                MATCH (s:AP243Entity:System)
                WHERE r.name CONTAINS s.name OR s.name CONTAINS r.name
                MERGE (r)-[:APPLIES_TO_SYSTEM]->(s)
                RETURN count(*) as created
                """
            },
            # AP243 Functions to AP242 Products
            {
                "name": "Function to Product realization",
                "cypher": """
                MATCH (f:AP243Entity:Function)
                MATCH (p:AP242Entity:Product)
                WHERE f.name CONTAINS p.name OR p.name CONTAINS f.name
                MERGE (f)-[:REALIZED_BY]->(p)  
                RETURN count(*) as created
                """
            },
            # AP239 Documents to AP242 Products
            {
                "name": "Document to Product association",
                "cypher": """
                MATCH (d:AP239Entity:Document)
                MATCH (p:AP242Entity:Product)
                WHERE d.name CONTAINS p.name OR p.name CONTAINS d.name
                MERGE (d)-[:DOCUMENTS]->(p)
                RETURN count(*) as created
                """
            },
            # Schema cross-references via imports
            {
                "name": "Cross-AP Schema imports",
                "cypher": """
                MATCH (s1:Schema)-[:IMPORTS]->(s2:Schema)
                WHERE s1.ap_level <> s2.ap_level
                SET s2.cross_referenced = true
                RETURN count(*) as created
                """
            },
        ]
        
        total_created = 0
        for rel in relationships:
            try:
                result = self.conn.execute_query(rel["cypher"])
                count = result[0]["created"] if result else 0
                total_created += count
                logger.info(f"  {rel['name']}: {count} relationships")
            except Exception as e:
                logger.warning(f"  {rel['name']}: Error - {e}")
        
        self.stats["total_relationships_created"] += total_created
        logger.info(f"\nTotal cross-schema relationships: {total_created}")
    
    def _create_graph_metadata(self):
        """Create metadata node for the knowledge graph"""
        logger.info("\nCreating graph metadata...")
        
        cypher = """
        MERGE (m:KnowledgeGraphMetadata {id: 'mbse-kg'})
        SET m.name = 'MBSE Knowledge Graph',
            m.version = '1.0.0',
            m.standards = $standards,
            m.schemas_count = $schemas_count,
            m.entities_count = $entities_count,
            m.types_count = $types_count,
            m.created_on = datetime($timestamp),
            m.smrl_root = $smrl_root
        RETURN m.name as name
        """
        
        params = {
            "standards": ["ISO 10303-239", "ISO 10303-242", "ISO 10303-243"],
            "schemas_count": self.stats["total_schemas_parsed"],
            "entities_count": self.stats["total_entities_found"],
            "types_count": self.stats["total_types_found"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "smrl_root": str(self.smrl_root),
        }
        
        self.conn.execute_query(cypher, params)
        logger.info("  Graph metadata created")
    
    def _print_final_summary(self):
        """Print final aggregated summary"""
        duration = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
        
        logger.info("\n" + "=" * 70)
        logger.info("FINAL INGESTION SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info(f"\nSchemas processed: {len(self.schemas)}")
        
        for ap_name, ap_stats in self.stats["by_ap"].items():
            logger.info(f"\n  {ap_name.upper()}:")
            logger.info(f"    Schemas parsed: {ap_stats.get('schemas_parsed', 0)}")
            logger.info(f"    Entities found: {ap_stats.get('entities_found', 0)}")
            logger.info(f"    Types found: {ap_stats.get('types_found', 0)}")
        
        logger.info(f"\nTOTALS:")
        logger.info(f"  Total schemas parsed:        {self.stats['total_schemas_parsed']}")
        logger.info(f"  Total entities found:        {self.stats['total_entities_found']}")
        logger.info(f"  Total types found:           {self.stats['total_types_found']}")
        
        if not self.dry_run:
            logger.info(f"  Total nodes created:         {self.stats['total_nodes_created']}")
            logger.info(f"  Total relationships created: {self.stats['total_relationships_created']}")
        else:
            logger.info("  [DRY RUN - No changes made to Neo4j]")
        
        if self.stats["errors"]:
            logger.warning(f"\nErrors ({len(self.stats['errors'])}):")
            for error in self.stats["errors"][:20]:
                logger.warning(f"  - {error}")
            if len(self.stats["errors"]) > 20:
                logger.warning(f"  ... and {len(self.stats['errors']) - 20} more")
        
        logger.info("=" * 70)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Master Knowledge Graph Ingestion Orchestrator"
    )
    parser.add_argument(
        "--schemas",
        nargs="+",
        choices=["ap239", "ap242", "ap243", "all"],
        default=["all"],
        help="Schemas to ingest (default: all)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse schemas without writing to Neo4j"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear database before ingestion"
    )
    parser.add_argument(
        "--smrl-root",
        type=str,
        default=None,
        help="Path to SMRL root directory"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Determine SMRL root
    if args.smrl_root:
        smrl_root = Path(args.smrl_root)
    else:
        smrl_root = PROJECT_ROOT / "smrlv12"
    
    if not smrl_root.exists():
        logger.error(f"SMRL root not found: {smrl_root}")
        sys.exit(1)
    
    # Determine schemas to run
    if "all" in args.schemas:
        schemas = None  # Will use all
    else:
        schemas = args.schemas
    
    # Run orchestrator
    orchestrator = KnowledgeGraphOrchestrator(
        smrl_root=smrl_root,
        schemas=schemas,
        dry_run=args.dry_run,
        clear_first=args.clear,
        verbose=args.verbose or True
    )
    
    stats = orchestrator.run()
    
    # Exit code
    if stats["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
