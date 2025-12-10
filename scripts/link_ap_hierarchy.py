#!/usr/bin/env python3
"""
Cross-Schema Linking Script for AP239/AP242/AP243 Hierarchy
============================================================================
Purpose: Establish relationships between AP levels based on naming patterns,
         semantic matching, and traceability specifications.

Architecture:
- Level 1 (AP239): Requirements, Analysis, Approvals, Documents
- Level 2 (AP242): Parts, Materials, CAD Geometry, Assemblies  
- Level 3 (AP243): Ontologies, Units, Value Types, Classifications

Linking Strategies:
1. Name-based matching (e.g., "Thermal" requirement → "Heat Sink" part)
2. Specification references (e.g., requirement ID in part description)
3. Material-to-ontology classification
4. Property-to-unit associations
5. Analysis-to-geometry validation chains

Usage:
    python scripts/link_ap_hierarchy.py [--dry-run] [--verbose]
    
Options:
    --dry-run    Show what would be linked without creating relationships
    --verbose    Print detailed matching information
"""

import argparse
import re
import sys
from typing import Dict, List, Set, Tuple

from loguru import logger

# Add parent directory to path
sys.path.insert(0, '.')
from src.web.services import get_neo4j_service


class APHierarchyLinker:
    """Creates cross-level relationships in AP239/AP242/AP243 hierarchy."""
    
    def __init__(self, neo4j_service, dry_run: bool = False):
        self.conn = neo4j_service
        self.dry_run = dry_run
        self.stats = {
            'requirement_to_part': 0,
            'requirement_to_material': 0,
            'analysis_to_geometry': 0,
            'analysis_to_material': 0,
            'approval_to_part_version': 0,
            'material_to_ontology': 0,
            'property_to_unit': 0,
            'requirement_to_unit': 0,
            'total': 0
        }
        
    def link_all(self):
        """Execute all linking strategies."""
        logger.info("Starting AP hierarchy linking process...")
        
        # Level 1 → Level 2 links
        self.link_requirements_to_parts()
        self.link_requirements_to_materials()
        self.link_analysis_to_geometry()
        self.link_analysis_to_materials()
        self.link_approvals_to_part_versions()
        
        # Level 2 → Level 3 links
        self.link_materials_to_ontologies()
        self.link_properties_to_units()
        
        # Level 1 → Level 3 direct links
        self.link_requirements_to_units()
        
        self._report_statistics()
        
    def link_requirements_to_parts(self):
        """Link Requirements (AP239) to Parts (AP242) based on name keywords."""
        logger.info("Linking requirements to parts...")
        
        # Get all requirements
        req_query = """
        MATCH (req:Requirement) 
        WHERE req.ap_level = 1
        RETURN req.id AS id, req.name AS name, req.description AS description
        """
        requirements = self.conn.execute_query(req_query)
        
        # Get all parts
        part_query = """
        MATCH (part:Part)
        WHERE part.ap_level = 2
        RETURN part.id AS id, part.name AS name, part.description AS description
        """
        parts = self.conn.execute_query(part_query)
        
        # Match based on keyword overlap
        for req in requirements:
            req_keywords = self._extract_keywords(req['name'], req.get('description', ''))
            
            for part in parts:
                part_keywords = self._extract_keywords(part['name'], part.get('description', ''))
                
                # Check for keyword overlap
                if self._has_keyword_match(req_keywords, part_keywords, threshold=0.3):
                    self._create_relationship(
                        'Requirement', req['id'], 
                        'Part', part['id'],
                        'SATISFIED_BY_PART',
                        {'match_score': self._calculate_match_score(req_keywords, part_keywords)}
                    )
                    self.stats['requirement_to_part'] += 1
                    
    def link_requirements_to_materials(self):
        """Link Requirements (AP239) to Materials (AP242) for material specs."""
        logger.info("Linking requirements to materials...")
        
        # Keywords that suggest material requirements
        material_keywords = [
            'material', 'thermal', 'conductivity', 'strength', 'density',
            'temperature', 'corrosion', 'resistance', 'durability', 'weight'
        ]
        
        req_query = """
        MATCH (req:Requirement)
        WHERE req.ap_level = 1
        RETURN req.id AS id, req.name AS name, req.description AS description
        """
        requirements = self.conn.execute_query(req_query)
        
        mat_query = """
        MATCH (mat:Material)
        WHERE mat.ap_level = 2
        RETURN mat.name AS name, mat.material_type AS type, mat.specification AS spec
        """
        materials = self.conn.execute_query(mat_query)
        
        for req in requirements:
            req_text = f"{req['name']} {req.get('description', '')}".lower()
            
            # Check if requirement mentions materials
            if any(kw in req_text for kw in material_keywords):
                for mat in materials:
                    mat_text = f"{mat['name']} {mat.get('type', '')}".lower()
                    
                    # Check for material name in requirement
                    if mat['name'].lower() in req_text:
                        self._create_relationship(
                            'Requirement', req['id'],
                            'Material', mat['name'],
                            'REQUIRES_MATERIAL',
                            {'context': 'Material specification requirement'}
                        )
                        self.stats['requirement_to_material'] += 1
                        
    def link_analysis_to_geometry(self):
        """Link Analysis (AP239) to GeometricModel (AP242) for simulation models."""
        logger.info("Linking analysis to geometry...")
        
        ana_query = """
        MATCH (ana:Analysis)
        WHERE ana.ap_level = 1
        RETURN ana.name AS name, ana.type AS type, ana.method AS method
        """
        analyses = self.conn.execute_query(ana_query)
        
        geo_query = """
        MATCH (geo:GeometricModel)
        WHERE geo.ap_level = 2
        RETURN geo.name AS name, geo.model_type AS type, geo.units AS units
        """
        geometries = self.conn.execute_query(geo_query)
        
        for ana in analyses:
            ana_keywords = self._extract_keywords(ana['name'], ana.get('type', ''))
            
            for geo in geometries:
                geo_keywords = self._extract_keywords(geo['name'], geo.get('type', ''))
                
                # Match analysis to corresponding CAD model
                if self._has_keyword_match(ana_keywords, geo_keywords, threshold=0.25):
                    self._create_relationship(
                        'Analysis', ana['name'],
                        'GeometricModel', geo['name'],
                        'ANALYZES_GEOMETRY',
                        {'method': ana.get('method', 'Unknown')}
                    )
                    self.stats['analysis_to_geometry'] += 1
                    
    def link_analysis_to_materials(self):
        """Link Analysis (AP239) to Materials (AP242) for material validation."""
        logger.info("Linking analysis to materials...")
        
        ana_query = """
        MATCH (ana:Analysis)
        WHERE ana.ap_level = 1 AND ana.type =~ '(?i).*thermal.*|.*mechanical.*|.*stress.*'
        RETURN ana.name AS name, ana.type AS type
        """
        analyses = self.conn.execute_query(ana_query)
        
        mat_query = """
        MATCH (mat:Material)
        WHERE mat.ap_level = 2
        RETURN mat.name AS name, mat.material_type AS type
        """
        materials = self.conn.execute_query(mat_query)
        
        for ana in analyses:
            # Match thermal analysis to thermal materials, etc.
            ana_type = ana.get('type', '').lower()
            
            for mat in materials:
                mat_name = mat['name'].lower()
                
                # Heuristic: if analysis mentions material keyword
                if ('thermal' in ana_type and 'thermal' in mat_name) or \
                   ('mechanical' in ana_type and mat.get('type') == 'Metal'):
                    self._create_relationship(
                        'Analysis', ana['name'],
                        'Material', mat['name'],
                        'ANALYZED_BY_MODEL',
                        {'notes': f"Material properties validated by {ana.get('type', 'analysis')}"}
                    )
                    self.stats['analysis_to_material'] += 1
                    
    def link_approvals_to_part_versions(self):
        """Link Approvals (AP239) to PartVersions (AP242)."""
        logger.info("Linking approvals to part versions...")
        
        appr_query = """
        MATCH (appr:Approval)
        WHERE appr.ap_level = 1 AND appr.status = 'Approved'
        RETURN appr.name AS name, appr.approval_date AS date
        """
        approvals = self.conn.execute_query(appr_query)
        
        pv_query = """
        MATCH (pv:PartVersion)
        WHERE pv.ap_level = 2 AND pv.status = 'Current'
        RETURN pv.name AS name, pv.version AS version
        """
        part_versions = self.conn.execute_query(pv_query)
        
        # Simple heuristic: approved designs → current part versions
        for appr in approvals:
            for pv in part_versions:
                # Check if approval name contains part version keywords
                appr_keywords = self._extract_keywords(appr['name'])
                pv_keywords = self._extract_keywords(pv['name'])
                
                if self._has_keyword_match(appr_keywords, pv_keywords, threshold=0.2):
                    self._create_relationship(
                        'Approval', appr['name'],
                        'PartVersion', pv['name'],
                        'APPROVED_FOR_VERSION',
                        {'approval_date': appr.get('date', 'Unknown')}
                    )
                    self.stats['approval_to_part_version'] += 1
                    
    def link_materials_to_ontologies(self):
        """Link Materials (AP242) to ExternalOwlClass (AP243) ontologies."""
        logger.info("Linking materials to ontologies...")
        
        mat_query = """
        MATCH (mat:Material)
        WHERE mat.ap_level = 2
        RETURN mat.name AS name, mat.material_type AS type
        """
        materials = self.conn.execute_query(mat_query)
        
        owl_query = """
        MATCH (owl:ExternalOwlClass)
        WHERE owl.ap_level = 3
        RETURN owl.name AS name, owl.ontology AS ontology, owl.uri AS uri
        """
        ontologies = self.conn.execute_query(owl_query)
        
        # Classify materials by ontology
        for mat in materials:
            mat_type = mat.get('type', '').lower()
            mat_name = mat['name'].lower()
            
            for owl in ontologies:
                owl_name = owl['name'].lower()
                
                # Match based on material type keywords
                if ('thermal' in mat_name and 'thermal' in owl_name) or \
                   ('metal' in mat_type and 'material' in owl_name):
                    self._create_relationship(
                        'Material', mat['name'],
                        'ExternalOwlClass', owl['name'],
                        'MATERIAL_CLASSIFIED_AS',
                        {'ontology': owl.get('ontology', 'Unknown')}
                    )
                    self.stats['material_to_ontology'] += 1
                    
    def link_properties_to_units(self):
        """Link MaterialProperty (AP242) to ExternalUnit (AP243)."""
        logger.info("Linking properties to units...")
        
        prop_query = """
        MATCH (prop:MaterialProperty)
        WHERE prop.ap_level = 2 AND prop.unit IS NOT NULL
        RETURN prop.name AS name, prop.unit AS unit, prop.value AS value
        """
        properties = self.conn.execute_query(prop_query)
        
        unit_query = """
        MATCH (unit:ExternalUnit)
        WHERE unit.ap_level = 3
        RETURN unit.name AS name, unit.symbol AS symbol, unit.unit_type AS type
        """
        units = self.conn.execute_query(unit_query)
        
        for prop in properties:
            prop_unit = prop['unit'].strip()
            
            for unit in units:
                unit_symbol = unit.get('symbol', '').strip()
                
                # Match by unit symbol
                if prop_unit == unit_symbol:
                    self._create_relationship(
                        'MaterialProperty', prop['name'],
                        'ExternalUnit', unit['name'],
                        'USES_UNIT',
                        {'value': prop.get('value', 'Unknown')}
                    )
                    self.stats['property_to_unit'] += 1
                    break  # Only one unit per property
                    
    def link_requirements_to_units(self):
        """Link Requirements (AP239) directly to ExternalUnit (AP243) for specs."""
        logger.info("Linking requirements to units (Level 1 → Level 3)...")
        
        req_query = """
        MATCH (req:Requirement)
        WHERE req.ap_level = 1
        RETURN req.id AS id, req.name AS name, req.description AS description
        """
        requirements = self.conn.execute_query(req_query)
        
        unit_query = """
        MATCH (unit:ExternalUnit)
        WHERE unit.ap_level = 3
        RETURN unit.name AS name, unit.symbol AS symbol, unit.unit_type AS type
        """
        units = self.conn.execute_query(unit_query)
        
        for req in requirements:
            req_text = f"{req['name']} {req.get('description', '')}"
            
            for unit in units:
                unit_symbol = unit.get('symbol', '')
                
                # Check if requirement mentions unit symbol
                if unit_symbol and unit_symbol in req_text:
                    self._create_relationship(
                        'Requirement', req['id'],
                        'ExternalUnit', unit['name'],
                        'REQUIREMENT_VALUE_TYPE',
                        {'context': 'Temperature specification', 'symbol': unit_symbol}
                    )
                    self.stats['requirement_to_unit'] += 1
                    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _extract_keywords(self, *texts: str) -> Set[str]:
        """Extract meaningful keywords from text fields."""
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        keywords = set()
        
        for text in texts:
            if not text:
                continue
            # Split on non-alphanumeric, lowercase, remove stopwords
            words = re.findall(r'\w+', text.lower())
            keywords.update(w for w in words if len(w) > 2 and w not in stopwords)
            
        return keywords
        
    def _has_keyword_match(self, keywords1: Set[str], keywords2: Set[str], threshold: float = 0.3) -> bool:
        """Check if keyword sets have sufficient overlap."""
        if not keywords1 or not keywords2:
            return False
        
        intersection = keywords1 & keywords2
        union = keywords1 | keywords2
        
        jaccard = len(intersection) / len(union) if union else 0
        return jaccard >= threshold
        
    def _calculate_match_score(self, keywords1: Set[str], keywords2: Set[str]) -> float:
        """Calculate Jaccard similarity coefficient."""
        if not keywords1 or not keywords2:
            return 0.0
        
        intersection = keywords1 & keywords2
        union = keywords1 | keywords2
        
        return len(intersection) / len(union) if union else 0.0
        
    def _create_relationship(
        self, 
        from_label: str, from_id: str,
        to_label: str, to_id: str,
        rel_type: str,
        properties: Dict = None
    ):
        """Create a cross-level relationship between nodes."""
        if self.dry_run:
            logger.info(f"[DRY RUN] Would create: ({from_label}:{from_id})-[:{rel_type}]->({to_label}:{to_id})")
            return
            
        # Use name or id for matching
        from_prop = 'id' if from_label in ['Requirement', 'Part'] else 'name'
        to_prop = 'id' if to_label in ['Requirement', 'Part'] else 'name'
        
        query = f"""
        MATCH (from:{from_label} {{{from_prop}: $from_id}})
        MATCH (to:{to_label} {{{to_prop}: $to_id}})
        MERGE (from)-[r:{rel_type}]->(to)
        SET r += $properties
        RETURN count(r) AS created
        """
        
        try:
            result = self.conn.execute_query(
                query,
                {'from_id': from_id, 'to_id': to_id, 'properties': properties or {}}
            )
            if result and result[0]['created'] > 0:
                self.stats['total'] += 1
                logger.debug(f"Created: ({from_label}:{from_id})-[:{rel_type}]->({to_label}:{to_id})")
        except Exception as e:
            logger.error(f"Failed to create relationship: {e}")
            
    def _report_statistics(self):
        """Print summary of linking operations."""
        logger.info("=" * 80)
        logger.info("AP HIERARCHY LINKING SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Requirements → Parts:         {self.stats['requirement_to_part']}")
        logger.info(f"Requirements → Materials:     {self.stats['requirement_to_material']}")
        logger.info(f"Analysis → Geometry:          {self.stats['analysis_to_geometry']}")
        logger.info(f"Analysis → Materials:         {self.stats['analysis_to_material']}")
        logger.info(f"Approvals → Part Versions:   {self.stats['approval_to_part_version']}")
        logger.info(f"Materials → Ontologies:       {self.stats['material_to_ontology']}")
        logger.info(f"Properties → Units:           {self.stats['property_to_unit']}")
        logger.info(f"Requirements → Units:         {self.stats['requirement_to_unit']}")
        logger.info("-" * 80)
        logger.info(f"TOTAL RELATIONSHIPS CREATED:  {self.stats['total']}")
        logger.info("=" * 80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Link AP239/AP242/AP243 hierarchy')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be linked')
    parser.add_argument('--verbose', action='store_true', help='Print detailed logs')
    args = parser.parse_args()
    
    if args.verbose:
        logger.remove()
        logger.add(lambda msg: print(msg, end=''), level='DEBUG')
    
    # Connect to Neo4j
    neo4j = get_neo4j_service()
    
    linker = APHierarchyLinker(neo4j, dry_run=args.dry_run)
    linker.link_all()
        
    logger.info("Cross-schema linking complete!")


if __name__ == '__main__':
    main()
