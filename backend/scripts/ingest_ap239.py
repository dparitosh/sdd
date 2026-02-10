#!/usr/bin/env python3
"""
AP239 Knowledge Graph Ingestion Script
============================================================================
ISO 10303-239: Product Life Cycle Support

Purpose:
    Parse AP239 EXPRESS schema modules and create Knowledge Graph nodes in Neo4j
    for requirements management, analysis, approvals, documents, and lifecycle.

Data Source:
    smrlv12/data/modules/ap239_* directories containing:
    - arm.exp (Application Reference Model)
    - mim.exp (Module Interpreted Model)

Node Types Created:
    Level 1 (Systems Engineering Core):
    - Requirement, RequirementVersion, RequirementRelationship
    - Analysis, AnalysisModel, AnalysisVersion
    - Approval, ApprovalAssignment, Certification
    - Document, DocumentVersion, Evidence
    - Activity, ActivityMethod, Effectivity
    - Event, Condition, Justification

Relationships Created:
    - SATISFIES, VERIFIES, REFINES (Requirement traceability)
    - APPROVES, CERTIFIES (Approval workflow)
    - DOCUMENTS, TRACES_TO (Document traceability)
    - DECOMPOSES_INTO, APPLIES_TO (Hierarchy)

Usage:
    python backend/scripts/ingest_ap239.py [--dry-run] [--clear]

Configuration:
    Uses .env for Neo4j connection settings
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from loguru import logger

from backend.src.parsers.express import (
    ExpressParser,
    ExpressSchema,
    parse_express_file,
    parse_express_directory,
    ExpressNeo4jConverter,
)
from backend.src.graph.connection import Neo4jConnection
from backend.src.utils.config import Config


# AP239 Module directories (relative to SMRL root)
AP239_MODULES = [
    "ap239_product_life_cycle_support",
    "ap239_activity_recording",
    "ap239_document_management",
    "ap239_management_resource_information",
    "ap239_part_definition_information",
    "ap239_product_definition_information",
    "ap239_product_status_recording",
    "ap239_properties",
    "ap239_task_specification_resourced",
    "ap239_work_definition",
]

# AP239 Entity to Neo4j Label mapping
AP239_LABEL_MAP = {
    # Requirements
    "Requirement": "Requirement",
    "RequirementVersion": "RequirementVersion",
    "RequirementSource": "RequirementSource",
    "RequirementAssignment": "RequirementAssignment",
    "RequirementRelationship": "RequirementRelationship",
    # Analysis
    "Analysis": "Analysis",
    "AnalysisModel": "AnalysisModel",
    "AnalysisVersion": "AnalysisVersion",
    "AnalysisRepresentationContext": "AnalysisContext",
    # Approvals
    "Approval": "Approval",
    "ApprovalAssignment": "ApprovalAssignment",
    "ApprovalRelationship": "ApprovalRelationship",
    "Certification": "Certification",
    "CertificationAssignment": "CertificationAssignment",
    # Documents
    "Document": "Document",
    "DocumentDefinition": "DocumentDefinition",
    "DocumentVersion": "DocumentVersion",
    "DocumentRelationship": "DocumentRelationship",
    "Evidence": "Evidence",
    "DigitalFile": "DigitalFile",
    # Lifecycle
    "Activity": "Activity",
    "ActivityMethod": "ActivityMethod",
    "ActivityAssignment": "ActivityAssignment",
    "ActivityRelationship": "ActivityRelationship",
    "Effectivity": "Effectivity",
    "DatedEffectivity": "DatedEffectivity",
    "EffectivityAssignment": "EffectivityAssignment",
    # Breakdown
    "BreakdownElement": "BreakdownElement",
    "BreakdownVersion": "BreakdownVersion",
    "Breakdown": "Breakdown",
    # Events & Conditions
    "Event": "Event",
    "EventAssignment": "EventAssignment",
    "Condition": "Condition",
    "ConditionEvaluation": "ConditionEvaluation",
    "ConditionAssignment": "ConditionAssignment",
    # Other
    "Assumption": "Assumption",
    "Justification": "Justification",
    "Contract": "Contract",
    "Collection": "Collection",
}

# Relationship prefix for AP239
AP239_REL_PREFIX = "ap239"


class AP239Ingester:
    """
    Ingests AP239 EXPRESS schemas into Neo4j Knowledge Graph.
    """
    
    def __init__(self, smrl_root: Path, connection: Neo4jConnection, dry_run: bool = False):
        self.smrl_root = smrl_root
        self.conn = connection
        self.dry_run = dry_run
        self.parser = ExpressParser()
        self.stats = {
            "schemas_parsed": 0,
            "entities_found": 0,
            "types_found": 0,
            "nodes_created": 0,
            "relationships_created": 0,
        }
        
    def ingest(self) -> Dict:
        """Main ingestion workflow"""
        logger.info("=" * 70)
        logger.info("AP239 Knowledge Graph Ingestion")
        logger.info("=" * 70)
        
        modules_dir = self.smrl_root / "data" / "modules"
        
        if not modules_dir.exists():
            logger.error(f"Modules directory not found: {modules_dir}")
            return self.stats
        
        # Parse all AP239 modules
        for module_name in AP239_MODULES:
            module_path = modules_dir / module_name
            if module_path.exists():
                self._process_module(module_path, module_name)
            else:
                logger.warning(f"Module not found: {module_name}")
        
        # Create schema nodes in Neo4j
        if not self.dry_run:
            self._create_schema_nodes()
            self._create_entity_nodes()
            self._create_type_nodes()
            self._create_import_relationships()
        
        self._print_summary()
        return self.stats
    
    def _process_module(self, module_path: Path, module_name: str):
        """Process a single AP239 module"""
        logger.info(f"\nProcessing: {module_name}")
        
        # Parse ARM (Application Reference Model) - preferred
        arm_file = module_path / "arm.exp"
        if arm_file.exists():
            schema = self.parser.parse_file(arm_file)
            if schema:
                self.stats["schemas_parsed"] += 1
                self.stats["entities_found"] += len(schema.entities)
                self.stats["types_found"] += len(schema.types)
        
        # Also parse concatenated version if available (more complete)
        concat_file = module_path / "arm_concatenated.exp"
        if concat_file.exists():
            self.parser.parse_file(concat_file)
    
    def _create_schema_nodes(self):
        """Create Schema nodes representing AP239 modules"""
        logger.info("\nCreating AP239 Schema nodes...")
        
        for schema_name, schema in self.parser.schemas.items():
            cypher = """
            MERGE (s:Schema:AP239Schema {name: $name})
            SET s.source_file = $source_file,
                s.entity_count = $entity_count,
                s.type_count = $type_count,
                s.import_count = $import_count,
                s.ap_level = 'AP239',
                s.standard = 'ISO 10303-239',
                s.domain = 'Product Life Cycle Support',
                s.created_on = datetime($timestamp),
                s.uid = 'AP239-' + $name
            RETURN s.name as name
            """
            
            params = {
                "name": schema_name,
                "source_file": schema.source_file,
                "entity_count": len(schema.entities),
                "type_count": len(schema.types),
                "import_count": len(schema.uses),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
            self.conn.execute_query(cypher, params)
            self.stats["nodes_created"] += 1
            
        logger.info(f"  Created {len(self.parser.schemas)} Schema nodes")
    
    def _create_entity_nodes(self):
        """Create Entity nodes for AP239 concepts"""
        logger.info("\nCreating AP239 Entity nodes...")
        
        entity_count = 0
        for schema_name, schema in self.parser.schemas.items():
            for entity_name, entity in schema.entities.items():
                # Determine Neo4j label
                label = AP239_LABEL_MAP.get(entity_name, entity_name)
                
                # Create entity node
                cypher = f"""
                MERGE (e:Entity:AP239Entity:{label} {{name: $name, schema: $schema}})
                SET e.is_abstract = $is_abstract,
                    e.supertype = $supertype,
                    e.attribute_count = $attr_count,
                    e.ap_level = 'AP239',
                    e.uid = 'AP239-' + $schema + '-' + $name,
                    e.created_on = datetime($timestamp),
                    e.source_standard = 'ISO 10303-239'
                """
                
                params = {
                    "name": entity_name,
                    "schema": schema_name,
                    "is_abstract": entity.is_abstract,
                    "supertype": entity.supertype,
                    "attr_count": len(entity.attributes),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                
                self.conn.execute_query(cypher, params)
                entity_count += 1
                
                # Create relationship to Schema
                rel_cypher = """
                MATCH (s:Schema {name: $schema})
                MATCH (e:Entity {name: $entity, schema: $schema})
                MERGE (s)-[:DEFINES_ENTITY]->(e)
                """
                self.conn.execute_query(rel_cypher, {"schema": schema_name, "entity": entity_name})
                
                # Create supertype relationship if exists
                if entity.supertype:
                    super_cypher = """
                    MATCH (sub:Entity {name: $child, schema: $schema})
                    MERGE (sup:Entity {name: $parent})
                    ON CREATE SET sup.ap_level = 'AP239', sup.uid = 'AP239-' + $parent
                    MERGE (sub)-[:SUBTYPE_OF]->(sup)
                    """
                    self.conn.execute_query(super_cypher, {
                        "child": entity_name,
                        "parent": entity.supertype,
                        "schema": schema_name,
                    })
                    self.stats["relationships_created"] += 1
        
        self.stats["nodes_created"] += entity_count
        logger.info(f"  Created {entity_count} Entity nodes")
    
    def _create_type_nodes(self):
        """Create Type nodes for AP239 SELECT/ENUMERATION types"""
        logger.info("\nCreating AP239 Type nodes...")
        
        type_count = 0
        for schema_name, schema in self.parser.schemas.items():
            for type_name, type_def in schema.types.items():
                cypher = """
                MERGE (t:Type:AP239Type {name: $name, schema: $schema})
                SET t.kind = $kind,
                    t.base_type = $base_type,
                    t.options = $options,
                    t.ap_level = 'AP239',
                    t.uid = 'AP239-TYPE-' + $schema + '-' + $name,
                    t.created_on = datetime($timestamp)
                """
                
                params = {
                    "name": type_name,
                    "schema": schema_name,
                    "kind": type_def.kind,
                    "base_type": type_def.base_type,
                    "options": type_def.options[:50] if type_def.options else [],  # Limit options
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                
                self.conn.execute_query(cypher, params)
                type_count += 1
                
                # Link type to schema
                rel_cypher = """
                MATCH (s:Schema {name: $schema})
                MATCH (t:Type {name: $type_name, schema: $schema})
                MERGE (s)-[:DEFINES_TYPE]->(t)
                """
                self.conn.execute_query(rel_cypher, {"schema": schema_name, "type_name": type_name})
        
        self.stats["nodes_created"] += type_count
        logger.info(f"  Created {type_count} Type nodes")
    
    def _create_import_relationships(self):
        """Create IMPORTS relationships between schemas"""
        logger.info("\nCreating Schema import relationships...")
        
        rel_count = 0
        for schema_name, schema in self.parser.schemas.items():
            for imported_schema, comment in schema.uses:
                cypher = """
                MATCH (s1:Schema {name: $from_schema})
                MERGE (s2:Schema {name: $to_schema})
                ON CREATE SET s2.external = true, s2.uid = 'EXTERNAL-' + $to_schema
                MERGE (s1)-[r:IMPORTS]->(s2)
                SET r.comment = $comment
                """
                
                params = {
                    "from_schema": schema_name,
                    "to_schema": imported_schema,
                    "comment": comment,
                }
                
                self.conn.execute_query(cypher, params)
                rel_count += 1
        
        self.stats["relationships_created"] += rel_count
        logger.info(f"  Created {rel_count} IMPORTS relationships")
    
    def _print_summary(self):
        """Print ingestion summary"""
        logger.info("\n" + "=" * 70)
        logger.info("AP239 Ingestion Summary")
        logger.info("=" * 70)
        logger.info(f"  Schemas Parsed:        {self.stats['schemas_parsed']}")
        logger.info(f"  Entities Found:        {self.stats['entities_found']}")
        logger.info(f"  Types Found:           {self.stats['types_found']}")
        logger.info(f"  Nodes Created:         {self.stats['nodes_created']}")
        logger.info(f"  Relationships Created: {self.stats['relationships_created']}")
        if self.dry_run:
            logger.info("  [DRY RUN - No changes made to database]")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Ingest AP239 schemas into Neo4j")
    parser.add_argument("--dry-run", action="store_true", help="Parse only, don't write to database")
    parser.add_argument("--clear", action="store_true", help="Clear existing AP239 nodes before ingestion")
    args = parser.parse_args()
    
    # Load environment
    load_dotenv()
    
    # Determine paths
    project_root = Path(__file__).resolve().parent.parent.parent
    smrl_root = project_root / "smrlv12"
    
    if not smrl_root.exists():
        logger.error(f"SMRL root not found: {smrl_root}")
        sys.exit(1)
    
    # Load config
    config = Config()
    
    logger.info(f"Project Root: {project_root}")
    logger.info(f"SMRL Root: {smrl_root}")
    logger.info(f"Neo4j URI: {config.neo4j_uri}")
    
    # Connect to Neo4j
    with Neo4jConnection(config.neo4j_uri, config.neo4j_user, config.neo4j_password) as conn:
        conn.connect()
        
        # Clear existing AP239 nodes if requested
        if args.clear and not args.dry_run:
            logger.warning("Clearing existing AP239 nodes...")
            conn.execute_query("MATCH (n:AP239Schema) DETACH DELETE n")
            conn.execute_query("MATCH (n:AP239Entity) DETACH DELETE n")
            conn.execute_query("MATCH (n:AP239Type) DETACH DELETE n")
            logger.info("Cleared.")
        
        # Run ingestion
        ingester = AP239Ingester(smrl_root, conn, dry_run=args.dry_run)
        stats = ingester.ingest()
    
    logger.success("AP239 ingestion complete!")


if __name__ == "__main__":
    main()
