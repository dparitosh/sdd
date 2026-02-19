#!/usr/bin/env python3
"""
Semantic Layer Augmentation for MBSE Knowledge Graph
=====================================================
Augments existing KG with derived semantic knowledge:
  - Domain Concepts extracted from entity names
  - Documentation nodes linked to elements
  - External References (href cross-model links)
  - Type resolution (TYPED_AS relationships)
  - Cross-schema equivalence (XMI ↔ XSD SAME_AS)
  - Value specifications (cardinality, constraints)
  - Semantic similarity links

Usage:
    python backend/scripts/ingest_semantic_layer.py [--dry-run]
"""

import os
import sys
import re
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Set, Tuple
from collections import defaultdict
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
# PYDANTIC MODELS FOR SEMANTIC LAYER
# ============================================================================

class SemanticRelationType(str, Enum):
    """Semantic relationship types for augmented knowledge"""
    # Documentation
    DOCUMENTED_BY = "DOCUMENTED_BY"
    ANNOTATES = "ANNOTATES"
    
    # Type system
    TYPED_AS = "TYPED_AS"
    INSTANCE_OF = "INSTANCE_OF"
    
    # Equivalence
    SAME_AS = "SAME_AS"
    SIMILAR_TO = "SIMILAR_TO"
    DERIVED_FROM = "DERIVED_FROM"
    
    # Domain concepts
    REPRESENTS = "REPRESENTS"
    CATEGORIZED_AS = "CATEGORIZED_AS"
    PART_OF_DOMAIN = "PART_OF_DOMAIN"
    
    # Cross-references
    REFERENCES_EXTERNAL = "REFERENCES_EXTERNAL"
    IMPORTS = "IMPORTS"
    
    # Constraints
    CONSTRAINED_BY = "CONSTRAINED_BY"
    HAS_CARDINALITY = "HAS_CARDINALITY"


class DomainConcept(BaseModel):
    """A domain concept extracted from MBSE elements"""
    name: str
    normalized_name: str  # lowercase, no special chars
    category: str  # Entity, Attribute, Action, etc.
    source_elements: List[str] = Field(default_factory=list)
    frequency: int = 1
    
    
class Documentation(BaseModel):
    """Documentation extracted from comments"""
    doc_id: str
    content: str
    element_ref: str
    doc_type: str = "note"  # note, description, rationale
    

class ExternalReference(BaseModel):
    """External model reference via href"""
    ref_id: str
    source_element: str
    target_href: str
    target_model: str
    target_element: str
    

class TypeDefinition(BaseModel):
    """Type specification for properties"""
    element_id: str
    type_ref: str
    type_name: str
    is_primitive: bool = False
    cardinality_lower: int = 1
    cardinality_upper: int = 1  # -1 for unlimited


class SemanticRelationship(BaseModel):
    """Semantic relationship between elements"""
    from_id: str
    to_id: str
    rel_type: SemanticRelationType
    confidence: float = 1.0
    properties: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# SEMANTIC LAYER BUILDER
# ============================================================================

