#!/usr/bin/env python3
"""
XSD Schema Ingester V2 - Enhanced with Pydantic Models
============================================================================
Parse XML Schema Definition (XSD) files with proper entity extraction and
rich relationship types.

Relationships Created:
    - DEFINES: Schema defines types/elements
    - CONTAINS: Type contains elements/attributes
    - EXTENDS: Type extends base type
    - RESTRICTS: Simple type restricts base
    - HAS_ATTRIBUTE: ComplexType has attribute
    - HAS_ELEMENT: ComplexType/Group has element
    - REFERENCES_TYPE: Element/Attribute references type
    - MEMBER_OF: Element member of group

Node Labels:
    - XSDNode (base label for all)
    - XSDSchema, XSDComplexType, XSDSimpleType, XSDElement, 
      XSDAttribute, XSDGroup, XSDAttributeGroup

Usage:
    python backend/scripts/ingest_xsd_v2.py [--dry-run] [--clear]
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
# PYDANTIC MODELS FOR XSD ELEMENTS
# ============================================================================

class XSDRelationType(str, Enum):
    """Relationship types for XSD Knowledge Graph"""
    DEFINES = "DEFINES"
    CONTAINS = "CONTAINS"
    EXTENDS = "EXTENDS"
    RESTRICTS = "RESTRICTS"
    HAS_ATTRIBUTE = "HAS_ATTRIBUTE"
    HAS_ELEMENT = "HAS_ELEMENT"
    REFERENCES_TYPE = "REFERENCES_TYPE"
    MEMBER_OF = "MEMBER_OF"
    IMPORTS = "IMPORTS"


class XSDNode(BaseModel):
    """Base Pydantic model for XSD elements"""
    id: str  # Unique identifier (schema:type:name)
    node_type: str  # XSDSchema, XSDComplexType, etc.
    name: str
    schema_name: str
    target_namespace: str = ""
    source_file: str = ""
    
    class Config:
        extra = "allow"


class XSDSchemaNode(XSDNode):
    """Schema root node"""
    element_form_default: str = "unqualified"
    attribute_form_default: str = "unqualified"
    imports: List[str] = Field(default_factory=list)


class XSDComplexTypeNode(XSDNode):
    """Complex type definition"""
    is_abstract: bool = False
    is_mixed: bool = False
    base_type: Optional[str] = None
    base_type_ref: Optional[str] = None  # Resolved ID


class XSDSimpleTypeNode(XSDNode):
    """Simple type definition"""
    base_type: Optional[str] = None
    base_type_ref: Optional[str] = None
    is_enumeration: bool = False
    enumeration_values: List[str] = Field(default_factory=list)
    pattern: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None


class XSDElementNode(XSDNode):
    """Element definition"""
    type_ref: Optional[str] = None  # Type reference
    type_ref_id: Optional[str] = None  # Resolved ID
    min_occurs: str = "1"
    max_occurs: str = "1"
    is_nillable: bool = False
    is_global: bool = False
    default_value: Optional[str] = None
    fixed_value: Optional[str] = None


class XSDAttributeNode(XSDNode):
    """Attribute definition"""
    type_ref: Optional[str] = None
    type_ref_id: Optional[str] = None
    use: str = "optional"
    default_value: Optional[str] = None
    fixed_value: Optional[str] = None


class XSDGroupNode(XSDNode):
    """Model group definition"""
    pass


class XSDAttributeGroupNode(XSDNode):
    """Attribute group definition"""
    pass


class XSDRelationship(BaseModel):
    """Relationship between XSD nodes"""
    from_id: str
    to_id: str
    rel_type: XSDRelationType
    properties: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# XSD INGESTER V2
# ============================================================================

class XSDIngesterV2:
    """
    Enhanced XSD Ingester with Pydantic models and rich relationship extraction.
    """
    
    XSD_NS = 'http://www.w3.org/2001/XMLSchema'
    XSD = '{http://www.w3.org/2001/XMLSchema}'
    
    def __init__(
        self,
        connection: Optional[Neo4jConnection] = None,
        dry_run: bool = False,
    ):
        self.dry_run = dry_run
        
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
        
        # Storage
        self.nodes: Dict[str, XSDNode] = {}
        self.relationships: List[XSDRelationship] = []
        
        # Type resolution map (name -> id)
        self.type_map: Dict[str, str] = {}
        
        # Current context
        self.current_schema: str = ""
        self.current_ns: str = ""
        
        # Statistics
        self.stats = {
            "files_processed": 0,
            "nodes_created": 0,
            "relationships_created": 0,
            "nodes_by_type": {},
            "relationships_by_type": {},
            "errors": [],
        }
    
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
            
            # Phase 1: Create schema node
            schema_node = self._create_schema_node(root, file_path)
            self.nodes[schema_node.id] = schema_node
            
            # Phase 2: Extract all types and build type map
            self._extract_types(root, schema_node.id)
            
            # Phase 3: Resolve type references and build relationships
            self._resolve_references()
            
            # Phase 4: Create in Neo4j
            if not self.dry_run and self.conn:
                self._create_nodes()
                self._create_relationships_batch()
            
            self.stats["files_processed"] += 1
            logger.info(f"  Extracted {len(self.nodes)} nodes from {file_path.name}")
            
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            self.stats["errors"].append(f"{file_path.name}: {str(e)}")
            import traceback
            traceback.print_exc()
        
        return self.stats
    
    def _create_schema_node(self, root: etree._Element, file_path: Path) -> XSDSchemaNode:
        """Create schema root node"""
        schema_id = f"schema:{self.current_schema}"
        
        # Extract imports
        imports = []
        for imp in root.findall(f'{self.XSD}import'):
            ns = imp.get('namespace', '')
            loc = imp.get('schemaLocation', '')
            if ns or loc:
                imports.append(loc or ns)
        
        return XSDSchemaNode(
            id=schema_id,
            node_type="XSDSchema",
            name=self.current_schema,
            schema_name=self.current_schema,
            target_namespace=self.current_ns,
            source_file=str(file_path),
            element_form_default=root.get('elementFormDefault', 'unqualified'),
            attribute_form_default=root.get('attributeFormDefault', 'unqualified'),
            imports=imports,
        )
    
    def _extract_types(self, root: etree._Element, schema_id: str):
        """Extract all type definitions"""
        
        # Complex Types
        for ct in root.findall(f'{self.XSD}complexType'):
            self._extract_complex_type(ct, schema_id, is_global=True)
        
        # Simple Types
        for st in root.findall(f'{self.XSD}simpleType'):
            self._extract_simple_type(st, schema_id)
        
        # Global Elements
        for elem in root.findall(f'{self.XSD}element'):
            self._extract_element(elem, schema_id, is_global=True)
        
        # Groups
        for group in root.findall(f'{self.XSD}group'):
            self._extract_group(group, schema_id)
        
        # Attribute Groups
        for ag in root.findall(f'{self.XSD}attributeGroup'):
            self._extract_attribute_group(ag, schema_id)
    
    def _extract_complex_type(self, elem: etree._Element, parent_id: str, is_global: bool = True):
        """Extract complex type definition"""
        name = elem.get('name', '')
        if not name:
            return None
        
        type_id = f"ct:{self.current_schema}:{name}"
        
        # Check for base type
        base_type = None
        cc = elem.find(f'{self.XSD}complexContent')
        sc = elem.find(f'{self.XSD}simpleContent')
        
        content = cc if cc is not None else sc
        if content is not None:
            ext = content.find(f'{self.XSD}extension')
            if ext is not None:
                base_type = ext.get('base', '')
            rest = content.find(f'{self.XSD}restriction')
            if rest is not None:
                base_type = rest.get('base', '')
        
        node = XSDComplexTypeNode(
            id=type_id,
            node_type="XSDComplexType",
            name=name,
            schema_name=self.current_schema,
            target_namespace=self.current_ns,
            is_abstract=elem.get('abstract', 'false') == 'true',
            is_mixed=elem.get('mixed', 'false') == 'true',
            base_type=self._strip_prefix(base_type) if base_type else None,
        )
        
        self.nodes[type_id] = node
        self.type_map[name] = type_id
        self._update_stats("XSDComplexType")
        
        # Add DEFINES relationship
        self.relationships.append(XSDRelationship(
            from_id=parent_id,
            to_id=type_id,
            rel_type=XSDRelationType.DEFINES
        ))
        
        # Extract nested elements
        self._extract_nested_content(elem, type_id)
        
        return type_id
    
    def _extract_simple_type(self, elem: etree._Element, parent_id: str):
        """Extract simple type definition"""
        name = elem.get('name', '')
        if not name:
            return
        
        type_id = f"st:{self.current_schema}:{name}"
        
        # Check restriction
        base_type = ''
        enum_values = []
        pattern = None
        min_length = None
        max_length = None
        
        rest = elem.find(f'{self.XSD}restriction')
        if rest is not None:
            base_type = rest.get('base', '')
            for enum in rest.findall(f'{self.XSD}enumeration'):
                val = enum.get('value', '')
                if val:
                    enum_values.append(val)
            pat = rest.find(f'{self.XSD}pattern')
            if pat is not None:
                pattern = pat.get('value', '')
            ml = rest.find(f'{self.XSD}minLength')
            if ml is not None:
                min_length = int(ml.get('value', 0))
            xl = rest.find(f'{self.XSD}maxLength')
            if xl is not None:
                max_length = int(xl.get('value', 0))
        
        node = XSDSimpleTypeNode(
            id=type_id,
            node_type="XSDSimpleType",
            name=name,
            schema_name=self.current_schema,
            target_namespace=self.current_ns,
            base_type=self._strip_prefix(base_type) if base_type else None,
            is_enumeration=len(enum_values) > 0,
            enumeration_values=enum_values[:100],  # Limit
            pattern=pattern,
            min_length=min_length,
            max_length=max_length,
        )
        
        self.nodes[type_id] = node
        self.type_map[name] = type_id
        self._update_stats("XSDSimpleType")
        
        self.relationships.append(XSDRelationship(
            from_id=parent_id,
            to_id=type_id,
            rel_type=XSDRelationType.DEFINES
        ))
    
    def _extract_element(self, elem: etree._Element, parent_id: str, is_global: bool = False):
        """Extract element definition"""
        name = elem.get('name', '')
        if not name:
            return
        
        prefix = "ge" if is_global else "le"
        elem_id = f"{prefix}:{self.current_schema}:{parent_id}:{name}" if not is_global else f"ge:{self.current_schema}:{name}"
        
        type_ref = elem.get('type', '')
        
        node = XSDElementNode(
            id=elem_id,
            node_type="XSDElement",
            name=name,
            schema_name=self.current_schema,
            target_namespace=self.current_ns,
            type_ref=self._strip_prefix(type_ref) if type_ref else None,
            min_occurs=elem.get('minOccurs', '1'),
            max_occurs=elem.get('maxOccurs', '1'),
            is_nillable=elem.get('nillable', 'false') == 'true',
            is_global=is_global,
            default_value=elem.get('default'),
            fixed_value=elem.get('fixed'),
        )
        
        self.nodes[elem_id] = node
        if is_global:
            self.type_map[name] = elem_id
        self._update_stats("XSDElement")
        
        rel_type = XSDRelationType.DEFINES if is_global else XSDRelationType.HAS_ELEMENT
        self.relationships.append(XSDRelationship(
            from_id=parent_id,
            to_id=elem_id,
            rel_type=rel_type
        ))
        
        # Check for inline complex type
        inline_ct = elem.find(f'{self.XSD}complexType')
        if inline_ct is not None:
            ct_id = self._extract_complex_type(inline_ct, elem_id, is_global=False)
            if ct_id:
                node.type_ref_id = ct_id
    
    def _extract_attribute(self, elem: etree._Element, parent_id: str):
        """Extract attribute definition"""
        name = elem.get('name', '')
        if not name:
            return
        
        attr_id = f"attr:{self.current_schema}:{parent_id}:{name}"
        type_ref = elem.get('type', '')
        
        node = XSDAttributeNode(
            id=attr_id,
            node_type="XSDAttribute",
            name=name,
            schema_name=self.current_schema,
            target_namespace=self.current_ns,
            type_ref=self._strip_prefix(type_ref) if type_ref else None,
            use=elem.get('use', 'optional'),
            default_value=elem.get('default'),
            fixed_value=elem.get('fixed'),
        )
        
        self.nodes[attr_id] = node
        self._update_stats("XSDAttribute")
        
        self.relationships.append(XSDRelationship(
            from_id=parent_id,
            to_id=attr_id,
            rel_type=XSDRelationType.HAS_ATTRIBUTE
        ))
    
    def _extract_group(self, elem: etree._Element, parent_id: str):
        """Extract group definition"""
        name = elem.get('name', '')
        if not name:
            return
        
        group_id = f"grp:{self.current_schema}:{name}"
        
        node = XSDGroupNode(
            id=group_id,
            node_type="XSDGroup",
            name=name,
            schema_name=self.current_schema,
            target_namespace=self.current_ns,
        )
        
        self.nodes[group_id] = node
        self.type_map[name] = group_id
        self._update_stats("XSDGroup")
        
        self.relationships.append(XSDRelationship(
            from_id=parent_id,
            to_id=group_id,
            rel_type=XSDRelationType.DEFINES
        ))
        
        self._extract_nested_content(elem, group_id)
    
    def _extract_attribute_group(self, elem: etree._Element, parent_id: str):
        """Extract attribute group definition"""
        name = elem.get('name', '')
        if not name:
            return
        
        ag_id = f"ag:{self.current_schema}:{name}"
        
        node = XSDAttributeGroupNode(
            id=ag_id,
            node_type="XSDAttributeGroup",
            name=name,
            schema_name=self.current_schema,
            target_namespace=self.current_ns,
        )
        
        self.nodes[ag_id] = node
        self._update_stats("XSDAttributeGroup")
        
        self.relationships.append(XSDRelationship(
            from_id=parent_id,
            to_id=ag_id,
            rel_type=XSDRelationType.DEFINES
        ))
        
        # Extract attributes in group
        for attr in elem.findall(f'{self.XSD}attribute'):
            self._extract_attribute(attr, ag_id)
    
    def _extract_nested_content(self, parent: etree._Element, parent_id: str):
        """Extract nested elements and attributes from complex type/group"""
        
        # Elements in sequence/choice/all
        for container_type in ['sequence', 'choice', 'all']:
            for container in parent.findall(f'.//{self.XSD}{container_type}'):
                for child in container.findall(f'{self.XSD}element'):
                    self._extract_element(child, parent_id, is_global=False)
        
        # Attributes
        for attr in parent.findall(f'.//{self.XSD}attribute'):
            self._extract_attribute(attr, parent_id)
    
    def _strip_prefix(self, value: str) -> str:
        """Strip namespace prefix from type reference"""
        if not value:
            return value
        return value.split(':')[-1] if ':' in value else value
    
    def _resolve_references(self):
        """Resolve type references and create relationships"""
        logger.info("  Resolving type references...")
        
        for node_id, node in self.nodes.items():
            # Resolve complex type base
            if isinstance(node, XSDComplexTypeNode) and node.base_type:
                base_id = self.type_map.get(node.base_type)
                if base_id:
                    node.base_type_ref = base_id
                    self.relationships.append(XSDRelationship(
                        from_id=node_id,
                        to_id=base_id,
                        rel_type=XSDRelationType.EXTENDS
                    ))
            
            # Resolve simple type base
            if isinstance(node, XSDSimpleTypeNode) and node.base_type:
                base_id = self.type_map.get(node.base_type)
                if base_id:
                    node.base_type_ref = base_id
                    self.relationships.append(XSDRelationship(
                        from_id=node_id,
                        to_id=base_id,
                        rel_type=XSDRelationType.RESTRICTS
                    ))
            
            # Resolve element type
            if isinstance(node, XSDElementNode) and node.type_ref:
                type_id = self.type_map.get(node.type_ref)
                if type_id:
                    node.type_ref_id = type_id
                    self.relationships.append(XSDRelationship(
                        from_id=node_id,
                        to_id=type_id,
                        rel_type=XSDRelationType.REFERENCES_TYPE
                    ))
            
            # Resolve attribute type
            if isinstance(node, XSDAttributeNode) and node.type_ref:
                type_id = self.type_map.get(node.type_ref)
                if type_id:
                    node.type_ref_id = type_id
                    self.relationships.append(XSDRelationship(
                        from_id=node_id,
                        to_id=type_id,
                        rel_type=XSDRelationType.REFERENCES_TYPE
                    ))
        
        # Update relationship stats
        for rel in self.relationships:
            rel_type = rel.rel_type.value
            if rel_type not in self.stats["relationships_by_type"]:
                self.stats["relationships_by_type"][rel_type] = 0
            self.stats["relationships_by_type"][rel_type] += 1
    
    def _update_stats(self, node_type: str):
        """Update statistics"""
        if node_type not in self.stats["nodes_by_type"]:
            self.stats["nodes_by_type"][node_type] = 0
        self.stats["nodes_by_type"][node_type] += 1
    
    def _create_nodes(self):
        """Create nodes in Neo4j"""
        logger.info("  Creating XSD nodes...")
        
        # Group by type
        by_type: Dict[str, List[Dict]] = {}
        
        for node_id, node in self.nodes.items():
            node_type = node.node_type
            if node_type not in by_type:
                by_type[node_type] = []
            
            # Convert to dict
            props = node.model_dump(exclude={'node_type', 'enumeration_values'})
            
            # Handle enumeration_values as string
            if hasattr(node, 'enumeration_values') and node.enumeration_values:
                props['enumeration_values'] = ';'.join(node.enumeration_values)
            
            # Remove None values
            props = {k: v for k, v in props.items() if v is not None}
            
            by_type[node_type].append(props)
        
        # Create in batches
        for node_type, items in by_type.items():
            labels = f"XSDNode:{node_type}"
            
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
                    logger.warning(f"Error creating {node_type} nodes: {e}")
            
            logger.info(f"    Created {len(items)} {node_type} nodes")
        
        logger.info(f"  Total nodes created: {self.stats['nodes_created']}")
    
    def _create_relationships_batch(self):
        """Create relationships in Neo4j"""
        logger.info("  Creating XSD relationships...")
        
        # Group by type
        by_type: Dict[str, List[Dict]] = {}
        
        for rel in self.relationships:
            rel_type = rel.rel_type.value
            if rel_type not in by_type:
                by_type[rel_type] = []
            by_type[rel_type].append({
                'from_id': rel.from_id,
                'to_id': rel.to_id,
            })
        
        # Create in batches
        for rel_type, items in by_type.items():
            for i in range(0, len(items), BATCH_SIZE):
                batch = items[i:i + BATCH_SIZE]
                
                cypher = f"""
                    UNWIND $batch AS rel
                    MATCH (a:XSDNode {{id: rel.from_id}})
                    MATCH (b:XSDNode {{id: rel.to_id}})
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
        logger.info("XSD INGESTION SUMMARY (V2)")
        logger.info("=" * 70)
        logger.info(f"  Files processed: {self.stats['files_processed']}")
        logger.info(f"  Nodes created: {self.stats['nodes_created']}")
        logger.info(f"  Relationships created: {self.stats['relationships_created']}")
        
        if self.stats["nodes_by_type"]:
            logger.info("  Nodes by type:")
            for node_type, count in sorted(self.stats["nodes_by_type"].items()):
                logger.info(f"    {node_type}: {count}")
        
        if self.stats["relationships_by_type"]:
            logger.info("  Relationships by type:")
            for rel_type, count in sorted(self.stats["relationships_by_type"].items()):
                logger.info(f"    {rel_type}: {count}")
        
        if self.stats["errors"]:
            logger.warning(f"  Errors ({len(self.stats['errors'])}):")
            for err in self.stats["errors"][:10]:
                logger.warning(f"    - {err}")
        
        logger.info("=" * 70)
    
    def ingest_directory(self, directory: Path, pattern: str = "*.xsd") -> Dict[str, Any]:
        """Ingest all XSD files in a directory"""
        logger.info(f"Scanning directory: {directory}")
        
        xsd_files = list(directory.rglob(pattern))
        logger.info(f"Found {len(xsd_files)} XSD files")
        
        for xsd_file in xsd_files:
            self.ingest_file(xsd_file)
        
        return self.stats
    
    def close(self):
        """Close Neo4j connection"""
        if self.conn:
            self.conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Ingest XSD schema files into Neo4j Knowledge Graph (V2)"
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
    
    # Default to SMRL data
    if not args.file and not args.directory:
        args.directory = PROJECT_ROOT / 'smrlv12' / 'data'
    
    ingester = XSDIngesterV2(dry_run=args.dry_run)
    
    try:
        # Clear if requested
        if args.clear and not args.dry_run and ingester.conn:
            logger.warning("Clearing existing XSDNode nodes...")
            ingester.conn.execute_query("MATCH (n:XSDNode) DETACH DELETE n")
        
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
