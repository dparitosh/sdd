#!/usr/bin/env python3
"""
XSD Schema Ingester (Optimized with Batch Operations)
============================================================================
Parse XML Schema Definition (XSD) files and create Knowledge Graph in Neo4j.

Supports:
    - W3C XML Schema 1.0/1.1
    - ISO 10303-15 STEP XML Schema
    - Complex types, simple types, elements, attributes
    - Type hierarchies and references

Data Sources:
    smrlv12/data/domain_models/product_life_cycle_support/Domain_model.xsd
    smrlv12/data/domain_models/managed_model_based_3d_engineering_domain/DomainModel.xsd
    smrlv12/data/business_object_models/managed_model_based_3d_engineering/bom.xsd

Node Types Created:
    - XSDSchema: Root schema information
    - XSDComplexType: Complex type definitions
    - XSDSimpleType: Simple type definitions (restrictions, enums)
    - XSDElement: Global and local element definitions
    - XSDAttribute: Attribute definitions
    - XSDGroup: Model group definitions
    - XSDAttributeGroup: Attribute group definitions

Usage:
    python backend/scripts/ingest_xsd.py [--dry-run] [--clear]
    python backend/scripts/ingest_xsd.py --file path/to/schema.xsd

Configuration:
    Uses .env for Neo4j connection settings
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Set
from lxml import etree

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from loguru import logger

from backend.src.graph.connection import Neo4jConnection
from backend.src.utils.config import Config

# Batch size for Neo4j operations
BATCH_SIZE = 500


class XSDIngester:
    """
    Ingest XML Schema Definition (XSD) files into Neo4j Knowledge Graph.
    Uses batch operations for performance.
    """
    
    # XSD namespace
    XSD_NS = 'http://www.w3.org/2001/XMLSchema'
    XSD = '{http://www.w3.org/2001/XMLSchema}'
    
    NAMESPACES = {
        'xs': 'http://www.w3.org/2001/XMLSchema',
        'xsd': 'http://www.w3.org/2001/XMLSchema',
    }
    
    def __init__(
        self,
        connection: Optional[Neo4jConnection] = None,
        dry_run: bool = False,
        verbose: bool = True
    ):
        self.dry_run = dry_run
        self.verbose = verbose
        
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
            self.conn.connect()
        else:
            self.conn = None
        
        # Statistics
        self.stats = {
            "files_processed": 0,
            "nodes_created": 0,
            "relationships_created": 0,
            "schemas": [],
            "elements_by_type": {},
            "errors": [],
        }
        
        # Element tracking
        self.elements: Dict[str, Dict[str, Any]] = {}
        self.relationships: List[Dict[str, Any]] = []
        self.current_schema: str = ""
        self.current_ns: str = ""
    
    def ingest_file(self, file_path: Path) -> Dict[str, Any]:
        """Ingest a single XSD file"""
        logger.info(f"Processing XSD file: {file_path.name}")
        
        try:
            tree = etree.parse(str(file_path))
            root = tree.getroot()
            
            # Get schema info
            target_ns = root.get('targetNamespace', '')
            self.current_ns = target_ns
            self.current_schema = file_path.stem
            
            # Create schema node
            schema_id = f"schema:{self.current_schema}"
            self.elements[schema_id] = {
                'id': schema_id,
                'type': 'XSDSchema',
                'name': self.current_schema,
                'target_namespace': target_ns,
                'source_file': str(file_path),
                'element_form_default': root.get('elementFormDefault', 'unqualified'),
                'attribute_form_default': root.get('attributeFormDefault', 'unqualified'),
            }
            self.stats["schemas"].append(self.current_schema)
            
            # Extract all elements
            self._extract_elements(root, schema_id, file_path)
            
            # Create nodes in Neo4j
            if not self.dry_run and self.conn:
                self._create_nodes()
                self._create_relationships()
            
            self.stats["files_processed"] += 1
            
            logger.info(f"  Extracted {len(self.elements)} elements from {file_path.name}")
            
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            self.stats["errors"].append(f"{file_path.name}: {str(e)}")
        
        return self.stats
    
    def ingest_directory(self, directory: Path, pattern: str = "*.xsd") -> Dict[str, Any]:
        """Ingest all XSD files in a directory"""
        logger.info(f"Scanning directory: {directory}")
        
        xsd_files = list(directory.rglob(pattern))
        logger.info(f"Found {len(xsd_files)} XSD files")
        
        for xsd_file in xsd_files:
            self.ingest_file(xsd_file)
        
        return self.stats
    
    def _extract_elements(self, root: etree._Element, schema_id: str, source_file: Path):
        """Extract all schema elements from XSD"""
        
        # Process complexTypes
        for ct in root.findall(f'{self.XSD}complexType'):
            self._process_complex_type(ct, schema_id)
        
        # Process simpleTypes
        for st in root.findall(f'{self.XSD}simpleType'):
            self._process_simple_type(st, schema_id)
        
        # Process global elements
        for elem in root.findall(f'{self.XSD}element'):
            self._process_element(elem, schema_id, is_global=True)
        
        # Process groups
        for group in root.findall(f'{self.XSD}group'):
            self._process_group(group, schema_id)
        
        # Process attributeGroups
        for ag in root.findall(f'{self.XSD}attributeGroup'):
            self._process_attribute_group(ag, schema_id)
        
        # Process imports/includes
        for imp in root.findall(f'{self.XSD}import'):
            ns = imp.get('namespace', '')
            loc = imp.get('schemaLocation', '')
            if ns or loc:
                self.relationships.append({
                    'from_id': schema_id,
                    'to_type': 'XSDSchema',
                    'to_name': loc or ns,
                    'type': 'IMPORTS',
                })
    
    def _process_complex_type(self, elem: etree._Element, parent_id: str):
        """Process complexType element"""
        name = elem.get('name', '')
        if not name:
            return
        
        elem_id = f"ct:{self.current_schema}:{name}"
        
        # Check for base type (extension/restriction)
        base_type = None
        cc = elem.find(f'{self.XSD}complexContent')
        if cc is not None:
            ext = cc.find(f'{self.XSD}extension')
            if ext is not None:
                base_type = ext.get('base', '')
            rest = cc.find(f'{self.XSD}restriction')
            if rest is not None:
                base_type = rest.get('base', '')
        
        self.elements[elem_id] = {
            'id': elem_id,
            'type': 'XSDComplexType',
            'name': name,
            'schema': self.current_schema,
            'is_abstract': elem.get('abstract', 'false') == 'true',
            'is_mixed': elem.get('mixed', 'false') == 'true',
            'base_type': base_type or '',
        }
        
        # Link to schema
        self.relationships.append({
            'from_id': parent_id,
            'to_id': elem_id,
            'type': 'DEFINES',
        })
        
        # Link to base type
        if base_type:
            # Clean namespace prefix
            base_name = base_type.split(':')[-1] if ':' in base_type else base_type
            self.relationships.append({
                'from_id': elem_id,
                'to_type': 'XSDComplexType',
                'to_name': base_name,
                'type': 'EXTENDS',
            })
        
        # Process nested elements
        self._process_sequence_or_choice(elem, elem_id)
        
        # Process attributes
        for attr in elem.findall(f'.//{self.XSD}attribute'):
            self._process_attribute(attr, elem_id)
        
        self._update_stats('XSDComplexType')
    
    def _process_simple_type(self, elem: etree._Element, parent_id: str):
        """Process simpleType element"""
        name = elem.get('name', '')
        if not name:
            return
        
        elem_id = f"st:{self.current_schema}:{name}"
        
        # Check for restriction info
        base_type = ''
        enumeration_values = []
        pattern = ''
        
        rest = elem.find(f'{self.XSD}restriction')
        if rest is not None:
            base_type = rest.get('base', '')
            for enum in rest.findall(f'{self.XSD}enumeration'):
                val = enum.get('value', '')
                if val:
                    enumeration_values.append(val)
            pat = rest.find(f'{self.XSD}pattern')
            if pat is not None:
                pattern = pat.get('value', '')
        
        self.elements[elem_id] = {
            'id': elem_id,
            'type': 'XSDSimpleType',
            'name': name,
            'schema': self.current_schema,
            'base_type': base_type.split(':')[-1] if base_type else '',
            'is_enumeration': len(enumeration_values) > 0,
            'enumeration_values': enumeration_values[:50],  # Limit stored values
            'pattern': pattern,
        }
        
        # Link to schema
        self.relationships.append({
            'from_id': parent_id,
            'to_id': elem_id,
            'type': 'DEFINES',
        })
        
        self._update_stats('XSDSimpleType')
    
    def _process_element(self, elem: etree._Element, parent_id: str, is_global: bool = False):
        """Process element definition"""
        name = elem.get('name', '')
        if not name:
            return
        
        prefix = "ge" if is_global else "le"
        elem_id = f"{prefix}:{self.current_schema}:{name}"
        
        type_ref = elem.get('type', '')
        min_occurs = elem.get('minOccurs', '1')
        max_occurs = elem.get('maxOccurs', '1')
        
        self.elements[elem_id] = {
            'id': elem_id,
            'type': 'XSDElement',
            'name': name,
            'schema': self.current_schema,
            'type_ref': type_ref.split(':')[-1] if type_ref else '',
            'is_global': is_global,
            'min_occurs': min_occurs,
            'max_occurs': max_occurs,
            'is_nillable': elem.get('nillable', 'false') == 'true',
            'default_value': elem.get('default', ''),
            'fixed_value': elem.get('fixed', ''),
        }
        
        # Link to parent
        self.relationships.append({
            'from_id': parent_id,
            'to_id': elem_id,
            'type': 'CONTAINS' if not is_global else 'DEFINES',
        })
        
        # Link to type
        if type_ref:
            type_name = type_ref.split(':')[-1]
            self.relationships.append({
                'from_id': elem_id,
                'to_name': type_name,
                'to_type': 'XSDType',
                'type': 'HAS_TYPE',
            })
        
        self._update_stats('XSDElement')
    
    def _process_attribute(self, elem: etree._Element, parent_id: str):
        """Process attribute definition"""
        name = elem.get('name', '')
        if not name:
            return
        
        elem_id = f"attr:{self.current_schema}:{parent_id}:{name}"
        
        type_ref = elem.get('type', '')
        
        self.elements[elem_id] = {
            'id': elem_id,
            'type': 'XSDAttribute',
            'name': name,
            'schema': self.current_schema,
            'type_ref': type_ref.split(':')[-1] if type_ref else '',
            'use': elem.get('use', 'optional'),
            'default_value': elem.get('default', ''),
            'fixed_value': elem.get('fixed', ''),
        }
        
        # Link to parent
        self.relationships.append({
            'from_id': parent_id,
            'to_id': elem_id,
            'type': 'HAS_ATTRIBUTE',
        })
        
        self._update_stats('XSDAttribute')
    
    def _process_group(self, elem: etree._Element, parent_id: str):
        """Process group definition"""
        name = elem.get('name', '')
        if not name:
            return
        
        elem_id = f"grp:{self.current_schema}:{name}"
        
        self.elements[elem_id] = {
            'id': elem_id,
            'type': 'XSDGroup',
            'name': name,
            'schema': self.current_schema,
        }
        
        # Link to schema
        self.relationships.append({
            'from_id': parent_id,
            'to_id': elem_id,
            'type': 'DEFINES',
        })
        
        # Process nested elements
        self._process_sequence_or_choice(elem, elem_id)
        
        self._update_stats('XSDGroup')
    
    def _process_attribute_group(self, elem: etree._Element, parent_id: str):
        """Process attributeGroup definition"""
        name = elem.get('name', '')
        if not name:
            return
        
        elem_id = f"ag:{self.current_schema}:{name}"
        
        self.elements[elem_id] = {
            'id': elem_id,
            'type': 'XSDAttributeGroup',
            'name': name,
            'schema': self.current_schema,
        }
        
        # Link to schema
        self.relationships.append({
            'from_id': parent_id,
            'to_id': elem_id,
            'type': 'DEFINES',
        })
        
        # Process nested attributes
        for attr in elem.findall(f'{self.XSD}attribute'):
            self._process_attribute(attr, elem_id)
        
        self._update_stats('XSDAttributeGroup')
    
    def _process_sequence_or_choice(self, parent: etree._Element, parent_id: str):
        """Process sequence/choice/all containers"""
        for seq in parent.findall(f'.//{self.XSD}sequence'):
            for child in seq.findall(f'{self.XSD}element'):
                self._process_element(child, parent_id, is_global=False)
        
        for choice in parent.findall(f'.//{self.XSD}choice'):
            for child in choice.findall(f'{self.XSD}element'):
                self._process_element(child, parent_id, is_global=False)
        
        for all_elem in parent.findall(f'.//{self.XSD}all'):
            for child in all_elem.findall(f'{self.XSD}element'):
                self._process_element(child, parent_id, is_global=False)
    
    def _update_stats(self, elem_type: str):
        """Update statistics counter"""
        if elem_type not in self.stats["elements_by_type"]:
            self.stats["elements_by_type"][elem_type] = 0
        self.stats["elements_by_type"][elem_type] += 1
    
    def _create_nodes(self):
        """Create nodes in Neo4j using batch operations"""
        logger.info("Creating XSD nodes (batched)...")
        
        # Group elements by type for efficient batch creation
        by_type: Dict[str, List[Dict]] = {}
        for elem_id, elem in self.elements.items():
            elem_type = elem['type']
            if elem_type not in by_type:
                by_type[elem_type] = []
            
            # Prepare properties
            props = {k: v for k, v in elem.items() if k not in ('type', 'enumeration_values')}
            if 'enumeration_values' in elem:
                props['enumeration_values'] = ';'.join(elem['enumeration_values'])
            by_type[elem_type].append(props)
        
        # Create nodes in batches by type
        for elem_type, items in by_type.items():
            labels = f"{elem_type}:XSDElement"
            
            # Process in batches
            for i in range(0, len(items), BATCH_SIZE):
                batch = items[i:i + BATCH_SIZE]
                
                cypher = f"""
                    UNWIND $batch AS props
                    MERGE (n:{labels} {{id: props.id}})
                    SET n += props
                """
                
                try:
                    self.conn.execute_query(cypher, {'batch': batch})
                    self.stats["nodes_created"] += len(batch)
                except Exception as e:
                    logger.warning(f"Error creating batch of {elem_type}: {e}")
            
            logger.info(f"  Created {len(items)} {elem_type} nodes")
        
        logger.info(f"  Total nodes created: {self.stats['nodes_created']}")
    
    def _create_relationships(self):
        """Create relationships in Neo4j using batch operations"""
        logger.info("Creating XSD relationships (batched)...")
        
        # Group relationships by type for efficient batch creation
        by_type: Dict[str, List[Dict]] = {}
        for rel in self.relationships:
            rel_type = rel['type']
            from_id = rel.get('from_id')
            to_id = rel.get('to_id')
            
            # Only process direct ID relationships (skip name-based ones for now)
            if from_id and to_id:
                if from_id in self.elements and to_id in self.elements:
                    if rel_type not in by_type:
                        by_type[rel_type] = []
                    by_type[rel_type].append({'from_id': from_id, 'to_id': to_id})
        
        # Create relationships in batches
        for rel_type, items in by_type.items():
            for i in range(0, len(items), BATCH_SIZE):
                batch = items[i:i + BATCH_SIZE]
                
                cypher = f"""
                    UNWIND $batch AS rel
                    MATCH (a:XSDElement {{id: rel.from_id}})
                    MATCH (b:XSDElement {{id: rel.to_id}})
                    MERGE (a)-[r:{rel_type}]->(b)
                """
                
                try:
                    self.conn.execute_query(cypher, {'batch': batch})
                    self.stats["relationships_created"] += len(batch)
                except Exception as e:
                    logger.warning(f"Error creating {rel_type} relationships: {e}")
            
            logger.info(f"  Created {len(items)} {rel_type} relationships")
        
        logger.info(f"  Total relationships created: {self.stats['relationships_created']}")
    
    def print_summary(self):
        """Print ingestion summary"""
        logger.info("=" * 70)
        logger.info("XSD INGESTION SUMMARY")
        logger.info("=" * 70)
        logger.info(f"  Files processed: {self.stats['files_processed']}")
        logger.info(f"  Schemas: {', '.join(self.stats['schemas'])}")
        logger.info(f"  Nodes created: {self.stats['nodes_created']}")
        logger.info(f"  Relationships created: {self.stats['relationships_created']}")
        
        if self.stats["elements_by_type"]:
            logger.info("  Elements by type:")
            for elem_type, count in sorted(self.stats["elements_by_type"].items()):
                logger.info(f"    {elem_type}: {count}")
        
        if self.stats["errors"]:
            logger.warning(f"  Errors ({len(self.stats['errors'])}):")
            for err in self.stats["errors"][:10]:
                logger.warning(f"    - {err}")
        
        logger.info("=" * 70)
    
    def close(self):
        """Close Neo4j connection"""
        if self.conn:
            self.conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Ingest XSD schema files into Neo4j Knowledge Graph"
    )
    parser.add_argument(
        '--file', '-f',
        type=Path,
        help='Specific XSD file to ingest'
    )
    parser.add_argument(
        '--directory', '-d',
        type=Path,
        help='Directory containing XSD files'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Parse only, do not write to Neo4j'
    )
    parser.add_argument(
        '--clear',
        action='store_true',
        help='Clear existing XSD nodes before ingestion'
    )
    
    args = parser.parse_args()
    
    # Default to SMRL data directories
    if not args.file and not args.directory:
        args.directory = PROJECT_ROOT / 'smrlv12' / 'data'
    
    ingester = XSDIngester(dry_run=args.dry_run)
    
    try:
        # Clear if requested
        if args.clear and not args.dry_run and ingester.conn:
            logger.warning("Clearing existing XSD nodes...")
            ingester.conn.execute_query("MATCH (n:XSDElement) DETACH DELETE n")
        
        # Ingest
        if args.file:
            ingester.ingest_file(args.file)
        elif args.directory:
            ingester.ingest_directory(args.directory)
        
        ingester.print_summary()
        
    finally:
        ingester.close()


if __name__ == "__main__":
    main()