class SemanticLayerBuilder:
    """
    Builds semantic layer on top of existing MBSE knowledge graph.
    Extracts domain concepts, documentation, and cross-references.
    """
    
    # XMI namespace
    XMI_NS = 'http://www.omg.org/spec/XMI/20131001'
    UML_NS = 'http://www.omg.org/spec/UML/20131001'
    
    NAMESPACES = {
        'xmi': XMI_NS,
        'uml': UML_NS,
    }
    
    # Primitive types
    PRIMITIVE_TYPES = {
        'STRING', 'INTEGER', 'BOOLEAN', 'REAL', 'DOUBLE', 'FLOAT',
        'string', 'integer', 'boolean', 'real', 'double', 'float',
        'int', 'bool', 'str', 'number'
    }
    
    # Domain categories based on naming patterns
    DOMAIN_CATEGORIES = {
        'entity': r'^[A-Z][a-z]+(?:[A-Z][a-z]+)*$',  # PascalCase nouns
        'action': r'^(create|update|delete|get|set|add|remove|validate|process)',
        'attribute': r'^(is|has|can|should|the)',
        'relationship': r'^(associated|related|linked|connected)',
        'container': r'^(list|set|collection|array|sequence)',
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
        
        # Storage
        self.domain_concepts: Dict[str, DomainConcept] = {}
        self.documentation: List[Documentation] = []
        self.external_refs: List[ExternalReference] = []
        self.type_definitions: List[TypeDefinition] = []
        self.semantic_rels: List[SemanticRelationship] = []
        
        # XMI element cache
        self.xmi_elements: Dict[str, Dict] = {}
        self.xmi_names: Dict[str, str] = {}  # id -> name mapping
        
        # Statistics
        self.stats = {
            "concepts_extracted": 0,
            "documentation_nodes": 0,
            "external_refs": 0,
            "type_definitions": 0,
            "semantic_relationships": 0,
            "cross_schema_links": 0,
            "errors": [],
        }
    
    def process_xmi_file(self, file_path: Path):
        """Process XMI file to extract semantic layer data"""
        logger.info(f"Processing XMI for semantic layer: {file_path.name}")
        
        try:
            tree = etree.parse(str(file_path))
            root = tree.getroot()
            
            # Phase 1: Cache all elements
            logger.info("  Phase 1: Caching XMI elements...")
            self._cache_elements(root)
            
            # Phase 2: Extract documentation
            logger.info("  Phase 2: Extracting documentation...")
            self._extract_documentation(root)
            
            # Phase 3: Extract external references
            logger.info("  Phase 3: Extracting external references...")
            self._extract_external_refs(root)
            
            # Phase 4: Extract type definitions
            logger.info("  Phase 4: Extracting type definitions...")
            self._extract_type_definitions(root)
            
            # Phase 5: Extract domain concepts from names
            logger.info("  Phase 5: Extracting domain concepts...")
            self._extract_domain_concepts()
            
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            self.stats["errors"].append(str(e))
            import traceback
            traceback.print_exc()
    
    def _cache_elements(self, root: etree._Element):
        """Cache all XMI elements for quick lookup"""
        count = 0
        for elem in root.iter():
            xmi_id = elem.get(f'{{{self.XMI_NS}}}id')
            if xmi_id:
                # Get name
                name = elem.get('name', '')
                if not name:
                    name_elem = elem.find('name')
                    if name_elem is not None and name_elem.text:
                        name = name_elem.text
                
                self.xmi_elements[xmi_id] = {
                    'id': xmi_id,
                    'type': elem.get(f'{{{self.XMI_NS}}}type', ''),
                    'name': name,
                    'element': elem
                }
                if name:
                    self.xmi_names[xmi_id] = name
                count += 1
        
        logger.info(f"    Cached {count} elements, {len(self.xmi_names)} named")
    
    def _extract_documentation(self, root: etree._Element):
        """Extract documentation from ownedComment elements"""
        for comment in root.iter():
            xmi_type = comment.get(f'{{{self.XMI_NS}}}type')
            if xmi_type != 'uml:Comment':
                continue
            
            xmi_id = comment.get(f'{{{self.XMI_NS}}}id')
            if not xmi_id:
                continue
            
            # Get comment body
            body_elem = comment.find('body')
            if body_elem is None or not body_elem.text:
                continue
            
            body = body_elem.text.strip()
            if not body:
                continue
            
            # Find annotated element
            annotated = comment.find('annotatedElement')
            element_ref = ''
            if annotated is not None:
                element_ref = annotated.get(f'{{{self.XMI_NS}}}idref', '')
            
            # Determine doc type from content
            doc_type = 'description'
            body_lower = body.lower()
            if '<note>' in body_lower or body_lower.startswith('note:'):
                doc_type = 'note'
            elif 'rationale' in body_lower or 'reason' in body_lower:
                doc_type = 'rationale'
            elif 'constraint' in body_lower or 'must' in body_lower:
                doc_type = 'constraint'
            elif 'example' in body_lower:
                doc_type = 'example'
            
            # Clean HTML-like tags from body
            clean_body = re.sub(r'<[^>]+>', '', body)
            clean_body = clean_body.replace('&#13;', '\n').strip()
            
            doc = Documentation(
                doc_id=xmi_id,
                content=clean_body[:2000],  # Truncate very long docs
                element_ref=element_ref,
                doc_type=doc_type
            )
            self.documentation.append(doc)
            self.stats["documentation_nodes"] += 1
        
        logger.info(f"    Extracted {len(self.documentation)} documentation nodes")
    
    def _extract_external_refs(self, root: etree._Element):
        """Extract external href references"""
        for elem in root.iter():
            xmi_id = elem.get(f'{{{self.XMI_NS}}}id')
            if not xmi_id:
                continue
            
            # Check for href in type references
            type_elem = elem.find('type')
            if type_elem is not None:
                href = type_elem.get('href')
                if href and '#' in href:
                    parts = href.rsplit('#', 1)
                    model_path = parts[0]
                    target_elem = parts[1] if len(parts) > 1 else ''
                    
                    # Extract model name from path
                    model_name = Path(model_path).stem if model_path else 'unknown'
                    
                    ref = ExternalReference(
                        ref_id=f"{xmi_id}_ref",
                        source_element=xmi_id,
                        target_href=href,
                        target_model=model_name,
                        target_element=target_elem
                    )
                    self.external_refs.append(ref)
                    self.stats["external_refs"] += 1
            
            # Check for general references (inheritance)
            general_elem = elem.find('general')
            if general_elem is not None:
                href = general_elem.get('href')
                if href and '#' in href:
                    parts = href.rsplit('#', 1)
                    model_path = parts[0]
                    target_elem = parts[1] if len(parts) > 1 else ''
                    model_name = Path(model_path).stem if model_path else 'unknown'
                    
                    ref = ExternalReference(
                        ref_id=f"{xmi_id}_gen_ref",
                        source_element=xmi_id,
                        target_href=href,
                        target_model=model_name,
                        target_element=target_elem
                    )
                    self.external_refs.append(ref)
                    self.stats["external_refs"] += 1
        
        logger.info(f"    Extracted {len(self.external_refs)} external references")
    
    def _extract_type_definitions(self, root: etree._Element):
        """Extract type definitions and cardinality"""
        for elem in root.iter():
            xmi_type = elem.get(f'{{{self.XMI_NS}}}type')
            xmi_id = elem.get(f'{{{self.XMI_NS}}}id')
            
            if not xmi_id or xmi_type not in ('uml:Property', 'uml:Port', 'uml:Parameter'):
                continue
            
            # Get type reference
            type_ref = elem.get('type', '')
            type_name = ''
            is_primitive = False
            
            if not type_ref:
                type_elem = elem.find('type')
                if type_elem is not None:
                    type_ref = type_elem.get(f'{{{self.XMI_NS}}}idref', '')
                    href = type_elem.get('href', '')
                    if href:
                        # Extract type name from href
                        if '#' in href:
                            type_name = href.split('#')[-1]
                        is_primitive = any(p in href.upper() for p in self.PRIMITIVE_TYPES)
            
            if type_ref and type_ref in self.xmi_names:
                type_name = self.xmi_names[type_ref]
            
            if not type_ref and not type_name:
                continue
            
            # Get cardinality
            lower = 1
            upper = 1
            
            lower_elem = elem.find('lowerValue')
            if lower_elem is not None:
                val = lower_elem.find('value')
                if val is not None and val.text:
                    try:
                        lower = int(val.text)
                    except ValueError:
                        lower = 0
            
            upper_elem = elem.find('upperValue')
            if upper_elem is not None:
                val = upper_elem.find('value')
                if val is not None and val.text:
                    if val.text == '*':
                        upper = -1  # Unlimited
                    else:
                        try:
                            upper = int(val.text)
                        except ValueError:
                            upper = 1
            
            type_def = TypeDefinition(
                element_id=xmi_id,
                type_ref=type_ref or type_name,
                type_name=type_name or type_ref,
                is_primitive=is_primitive,
                cardinality_lower=lower,
                cardinality_upper=upper
            )
            self.type_definitions.append(type_def)
            self.stats["type_definitions"] += 1
        
        logger.info(f"    Extracted {len(self.type_definitions)} type definitions")
    
    def _extract_domain_concepts(self):
        """Extract domain concepts from element names"""
        name_frequency: Dict[str, int] = defaultdict(int)
        name_sources: Dict[str, List[str]] = defaultdict(list)
        
        for xmi_id, name in self.xmi_names.items():
            if not name or len(name) < 2:
                continue
            
            # Split compound names (camelCase, PascalCase)
            words = self._split_name(name)
            
            for word in words:
                if len(word) >= 3:  # Skip very short words
                    normalized = word.lower()
                    name_frequency[normalized] += 1
                    if xmi_id not in name_sources[normalized]:
                        name_sources[normalized].append(xmi_id)
            
            # Also store full name as concept
            normalized_full = name.lower()
            name_frequency[normalized_full] += 1
            if xmi_id not in name_sources[normalized_full]:
                name_sources[normalized_full].append(xmi_id)
        
        # Create domain concepts for significant terms
        for normalized, freq in name_frequency.items():
            if freq >= 2:  # Only concepts that appear multiple times
                category = self._categorize_concept(normalized)
                concept = DomainConcept(
                    name=normalized.title(),
                    normalized_name=normalized,
                    category=category,
                    source_elements=name_sources[normalized][:10],  # Limit sources
                    frequency=freq
                )
                self.domain_concepts[normalized] = concept
                self.stats["concepts_extracted"] += 1
        
        logger.info(f"    Extracted {len(self.domain_concepts)} domain concepts")
    
    def _split_name(self, name: str) -> List[str]:
        """Split compound name into words"""
        # Split on camelCase and PascalCase
        words = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\d|\W|$)|\d+', name)
        return [w for w in words if len(w) >= 2]
    
    def _categorize_concept(self, name: str) -> str:
        """Categorize a concept based on naming patterns"""
        name_lower = name.lower()
        
        if name_lower.endswith(('item', 'entity', 'object', 'element', 'type')):
            return 'Entity'
        elif name_lower.endswith(('id', 'name', 'value', 'code', 'number')):
            return 'Attribute'
        elif name_lower.endswith(('tion', 'ment', 'ing')):
            return 'Action'
        elif name_lower.startswith(('is', 'has', 'can')):
            return 'Predicate'
        elif name_lower.endswith(('list', 'set', 'collection', 'array')):
            return 'Container'
        else:
            return 'Concept'
    
    def build_cross_schema_links(self):
        """Build SAME_AS links between XMI and XSD elements by name matching"""
        logger.info("Building cross-schema links (XMI ↔ XSD)...")
        
        if self.dry_run or not self.conn:
            return
        
        # Get XMI element names
        xmi_names_query = """
        MATCH (n:MBSEElement)
        WHERE n.name IS NOT NULL AND n.name <> ''
        RETURN n.xmi_id as id, n.name as name, labels(n) as labels
        """
        xmi_results = self.conn.execute_query(xmi_names_query)
        xmi_name_map = {r['name'].lower(): r for r in xmi_results if r['name']}
        
        # Get XSD element names
        xsd_names_query = """
        MATCH (n)
        WHERE (n:XSDComplexType OR n:XSDElement OR n:XSDSimpleType)
          AND n.name IS NOT NULL AND n.name <> ''
        RETURN elementId(n) as id, n.name as name, labels(n) as labels
        """
        xsd_results = self.conn.execute_query(xsd_names_query)
        
        # Find matches
        matches = []
        for xsd in xsd_results:
            xsd_name = xsd['name'].lower()
            if xsd_name in xmi_name_map:
                xmi = xmi_name_map[xsd_name]
                matches.append({
                    'xmi_id': xmi['id'],
                    'xsd_id': xsd['id'],
                    'name': xsd['name'],
                    'xmi_labels': xmi['labels'],
                    'xsd_labels': xsd['labels'],
                })
        
        logger.info(f"  Found {len(matches)} potential cross-schema matches")
        
        # Create SAME_AS relationships
        if matches:
            for i in range(0, len(matches), BATCH_SIZE):
                batch = matches[i:i+BATCH_SIZE]
                query = """
                UNWIND $batch as m
                MATCH (xmi:MBSEElement {xmi_id: m.xmi_id})
                MATCH (xsd) WHERE elementId(xsd) = m.xsd_id
                MERGE (xmi)-[r:SAME_AS]->(xsd)
                SET r.matched_by = 'name',
                    r.confidence = 0.9,
                    r.matched_name = m.name
                """
                self.conn.execute_query(query, {'batch': batch})
            
            self.stats["cross_schema_links"] = len(matches)
            logger.info(f"  Created {len(matches)} SAME_AS relationships")
    
    def create_semantic_nodes(self):
        """Create semantic layer nodes in Neo4j"""
        if self.dry_run or not self.conn:
            logger.info("[DRY RUN] Would create semantic nodes")
            return
        
        # Create Documentation nodes
        logger.info("Creating Documentation nodes...")
        doc_batch = [
            {
                'doc_id': d.doc_id,
                'content': d.content,
                'element_ref': d.element_ref,
                'doc_type': d.doc_type
            }
            for d in self.documentation
        ]
        
        for i in range(0, len(doc_batch), BATCH_SIZE):
            batch = doc_batch[i:i+BATCH_SIZE]
            query = """
            UNWIND $batch as d
            MERGE (doc:Documentation {doc_id: d.doc_id})
            SET doc.content = d.content,
                doc.doc_type = d.doc_type,
                doc.element_ref = d.element_ref
            WITH doc, d
            MATCH (elem:MBSEElement {xmi_id: d.element_ref})
            MERGE (elem)-[:DOCUMENTED_BY]->(doc)
            """
            self.conn.execute_query(query, {'batch': batch})
        
        logger.info(f"  Created {len(doc_batch)} Documentation nodes")
        
        # Create DomainConcept nodes
        logger.info("Creating DomainConcept nodes...")
        concept_batch = [
            {
                'name': c.name,
                'normalized_name': c.normalized_name,
                'category': c.category,
                'frequency': c.frequency,
                'source_ids': c.source_elements
            }
            for c in self.domain_concepts.values()
        ]
        
        for i in range(0, len(concept_batch), BATCH_SIZE):
            batch = concept_batch[i:i+BATCH_SIZE]
            query = """
            UNWIND $batch as c
            MERGE (concept:DomainConcept {normalized_name: c.normalized_name})
            SET concept.name = c.name,
                concept.category = c.category,
                concept.frequency = c.frequency
            WITH concept, c
            UNWIND c.source_ids as src_id
            MATCH (elem:MBSEElement {xmi_id: src_id})
            MERGE (elem)-[:REPRESENTS]->(concept)
            """
            self.conn.execute_query(query, {'batch': batch})
        
        logger.info(f"  Created {len(concept_batch)} DomainConcept nodes")
        
        # Create ExternalModel nodes and references
        logger.info("Creating ExternalReference relationships...")
        model_refs: Dict[str, List[ExternalReference]] = defaultdict(list)
        for ref in self.external_refs:
            model_refs[ref.target_model].append(ref)
        
        # Create model nodes
        for model_name in model_refs.keys():
            query = """
            MERGE (m:ExternalModel {name: $name})
            SET m.created_at = datetime()
            """
            self.conn.execute_query(query, {'name': model_name})
        
        # Create references
        ref_batch = [
            {
                'source_id': r.source_element,
                'target_model': r.target_model,
                'target_element': r.target_element,
                'href': r.target_href
            }
            for r in self.external_refs
        ]
        
        for i in range(0, len(ref_batch), BATCH_SIZE):
            batch = ref_batch[i:i+BATCH_SIZE]
            query = """
            UNWIND $batch as r
            MATCH (elem:MBSEElement {xmi_id: r.source_id})
            MATCH (model:ExternalModel {name: r.target_model})
            MERGE (elem)-[rel:REFERENCES_EXTERNAL]->(model)
            SET rel.target_element = r.target_element,
                rel.href = r.href
            """
            self.conn.execute_query(query, {'batch': batch})
        
        logger.info(f"  Created references to {len(model_refs)} external models")
        
        # Create TYPED_AS relationships with cardinality
        logger.info("Creating TYPED_AS relationships...")
        type_batch = [
            {
                'element_id': t.element_id,
                'type_ref': t.type_ref,
                'type_name': t.type_name,
                'is_primitive': t.is_primitive,
                'lower': t.cardinality_lower,
                'upper': t.cardinality_upper
            }
            for t in self.type_definitions
        ]
        
        for i in range(0, len(type_batch), BATCH_SIZE):
            batch = type_batch[i:i+BATCH_SIZE]
            # Link to existing type elements
            query = """
            UNWIND $batch as t
            MATCH (elem:MBSEElement {xmi_id: t.element_id})
            OPTIONAL MATCH (type_elem:MBSEElement {xmi_id: t.type_ref})
            FOREACH (_ IN CASE WHEN type_elem IS NOT NULL THEN [1] ELSE [] END |
                MERGE (elem)-[r:TYPED_AS]->(type_elem)
                SET r.type_name = t.type_name,
                    r.cardinality_lower = t.lower,
                    r.cardinality_upper = t.upper
            )
            SET elem.type_name = t.type_name,
                elem.is_primitive_type = t.is_primitive,
                elem.cardinality_lower = t.lower,
                elem.cardinality_upper = t.upper
            """
            self.conn.execute_query(query, {'batch': batch})
        
        logger.info(f"  Created {len(type_batch)} type definitions")
    
    def create_semantic_indexes(self):
        """Create indexes for semantic layer nodes"""
        if self.dry_run or not self.conn:
            return
        
        indexes = [
            "CREATE INDEX doc_id_idx IF NOT EXISTS FOR (n:Documentation) ON (n.doc_id)",
            "CREATE INDEX concept_name_idx IF NOT EXISTS FOR (n:DomainConcept) ON (n.normalized_name)",
            "CREATE INDEX ext_model_idx IF NOT EXISTS FOR (n:ExternalModel) ON (n.name)",
            "CREATE FULLTEXT INDEX doc_content_idx IF NOT EXISTS FOR (n:Documentation) ON EACH [n.content]",
        ]
        
        for idx_query in indexes:
            try:
                self.conn.execute_query(idx_query)
            except Exception as e:
                if 'already exists' not in str(e).lower():
                    logger.warning(f"Index creation warning: {e}")
    
    def print_summary(self):
        """Print processing summary"""
        logger.info("=" * 70)
        logger.info("SEMANTIC LAYER SUMMARY")
        logger.info("=" * 70)
        logger.info(f"  Domain concepts extracted: {self.stats['concepts_extracted']}")
        logger.info(f"  Documentation nodes: {self.stats['documentation_nodes']}")
        logger.info(f"  External references: {self.stats['external_refs']}")
        logger.info(f"  Type definitions: {self.stats['type_definitions']}")
        logger.info(f"  Cross-schema links: {self.stats['cross_schema_links']}")
        
        if self.domain_concepts:
            logger.info("\n  Top domain concepts by frequency:")
            sorted_concepts = sorted(
                self.domain_concepts.values(),
                key=lambda c: c.frequency,
                reverse=True
            )[:15]
            for c in sorted_concepts:
                logger.info(f"    {c.name} ({c.category}): {c.frequency} occurrences")
        
        if self.stats["errors"]:
            logger.warning(f"\n  Errors: {len(self.stats['errors'])}")
            for err in self.stats["errors"][:5]:
                logger.warning(f"    - {err}")
        
        logger.info("=" * 70)
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Build semantic layer on MBSE knowledge graph'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Parse without writing to database'
    )
    parser.add_argument(
        '--data-dir',
        type=str,
        default=None,
        help='Directory containing XMI files'
    )
    
    args = parser.parse_args()
    
    # Determine data directory
    if args.data_dir:
        data_dir = Path(args.data_dir)
    else:
        data_dir = PROJECT_ROOT / 'backend' / 'data' / 'raw'
        if not data_dir.exists():
            data_dir = PROJECT_ROOT / 'smrlv12' / 'data' / 'domain_models' / 'mossec'
    
    # Find XMI files
    xmi_files = list(data_dir.glob('**/*.xmi')) if data_dir.exists() else []
    if not xmi_files:
        logger.error(f"No XMI files found in {data_dir}")
        return
    
    logger.info(f"Found {len(xmi_files)} XMI files")
    
    # Build semantic layer
    builder = SemanticLayerBuilder(dry_run=args.dry_run)
    
    try:
        # Process each XMI file
        for xmi_file in xmi_files:
            builder.process_xmi_file(xmi_file)
        
        # Create semantic nodes
        builder.create_semantic_nodes()
        
        # Build cross-schema links
        builder.build_cross_schema_links()
        
        # Create indexes
        builder.create_semantic_indexes()
        
        # Print summary
        builder.print_summary()
        
    finally:
        builder.close()


if __name__ == '__main__':
    main()
