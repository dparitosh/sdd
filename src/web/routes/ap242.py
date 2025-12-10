"""
AP242 REST API Routes - 3D Engineering and Manufacturing
========================================================
Endpoints for Parts, Assemblies, Materials, and CAD Geometry

ISO 10303 AP242 provides 3D engineering capabilities including CAD models,
Bill of Materials (BOM), material specifications, and assembly structures.
"""

import re
from flask import Blueprint, jsonify, request
from loguru import logger

from src.web.services import get_neo4j_service

ap242_bp = Blueprint('ap242', __name__, url_prefix='/api/ap242')

# Valid status values to prevent invalid queries
VALID_STATUSES = {'Released', 'Development', 'Obsolete', 'Draft', 'In Review', 'Approved'}


# ============================================================================
# PARTS ENDPOINTS
# ============================================================================

@ap242_bp.route('/parts', methods=['GET'])
def get_parts():
    """
    Get all parts with optional filtering.
    
    Query Parameters:
        status: Filter by status (Released, Development, Obsolete)
        search: Text search in name and description
        
    Returns:
        JSON array of part objects
    """
    try:
        neo4j = get_neo4j_service()
        
        
        filters = []
        params = {}
        
        if status := request.args.get('status'):
            # Validate status against whitelist
            if status in VALID_STATUSES:
                filters.append("part.status = $status")
                params['status'] = status
            
        if search := request.args.get('search'):
            # Escape regex metacharacters to prevent injection
            escaped_search = re.escape(search)
            filters.append("(part.name =~ $search OR part.description =~ $search)")
            params['search'] = f"(?i).*{escaped_search}.*"
            
        where_clause = " AND ".join(filters) if filters else "1=1"
        
        query = f"""
        MATCH (part:Part)
        WHERE part.ap_level = 2 AND {where_clause}
        OPTIONAL MATCH (part)-[:HAS_VERSION]->(v:PartVersion)
        OPTIONAL MATCH (part)-[:USES_MATERIAL]->(mat:Material)
        OPTIONAL MATCH (req:Requirement)-[:SATISFIED_BY_PART]->(part)
        RETURN part.id AS id,
               part.name AS name,
               part.description AS description,
               part.part_number AS part_number,
               part.status AS status,
               COLLECT(DISTINCT v.version) AS versions,
               COLLECT(DISTINCT mat.name) AS materials,
               COLLECT(DISTINCT req.name) AS satisfies_requirements
        ORDER BY part.part_number, part.name
        """
        
        results = neo4j.execute_query(query, params)
        
        parts = [{
            'id': r['id'],
            'name': r['name'],
            'description': r['description'],
            'part_number': r['part_number'],
            'status': r['status'],
            'versions': [v for v in r['versions'] if v],
            'materials': [m for m in r['materials'] if m],
            'requirements': [req for req in r['satisfies_requirements'] if req]
        } for r in results]
        
        return jsonify({
            'count': len(parts),
            'parts': parts
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching parts: {e}")
        return jsonify({'error': str(e)}), 500


@ap242_bp.route('/parts/<part_id>', methods=['GET'])
def get_part_detail(part_id: str):
    """
    Get detailed information about a specific part.
    
    Returns:
        Part with all relationships (versions, materials, geometry, assemblies, etc.)
    """
    try:
        neo4j = get_neo4j_service()
        
        
        query = """
        MATCH (part:Part {id: $part_id})
        OPTIONAL MATCH (part)-[:HAS_VERSION]->(v:PartVersion)
        OPTIONAL MATCH (part)-[:USES_MATERIAL]->(mat:Material)
        OPTIONAL MATCH (part)-[:HAS_GEOMETRY]->(geo:GeometricModel)
        OPTIONAL MATCH (asm:Assembly)-[:ASSEMBLES_WITH]->(part)
        OPTIONAL MATCH (req:Requirement)-[:SATISFIED_BY_PART]->(part)
        OPTIONAL MATCH (appr:Approval)-[:APPROVED_FOR_VERSION]->(v)
        RETURN part,
               COLLECT(DISTINCT {version: v.version, name: v.name, status: v.status}) AS versions,
               COLLECT(DISTINCT {name: mat.name, type: mat.material_type, spec: mat.specification}) AS materials,
               COLLECT(DISTINCT {name: geo.name, type: geo.model_type, units: geo.units}) AS geometry,
               COLLECT(DISTINCT asm.name) AS assemblies,
               COLLECT(DISTINCT req.name) AS requirements,
               COLLECT(DISTINCT appr.name) AS approvals
        """
        
        results = neo4j.execute_query(query, {'part_id': part_id})
        
        if not results or not results[0].get('part'):
            return jsonify({'error': 'Part not found'}), 404
        
        r = results[0]
        part = r['part']
        
        part_detail = {
            'id': part['id'],
            'name': part['name'],
            'description': part.get('description'),
            'part_number': part.get('part_number'),
            'status': part.get('status'),
            'created_at': str(part.get('created_at')) if part.get('created_at') else None,
            'ap_level': part.get('ap_level'),
            'ap_schema': part.get('ap_schema'),
            'versions': [v for v in r['versions'] if v.get('version')],
            'materials': [m for m in r['materials'] if m.get('name')],
            'geometry': [g for g in r['geometry'] if g.get('name')],
            'assemblies': [a for a in r['assemblies'] if a],
            'requirements': [req for req in r['requirements'] if req],
            'approvals': [appr for appr in r['approvals'] if appr]
        }
        
        return jsonify(part_detail), 200
        
    except Exception as e:
        logger.error(f"Error fetching part {part_id}: {e}")
        return jsonify({'error': str(e)}), 500


@ap242_bp.route('/parts/<part_id>/bom', methods=['GET'])
def get_part_bom(part_id: str):
    """
    Get Bill of Materials (BOM) for a part.
    
    Returns:
        Tree structure of assembly components
    """
    try:
        neo4j = get_neo4j_service()
        
        
        query = """
        MATCH (part:Part {id: $part_id})
        OPTIONAL MATCH (asm:Assembly)-[:ASSEMBLES_WITH]->(part)
        OPTIONAL MATCH (asm)-[:ASSEMBLES_WITH]->(subpart:Part)
        WHERE subpart.id <> $part_id
        RETURN part.name AS root_part,
               asm.name AS assembly,
               COLLECT(DISTINCT {
                   id: subpart.id,
                   name: subpart.name,
                   part_number: subpart.part_number
               }) AS components
        """
        
        results = neo4j.execute_query(query, {'part_id': part_id})
        
        if not results:
            return jsonify({'error': 'Part not found'}), 404
            
        return jsonify({
            'root_part': results[0]['root_part'],
            'assembly': results[0]['assembly'],
            'components': [c for c in results[0]['components'] if c.get('id')]
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching BOM for {part_id}: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# ASSEMBLIES ENDPOINTS
# ============================================================================

@ap242_bp.route('/assemblies', methods=['GET'])
def get_assemblies():
    """
    Get all assemblies.
    
    Query Parameters:
        type: Filter by assembly type (Mechanical, Electrical, etc.)
        
    Returns:
        JSON array of assembly objects
    """
    try:
        neo4j = get_neo4j_service()
        
        
        asm_type = request.args.get('type')
        where_clause = "asm.assembly_type = $type" if asm_type else "1=1"
        params = {'type': asm_type} if asm_type else {}
        
        query = f"""
        MATCH (asm:Assembly)
        WHERE asm.ap_level = 2 AND {where_clause}
        OPTIONAL MATCH (asm)-[:ASSEMBLES_WITH]->(part:Part)
        RETURN asm.name AS name,
               asm.assembly_type AS type,
               asm.component_count AS component_count,
               COLLECT(DISTINCT part.name) AS parts
        ORDER BY asm.name
        """
        
        results = neo4j.execute_query(query, params)
        
        assemblies = [{
            'name': r['name'],
            'type': r['type'],
            'component_count': r['component_count'],
            'parts': [p for p in r['parts'] if p]
        } for r in results]
        
        return jsonify({
            'count': len(assemblies),
            'assemblies': assemblies
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching assemblies: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# MATERIALS ENDPOINTS
# ============================================================================

@ap242_bp.route('/materials', methods=['GET'])
def get_materials():
    """
    Get all materials with optional filtering.
    
    Query Parameters:
        type: Filter by material type (Metal, Polymer, Composite, etc.)
        search: Text search in name and specification
        
    Returns:
        JSON array of material objects
    """
    try:
        neo4j = get_neo4j_service()
        
        
        filters = []
        params = {}
        
        if mat_type := request.args.get('type'):
            filters.append("mat.material_type = $type")
            params['type'] = mat_type
            
        if search := request.args.get('search'):
            filters.append("(mat.name =~ $search OR mat.specification =~ $search)")
            params['search'] = f"(?i).*{search}.*"
            
        where_clause = " AND ".join(filters) if filters else "1=1"
        
        query = f"""
        MATCH (mat:Material)
        WHERE mat.ap_level = 2 AND {where_clause}
        OPTIONAL MATCH (mat)-[:HAS_PROPERTY]->(prop:MaterialProperty)
        OPTIONAL MATCH (part:Part)-[:USES_MATERIAL]->(mat)
        OPTIONAL MATCH (mat)-[:MATERIAL_CLASSIFIED_AS]->(owl:ExternalOwlClass)
        RETURN mat.name AS material_name,
               mat.material_type AS material_type,
               mat.specification AS material_specification,
               COLLECT(DISTINCT {{
                   prop_name: prop.name,
                   prop_value: prop.value,
                   prop_unit: prop.unit
               }}) AS properties,
               COLLECT(DISTINCT part.name) AS used_in_parts,
               COLLECT(DISTINCT owl.name) AS ontology_classes
        ORDER BY mat.name
        """
        
        results = neo4j.execute_query(query, params)
        
        materials = [{
            'name': r.get('material_name'),
            'type': r.get('material_type'),
            'specification': r.get('material_specification'),
            'properties': [{'name': p.get('prop_name'), 'value': p.get('prop_value'), 'unit': p.get('prop_unit')} 
                          for p in r.get('properties', []) if p and p.get('prop_name')],
            'used_in_parts': [p for p in r.get('used_in_parts', []) if p],
            'ontology_classes': [o for o in r.get('ontology_classes', []) if o]
        } for r in results if r.get('material_name')]
        
        return jsonify({
            'count': len(materials),
            'materials': materials
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching materials: {e}")
        return jsonify({'error': str(e)}), 500


@ap242_bp.route('/materials/<material_name>', methods=['GET'])
def get_material_detail(material_name: str):
    """
    Get detailed information about a specific material.
    
    Returns:
        Material with all properties and relationships
    """
    try:
        neo4j = get_neo4j_service()
        
        
        query = """
        MATCH (mat:Material {name: $material_name})
        OPTIONAL MATCH (mat)-[:HAS_PROPERTY]->(prop:MaterialProperty)
        OPTIONAL MATCH (prop)-[:USES_UNIT]->(unit:ExternalUnit)
        OPTIONAL MATCH (part:Part)-[:USES_MATERIAL]->(mat)
        OPTIONAL MATCH (mat)-[:MATERIAL_CLASSIFIED_AS]->(owl:ExternalOwlClass)
        OPTIONAL MATCH (req:Requirement)-[:REQUIRES_MATERIAL]->(mat)
        RETURN mat,
               COLLECT(DISTINCT {
                   name: prop.name,
                   value: prop.value,
                   unit: prop.unit,
                   temperature: prop.temperature,
                   unit_name: unit.name
               }) AS properties,
               COLLECT(DISTINCT part.name) AS parts,
               COLLECT(DISTINCT {name: owl.name, ontology: owl.ontology}) AS ontologies,
               COLLECT(DISTINCT req.name) AS requirements
        """
        
        results = neo4j.execute_query(query, {'material_name': material_name})
        
        if not results:
            return jsonify({'error': 'Material not found'}), 404
            
        r = results[0]
        mat = r['mat']
        
        material_detail = {
            'name': mat['name'],
            'material_type': mat.get('material_type'),
            'specification': mat.get('specification'),
            'ap_level': mat.get('ap_level'),
            'ap_schema': mat.get('ap_schema'),
            'properties': [p for p in r['properties'] if p.get('name')],
            'used_in_parts': [p for p in r['parts'] if p],
            'ontology_classes': [o for o in r['ontologies'] if o.get('name')],
            'requirements': [req for req in r['requirements'] if req]
        }
        
        return jsonify(material_detail), 200
        
    except Exception as e:
        logger.error(f"Error fetching material {material_name}: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# GEOMETRY ENDPOINTS
# ============================================================================

@ap242_bp.route('/geometry', methods=['GET'])
def get_geometry_models():
    """
    Get all CAD geometry models.
    
    Query Parameters:
        type: Filter by model type (Solid, Surface, Wireframe)
        
    Returns:
        JSON array of geometric model objects
    """
    try:
        neo4j = get_neo4j_service()
        
        
        model_type = request.args.get('type')
        where_clause = "geo.model_type = $type" if model_type else "1=1"
        params = {'type': model_type} if model_type else {}
        
        query = f"""
        MATCH (geo:GeometricModel)
        WHERE geo.ap_level = 2 AND {where_clause}
        OPTIONAL MATCH (geo)-[:HAS_REPRESENTATION]->(shape:ShapeRepresentation)
        OPTIONAL MATCH (part:Part)-[:HAS_GEOMETRY]->(geo)
        OPTIONAL MATCH (ana:Analysis)-[:ANALYZES_GEOMETRY]->(geo)
        RETURN geo.name AS name,
               geo.model_type AS type,
               geo.units AS units,
               COLLECT(DISTINCT shape.representation_type) AS representations,
               COLLECT(DISTINCT part.name) AS parts,
               COLLECT(DISTINCT ana.name) AS analyses
        ORDER BY geo.name
        """
        
        results = neo4j.execute_query(query, params)
        
        geometry = [{
            'name': r['name'],
            'type': r['type'],
            'units': r['units'],
            'representations': [rep for rep in r['representations'] if rep],
            'parts': [p for p in r['parts'] if p],
            'analyses': [a for a in r['analyses'] if a]
        } for r in results]
        
        return jsonify({
            'count': len(geometry),
            'geometry': geometry
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching geometry models: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# STATISTICS ENDPOINT
# ============================================================================

@ap242_bp.route('/statistics', methods=['GET'])
def get_ap242_statistics():
    """
    Get summary statistics for AP242 data.
    
    Returns:
        Counts and type breakdown for all AP242 entities
    """
    try:
        neo4j = get_neo4j_service()
        
        
        query = """
        MATCH (n)
        WHERE n.ap_level = 2 AND n.ap_schema = 'AP242'
        WITH labels(n)[0] AS node_type, 
             COALESCE(n.status, n.material_type, n.assembly_type, n.model_type) AS type_or_status
        RETURN node_type, type_or_status, count(*) AS count
        ORDER BY node_type, type_or_status
        """
        
        results = neo4j.execute_query(query)
        
        # Group by node type
        stats = {}
        for r in results:
            node_type = r['node_type']
            if node_type not in stats:
                stats[node_type] = {'total': 0, 'breakdown': {}}
            stats[node_type]['total'] += r['count']
            if r['type_or_status']:
                stats[node_type]['breakdown'][r['type_or_status']] = r['count']
                
        return jsonify({
            'ap_level': 2,
            'ap_schema': 'AP242',
            'statistics': stats
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching AP242 statistics: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@ap242_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404


@ap242_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500
