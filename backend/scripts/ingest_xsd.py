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

# XSD built-in data types — elements referencing these become owl:DatatypeProperty
XSD_BUILTIN_TYPES = {
    'string', 'boolean', 'decimal', 'float', 'double',
    'duration', 'dateTime', 'time', 'date',
    'gYearMonth', 'gYear', 'gMonthDay', 'gDay', 'gMonth',
    'hexBinary', 'base64Binary', 'anyURI', 'QName', 'NOTATION',
    'normalizedString', 'token', 'language',
    'NMTOKEN', 'NMTOKENS', 'Name', 'NCName',
    'ID', 'IDREF', 'IDREFS', 'ENTITY', 'ENTITIES',
    'integer', 'nonPositiveInteger', 'negativeInteger',
    'long', 'int', 'short', 'byte',
    'nonNegativeInteger', 'unsignedLong', 'unsignedInt',
    'unsignedShort', 'unsignedByte', 'positiveInteger',
    'anySimpleType', 'anyType',
}


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

    # Map directory path fragments to AP level
    AP_LEVEL_MAP = {
        'managed_model_based_3d_engineering': 'AP242',
        'product_life_cycle_support': 'AP239',
        'mossec': 'AP243',
    }
    
    def __init__(
        self,
        connection: Optional[Neo4jConnection] = None,
        dry_run: bool = False,
        verbose: bool = True,
        ap_level: Optional[str] = None,
    ):
        self.dry_run = dry_run
        self.verbose = verbose
        self.default_ap_level = ap_level  # Explicit override
        
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
            "schemas": [],
            "elements_by_type": {},
            "errors": [],
        }
        
        # Element tracking
        self.elements: Dict[str, Dict[str, Any]] = {}
        self.relationships: List[Dict[str, Any]] = []
        self.current_schema: str = ""
        self.current_ns: str = ""
    
    def _detect_ap_level(self, file_path: Path) -> Optional[str]:
        """Detect AP level from file path directory structure"""
        if self.default_ap_level:
            return self.default_ap_level
        path_str = str(file_path).replace('\\', '/').lower()
        for fragment, ap_level in self.AP_LEVEL_MAP.items():
            if fragment in path_str:
                logger.info(f"  Auto-detected ap_level={ap_level} from path fragment '{fragment}'")
                return ap_level
        return None

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
            
            # Detect AP level from path
            self.current_ap_level = self._detect_ap_level(file_path)
            
            # Create schema node
            schema_id = f"schema:{self.current_schema}"
            schema_props = {
                'id': schema_id,
                'type': 'XSDSchema',
                'name': self.current_schema,
                'target_namespace': target_ns,
                'source_file': str(file_path),
                'element_form_default': root.get('elementFormDefault', 'unqualified'),
                'attribute_form_default': root.get('attributeFormDefault', 'unqualified'),
            }
            if self.current_ap_level:
                schema_props['ap_level'] = self.current_ap_level
            self.elements[schema_id] = schema_props
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
    
    def finalize(self):
        """Run post-ingestion linking (call after all files are ingested)."""
        self._generate_owl_layer()
        self._link_ontology_classes()
    
    def ingest_directory(self, directory: Path, pattern: str = "*.xsd") -> Dict[str, Any]:
        """Ingest all XSD files in a directory"""
        logger.info(f"Scanning directory: {directory}")
        
        xsd_files = list(directory.rglob(pattern))
        logger.info(f"Found {len(xsd_files)} XSD files")
        
        for xsd_file in xsd_files:
            self.ingest_file(xsd_file)
        
        # Post-ingestion: link OntologyClass to XSD types
        self.finalize()
        
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
        if self.current_ap_level:
            self.elements[elem_id]['ap_level'] = self.current_ap_level
        
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
        if self.current_ap_level:
            self.elements[elem_id]['ap_level'] = self.current_ap_level
        
        # Link to schema
        self.relationships.append({
            'from_id': parent_id,
            'to_id': elem_id,
            'type': 'DEFINES',
        })
        
        # Link to base type (restriction)
        if base_type:
            base_name = base_type.split(':')[-1] if ':' in base_type else base_type
            self.relationships.append({
                'from_id': elem_id,
                'to_name': base_name,
                'to_type': 'XSDType',
                'type': 'RESTRICTS',
            })
        
        self._update_stats('XSDSimpleType')
    
    def _process_element(self, elem: etree._Element, parent_id: str, is_global: bool = False, container_type: str = ''):
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
            'container_type': container_type,
        }
        if self.current_ap_level:
            self.elements[elem_id]['ap_level'] = self.current_ap_level
        
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
        if self.current_ap_level:
            self.elements[elem_id]['ap_level'] = self.current_ap_level
        
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
        if self.current_ap_level:
            self.elements[elem_id]['ap_level'] = self.current_ap_level
        
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
        if self.current_ap_level:
            self.elements[elem_id]['ap_level'] = self.current_ap_level
        
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
        """Process sequence/choice/all containers, tracking container type for OWL mapping.
        
        Container semantics:
        - sequence → ordered composition (maps to isPartOf)
        - all → unordered composition (maps to isPartOf)
        - choice → disjunctive alternatives (maps to isKindOf)
        """
        for seq in parent.findall(f'.//{self.XSD}sequence'):
            for child in seq.findall(f'{self.XSD}element'):
                self._process_element(child, parent_id, is_global=False, container_type='sequence')
        
        for choice in parent.findall(f'.//{self.XSD}choice'):
            for child in choice.findall(f'{self.XSD}element'):
                self._process_element(child, parent_id, is_global=False, container_type='choice')
        
        for all_elem in parent.findall(f'.//{self.XSD}all'):
            for child in all_elem.findall(f'{self.XSD}element'):
                self._process_element(child, parent_id, is_global=False, container_type='all')
    
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
    
    def _build_type_resolution_map(self):
        """Build a map from type name -> element id for resolving name-based refs.
        
        Resolves ComplexType, SimpleType, and Group names to their IDs.
        When names collide across schemas, prefer same-schema matches.
        """
        self._type_map: Dict[str, str] = {}  # name -> id (global fallback)
        self._type_map_by_schema: Dict[str, Dict[str, str]] = {}  # schema -> {name -> id}
        
        for elem_id, elem in self.elements.items():
            etype = elem['type']
            if etype in ('XSDComplexType', 'XSDSimpleType', 'XSDGroup'):
                name = elem.get('name', '')
                schema = elem.get('schema', '')
                if name:
                    self._type_map[name] = elem_id
                    if schema not in self._type_map_by_schema:
                        self._type_map_by_schema[schema] = {}
                    self._type_map_by_schema[schema][name] = elem_id
    
    def _resolve_type_name(self, name: str, from_schema: str = '') -> Optional[str]:
        """Resolve a type name to an element ID, preferring same-schema."""
        # Try same-schema first
        if from_schema and from_schema in self._type_map_by_schema:
            eid = self._type_map_by_schema[from_schema].get(name)
            if eid:
                return eid
        # Fallback to global
        return self._type_map.get(name)

    def _create_relationships(self):
        """Create relationships in Neo4j using batch operations"""
        logger.info("Creating XSD relationships (batched)...")
        
        # Build resolution map for name-based refs
        self._build_type_resolution_map()
        
        # Group relationships by type for efficient batch creation
        by_type: Dict[str, List[Dict]] = {}
        name_resolved = 0
        name_unresolved = 0
        
        for rel in self.relationships:
            rel_type = rel['type']
            from_id = rel.get('from_id')
            to_id = rel.get('to_id')
            to_name = rel.get('to_name')
            
            # Direct ID relationship
            if from_id and to_id:
                if from_id in self.elements and to_id in self.elements:
                    if rel_type not in by_type:
                        by_type[rel_type] = []
                    by_type[rel_type].append({'from_id': from_id, 'to_id': to_id})
            # Name-based relationship — resolve to ID
            elif from_id and to_name and from_id in self.elements:
                from_schema = self.elements[from_id].get('schema', '')
                resolved_id = self._resolve_type_name(to_name, from_schema)
                if resolved_id:
                    if rel_type not in by_type:
                        by_type[rel_type] = []
                    by_type[rel_type].append({'from_id': from_id, 'to_id': resolved_id})
                    name_resolved += 1
                else:
                    name_unresolved += 1
        
        logger.info(f"  Name-based refs resolved: {name_resolved}, unresolved: {name_unresolved}")
        
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
    
    def _generate_owl_layer(self):
        """Generate OWL ontology layer from XSD schema nodes in Neo4j.
        
        XSD-to-OWL Mapping Rules:
        1. xs:complexType         → owl:Class
        2. xs:element (complex)   → owl:ObjectProperty  (nested) / owl:Class (global named)
        3. xs:element (simple)    → owl:DatatypeProperty
        4. xs:attribute           → owl:DatatypeProperty
        5. xs:extension           → rdfs:subClassOf
        6. minOccurs / maxOccurs  → Cardinality Constraints
        7. xs:sequence / xs:all   → isPartOf properties
           xs:choice              → isKindOf properties
        """
        if self.dry_run or not self.conn:
            return
        
        logger.info("Generating OWL ontology layer from XSD schema...")
        owl = {}
        
        # Ensure indexes for OWL nodes (speeds up MATCH lookups in batch operations)
        for idx in [
            "CREATE INDEX IF NOT EXISTS FOR (n:OWLObjectProperty) ON (n.id)",
            "CREATE INDEX IF NOT EXISTS FOR (n:OWLDatatypeProperty) ON (n.id)",
        ]:
            try:
                self.conn.execute_query(idx)
            except Exception:
                pass  # Index may already exist
        
        # ── 1. xs:complexType → owl:Class ──
        result = self.conn.execute_query("""
            MATCH (n:XSDComplexType)
            SET n:OWLClass
            SET n.owl_type = 'owl:Class',
                n.owl_iri = 'urn:xsd:' + coalesce(n.schema, '') + '#' + n.name
            RETURN count(n) AS cnt
        """)
        owl['classes'] = result[0]['cnt'] if result else 0
        logger.info(f"  owl:Class labels: {owl['classes']} ComplexType nodes")
        
        # ── 2. Named global elements with complex type refs → owl:Class + subClassOf ──
        result = self.conn.execute_query("""
            MATCH (e:XSDElement {is_global: true})-[:HAS_TYPE]->(ct:OWLClass)
            SET e:OWLClass
            SET e.owl_type = 'owl:Class',
                e.owl_iri = 'urn:xsd:' + coalesce(e.schema, '') + '#' + e.name
            MERGE (e)-[r:SUBCLASS_OF]->(ct)
            RETURN count(e) AS cnt
        """)
        owl['global_element_classes'] = result[0]['cnt'] if result else 0
        logger.info(f"  owl:Class (global elements): {owl['global_element_classes']}")
        
        # ── 3. xs:extension → rdfs:subClassOf ──
        result = self.conn.execute_query("""
            MATCH (child:OWLClass)-[:EXTENDS]->(parent:OWLClass)
            MERGE (child)-[r:SUBCLASS_OF]->(parent)
            RETURN count(r) AS cnt
        """)
        owl['subclass_of'] = result[0]['cnt'] if result else 0
        logger.info(f"  rdfs:subClassOf: {owl['subclass_of']}")
        
        # ── 4. Elements referencing ComplexType → owl:ObjectProperty (batched) ──
        #    Collect triples, then batch-create nodes and relationships
        triples = self.conn.execute_query("""
            MATCH (domain:OWLClass)-[:CONTAINS]->(elem:XSDElement)-[:HAS_TYPE]->(range:OWLClass)
            RETURN
                domain.id AS domain_id,
                domain.name AS domain_name,
                elem.name AS elem_name,
                elem.schema AS elem_schema,
                elem.min_occurs AS min_occurs,
                elem.max_occurs AS max_occurs,
                elem.container_type AS container_type,
                elem.ap_level AS elem_ap_level,
                domain.ap_level AS domain_ap_level,
                range.id AS range_id,
                range.name AS range_name
        """)
        logger.info(f"  ObjectProperty triples found: {len(triples)}")
        
        # Build batch of OWLObjectProperty props
        op_batch = []
        seen_ops = set()
        for t in triples:
            schema = t.get('elem_schema') or ''
            prop_id = f"op:{schema}:{t['domain_name']}:{t['elem_name']}"
            ct = t.get('container_type') or 'sequence'
            if prop_id not in seen_ops:
                seen_ops.add(prop_id)
                op_batch.append({
                    'id': prop_id,
                    'name': t['elem_name'],
                    'schema': schema,
                    'owl_type': 'owl:ObjectProperty',
                    'domain_class': t['domain_name'],
                    'range_class': t['range_name'],
                    'min_cardinality': t.get('min_occurs') or '1',
                    'max_cardinality': t.get('max_occurs') or '1',
                    'container_type': ct,
                    'semantic_relation': 'isKindOf' if ct == 'choice' else 'isPartOf',
                    'ap_level': t.get('elem_ap_level') or t.get('domain_ap_level') or '',
                    'domain_id': t['domain_id'],
                    'range_id': t['range_id'],
                })
        
        # Batch-create OWLObjectProperty nodes
        for i in range(0, len(op_batch), BATCH_SIZE):
            batch = op_batch[i:i + BATCH_SIZE]
            try:
                self.conn.execute_query("""
                    UNWIND $batch AS p
                    MERGE (op:OWLObjectProperty {id: p.id})
                    SET op:OWLProperty,
                        op.name = p.name,
                        op.schema = p.schema,
                        op.owl_type = p.owl_type,
                        op.domain_class = p.domain_class,
                        op.range_class = p.range_class,
                        op.min_cardinality = p.min_cardinality,
                        op.max_cardinality = p.max_cardinality,
                        op.container_type = p.container_type,
                        op.semantic_relation = p.semantic_relation,
                        op.ap_level = p.ap_level
                """, {'batch': batch})
            except Exception as e:
                logger.warning(f"Error creating OWLObjectProperty batch at {i}: {e}")
        
        logger.info(f"  OWLObjectProperty nodes: {len(op_batch)} created")
        
        # Batch-create HAS_OBJECT_PROPERTY (domain → property)
        for i in range(0, len(op_batch), BATCH_SIZE):
            batch = op_batch[i:i + BATCH_SIZE]
            try:
                self.conn.execute_query("""
                    UNWIND $batch AS p
                    MATCH (domain:OWLClass {id: p.domain_id})
                    MATCH (op:OWLObjectProperty {id: p.id})
                    MERGE (domain)-[:HAS_OBJECT_PROPERTY]->(op)
                """, {'batch': batch})
            except Exception as e:
                logger.warning(f"Error creating HAS_OBJECT_PROPERTY batch at {i}: {e}")
        
        # Batch-create RANGE_CLASS (property → range class)
        for i in range(0, len(op_batch), BATCH_SIZE):
            batch = op_batch[i:i + BATCH_SIZE]
            try:
                self.conn.execute_query("""
                    UNWIND $batch AS p
                    MATCH (op:OWLObjectProperty {id: p.id})
                    MATCH (rng:OWLClass {id: p.range_id})
                    MERGE (op)-[:RANGE_CLASS]->(rng)
                """, {'batch': batch})
            except Exception as e:
                logger.warning(f"Error creating RANGE_CLASS batch at {i}: {e}")
        
        owl['object_properties'] = len(op_batch)
        logger.info(f"  owl:ObjectProperty: {owl['object_properties']}")
        
        # ── 5a. Elements referencing SimpleType → owl:DatatypeProperty (batched) ──
        dt_triples = self.conn.execute_query("""
            MATCH (domain:OWLClass)-[:CONTAINS]->(elem:XSDElement)-[:HAS_TYPE]->(st:XSDSimpleType)
            WHERE NOT (elem)-[:HAS_TYPE]->(:OWLClass)
            RETURN
                domain.id AS domain_id,
                domain.name AS domain_name,
                elem.name AS elem_name,
                elem.schema AS elem_schema,
                elem.min_occurs AS min_occurs,
                elem.max_occurs AS max_occurs,
                elem.container_type AS container_type,
                elem.ap_level AS elem_ap_level,
                domain.ap_level AS domain_ap_level,
                st.name AS range_name
        """)
        
        # ── 5b. Elements referencing XSD built-in types → owl:DatatypeProperty ──
        builtin_triples = self.conn.execute_query("""
            MATCH (domain:OWLClass)-[:CONTAINS]->(elem:XSDElement)
            WHERE elem.type_ref IS NOT NULL AND elem.type_ref <> ''
            AND NOT (elem)-[:HAS_TYPE]->(:XSDComplexType)
            AND NOT (elem)-[:HAS_TYPE]->(:XSDSimpleType)
            RETURN
                domain.id AS domain_id,
                domain.name AS domain_name,
                elem.name AS elem_name,
                elem.schema AS elem_schema,
                elem.min_occurs AS min_occurs,
                elem.max_occurs AS max_occurs,
                elem.container_type AS container_type,
                elem.ap_level AS elem_ap_level,
                domain.ap_level AS domain_ap_level,
                elem.type_ref AS range_name
        """)
        
        # ── 6. xs:attribute → owl:DatatypeProperty ──
        attr_triples = self.conn.execute_query("""
            MATCH (domain:OWLClass)-[:HAS_ATTRIBUTE]->(attr:XSDAttribute)
            RETURN
                domain.id AS domain_id,
                domain.name AS domain_name,
                '@' + attr.name AS elem_name,
                attr.schema AS elem_schema,
                CASE WHEN attr.use = 'required' THEN '1' ELSE '0' END AS min_occurs,
                '1' AS max_occurs,
                '' AS container_type,
                attr.ap_level AS elem_ap_level,
                domain.ap_level AS domain_ap_level,
                CASE WHEN attr.type_ref IS NOT NULL AND attr.type_ref <> '' THEN attr.type_ref ELSE 'string' END AS range_name
        """)
        
        # Combine all DatatypeProperty triples
        all_dt = list(dt_triples) + list(builtin_triples) + list(attr_triples)
        logger.info(f"  DatatypeProperty triples: {len(dt_triples)} (SimpleType) + {len(builtin_triples)} (built-in) + {len(attr_triples)} (attribute)")
        
        # Build batch of OWLDatatypeProperty props
        dp_batch = []
        seen_dps = set()
        for t in all_dt:
            schema = t.get('elem_schema') or ''
            prop_id = f"dp:{schema}:{t['domain_name']}:{t['elem_name']}"
            if prop_id not in seen_dps:
                seen_dps.add(prop_id)
                dp_batch.append({
                    'id': prop_id,
                    'name': t['elem_name'],
                    'schema': schema,
                    'owl_type': 'owl:DatatypeProperty',
                    'domain_class': t['domain_name'],
                    'range_datatype': t.get('range_name') or 'string',
                    'min_cardinality': t.get('min_occurs') or '1',
                    'max_cardinality': t.get('max_occurs') or '1',
                    'container_type': t.get('container_type') or '',
                    'ap_level': t.get('elem_ap_level') or t.get('domain_ap_level') or '',
                    'domain_id': t['domain_id'],
                })
        
        # Batch-create OWLDatatypeProperty nodes
        for i in range(0, len(dp_batch), BATCH_SIZE):
            batch = dp_batch[i:i + BATCH_SIZE]
            try:
                self.conn.execute_query("""
                    UNWIND $batch AS p
                    MERGE (dp:OWLDatatypeProperty {id: p.id})
                    SET dp:OWLProperty,
                        dp.name = p.name,
                        dp.schema = p.schema,
                        dp.owl_type = p.owl_type,
                        dp.domain_class = p.domain_class,
                        dp.range_datatype = p.range_datatype,
                        dp.min_cardinality = p.min_cardinality,
                        dp.max_cardinality = p.max_cardinality,
                        dp.container_type = p.container_type,
                        dp.ap_level = p.ap_level
                """, {'batch': batch})
            except Exception as e:
                logger.warning(f"Error creating OWLDatatypeProperty batch at {i}: {e}")
        
        logger.info(f"  OWLDatatypeProperty nodes: {len(dp_batch)} created")
        
        # Batch-create HAS_DATATYPE_PROPERTY (domain → property)
        for i in range(0, len(dp_batch), BATCH_SIZE):
            batch = dp_batch[i:i + BATCH_SIZE]
            try:
                self.conn.execute_query("""
                    UNWIND $batch AS p
                    MATCH (domain:OWLClass {id: p.domain_id})
                    MATCH (dp:OWLDatatypeProperty {id: p.id})
                    MERGE (domain)-[:HAS_DATATYPE_PROPERTY]->(dp)
                """, {'batch': batch})
            except Exception as e:
                logger.warning(f"Error creating HAS_DATATYPE_PROPERTY batch at {i}: {e}")
        
        owl['dt_simple'] = len(dt_triples)
        owl['dt_builtin'] = len(builtin_triples)
        owl['dt_attr'] = len(attr_triples)
        owl['datatype_properties'] = len(dp_batch)
        logger.info(f"  owl:DatatypeProperty: {owl['datatype_properties']} unique nodes")
        
        # ── Summary ──
        total_classes = owl['classes'] + owl.get('global_element_classes', 0)
        logger.info(f"  ── OWL Layer Summary ──")
        logger.info(f"    owl:Class:            {total_classes}")
        logger.info(f"    owl:ObjectProperty:   {owl['object_properties']}")
        logger.info(f"    owl:DatatypeProperty: {owl['datatype_properties']}")
        logger.info(f"    rdfs:subClassOf:      {owl['subclass_of']}")
        
        self.stats['owl_stats'] = owl
    
    def _link_ontology_classes(self):
        """Create MAPS_TO_SCHEMA relationships between OntologyClass and XSDComplexType.
        
        OntologyClass nodes have a 'label' property (e.g., 'Part', 'Assembly').
        XSDComplexType nodes have a 'name' property (e.g., 'Part', 'Assembly').
        When they share the same ap_level and the label matches the name,
        create an OntologyClass -[MAPS_TO_SCHEMA]-> XSDComplexType relationship.
        """
        if self.dry_run or not self.conn:
            return
        
        logger.info("Linking OntologyClass nodes to XSD ComplexTypes...")
        
        cypher = """
            MATCH (o:OntologyClass)
            WHERE o.ap_level IS NOT NULL AND o.label IS NOT NULL
            MATCH (x:XSDComplexType)
            WHERE x.ap_level = o.ap_level AND x.name = o.label
            MERGE (o)-[r:MAPS_TO_SCHEMA]->(x)
            RETURN count(r) AS cnt
        """
        
        try:
            result = self.conn.execute_query(cypher)
            cnt = result[0]['cnt'] if result else 0
            logger.info(f"  Created {cnt} MAPS_TO_SCHEMA links (OntologyClass -> XSDComplexType)")
            self.stats["relationships_created"] += cnt
        except Exception as e:
            logger.warning(f"Error creating OntologyClass links: {e}")
    
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
        
        if 'owl_stats' in self.stats:
            owl = self.stats['owl_stats']
            total_dt = owl.get('dt_simple', 0) + owl.get('dt_builtin', 0) + owl.get('dt_attr', 0)
            total_classes = owl.get('classes', 0) + owl.get('global_element_classes', 0)
            logger.info("  OWL Ontology Layer:")
            logger.info(f"    owl:Class:            {total_classes}")
            logger.info(f"    owl:ObjectProperty:   {owl.get('object_properties', 0)}")
            logger.info(f"    owl:DatatypeProperty: {total_dt}")
            logger.info(f"    rdfs:subClassOf:      {owl.get('subclass_of', 0)}")
        
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
    parser.add_argument(
        '--ap-level',
        type=str,
        default=None,
        help='Explicit AP level to tag nodes with (e.g., AP242, AP239). Auto-detected from path if not specified.'
    )
    
    args = parser.parse_args()
    
    # Default to SMRL data directories
    if not args.file and not args.directory:
        args.directory = PROJECT_ROOT / 'smrlv12' / 'data'
    
    ingester = XSDIngester(dry_run=args.dry_run, ap_level=args.ap_level)
    
    try:
        # Clear if requested
        if args.clear and not args.dry_run and ingester.conn:
            logger.warning("Clearing existing XSD and OWL nodes...")
            ingester.conn.execute_query("MATCH (n:OWLProperty) DETACH DELETE n")
            ingester.conn.execute_query("MATCH (n:XSDElement) DETACH DELETE n")
        
        # Ingest
        if args.file:
            ingester.ingest_file(args.file)
            ingester.finalize()
        elif args.directory:
            ingester.ingest_directory(args.directory)
        
        ingester.print_summary()
        
    finally:
        ingester.close()


if __name__ == "__main__":
    main()
