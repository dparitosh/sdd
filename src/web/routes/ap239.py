"""
AP239 REST API Routes - Product Life Cycle Support
==================================================
Endpoints for Requirements, Analysis, Approvals, and Documents

ISO 10303 AP239 provides PLCS (Product Life Cycle Support) capabilities
including requirements management, design approvals, and engineering analysis.
"""

from flask import Blueprint, jsonify, request
from loguru import logger

from src.web.services import get_neo4j_service

ap239_bp = Blueprint('ap239', __name__, url_prefix='/api/ap239')


# ============================================================================
# REQUIREMENTS ENDPOINTS
# ============================================================================

@ap239_bp.route('/requirements', methods=['GET'])
def get_requirements():
    """
    Get all requirements with optional filtering.
    
    Query Parameters:
        type: Filter by requirement type (Performance, Functional, etc.)
        priority: Filter by priority (High, Medium, Low)
        status: Filter by status (Draft, Approved, Obsolete)
        search: Text search in name and description
        
    Returns:
        JSON array of requirement objects
    """
    try:
        neo4j = get_neo4j_service()
        
        # Build dynamic query based on filters
        filters = []
        params = {}
        
        if req_type := request.args.get('type'):
            filters.append("req.type = $type")
            params['type'] = req_type
            
        if priority := request.args.get('priority'):
            filters.append("req.priority = $priority")
            params['priority'] = priority
            
        if status := request.args.get('status'):
            filters.append("req.status = $status")
            params['status'] = status
            
        if search := request.args.get('search'):
            filters.append("(req.name =~ $search OR req.description =~ $search)")
            params['search'] = f"(?i).*{search}.*"
            
        where_clause = " AND ".join(filters) if filters else "1=1"
        
        query = f"""
        MATCH (req:Requirement)
        WHERE req.ap_level = 1 AND {where_clause}
        OPTIONAL MATCH (req)-[:HAS_VERSION]->(v:RequirementVersion)
        OPTIONAL MATCH (req)-[:SATISFIED_BY_PART]->(part:Part)
        RETURN req.id AS id,
               req.name AS name,
               req.description AS description,
               req.type AS type,
               req.priority AS priority,
               req.status AS status,
               req.created_at AS created_at,
               COLLECT(DISTINCT v.version) AS versions,
               COLLECT(DISTINCT part.name) AS satisfied_by_parts
        ORDER BY req.priority DESC, req.created_at DESC
        """
        
        results = neo4j.execute_query(query, params)
        
        requirements = [{
            'id': r['id'],
            'name': r['name'],
            'description': r['description'],
            'type': r['type'],
            'priority': r['priority'],
            'status': r['status'],
            'created_at': str(r['created_at']) if r['created_at'] else None,
            'versions': [v for v in r['versions'] if v],
            'satisfied_by_parts': [p for p in r['satisfied_by_parts'] if p]
        } for r in results]
        
        return jsonify({
            'count': len(requirements),
            'requirements': requirements
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching requirements: {e}")
        return jsonify({'error': str(e)}), 500


@ap239_bp.route('/requirements/<req_id>', methods=['GET'])
def get_requirement_detail(req_id: str):
    """
    Get detailed information about a specific requirement.
    
    Returns:
        Requirement with all relationships (versions, analyses, approvals, etc.)
    """
    try:
        neo4j = get_neo4j_service()
        
        
        query = """
        MATCH (req:Requirement {id: $req_id})
        OPTIONAL MATCH (req)-[:HAS_VERSION]->(v:RequirementVersion)
        OPTIONAL MATCH (req)-[:VERIFIES]->(ana:Analysis)
        OPTIONAL MATCH (req)-[:APPROVES]->(appr:Approval)
        OPTIONAL MATCH (doc:Document)-[:DOCUMENTS]->(req)
        OPTIONAL MATCH (req)-[:SATISFIED_BY_PART]->(part:Part)
        OPTIONAL MATCH (req)-[:REQUIREMENT_VALUE_TYPE]->(unit:ExternalUnit)
        RETURN req,
               COLLECT(DISTINCT {version: v.version, name: v.name, status: v.status}) AS versions,
               COLLECT(DISTINCT {name: ana.name, type: ana.type, status: ana.status}) AS analyses,
               COLLECT(DISTINCT {name: appr.name, status: appr.status, date: toString(appr.approval_date)}) AS approvals,
               COLLECT(DISTINCT {name: doc.name, id: doc.document_id, version: doc.version}) AS documents,
               COLLECT(DISTINCT {id: part.id, name: part.name}) AS parts,
               COLLECT(DISTINCT {name: unit.name, symbol: unit.symbol}) AS units
        """
        
        results = neo4j.execute_query(query, {'req_id': req_id})
        
        if not results:
            return jsonify({'error': 'Requirement not found'}), 404
            
        r = results[0]
        req = r['req']
        
        requirement = {
            'id': req['id'],
            'name': req['name'],
            'description': req.get('description'),
            'type': req.get('type'),
            'priority': req.get('priority'),
            'status': req.get('status'),
            'created_at': str(req.get('created_at')) if req.get('created_at') else None,
            'ap_level': req.get('ap_level'),
            'ap_schema': req.get('ap_schema'),
            'versions': [{
                'version': v.get('version'),
                'description': v.get('description'),
                'status': v.get('status'),
                'created_at': str(v.get('created_at')) if v.get('created_at') else None
            } for v in r['versions'] if v.get('version')],
            'analyses': [a for a in r['analyses'] if a.get('name')],
            'approvals': [a for a in r['approvals'] if a.get('name')],
            'documents': [d for d in r['documents'] if d.get('name')],
            'satisfied_by_parts': [p for p in r['parts'] if p.get('id')],
            'units': [u for u in r['units'] if u.get('name')]
        }
        
        return jsonify(requirement), 200
        
    except Exception as e:
        logger.error(f"Error fetching requirement {req_id}: {e}")
        return jsonify({'error': str(e)}), 500


@ap239_bp.route('/requirements/<req_id>/traceability', methods=['GET'])
def get_requirement_traceability(req_id: str):
    """
    Get full traceability chain for a requirement (AP239 → AP242 → AP243).
    
    Returns:
        Tree structure showing how requirement flows through parts to ontologies
    """
    try:
        neo4j = get_neo4j_service()
        
        
        query = """
        MATCH (req:Requirement {id: $req_id})
        OPTIONAL MATCH path1 = (req)-[:SATISFIED_BY_PART]->(part:Part)
        OPTIONAL MATCH path2 = (part)-[:USES_MATERIAL]->(mat:Material)
        OPTIONAL MATCH path3 = (mat)-[:MATERIAL_CLASSIFIED_AS]->(owl:ExternalOwlClass)
        RETURN req.name AS requirement,
               COLLECT(DISTINCT {
                   part_id: part.id,
                   part_name: part.name,
                   materials: COLLECT(DISTINCT mat.name),
                   ontologies: COLLECT(DISTINCT owl.name)
               }) AS traceability_chain
        """
        
        results = neo4j.execute_query(query, {'req_id': req_id})
        
        if not results:
            return jsonify({'error': 'Requirement not found'}), 404
            
        return jsonify({
            'requirement': results[0]['requirement'],
            'traceability': results[0]['traceability_chain']
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching traceability for {req_id}: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# ANALYSIS ENDPOINTS
# ============================================================================

@ap239_bp.route('/analyses', methods=['GET'])
def get_analyses():
    """
    Get all engineering analyses.
    
    Query Parameters:
        type: Filter by analysis type (ThermalSimulation, StressAnalysis, etc.)
        status: Filter by status (Planned, Running, Completed)
        
    Returns:
        JSON array of analysis objects
    """
    try:
        neo4j = get_neo4j_service()
        
        filters = []
        params = {}
        
        if ana_type := request.args.get('type'):
            filters.append("ana.type = $type")
            params['type'] = ana_type
            
        if status := request.args.get('status'):
            filters.append("ana.status = $status")
            params['status'] = status
            
        where_clause = " AND ".join(filters) if filters else "1=1"
        
        query = f"""
        MATCH (ana:Analysis)
        WHERE ana.ap_level = 1 AND {where_clause}
        OPTIONAL MATCH (ana)-[:USES_MODEL]->(model:AnalysisModel)
        OPTIONAL MATCH (req:Requirement)-[:VERIFIES]->(ana)
        OPTIONAL MATCH (ana)-[:ANALYZED_BY_MODEL]->(geo:GeometricModel)
        RETURN ana.name AS name,
               ana.type AS type,
               ana.method AS method,
               ana.status AS status,
               COLLECT(DISTINCT model.name) AS models,
               COLLECT(DISTINCT req.name) AS verifies_requirements,
               COLLECT(DISTINCT geo.name) AS geometry_models
        ORDER BY ana.status, ana.name
        """
        
        results = neo4j.execute_query(query, params)
        
        analyses = [{
            'name': r['name'],
            'type': r['type'],
            'method': r['method'],
            'status': r['status'],
            'models': [m for m in r['models'] if m],
            'verifies_requirements': [req for req in r['verifies_requirements'] if req],
            'geometry_models': [g for g in r['geometry_models'] if g]
        } for r in results]
        
        return jsonify({
            'count': len(analyses),
            'analyses': analyses
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching analyses: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# APPROVAL ENDPOINTS
# ============================================================================

@ap239_bp.route('/approvals', methods=['GET'])
def get_approvals():
    """
    Get all design approvals.
    
    Query Parameters:
        status: Filter by approval status (Pending, Approved, Rejected)
        
    Returns:
        JSON array of approval objects
    """
    try:
        neo4j = get_neo4j_service()
        
        status_filter = request.args.get('status')
        where_clause = "appr.status = $status" if status_filter else "1=1"
        params = {'status': status_filter} if status_filter else {}
        
        query = f"""
        MATCH (appr:Approval)
        WHERE appr.ap_level = 1 AND {where_clause}
        OPTIONAL MATCH (req:Requirement)-[:APPROVES]->(appr)
        OPTIONAL MATCH (appr)-[:APPROVED_FOR_VERSION]->(pv:PartVersion)
        RETURN appr.name AS name,
               appr.status AS status,
               appr.approved_by AS approved_by,
               appr.approval_date AS approval_date,
               COLLECT(DISTINCT req.name) AS approves_requirements,
               COLLECT(DISTINCT pv.name) AS approved_part_versions
        ORDER BY appr.approval_date DESC
        """
        
        results = neo4j.execute_query(query, params)
        
        approvals = [{
            'name': r['name'],
            'status': r['status'],
            'approved_by': r['approved_by'],
            'approval_date': str(r['approval_date']) if r['approval_date'] else None,
            'approves_requirements': [req for req in r['approves_requirements'] if req],
            'approved_part_versions': [pv for pv in r['approved_part_versions'] if pv]
        } for r in results]
        
        return jsonify({
            'count': len(approvals),
            'approvals': approvals
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching approvals: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# DOCUMENT ENDPOINTS
# ============================================================================

@ap239_bp.route('/documents', methods=['GET'])
def get_documents():
    """
    Get all engineering documents.
    
    Query Parameters:
        type: Filter by document type (Specification, Report, Drawing)
        
    Returns:
        JSON array of document objects
    """
    try:
        neo4j = get_neo4j_service()
        
        doc_type = request.args.get('type')
        where_clause = "doc.type = $type" if doc_type else "1=1"
        params = {'type': doc_type} if doc_type else {}
        
        query = f"""
        MATCH (doc:Document)
        WHERE doc.ap_level = 1 AND {where_clause}
        OPTIONAL MATCH (doc)-[:DOCUMENTS]->(req:Requirement)
        RETURN doc.name AS name,
               doc.document_id AS document_id,
               doc.version AS version,
               doc.type AS type,
               COLLECT(DISTINCT req.name) AS documents_requirements
        ORDER BY doc.name
        """
        
        results = neo4j.execute_query(query, params)
        
        documents = [{
            'name': r['name'],
            'document_id': r['document_id'],
            'version': r['version'],
            'type': r['type'],
            'documents_requirements': [req for req in r['documents_requirements'] if req]
        } for r in results]
        
        return jsonify({
            'count': len(documents),
            'documents': documents
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching documents: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# STATISTICS ENDPOINT
# ============================================================================

@ap239_bp.route('/statistics', methods=['GET'])
def get_ap239_statistics():
    """
    Get summary statistics for AP239 data.
    
    Returns:
        Counts and status breakdown for all AP239 entities
    """
    try:
        neo4j = get_neo4j_service()
        
        
        query = """
        MATCH (n)
        WHERE n.ap_level = 1 AND n.ap_schema = 'AP239'
        WITH labels(n)[0] AS node_type, n.status AS status
        RETURN node_type, status, count(*) AS count
        ORDER BY node_type, status
        """
        
        results = neo4j.execute_query(query)
        
        # Group by node type
        stats = {}
        for r in results:
            node_type = r['node_type']
            if node_type not in stats:
                stats[node_type] = {'total': 0, 'by_status': {}}
            stats[node_type]['total'] += r['count']
            if r['status']:
                stats[node_type]['by_status'][r['status']] = r['count']
                
        return jsonify({
            'ap_level': 1,
            'ap_schema': 'AP239',
            'statistics': stats
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching AP239 statistics: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@ap239_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404


@ap239_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500
