"""
AP243 REST API Routes - Reference Data and Ontologies
=====================================================
Endpoints for External Ontologies, Units, Value Types, and Classifications

ISO 10303 AP243 provides reference data integration with external ontologies
like EMMO, standardized units, value types, and classification systems.
"""

from flask import Blueprint, jsonify, request
from loguru import logger

from src.web.services import get_neo4j_service

ap243_bp = Blueprint('ap243', __name__, url_prefix='/api/ap243')


# ============================================================================
# ONTOLOGY ENDPOINTS
# ============================================================================

@ap243_bp.route('/ontologies', methods=['GET'])
def get_ontologies():
    """
    Get all external ontology classes.
    
    Query Parameters:
        ontology: Filter by ontology name (EMMO, QUDT, etc.)
        search: Text search in name and description
        
    Returns:
        JSON array of ontology class objects
    """
    try:
        neo4j = get_neo4j_service()
        
        
        filters = []
        params = {}
        
        if ontology := request.args.get('ontology'):
            filters.append("owl.ontology = $ontology")
            params['ontology'] = ontology
            
        if search := request.args.get('search'):
            filters.append("(owl.name =~ $search OR owl.description =~ $search)")
            params['search'] = f"(?i).*{search}.*"
            
        where_clause = " AND ".join(filters) if filters else "1=1"
        
        query = f"""
        MATCH (owl:ExternalOwlClass)
        WHERE owl.ap_level = 3 AND {where_clause}
        OPTIONAL MATCH (mat:Material)-[:MATERIAL_CLASSIFIED_AS]->(owl)
        RETURN owl.name AS name,
               owl.ontology AS ontology,
               owl.uri AS uri,
               owl.description AS description,
               COLLECT(DISTINCT mat.name) AS classified_materials
        ORDER BY owl.ontology, owl.name
        """
        
        results = neo4j.execute_query(query, params)
        
        ontologies = [{
            'name': r['name'],
            'ontology': r['ontology'],
            'uri': r['uri'],
            'description': r['description'],
            'classified_materials': [m for m in r['classified_materials'] if m]
        } for r in results]
        
        return jsonify({
            'count': len(ontologies),
            'ontologies': ontologies
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching ontologies: {e}")
        return jsonify({'error': str(e)}), 500


@ap243_bp.route('/ontologies/<ontology_name>', methods=['GET'])
def get_ontology_detail(ontology_name: str):
    """
    Get detailed information about a specific ontology class.
    
    Returns:
        Ontology class with all relationships
    """
    try:
        neo4j = get_neo4j_service()
        
        
        query = """
        MATCH (owl:ExternalOwlClass {name: $ontology_name})
        OPTIONAL MATCH (mat:Material)-[:MATERIAL_CLASSIFIED_AS]->(owl)
        OPTIONAL MATCH (mat)<-[:USES_MATERIAL]-(part:Part)
        OPTIONAL MATCH (req:Requirement)-[:SATISFIED_BY_PART]->(part)
        RETURN owl,
               COLLECT(DISTINCT mat.name) AS materials,
               COLLECT(DISTINCT part.name) AS parts,
               COLLECT(DISTINCT req.name) AS requirements
        """
        
        results = neo4j.execute_query(query, {'ontology_name': ontology_name})
        
        if not results:
            return jsonify({'error': 'Ontology class not found'}), 404
            
        r = results[0]
        owl = r['owl']
        
        ontology_detail = {
            'name': owl['name'],
            'ontology': owl.get('ontology'),
            'uri': owl.get('uri'),
            'description': owl.get('description'),
            'ap_level': owl.get('ap_level'),
            'ap_schema': owl.get('ap_schema'),
            'classified_materials': [m for m in r['materials'] if m],
            'related_parts': [p for p in r['parts'] if p],
            'related_requirements': [req for req in r['requirements'] if req]
        }
        
        return jsonify(ontology_detail), 200
        
    except Exception as e:
        logger.error(f"Error fetching ontology {ontology_name}: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# UNITS ENDPOINTS
# ============================================================================

@ap243_bp.route('/units', methods=['GET'])
def get_units():
    """
    Get all standardized units.
    
    Query Parameters:
        type: Filter by unit type (Temperature, ThermalConductivity, etc.)
        
    Returns:
        JSON array of unit objects
    """
    try:
        neo4j = get_neo4j_service()
        
        
        unit_type = request.args.get('type')
        where_clause = "unit.unit_type = $type" if unit_type else "1=1"
        params = {'type': unit_type} if unit_type else {}
        
        query = f"""
        MATCH (unit:ExternalUnit)
        WHERE unit.ap_level = 3 AND {where_clause}
        OPTIONAL MATCH (prop:MaterialProperty)-[:USES_UNIT]->(unit)
        OPTIONAL MATCH (req:Requirement)-[:REQUIREMENT_VALUE_TYPE]->(unit)
        RETURN unit.name AS name,
               unit.symbol AS symbol,
               unit.unit_type AS type,
               unit.si_conversion AS si_conversion,
               COLLECT(DISTINCT prop.name) AS used_in_properties,
               COLLECT(DISTINCT req.name) AS used_in_requirements
        ORDER BY unit.unit_type, unit.name
        """
        
        results = neo4j.execute_query(query, params)
        
        units = [{
            'name': r['name'],
            'symbol': r['symbol'],
            'type': r['type'],
            'si_conversion': r['si_conversion'],
            'used_in_properties': [p for p in r['used_in_properties'] if p],
            'used_in_requirements': [req for req in r['used_in_requirements'] if req]
        } for r in results]
        
        return jsonify({
            'count': len(units),
            'units': units
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching units: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# VALUE TYPES ENDPOINTS
# ============================================================================

@ap243_bp.route('/value-types', methods=['GET'])
def get_value_types():
    """
    Get all value type definitions.
    
    Returns:
        JSON array of value type objects
    """
    try:
        neo4j = get_neo4j_service()
        
        
        query = """
        MATCH (vt:ValueType)
        WHERE vt.ap_level = 3
        OPTIONAL MATCH (prop:MaterialProperty)-[:HAS_VALUE_TYPE]->(vt)
        RETURN vt.name AS name,
               vt.data_type AS data_type,
               vt.unit_reference AS unit_reference,
               COLLECT(DISTINCT prop.name) AS used_in_properties
        ORDER BY vt.name
        """
        
        results = neo4j.execute_query(query)
        
        value_types = [{
            'name': r['name'],
            'data_type': r['data_type'],
            'unit_reference': r['unit_reference'],
            'used_in_properties': [p for p in r['used_in_properties'] if p]
        } for r in results]
        
        return jsonify({
            'count': len(value_types),
            'value_types': value_types
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching value types: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# CLASSIFICATIONS ENDPOINTS
# ============================================================================

@ap243_bp.route('/classifications', methods=['GET'])
def get_classifications():
    """
    Get all classification systems.
    
    Query Parameters:
        system: Filter by classification system (ISO 13584-501, etc.)
        
    Returns:
        JSON array of classification objects
    """
    try:
        neo4j = get_neo4j_service()
        
        
        system = request.args.get('system')
        where_clause = "class.classification_system = $system" if system else "1=1"
        params = {'system': system} if system else {}
        
        query = f"""
        MATCH (class:Classification)
        WHERE class.ap_level = 3 AND {where_clause}
        OPTIONAL MATCH (part:Part)-[:CLASSIFIED_AS]->(class)
        RETURN class.name AS name,
               class.classification_system AS system,
               class.code AS code,
               COLLECT(DISTINCT part.name) AS classified_parts
        ORDER BY class.classification_system, class.code
        """
        
        results = neo4j.execute_query(query, params)
        
        classifications = [{
            'name': r['name'],
            'system': r['system'],
            'code': r['code'],
            'classified_parts': [p for p in r['classified_parts'] if p]
        } for r in results]
        
        return jsonify({
            'count': len(classifications),
            'classifications': classifications
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching classifications: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# STATISTICS ENDPOINT
# ============================================================================

@ap243_bp.route('/statistics', methods=['GET'])
def get_ap243_statistics():
    """
    Get summary statistics for AP243 reference data.
    
    Returns:
        Counts for all AP243 entities
    """
    try:
        neo4j = get_neo4j_service()
        
        
        query = """
        MATCH (n)
        WHERE n.ap_level = 3 AND n.ap_schema = 'AP243'
        WITH labels(n)[0] AS node_type
        RETURN node_type, count(*) AS count
        ORDER BY count DESC
        """
        
        results = neo4j.execute_query(query)
        
        stats = {r['node_type']: r['count'] for r in results}
        
        return jsonify({
            'ap_level': 3,
            'ap_schema': 'AP243',
            'statistics': stats
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching AP243 statistics: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@ap243_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404


@ap243_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500
