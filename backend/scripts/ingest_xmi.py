#!/usr/bin/env python3
"""
XMI Domain Model Ingester
============================================================================
Parse XMI (UML/SysML) domain models and create Knowledge Graph in Neo4j.

Supports:
    - OMG UML 2.5.1 XMI format
    - OMG SysML 1.6 profiles
    - MagicDraw/Cameo XMI exports
    - Eclipse Papyrus XMI exports

Data Sources:
    smrlv12/data/domain_models/mossec/Domain_model.xmi

Node Types Created:
    - Package, Class, Interface, Component
    - Property, Operation, Parameter
    - Block, Requirement, ValueType (SysML)
    - Association, Generalization

Usage:
    python backend/scripts/ingest_xmi.py [--dry-run] [--clear]
    python backend/scripts/ingest_xmi.py --file path/to/model.xmi

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


class XMIIngester:
    """
    Ingest XMI (UML/SysML) domain models into Neo4j Knowledge Graph.
    """
    
    # XMI namespaces
    NAMESPACES = {
        'xmi': 'http://www.omg.org/spec/XMI/20131001',
        'uml': 'http://www.omg.org/spec/UML/20131001',
        'sysml': 'http://www.omg.org/spec/SysML/20150709/SysML',
        'StandardProfile': 'http://www.omg.org/spec/UML/20131001/StandardProfile',
    }
    
    # Node types to extract - includes both qualified and local names
    NODE_TYPES = {
        # UML Core - qualified names
        '{http://www.omg.org/spec/UML/20131001}Model': 'Model',
        '{http://www.omg.org/spec/UML/20131001}Package': 'Package',
        '{http://www.omg.org/spec/UML/20131001}Class': 'Class',
        '{http://www.omg.org/spec/UML/20131001}Interface': 'Interface',
        '{http://www.omg.org/spec/UML/20131001}Component': 'Component',
        '{http://www.omg.org/spec/UML/20131001}Property': 'Property',
        '{http://www.omg.org/spec/UML/20131001}Operation': 'Operation',
        '{http://www.omg.org/spec/UML/20131001}Parameter': 'Parameter',
        '{http://www.omg.org/spec/UML/20131001}DataType': 'DataType',
        '{http://www.omg.org/spec/UML/20131001}Enumeration': 'Enumeration',
        '{http://www.omg.org/spec/UML/20131001}EnumerationLiteral': 'EnumerationLiteral',
        '{http://www.omg.org/spec/UML/20131001}PrimitiveType': 'PrimitiveType',
        '{http://www.omg.org/spec/UML/20131001}Association': 'Association',
        '{http://www.omg.org/spec/UML/20131001}Port': 'Port',
        '{http://www.omg.org/spec/UML/20131001}Connector': 'Connector',
        # UML Behavioral - qualified names
        '{http://www.omg.org/spec/UML/20131001}StateMachine': 'StateMachine',
        '{http://www.omg.org/spec/UML/20131001}State': 'State',
        '{http://www.omg.org/spec/UML/20131001}Transition': 'Transition',
        '{http://www.omg.org/spec/UML/20131001}Activity': 'Activity',
        '{http://www.omg.org/spec/UML/20131001}Action': 'Action',
        # Local names (for xmi:type="uml:Class" style)
        'Model': 'Model',
        'Package': 'Package',
        'Class': 'Class',
        'Interface': 'Interface',
        'Component': 'Component',
        'Property': 'Property',
        'Operation': 'Operation',
        'Parameter': 'Parameter',
        'DataType': 'DataType',
        'Enumeration': 'Enumeration',
        'EnumerationLiteral': 'EnumerationLiteral',
        'PrimitiveType': 'PrimitiveType',
        'Association': 'Association',
        'Port': 'Port',
        'Connector': 'Connector',
        'StateMachine': 'StateMachine',
        'State': 'State',
        'Transition': 'Transition',
        'Activity': 'Activity',
        'Action': 'Action',
        'InstanceSpecification': 'InstanceSpecification',
        'Comment': 'Comment',
        'Constraint': 'Constraint',
        'Dependency': 'Dependency',
        'Abstraction': 'Abstraction',
        'Realization': 'Realization',
        'Usage': 'Usage',
        'Signal': 'Signal',
        'Reception': 'Reception',
        'Generalization': 'Generalization',
        # SysML
        'Block': 'Block',
        'Requirement': 'Requirement',
        'ValueType': 'ValueType',
        'FlowPort': 'FlowPort',
        'InterfaceBlock': 'InterfaceBlock',
        'ConstraintBlock': 'ConstraintBlock',
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
            load_dotenv(PROJECT_ROOT / ".env")
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
            "elements_found": {},
            "errors": [],
        }
        
        # Element tracking
        self.elements: Dict[str, Dict[str, Any]] = {}
        self.relationships: List[Dict[str, Any]] = []
    
    def ingest_file(self, file_path: Path) -> Dict[str, Any]:
        """Ingest a single XMI file"""
        logger.info(f"Processing XMI file: {file_path.name}")
        
        try:
            tree = etree.parse(str(file_path))
            root = tree.getroot()
            
            # Extract all elements
            self._extract_elements(root, file_path)
            
            # Create nodes in Neo4j
            if not self.dry_run and self.conn:
                self._create_nodes()
                self._create_relationships()
            
            self.stats["files_processed"] += 1
            
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            self.stats["errors"].append(f"{file_path.name}: {str(e)}")
        
        return self.stats
    
    def ingest_directory(self, directory: Path, pattern: str = "*.xmi") -> Dict[str, Any]:
        """Ingest all XMI files in a directory"""
        logger.info(f"Scanning directory: {directory}")
        
        xmi_files = list(directory.rglob(pattern))
        logger.info(f"Found {len(xmi_files)} XMI files")
        
        for xmi_file in xmi_files:
            self.ingest_file(xmi_file)
        
        return self.stats
    
    def _extract_elements(self, root: etree._Element, source_file: Path):
        """Extract all UML/SysML elements from XMI"""
        
        # Process all elements recursively
        for elem in root.iter():
            xmi_type = elem.get('{http://www.omg.org/spec/XMI/20131001}type')
            xmi_id = elem.get('{http://www.omg.org/spec/XMI/20131001}id')
            
            if not xmi_id:
                continue
            
            # Determine element type - handle both xmi:type="uml:Class" and tag names
            elem_type = None
            
            # First try xmi:type attribute (e.g., "uml:Package", "uml:Class")
            if xmi_type:
                # Handle prefix:type format
                type_local = xmi_type.split(':')[-1] if ':' in xmi_type else xmi_type
                if type_local in self.NODE_TYPES:
                    elem_type = self.NODE_TYPES[type_local]
                elif xmi_type in self.NODE_TYPES:
                    elem_type = self.NODE_TYPES[xmi_type]
            
            # Then try full qualified tag name
            if not elem_type:
                if elem.tag in self.NODE_TYPES:
                    elem_type = self.NODE_TYPES[elem.tag]
                else:
                    # Try just the local name
                    local_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                    if local_name in self.NODE_TYPES:
                        elem_type = self.NODE_TYPES[local_name]
            
            if elem_type:
                # Extract element data - check both attribute and child element for name
                name = elem.get('name', '')
                if not name:
                    # Try to find <name> child element (MagicDraw/Cameo XMI format)
                    name_elem = elem.find('name')
                    if name_elem is not None and name_elem.text:
                        name = name_elem.text
                
                # Same for visibility and isAbstract - check child elements
                visibility = elem.get('visibility', '')
                if not visibility:
                    vis_elem = elem.find('visibility')
                    if vis_elem is not None and vis_elem.text:
                        visibility = vis_elem.text
                    else:
                        visibility = 'public'
                
                is_abstract_attr = elem.get('isAbstract', '')
                if not is_abstract_attr:
                    abs_elem = elem.find('isAbstract')
                    if abs_elem is not None and abs_elem.text:
                        is_abstract_attr = abs_elem.text
                is_abstract = is_abstract_attr == 'true'
                
                element_data = {
                    'xmi_id': xmi_id,
                    'type': elem_type,
                    'name': name,
                    'visibility': visibility,
                    'is_abstract': is_abstract,
                    'source_file': str(source_file),
                }
                
                # Extract additional properties based on type
                if elem_type == 'Property':
                    element_data['type_ref'] = elem.get('type')
                    element_data['aggregation'] = elem.get('aggregation', 'none')
                    element_data['is_derived'] = elem.get('isDerived', 'false') == 'true'
                    element_data['is_read_only'] = elem.get('isReadOnly', 'false') == 'true'
                
                elif elem_type == 'Operation':
                    element_data['is_query'] = elem.get('isQuery', 'false') == 'true'
                    element_data['is_static'] = elem.get('isStatic', 'false') == 'true'
                
                elif elem_type in ('Class', 'Interface', 'Block'):
                    element_data['is_final'] = elem.get('isFinalSpecialization', 'false') == 'true'
                
                elif elem_type == 'Comment':
                    # Extract comment body
                    body_elem = elem.find('body')
                    if body_elem is not None and body_elem.text:
                        element_data['body'] = body_elem.text[:500]  # Truncate long comments
                
                # Track parent element
                parent = elem.getparent()
                if parent is not None:
                    parent_id = parent.get('{http://www.omg.org/spec/XMI/20131001}id')
                    if parent_id:
                        element_data['parent_id'] = parent_id
                        self.relationships.append({
                            'from_id': parent_id,
                            'to_id': xmi_id,
                            'type': 'CONTAINS',
                        })
                
                # Extract generalization relationships
                for gen in elem.findall('.//generalization', self.NAMESPACES):
                    general_ref = gen.get('general')
                    if general_ref:
                        self.relationships.append({
                            'from_id': xmi_id,
                            'to_id': general_ref,
                            'type': 'GENERALIZES',
                        })
                
                self.elements[xmi_id] = element_data
                
                # Update stats
                if elem_type not in self.stats["elements_found"]:
                    self.stats["elements_found"][elem_type] = 0
                self.stats["elements_found"][elem_type] += 1
        
        logger.info(f"  Found {len(self.elements)} elements")
    
    def _create_nodes(self):
        """Create nodes in Neo4j using batch operations"""
        logger.info("Creating XMI element nodes (batched)...")
        
        # Group elements by type for efficient batch creation
        by_type: Dict[str, List[Dict]] = {}
        for xmi_id, elem in self.elements.items():
            elem_type = elem['type']
            if elem_type not in by_type:
                by_type[elem_type] = []
            
            # Build properties
            props = {
                'xmi_id': elem['xmi_id'],
                'name': elem.get('name', ''),
                'visibility': elem.get('visibility', 'public'),
                'is_abstract': elem.get('is_abstract', False),
                'source_file': elem.get('source_file', ''),
            }
            
            # Add type-specific properties
            for key in ['type_ref', 'aggregation', 'is_derived', 'is_read_only', 
                       'is_query', 'is_static', 'is_final', 'body']:
                if key in elem and elem[key] is not None:
                    props[key] = elem[key]
            
            by_type[elem_type].append(props)
        
        # Create nodes in batches by type
        BATCH_SIZE = 500
        for elem_type, items in by_type.items():
            labels = f"{elem_type}:XMIElement"
            
            for i in range(0, len(items), BATCH_SIZE):
                batch = items[i:i + BATCH_SIZE]
                
                cypher = f"""
                    UNWIND $batch AS props
                    MERGE (n:{labels} {{xmi_id: props.xmi_id}})
                    SET n += props
                """
                
                try:
                    self.conn.execute_query(cypher, {'batch': batch})
                    self.stats["nodes_created"] += len(batch)
                except Exception as e:
                    logger.warning(f"Error creating batch of {elem_type}: {e}")
            
            logger.info(f"    Created {len(items)} {elem_type} nodes")
        
        logger.info(f"  Total nodes created: {self.stats['nodes_created']}")
    
    def _create_relationships(self):
        """Create relationships in Neo4j using batch operations"""
        logger.info("Creating XMI relationships (batched)...")
        
        # Group relationships by type
        by_type: Dict[str, List[Dict]] = {}
        for rel in self.relationships:
            from_id = rel['from_id']
            to_id = rel['to_id']
            rel_type = rel['type']
            
            if from_id in self.elements and to_id in self.elements:
                if rel_type not in by_type:
                    by_type[rel_type] = []
                by_type[rel_type].append({'from_id': from_id, 'to_id': to_id})
        
        # Create relationships in batches
        BATCH_SIZE = 500
        for rel_type, items in by_type.items():
            for i in range(0, len(items), BATCH_SIZE):
                batch = items[i:i + BATCH_SIZE]
                
                cypher = f"""
                    UNWIND $batch AS rel
                    MATCH (a:XMIElement {{xmi_id: rel.from_id}})
                    MATCH (b:XMIElement {{xmi_id: rel.to_id}})
                    MERGE (a)-[r:{rel_type}]->(b)
                """
                
                try:
                    self.conn.execute_query(cypher, {'batch': batch})
                    self.stats["relationships_created"] += len(batch)
                except Exception as e:
                    logger.warning(f"Error creating {rel_type} relationships: {e}")
            
            logger.info(f"    Created {len(items)} {rel_type} relationships")
        
        logger.info(f"  Total relationships created: {self.stats['relationships_created']}")
    
    def print_summary(self):
        """Print ingestion summary"""
        logger.info("=" * 70)
        logger.info("XMI INGESTION SUMMARY")
        logger.info("=" * 70)
        logger.info(f"  Files processed: {self.stats['files_processed']}")
        logger.info(f"  Nodes created: {self.stats['nodes_created']}")
        logger.info(f"  Relationships created: {self.stats['relationships_created']}")
        
        if self.stats["elements_found"]:
            logger.info("  Elements by type:")
            for elem_type, count in sorted(self.stats["elements_found"].items()):
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
        description="Ingest XMI domain models into Neo4j Knowledge Graph"
    )
    parser.add_argument(
        '--file', '-f',
        type=Path,
        help='Specific XMI file to ingest'
    )
    parser.add_argument(
        '--directory', '-d',
        type=Path,
        help='Directory containing XMI files'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Parse only, do not write to Neo4j'
    )
    parser.add_argument(
        '--clear',
        action='store_true',
        help='Clear existing XMI nodes before ingestion'
    )
    
    args = parser.parse_args()
    
    # Default to SMRL domain models
    if not args.file and not args.directory:
        args.directory = PROJECT_ROOT / 'smrlv12' / 'data' / 'domain_models'
    
    ingester = XMIIngester(dry_run=args.dry_run)
    
    try:
        # Clear if requested
        if args.clear and not args.dry_run and ingester.conn:
            logger.warning("Clearing existing XMI nodes...")
            ingester.conn.execute_query("MATCH (n:XMIElement) DETACH DELETE n")
        
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
