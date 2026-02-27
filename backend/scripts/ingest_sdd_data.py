#!/usr/bin/env python3
"""
SDD (Simulation Data Dossier) Ingestion Script
============================================================================
Purpose: Load SDD mock data into Neo4j knowledge graph with AP243/AP239 alignment
Created: February 24, 2026
Phase: Sprint 1 - Data Migration
Related: docs/SDD_INTEGRATION_TRACKER.md, docs/SDD_DATA_MAPPING.csv
============================================================================

Usage:
    # Ingest SDD data (requires schema migration to run first)
    python backend/scripts/ingest_sdd_data.py
    
    # Clear existing SDD data and re-ingest
    python backend/scripts/ingest_sdd_data.py --clear
    
    # Dry run (show what would be created)
    python backend/scripts/ingest_sdd_data.py --dry-run

Prerequisites:
    1. Run schema migration: backend/scripts/migrations/sdd_schema_migration.cypher
    2. Ensure AP239 Requirements exist (REQ-01 through REQ-V1)
    3. Neo4j connection configured in .env

Expected Results:
    - 5 SimulationDossier nodes
    - 9 SimulationArtifact nodes per dossier (45 total)
    - 8 EvidenceCategory nodes per dossier (40 total)
    - 13 MOSSEC relationship links per dossier
    - All nodes have ap_level='AP243', ap_schema='AP243'
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv()

# Neo4j connection imports
from backend.src.graph.connection import Neo4jConnection
from backend.src.utils.config import Config


class SDDDataIngester:
    """Ingest SDD mock data into Neo4j with AP-level properties"""
    
    def __init__(self, conn: Neo4jConnection):
        self.conn = conn
        self.stats = {
            'dossiers_created': 0,
            'artifacts_created': 0,
            'evidence_categories_created': 0,
            'relationships_created': 0,
            'errors': []
        }
    
    def clear_sdd_data(self):
        """Remove all SDD-related nodes and relationships"""
        logger.warning("Clearing existing SDD data...")
        
        sdd_labels = [
            'SimulationDossier',
            'SimulationArtifact',
            'SimulationRun',
            'EvidenceCategory',
            'ValidationCase',
            'ComplianceAudit',
            'DecisionLog'
        ]
        
        for label in sdd_labels:
            query = f"MATCH (n:{label}) DETACH DELETE n"
            self.conn.execute_query(query)
            logger.info(f"Cleared {label} nodes")
    
    def load_mock_data(self) -> Dict[str, Any]:
        """Load mock data from JSON file"""
        data_file = PROJECT_ROOT / 'backend' / 'data' / 'raw' / 'sdd_mock_data.json'
        
        if not data_file.exists():
            raise FileNotFoundError(f"Mock data file not found: {data_file}")
        
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"Loaded mock data from {data_file}")
        logger.info(f"  - {len(data['dossiers'])} dossiers")
        logger.info(f"  - {len(data['artifacts'])} artifacts")
        logger.info(f"  - {len(data['evidence_categories'])} evidence categories")
        logger.info(f"  - {len(data['mossec_links'])} MOSSEC links")
        
        return data
    
    def create_dossiers(self, dossiers: List[Dict]):
        """Create SimulationDossier nodes"""
        logger.info("Creating SimulationDossier nodes...")
        
        query = """
        UNWIND $dossiers AS dossier
        MERGE (d:SimulationDossier {id: dossier.id})
        SET d.name = dossier.projectName,
            d.version = dossier.version,
            d.credibility_level = dossier.credibilityLevel,
            d.motor_id = dossier.motorId,
            d.project_name = dossier.projectName,
            d.status = dossier.status,
            d.last_updated = dossier.lastUpdated,
            d.engineer = dossier.engineer,
            d.ap_level = dossier.ap_level,
            d.ap_schema = dossier.ap_schema,
            d.created_at = datetime()
        RETURN count(d) AS count
        """
        
        result = self.conn.execute_query(query, {'dossiers': dossiers})
        count = result[0]['count'] if result else 0
        self.stats['dossiers_created'] = count
        logger.success(f"Created {count} SimulationDossier nodes")
    
    def create_artifacts(self, artifacts: List[Dict]):
        """Create SimulationArtifact nodes"""
        logger.info("Creating SimulationArtifact nodes...")
        
        query = """
        UNWIND $artifacts AS artifact
        MERGE (a:SimulationArtifact {id: artifact.id})
        SET a.name = artifact.name,
            a.type = artifact.type,
            a.timestamp = artifact.timestamp,
            a.size = artifact.size,
            a.status = artifact.status,
            a.checksum = artifact.checksum,
            a.ap_level = artifact.ap_level,
            a.ap_schema = artifact.ap_schema,
            a.created_at = datetime()
        RETURN count(a) AS count
        """
        
        result = self.conn.execute_query(query, {'artifacts': artifacts})
        count = result[0]['count'] if result else 0
        self.stats['artifacts_created'] = count
        logger.success(f"Created {count} SimulationArtifact nodes")
    
    def create_evidence_categories(self, categories: List[Dict]):
        """Create EvidenceCategory nodes"""
        logger.info("Creating EvidenceCategory nodes...")
        
        query = """
        UNWIND $categories AS cat
        MERGE (e:EvidenceCategory {id: cat.id})
        SET e.label = cat.label,
            e.status = cat.status,
            e.type = cat.type,
            e.created_at = datetime()
        RETURN count(e) AS count
        """
        
        result = self.conn.execute_query(query, {'categories': categories})
        count = result[0]['count'] if result else 0
        self.stats['evidence_categories_created'] = count
        logger.success(f"Created {count} EvidenceCategory nodes")
    
    def link_artifacts_to_requirements(self, artifacts: List[Dict]):
        """Create relationships between artifacts and AP239 requirements"""
        logger.info("Linking artifacts to AP239 requirements...")
        
        # Filter artifacts that have requirementId
        artifacts_with_reqs = [a for a in artifacts if a.get('requirementId')]
        
        query = """
        UNWIND $artifacts AS artifact
        MATCH (a:SimulationArtifact {id: artifact.id})
        MATCH (r:Requirement {id: artifact.requirementId})
        MERGE (a)-[:LINKED_TO_REQUIREMENT {
            created_at: datetime(),
            trace_type: 'MOSSEC'
        }]->(r)
        RETURN count(*) AS count
        """
        
        result = self.conn.execute_query(query, {'artifacts': artifacts_with_reqs})
        count = result[0]['count'] if result else 0
        logger.success(f"Created {count} artifact→requirement links")
        self.stats['relationships_created'] += count
    
    def link_artifacts_to_dossiers(self):
        """Link all artifacts to DOS-2024-001 (all mock artifacts belong to first dossier)"""
        logger.info("Linking artifacts to dossiers...")
        
        query = """
        MATCH (d:SimulationDossier {id: 'DOS-2024-001'})
        MATCH (a:SimulationArtifact)
        WHERE a.id IN ['A1', 'A2', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1', 'H1']
        MERGE (d)-[:CONTAINS_ARTIFACT]->(a)
        RETURN count(*) AS count
        """
        
        result = self.conn.execute_query(query)
        count = result[0]['count'] if result else 0
        logger.success(f"Created {count} dossier→artifact links")
        self.stats['relationships_created'] += count
    
    def link_evidence_categories_to_dossiers(self):
        """Link evidence categories to all dossiers"""
        logger.info("Linking evidence categories to dossiers...")
        
        query = """
        MATCH (d:SimulationDossier)
        MATCH (e:EvidenceCategory)
        MERGE (d)-[:HAS_EVIDENCE_CATEGORY]->(e)
        RETURN count(*) AS count
        """
        
        result = self.conn.execute_query(query)
        count = result[0]['count'] if result else 0
        logger.success(f"Created {count} dossier→evidence category links")
        self.stats['relationships_created'] += count
    
    def verify_schema(self) -> bool:
        """Verify that schema migration was run"""
        logger.info("Verifying schema prerequisites...")
        
        # Check if requirements exist
        query = """
        MATCH (r:Requirement)
        WHERE r.id IN ['REQ-01', 'REQ-02', 'REQ-03', 'REQ-04', 'REQ-05', 'REQ-06', 'REQ-07', 'REQ-V1']
        RETURN count(r) AS count
        """
        
        result = self.conn.execute_query(query)
        req_count = result[0]['count'] if result else 0
        
        if req_count < 8:
            logger.error(f"Only {req_count}/8 requirements found. Run schema migration first!")
            logger.error("Execute: backend/scripts/migrations/sdd_schema_migration.cypher")
            return False
        
        logger.success(f"All {req_count} AP239 requirements found ✓")
        return True
    
    def ingest(self, clear: bool = False, dry_run: bool = False):
        """Main ingestion pipeline"""
        logger.info("\n" + "=" * 70)
        logger.info("SDD DATA INGESTION")
        logger.info("=" * 70)
        
        # Verify prerequisites
        if not self.verify_schema():
            logger.error("Schema verification failed. Aborting.")
            return False
        
        # Load data
        data = self.load_mock_data()
        
        if dry_run:
            logger.info("\n[DRY RUN MODE - No changes will be made]")
            logger.info(f"Would create {len(data['dossiers'])} dossiers")
            logger.info(f"Would create {len(data['artifacts'])} artifacts")
            logger.info(f"Would create {len(data['evidence_categories'])} evidence categories")
            return True
        
        # Clear existing data if requested
        if clear:
            self.clear_sdd_data()
        
        # Ingest nodes
        self.create_dossiers(data['dossiers'])
        self.create_artifacts(data['artifacts'])
        self.create_evidence_categories(data['evidence_categories'])
        
        # Create relationships
        self.link_artifacts_to_requirements(data['artifacts'])
        self.link_artifacts_to_dossiers()
        self.link_evidence_categories_to_dossiers()
        
        # Print summary
        logger.info("\n" + "=" * 70)
        logger.info("INGESTION SUMMARY")
        logger.info("=" * 70)
        logger.success(f"Dossiers created:           {self.stats['dossiers_created']}")
        logger.success(f"Artifacts created:          {self.stats['artifacts_created']}")
        logger.success(f"Evidence categories:        {self.stats['evidence_categories_created']}")
        logger.success(f"Relationships created:      {self.stats['relationships_created']}")
        
        if self.stats['errors']:
            logger.error(f"Errors encountered:         {len(self.stats['errors'])}")
            for error in self.stats['errors']:
                logger.error(f"  - {error}")
        
        logger.info("=" * 70)
        
        return True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Ingest SDD mock data into Neo4j')
    parser.add_argument('--clear', action='store_true', help='Clear existing SDD data before ingesting')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be created without making changes')
    args = parser.parse_args()
    
    # Initialize connection
    config = Config()
    conn = Neo4jConnection(
        uri=config.neo4j_uri,
        user=config.neo4j_user,
        password=config.neo4j_password
    )
    conn.connect()
    
    try:
        # Create ingester and run
        ingester = SDDDataIngester(conn)
        success = ingester.ingest(clear=args.clear, dry_run=args.dry_run)
        
        if success:
            logger.success("\n✅ SDD data ingestion completed successfully")
            return 0
        else:
            logger.error("\n❌ SDD data ingestion failed")
            return 1
    
    except Exception as e:
        logger.exception(f"Ingestion failed: {e}")
        return 1
    
    finally:
        conn.close()


if __name__ == '__main__':
    sys.exit(main())
