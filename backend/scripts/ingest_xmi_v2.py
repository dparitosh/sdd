#!/usr/bin/env python3
"""
XMI Domain Model Ingester V2 - Enhanced with Pydantic Models
============================================================================
Parse XMI (UML/SysML) domain models with proper entity extraction and 
rich relationship types matching MBSE semantics.

Relationships Created:
    - OWNS: Parent ownership (xmi:owner)
    - ASSOCIATES_WITH: Association memberEnd
    - GENERALIZES_TO: Inheritance/Generalization
    - DEPENDS_ON: Dependency relationships
    - REALIZES: Realization relationships
    - HAS_ATTRIBUTE: ownedAttribute/Property
    - HAS_PORT: Port ownership
    - CONNECTS_TO: Connector ends
    - ALLOCATED_TO: SysML Allocate stereotype

Node Labels:
    - MBSEElement (base label for all)
    - Dynamic labels from xmi:type (Class, Package, Block, etc.)

Usage:
    python backend/scripts/ingest_xmi_v2.py [--dry-run] [--clear]
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Set
from enum import Enum
from pydantic import BaseModel, Field
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


# ============================================================================
# PYDANTIC MODELS FOR XMI ELEMENTS
# ============================================================================

class RelationType(str, Enum):
    """Relationship types for MBSE Knowledge Graph"""
    OWNS = "OWNS"
    ASSOCIATES_WITH = "ASSOCIATES_WITH"
    GENERALIZES_TO = "GENERALIZES_TO"
    DEPENDS_ON = "DEPENDS_ON"
    REALIZES = "REALIZES"
    HAS_ATTRIBUTE = "HAS_ATTRIBUTE"
    HAS_PORT = "HAS_PORT"
    HAS_OPERATION = "HAS_OPERATION"
    CONNECTS_TO = "CONNECTS_TO"
    ALLOCATED_TO = "ALLOCATED_TO"
    CONTAINS = "CONTAINS"
    TYPED_BY = "TYPED_BY"


class MBSEElement(BaseModel):
    """Pydantic model for MBSE elements extracted from XMI"""
    xmi_id: str
    xmi_type: str
    name: str = ""
    label: str = ""  # Simplified type for Neo4j label
    visibility: str = "public"
    is_abstract: bool = False
    stereotype: Optional[str] = None
    documentation: Optional[str] = None
    
    # References
    xmi_owner: Optional[str] = None
    type_ref: Optional[str] = None  # For typed elements
    general_ref: Optional[str] = None  # For generalizations
    
    # Association specific
    member_ends: List[str] = Field(default_factory=list)
    
    # Dependency/Realization specific
    client_ref: Optional[str] = None
    supplier_refs: List[str] = Field(default_factory=list)
    
    # Connector specific
    connector_ends: List[str] = Field(default_factory=list)
    
    # Port/Property specific
    aggregation: Optional[str] = None
    is_derived: bool = False
    is_read_only: bool = False
    is_composite: bool = False
    
    # Metadata
    source_file: str = ""
    
    class Config:
        extra = "allow"  # Allow additional properties


class MBSERelationship(BaseModel):
    """Pydantic model for relationships between MBSE elements"""
    from_id: str
    to_id: str
    rel_type: RelationType
    properties: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# XMI INGESTER V2
# ============================================================================

class XMIIngesterV2:
    """
    Enhanced XMI Ingester with Pydantic models and rich relationship extraction.
    """
    
    # XMI namespace
    XMI_NS = 'http://www.omg.org/spec/XMI/20131001'
    UML_NS = 'http://www.omg.org/spec/UML/20131001'
    SYSML_NS = 'http://www.omg.org/spec/SysML/20150709/SysML'
    
    NAMESPACES = {
        'xmi': XMI_NS,
        'uml': UML_NS,
        'sysml': SYSML_NS,
    }
    
    # UML types to extract
    UML_TYPES = {
        'uml:Model', 'uml:Package', 'uml:Class', 'uml:Interface',
        'uml:Component', 'uml:Property', 'uml:Operation', 'uml:Parameter',
        'uml:DataType', 'uml:Enumeration', 'uml:EnumerationLiteral',
        'uml:PrimitiveType', 'uml:Association', 'uml:Port', 'uml:Connector',
        'uml:StateMachine', 'uml:State', 'uml:Transition',
        'uml:Activity', 'uml:Action', 'uml:Comment',
        'uml:Constraint', 'uml:Dependency', 'uml:Abstraction',
        'uml:Realization', 'uml:Usage', 'uml:Generalization',
        'uml:InstanceSpecification', 'uml:Signal', 'uml:Reception',
    }
    
    # SysML stereotypes
    SYSML_STEREOTYPES = {
        'Block', 'Requirement', 'ValueType', 'FlowPort',
        'InterfaceBlock', 'ConstraintBlock', 'allocate',
    }
    
    def __init__(
        self,
        connection: Optional[Neo4jConnection] = None,
        dry_run: bool = False,
    ):
        self.dry_run = dry_run
        
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
        
        # Element storage
        self.elements: Dict[str, MBSEElement] = {}
        self.relationships: List[MBSERelationship] = []
        
        # Stereotype mapping (xmi:id -> stereotype name)
        self.stereotype_map: Dict[str, str] = {}
        
        # Statistics
        self.stats = {
            "files_processed": 0,
            "nodes_created": 0,
            "relationships_created": 0,
            "elements_by_type": {},
            "relationships_by_type": {},
            "errors": [],
        }
    
    def ingest_file(self, file_path: Path) -> Dict[str, Any]:
        """Ingest a single XMI file"""
        logger.info(f"Processing XMI file: {file_path.name}")
        
        try:
            tree = etree.parse(str(file_path))
            root = tree.getroot()
            
            # Phase 1: Extract stereotype applications
            self._extract_stereotypes(root)
            
            # Phase 2: Extract all UML elements
            self._extract_elements(root, file_path)
            
            # Phase 3: Build relationships
            self._build_relationships()
            
            # Phase 4: Create nodes and relationships in Neo4j
            if not self.dry_run and self.conn:
                self._create_nodes()
                self._create_relationships_batch()
            
            self.stats["files_processed"] += 1
            
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            self.stats["errors"].append(f"{file_path.name}: {str(e)}")
            import traceback
            traceback.print_exc()
        
        return self.stats
    
    def _extract_stereotypes(self, root: etree._Element):
        """Extract SysML stereotype applications"""
        logger.info("  Phase 1: Extracting stereotype applications...")
        
        # Look for sysml:Block, sysml:Requirement, etc.
        for stereotype in self.SYSML_STEREOTYPES:
            # Try different namespace patterns
            for ns_prefix in ['sysml', 'SysML']:
                elements = root.findall(f'.//{{{self.SYSML_NS}}}{stereotype}', self.NAMESPACES)
                for elem in elements:
                    base_class = elem.find('base_Class')
                    if base_class is not None:
                        ref = base_class.get(f'{{{self.XMI_NS}}}idref')
                        if ref:
                            self.stereotype_map[ref] = stereotype
            
            # Also check StandardProfile namespace
            std_profile_ns = 'http://www.omg.org/spec/UML/20131001/StandardProfile'
            elements = root.findall(f'.//{{{std_profile_ns}}}*')
            for elem in elements:
                base_class = elem.find('base_Class')
                if base_class is not None:
                    ref = base_class.get(f'{{{self.XMI_NS}}}idref')
                    if ref:
                        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                        self.stereotype_map[ref] = tag
        
        logger.info(f"    Found {len(self.stereotype_map)} stereotype applications")
    
    def _extract_elements(self, root: etree._Element, source_file: Path):
        """Extract all UML/SysML elements"""
        logger.info("  Phase 2: Extracting UML elements...")
        
        for elem in root.iter():
            xmi_type = elem.get(f'{{{self.XMI_NS}}}type')
            xmi_id = elem.get(f'{{{self.XMI_NS}}}id')
            
            if not xmi_id:
                continue
            
            # Check if this is a UML type we care about
            if xmi_type and xmi_type in self.UML_TYPES:
                mbse_elem = self._parse_element(elem, xmi_type, xmi_id, source_file)
                self.elements[xmi_id] = mbse_elem
                
                # Update stats
                label = mbse_elem.label
                if label not in self.stats["elements_by_type"]:
                    self.stats["elements_by_type"][label] = 0
                self.stats["elements_by_type"][label] += 1
        
        logger.info(f"    Found {len(self.elements)} UML elements")
    
    def _parse_element(
        self, 
        elem: etree._Element, 
        xmi_type: str, 
        xmi_id: str, 
        source_file: Path
    ) -> MBSEElement:
        """Parse a single XMI element into Pydantic model"""
        
        # Extract name (attribute or child element)
        name = elem.get('name', '')
        if not name:
            name_elem = elem.find('name')
            if name_elem is not None and name_elem.text:
                name = name_elem.text
        
        # Extract visibility
        visibility = elem.get('visibility', '')
        if not visibility:
            vis_elem = elem.find('visibility')
            if vis_elem is not None and vis_elem.text:
                visibility = vis_elem.text
            else:
                visibility = 'public'
        
        # Extract isAbstract
        is_abstract_attr = elem.get('isAbstract', '')
        if not is_abstract_attr:
            abs_elem = elem.find('isAbstract')
            if abs_elem is not None and abs_elem.text:
                is_abstract_attr = abs_elem.text
        is_abstract = is_abstract_attr == 'true'
        
        # Get label from xmi:type (strip "uml:" prefix)
        label = xmi_type.replace('uml:', '').replace('sysml:', '')
        
        # Get owner (parent element with xmi:id)
        xmi_owner = None
        parent = elem.getparent()
        if parent is not None:
            xmi_owner = parent.get(f'{{{self.XMI_NS}}}id')
        
        # Get type reference
        type_ref = elem.get('type')
        if not type_ref:
            type_elem = elem.find('type')
            if type_elem is not None:
                type_ref = type_elem.get(f'{{{self.XMI_NS}}}idref')
        
        # Get stereotype from our map
        stereotype = self.stereotype_map.get(xmi_id)
        
        # Extract documentation/comments
        documentation = None
        body_elem = elem.find('body')
        if body_elem is not None and body_elem.text:
            documentation = body_elem.text[:1000]  # Truncate long docs
        
        # Build element
        mbse_elem = MBSEElement(
            xmi_id=xmi_id,
            xmi_type=xmi_type,
            name=name,
            label=label,
            visibility=visibility,
            is_abstract=is_abstract,
            stereotype=stereotype,
            documentation=documentation,
            xmi_owner=xmi_owner,
            type_ref=type_ref,
            source_file=str(source_file),
        )
        
        # Type-specific extraction
        if xmi_type == 'uml:Association':
            mbse_elem.member_ends = self._extract_member_ends(elem)
        
        elif xmi_type == 'uml:Generalization':
            general = elem.get('general')
            if not general:
                gen_elem = elem.find('general')
                if gen_elem is not None:
                    general = gen_elem.get(f'{{{self.XMI_NS}}}idref')
            mbse_elem.general_ref = general
        
        elif xmi_type in ('uml:Dependency', 'uml:Abstraction', 'uml:Realization', 'uml:Usage'):
            mbse_elem.supplier_refs = self._extract_suppliers(elem)
            mbse_elem.client_ref = xmi_owner
        
        elif xmi_type == 'uml:Connector':
            mbse_elem.connector_ends = self._extract_connector_ends(elem)
        
        elif xmi_type == 'uml:Property':
            mbse_elem.aggregation = elem.get('aggregation', 'none')
            mbse_elem.is_derived = elem.get('isDerived', 'false') == 'true'
            mbse_elem.is_read_only = elem.get('isReadOnly', 'false') == 'true'
            agg = mbse_elem.aggregation
            mbse_elem.is_composite = agg == 'composite'
        
        return mbse_elem
    
    def _extract_member_ends(self, elem: etree._Element) -> List[str]:
        """Extract memberEnd references from Association"""
        ends = []
        
        # Check attribute
        member_end_attr = elem.get('memberEnd', '')
        if member_end_attr:
            ends.extend(member_end_attr.split())
        
        # Check child elements
        for end in elem.findall('memberEnd'):
            ref = end.get(f'{{{self.XMI_NS}}}idref')
            if ref:
                ends.append(ref)
        
        # Check ownedEnd
        for owned_end in elem.findall('ownedEnd'):
            end_id = owned_end.get(f'{{{self.XMI_NS}}}id')
            if end_id:
                ends.append(end_id)
        
        return ends
    
    def _extract_suppliers(self, elem: etree._Element) -> List[str]:
        """Extract supplier references from Dependency/Realization"""
        suppliers = []
        
        supplier_attr = elem.get('supplier', '')
        if supplier_attr:
            suppliers.extend(supplier_attr.split())
        
        for sup in elem.findall('supplier'):
            ref = sup.get(f'{{{self.XMI_NS}}}idref')
            if ref:
                suppliers.append(ref)
        
        return suppliers
    
    def _extract_connector_ends(self, elem: etree._Element) -> List[str]:
        """Extract end references from Connector"""
        ends = []
        
        for end in elem.findall('.//end'):
            role = end.get('role')
            if role:
                ends.append(role)
        
        return ends
    
    def _build_relationships(self):
        """Build all relationships from extracted elements"""
        logger.info("  Phase 3: Building relationships...")
        
        for xmi_id, elem in self.elements.items():
            
            # OWNS relationship (parent-child via xmi:owner)
            if elem.xmi_owner and elem.xmi_owner in self.elements:
                self.relationships.append(MBSERelationship(
                    from_id=elem.xmi_owner,
                    to_id=xmi_id,
                    rel_type=RelationType.OWNS
                ))
            
            # HAS_ATTRIBUTE for Properties owned by Classes
            if elem.xmi_type == 'uml:Property' and elem.xmi_owner:
                owner = self.elements.get(elem.xmi_owner)
                if owner and owner.xmi_type in ('uml:Class', 'uml:Interface', 'uml:DataType'):
                    self.relationships.append(MBSERelationship(
                        from_id=elem.xmi_owner,
                        to_id=xmi_id,
                        rel_type=RelationType.HAS_ATTRIBUTE
                    ))
            
            # HAS_PORT for Ports
            if elem.xmi_type == 'uml:Port' and elem.xmi_owner:
                self.relationships.append(MBSERelationship(
                    from_id=elem.xmi_owner,
                    to_id=xmi_id,
                    rel_type=RelationType.HAS_PORT
                ))
            
            # HAS_OPERATION for Operations
            if elem.xmi_type == 'uml:Operation' and elem.xmi_owner:
                self.relationships.append(MBSERelationship(
                    from_id=elem.xmi_owner,
                    to_id=xmi_id,
                    rel_type=RelationType.HAS_OPERATION
                ))
            
            # ASSOCIATES_WITH for Associations
            if elem.xmi_type == 'uml:Association':
                for end_id in elem.member_ends:
                    if end_id in self.elements:
                        self.relationships.append(MBSERelationship(
                            from_id=xmi_id,
                            to_id=end_id,
                            rel_type=RelationType.ASSOCIATES_WITH
                        ))
            
            # GENERALIZES_TO for Generalizations
            if elem.xmi_type == 'uml:Generalization' and elem.general_ref:
                if elem.xmi_owner and elem.general_ref in self.elements:
                    self.relationships.append(MBSERelationship(
                        from_id=elem.xmi_owner,
                        to_id=elem.general_ref,
                        rel_type=RelationType.GENERALIZES_TO
                    ))
            
            # DEPENDS_ON for Dependencies
            if elem.xmi_type == 'uml:Dependency':
                for sup_id in elem.supplier_refs:
                    if elem.client_ref and sup_id in self.elements:
                        self.relationships.append(MBSERelationship(
                            from_id=elem.client_ref,
                            to_id=sup_id,
                            rel_type=RelationType.DEPENDS_ON
                        ))
            
            # REALIZES for Realizations
            if elem.xmi_type == 'uml:Realization':
                for sup_id in elem.supplier_refs:
                    if elem.client_ref and sup_id in self.elements:
                        self.relationships.append(MBSERelationship(
                            from_id=elem.client_ref,
                            to_id=sup_id,
                            rel_type=RelationType.REALIZES
                        ))
            
            # ALLOCATED_TO for Abstractions with allocate stereotype
            if elem.xmi_type == 'uml:Abstraction' and elem.stereotype == 'allocate':
                for sup_id in elem.supplier_refs:
                    if elem.client_ref and sup_id in self.elements:
                        self.relationships.append(MBSERelationship(
                            from_id=elem.client_ref,
                            to_id=sup_id,
                            rel_type=RelationType.ALLOCATED_TO
                        ))
            
            # CONNECTS_TO for Connectors
            if elem.xmi_type == 'uml:Connector':
                for end_id in elem.connector_ends:
                    if end_id in self.elements:
                        self.relationships.append(MBSERelationship(
                            from_id=xmi_id,
                            to_id=end_id,
                            rel_type=RelationType.CONNECTS_TO
                        ))
            
            # TYPED_BY for typed elements
            if elem.type_ref and elem.type_ref in self.elements:
                self.relationships.append(MBSERelationship(
                    from_id=xmi_id,
                    to_id=elem.type_ref,
                    rel_type=RelationType.TYPED_BY
                ))
        
        # Count relationships by type
        for rel in self.relationships:
            rel_type = rel.rel_type.value
            if rel_type not in self.stats["relationships_by_type"]:
                self.stats["relationships_by_type"][rel_type] = 0
            self.stats["relationships_by_type"][rel_type] += 1
        
        logger.info(f"    Built {len(self.relationships)} relationships")
    
    def _create_nodes(self):
        """Create nodes in Neo4j using batch operations"""
        logger.info("  Phase 4a: Creating MBSEElement nodes...")
        
        # Group by label for efficient batching
        by_label: Dict[str, List[Dict]] = {}
        
        for xmi_id, elem in self.elements.items():
            label = elem.label
            if label not in by_label:
                by_label[label] = []
            
            # Convert Pydantic model to dict for Neo4j
            props = {
                'id': elem.xmi_id,
                'xmi_id': elem.xmi_id,
                'xmi_type': elem.xmi_type,
                'name': elem.name,
                'visibility': elem.visibility,
                'is_abstract': elem.is_abstract,
                'source_file': elem.source_file,
            }
            
            # Add optional properties
            if elem.stereotype:
                props['stereotype'] = elem.stereotype
            if elem.documentation:
                props['documentation'] = elem.documentation
            if elem.aggregation:
                props['aggregation'] = elem.aggregation
            if elem.is_derived:
                props['is_derived'] = elem.is_derived
            if elem.is_composite:
                props['is_composite'] = elem.is_composite
            
            by_label[label].append(props)
        
        # Create nodes in batches
        for label, items in by_label.items():
            # Use both MBSEElement and specific label
            labels = f"MBSEElement:{label}"
            
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
                    logger.warning(f"Error creating {label} nodes: {e}")
            
            logger.info(f"    Created {len(items)} {label} nodes")
        
        logger.info(f"  Total nodes created: {self.stats['nodes_created']}")
    
    def _create_relationships_batch(self):
        """Create relationships in Neo4j using batch operations"""
        logger.info("  Phase 4b: Creating relationships...")
        
        # Group by relationship type
        by_type: Dict[str, List[Dict]] = {}
        
        for rel in self.relationships:
            rel_type = rel.rel_type.value
            if rel_type not in by_type:
                by_type[rel_type] = []
            by_type[rel_type].append({
                'from_id': rel.from_id,
                'to_id': rel.to_id,
            })
        
        # Create relationships in batches
        for rel_type, items in by_type.items():
            for i in range(0, len(items), BATCH_SIZE):
                batch = items[i:i + BATCH_SIZE]
                
                cypher = f"""
                    UNWIND $batch AS rel
                    MATCH (a:MBSEElement {{id: rel.from_id}})
                    MATCH (b:MBSEElement {{id: rel.to_id}})
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
        logger.info("XMI INGESTION SUMMARY (V2)")
        logger.info("=" * 70)
        logger.info(f"  Files processed: {self.stats['files_processed']}")
        logger.info(f"  Nodes created: {self.stats['nodes_created']}")
        logger.info(f"  Relationships created: {self.stats['relationships_created']}")
        
        if self.stats["elements_by_type"]:
            logger.info("  Elements by type:")
            for elem_type, count in sorted(self.stats["elements_by_type"].items()):
                logger.info(f"    {elem_type}: {count}")
        
        if self.stats["relationships_by_type"]:
            logger.info("  Relationships by type:")
            for rel_type, count in sorted(self.stats["relationships_by_type"].items()):
                logger.info(f"    {rel_type}: {count}")
        
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
        description="Ingest XMI domain models into Neo4j Knowledge Graph (V2)"
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
        help='Clear existing MBSE nodes before ingestion'
    )
    
    args = parser.parse_args()
    
    # Default to SMRL domain models
    if not args.file and not args.directory:
        args.directory = PROJECT_ROOT / 'smrlv12' / 'data' / 'domain_models'
    
    ingester = XMIIngesterV2(dry_run=args.dry_run)
    
    try:
        # Clear if requested
        if args.clear and not args.dry_run and ingester.conn:
            logger.warning("Clearing existing MBSEElement nodes...")
            ingester.conn.execute_query("MATCH (n:MBSEElement) DETACH DELETE n")
        
        # Ingest
        if args.file:
            ingester.ingest_file(args.file)
        elif args.directory:
            xmi_files = list(args.directory.rglob("*.xmi"))
            logger.info(f"Found {len(xmi_files)} XMI files")
            for xmi_file in xmi_files:
                ingester.ingest_file(xmi_file)
        
        ingester.print_summary()
        
    finally:
        ingester.close()


if __name__ == "__main__":
    main()
