#!/usr/bin/env python3
"""
Base Schema Ingester
============================================================================
Abstract base class for EXPRESS schema ingestion into Neo4j Knowledge Graph.
Provides common functionality for AP239, AP242, AP243 ingesters.

Configuration:
    Uses .env for Neo4j connection settings
"""

import os
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from loguru import logger

from backend.src.parsers.express import (
    ExpressParser,
    ExpressSchema,
    ExpressEntity,
    ExpressType,
    ExpressNeo4jConverter,
    ParseResult,
)
from backend.src.graph.connection import Neo4jConnection
from backend.src.utils.config import Config


class BaseSchemaIngester(ABC):
    """
    Abstract base class for EXPRESS schema ingestion.
    
    Subclasses must implement:
        - get_module_names(): Return list of module directory names
        - get_label_map(): Return entity name to Neo4j label mapping
        - get_ap_level(): Return AP level (e.g., "AP239")
        - get_standard(): Return ISO standard (e.g., "ISO 10303-239")
        - get_domain(): Return domain description
    """
    
    def __init__(
        self,
        smrl_root: Path,
        connection: Optional[Neo4jConnection] = None,
        dry_run: bool = False,
        verbose: bool = True
    ):
        """
        Initialize the ingester.
        
        Args:
            smrl_root: Path to SMRL root directory
            connection: Neo4j connection (optional, creates from config if not provided)
            dry_run: If True, parse but don't write to Neo4j
            verbose: Enable verbose logging
        """
        self.smrl_root = smrl_root
        self.dry_run = dry_run
        self.verbose = verbose
        self.parser = ExpressParser()
        
        # Schema storage
        self.schemas: Dict[str, ExpressSchema] = {}
        
        # Statistics
        self.stats = {
            "schemas_parsed": 0,
            "schemas_failed": 0,
            "entities_found": 0,
            "types_found": 0,
            "imports_found": 0,
            "nodes_created": 0,
            "relationships_created": 0,
            "errors": [],
        }
        
        # Initialize connection
        if connection:
            self.conn = connection
        elif not dry_run:
            load_dotenv()
            config = Config()
            self.conn = Neo4jConnection(
                uri=config.neo4j_uri,
                user=config.neo4j_user,
                password=config.neo4j_password
            )
            self.conn.connect()  # Establish the actual connection
        else:
            self.conn = None
    
    # ========================================================================
    # Abstract methods - must be implemented by subclasses
    # ========================================================================
    
    @abstractmethod
    def get_module_names(self) -> List[str]:
        """Return list of module directory names to process"""
        pass
    
    @abstractmethod
    def get_label_map(self) -> Dict[str, str]:
        """Return entity name to Neo4j label mapping"""
        pass
    
    @abstractmethod
    def get_ap_level(self) -> str:
        """Return AP level identifier (e.g., 'AP239')"""
        pass
    
    @abstractmethod
    def get_standard(self) -> str:
        """Return ISO standard reference (e.g., 'ISO 10303-239')"""
        pass
    
    @abstractmethod
    def get_domain(self) -> str:
        """Return domain description"""
        pass
    
    # ========================================================================
    # Main ingestion workflow
    # ========================================================================
    
    def ingest(self) -> Dict[str, Any]:
        """
        Main ingestion workflow.
        
        Returns:
            Dictionary with ingestion statistics
        """
        ap_level = self.get_ap_level()
        
        logger.info("=" * 70)
        logger.info(f"{ap_level} Knowledge Graph Ingestion")
        logger.info(f"Standard: {self.get_standard()}")
        logger.info(f"Domain: {self.get_domain()}")
        logger.info("=" * 70)
        
        # Step 1: Parse all modules
        self._parse_all_modules()
        
        # Step 2: Create Neo4j nodes (if not dry run)
        if not self.dry_run and self.conn:
            self._create_schema_nodes()
            self._create_entity_nodes()
            self._create_type_nodes()
            self._create_import_relationships()
            self._create_inheritance_relationships()
        
        # Step 3: Print summary
        self._print_summary()
        
        return self.stats
    
    def _parse_all_modules(self):
        """Parse all module directories"""
        modules_dir = self.smrl_root / "data" / "modules"
        
        if not modules_dir.exists():
            logger.error(f"Modules directory not found: {modules_dir}")
            self.stats["errors"].append(f"Modules directory not found: {modules_dir}")
            return
        
        for module_name in self.get_module_names():
            module_path = modules_dir / module_name
            if module_path.exists():
                self._process_module(module_path, module_name)
            else:
                logger.warning(f"Module not found: {module_name}")
                self.stats["errors"].append(f"Module not found: {module_name}")
    
    def _process_module(self, module_path: Path, module_name: str):
        """Process a single module directory"""
        if self.verbose:
            logger.info(f"Processing: {module_name}")
        
        # Try ARM first (Application Reference Model)
        arm_file = module_path / "arm.exp"
        if arm_file.exists():
            result = self.parser.parse_file(str(arm_file))
            if result.success and result.parsed_schema:
                self.schemas[result.parsed_schema.name] = result.parsed_schema
                self.stats["schemas_parsed"] += 1
                self.stats["entities_found"] += len(result.parsed_schema.entities)
                self.stats["types_found"] += len(result.parsed_schema.types)
                self.stats["imports_found"] += len(result.parsed_schema.imports)
                
                if self.verbose and result.warnings:
                    for warning in result.warnings:
                        logger.warning(f"  {warning}")
            else:
                self.stats["schemas_failed"] += 1
                self.stats["errors"].append(f"Failed to parse {arm_file}: {result.error}")
                logger.error(f"  Failed: {result.error}")
        
        # Also try MIM (Module Interpreted Model)
        mim_file = module_path / "mim.exp"
        if mim_file.exists():
            result = self.parser.parse_file(str(mim_file))
            if result.success and result.parsed_schema:
                self.schemas[result.parsed_schema.name] = result.parsed_schema
                self.stats["schemas_parsed"] += 1
                self.stats["entities_found"] += len(result.parsed_schema.entities)
                self.stats["types_found"] += len(result.parsed_schema.types)
    
    # ========================================================================
    # Neo4j node creation
    # ========================================================================
    
    def _create_schema_nodes(self):
        """Create Schema nodes in Neo4j"""
        ap_level = self.get_ap_level()
        logger.info(f"\nCreating {ap_level} Schema nodes...")
        
        for schema_name, schema in self.schemas.items():
            cypher = f"""
            MERGE (s:Schema:{ap_level}Schema {{name: $name}})
            SET s.source_file = $source_file,
                s.entity_count = $entity_count,
                s.type_count = $type_count,
                s.import_count = $import_count,
                s.ap_level = $ap_level,
                s.standard = $standard,
                s.domain = $domain,
                s.created_on = datetime($timestamp),
                s.uid = $ap_level + '-' + $name
            RETURN s.name as name
            """
            
            params = {
                "name": schema_name,
                "source_file": str(schema.source_file),
                "entity_count": len(schema.entities),
                "type_count": len(schema.types),
                "import_count": len(schema.imports),
                "ap_level": ap_level,
                "standard": self.get_standard(),
                "domain": self.get_domain(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
            self.conn.execute_query(cypher, params)
            self.stats["nodes_created"] += 1
        
        logger.info(f"  Created {len(self.schemas)} Schema nodes")
    
    def _create_entity_nodes(self):
        """Create Entity nodes in Neo4j"""
        ap_level = self.get_ap_level()
        label_map = self.get_label_map()
        
        logger.info(f"\nCreating {ap_level} Entity nodes...")
        
        entity_count = 0
        for schema_name, schema in self.schemas.items():
            for entity_name, entity in schema.entities.items():
                # Get mapped label or use entity name
                label = label_map.get(entity_name, entity_name)
                
                # Create entity node with dynamic label
                cypher = f"""
                MERGE (e:Entity:{ap_level}Entity:{label} {{name: $name, schema: $schema}})
                SET e.is_abstract = $is_abstract,
                    e.supertype = $supertype,
                    e.attribute_count = $attr_count,
                    e.ap_level = $ap_level,
                    e.uid = $ap_level + '-' + $schema + '-' + $name,
                    e.created_on = datetime($timestamp),
                    e.source_standard = $standard
                """
                
                params = {
                    "name": entity_name,
                    "schema": schema_name,
                    "is_abstract": entity.is_abstract,
                    "supertype": entity.supertype,
                    "attr_count": len(entity.attributes),
                    "ap_level": ap_level,
                    "standard": self.get_standard(),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                
                self.conn.execute_query(cypher, params)
                entity_count += 1
                
                # Link to schema
                rel_cypher = """
                MATCH (s:Schema {name: $schema})
                MATCH (e:Entity {name: $entity, schema: $schema})
                MERGE (s)-[:DEFINES_ENTITY]->(e)
                """
                self.conn.execute_query(rel_cypher, {
                    "schema": schema_name,
                    "entity": entity_name
                })
                self.stats["relationships_created"] += 1
        
        self.stats["nodes_created"] += entity_count
        logger.info(f"  Created {entity_count} Entity nodes")
    
    def _create_type_nodes(self):
        """Create Type nodes for SELECT/ENUMERATION types"""
        ap_level = self.get_ap_level()
        logger.info(f"\nCreating {ap_level} Type nodes...")
        
        type_count = 0
        for schema_name, schema in self.schemas.items():
            for type_name, type_def in schema.types.items():
                cypher = f"""
                MERGE (t:Type:{ap_level}Type {{name: $name, schema: $schema}})
                SET t.kind = $kind,
                    t.base_type = $base_type,
                    t.options = $options,
                    t.ap_level = $ap_level,
                    t.uid = $ap_level + '-TYPE-' + $schema + '-' + $name,
                    t.created_on = datetime($timestamp)
                """
                
                # Limit options to avoid large arrays
                options = type_def.options[:50] if type_def.options else []
                
                params = {
                    "name": type_name,
                    "schema": schema_name,
                    "kind": type_def.kind,
                    "base_type": type_def.base_type,
                    "options": options,
                    "ap_level": ap_level,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                
                self.conn.execute_query(cypher, params)
                type_count += 1
                
                # Link to schema
                rel_cypher = """
                MATCH (s:Schema {name: $schema})
                MATCH (t:Type {name: $type_name, schema: $schema})
                MERGE (s)-[:DEFINES_TYPE]->(t)
                """
                self.conn.execute_query(rel_cypher, {
                    "schema": schema_name,
                    "type_name": type_name
                })
                self.stats["relationships_created"] += 1
        
        self.stats["nodes_created"] += type_count
        logger.info(f"  Created {type_count} Type nodes")
    
    def _create_import_relationships(self):
        """Create IMPORTS relationships between schemas"""
        ap_level = self.get_ap_level()
        logger.info(f"\nCreating {ap_level} import relationships...")
        
        rel_count = 0
        for schema_name, schema in self.schemas.items():
            for imp in schema.imports:
                cypher = """
                MATCH (s1:Schema {name: $from_schema})
                MERGE (s2:Schema {name: $to_schema})
                ON CREATE SET s2.external = true, s2.uid = 'EXTERNAL-' + $to_schema
                MERGE (s1)-[r:IMPORTS]->(s2)
                SET r.comment = $comment
                """
                
                params = {
                    "from_schema": schema_name,
                    "to_schema": imp.schema_name,
                    "comment": imp.comment,
                }
                
                self.conn.execute_query(cypher, params)
                rel_count += 1
        
        self.stats["relationships_created"] += rel_count
        logger.info(f"  Created {rel_count} IMPORTS relationships")
    
    def _create_inheritance_relationships(self):
        """Create SUBTYPE_OF relationships between entities"""
        ap_level = self.get_ap_level()
        logger.info(f"\nCreating {ap_level} inheritance relationships...")
        
        rel_count = 0
        for schema_name, schema in self.schemas.items():
            for entity_name, entity in schema.entities.items():
                if entity.supertype:
                    cypher = """
                    MATCH (sub:Entity {name: $child, schema: $schema})
                    MERGE (sup:Entity {name: $parent})
                    ON CREATE SET sup.ap_level = $ap_level, sup.uid = $ap_level + '-' + $parent
                    MERGE (sub)-[:SUBTYPE_OF]->(sup)
                    """
                    
                    self.conn.execute_query(cypher, {
                        "child": entity_name,
                        "parent": entity.supertype,
                        "schema": schema_name,
                        "ap_level": ap_level,
                    })
                    rel_count += 1
        
        self.stats["relationships_created"] += rel_count
        logger.info(f"  Created {rel_count} SUBTYPE_OF relationships")
    
    # ========================================================================
    # Utilities
    # ========================================================================
    
    def _print_summary(self):
        """Print ingestion summary"""
        ap_level = self.get_ap_level()
        
        logger.info("\n" + "=" * 70)
        logger.info(f"{ap_level} Ingestion Summary")
        logger.info("=" * 70)
        logger.info(f"  Schemas parsed:        {self.stats['schemas_parsed']}")
        logger.info(f"  Schemas failed:        {self.stats['schemas_failed']}")
        logger.info(f"  Entities found:        {self.stats['entities_found']}")
        logger.info(f"  Types found:           {self.stats['types_found']}")
        logger.info(f"  Imports found:         {self.stats['imports_found']}")
        
        if not self.dry_run:
            logger.info(f"  Nodes created:         {self.stats['nodes_created']}")
            logger.info(f"  Relationships created: {self.stats['relationships_created']}")
        else:
            logger.info("  [DRY RUN - No changes made to Neo4j]")
        
        if self.stats['errors']:
            logger.warning(f"\nErrors ({len(self.stats['errors'])}):")
            for error in self.stats['errors'][:10]:  # Show first 10
                logger.warning(f"  - {error}")
        
        logger.info("=" * 70)
    
    def get_parsed_schemas(self) -> Dict[str, ExpressSchema]:
        """Return dictionary of parsed schemas"""
        return self.schemas
    
    def close(self):
        """Close Neo4j connection"""
        if self.conn:
            self.conn.close()
