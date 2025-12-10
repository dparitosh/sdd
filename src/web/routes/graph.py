"""
Graph Visualization API Routes
Provides endpoints for fetching graph data in format suitable for visualization
"""

from flask import Blueprint, jsonify, request
from loguru import logger

from src.web.services import get_neo4j_service

graph_bp = Blueprint('graph', __name__, url_prefix='/api/graph')

# Whitelist of allowed node types to prevent Cypher injection
ALLOWED_NODE_TYPES = {
    'Requirement', 'Part', 'Class', 'Package', 'Property', 'Association',
    'Port', 'InstanceSpecification', 'Constraint', 'Material', 'Assembly',
    'Document', 'Person', 'ExternalUnit', 'Analysis', 'AnalysisModel',
    'Approval', 'Classification', 'ExternalOwlClass', 'GeometricModel',
    'MaterialProperty', 'PartVersion', 'RequirementVersion', 
    'ShapeRepresentation', 'ValueType', 'Activity', 'Breakdown',
    'Component', 'ComponentPlacement', 'Event', 'ExternalPropertyDefinition',
    'Interface', 'Parameter', 'System', 'Slot', 'Comment'
}


@graph_bp.route('/data', methods=['GET'])
def get_graph_data():
    """
    Get graph data for visualization (nodes and edges).
    
    Query Parameters:
        node_types: Comma-separated list of node types to include (e.g., 'Requirement,Part,Class')
        limit: Maximum number of nodes to return (default: 500, max: 2000)
        depth: Relationship traversal depth (default: 1, max: 3)
        ap_level: Filter by AP level (1=AP239, 2=AP242, 3=AP243)
        
    Returns:
        JSON with nodes and links arrays suitable for force-graph visualization
    """
    try:
        neo4j = get_neo4j_service()
        
        # Parse parameters
        node_types_param = request.args.get('node_types', '')
        requested_types = [nt.strip() for nt in node_types_param.split(',') if nt.strip()]
        
        # Sanitize node types against whitelist to prevent injection
        node_types = [nt for nt in requested_types if nt in ALLOWED_NODE_TYPES]
        
        # Validate and sanitize numeric parameters
        try:
            limit = min(int(request.args.get('limit', 500)), 2000)
            if limit < 1:
                limit = 50
        except (ValueError, TypeError):
            limit = 500
            
        try:
            depth = min(int(request.args.get('depth', 1)), 3)
            if depth < 1:
                depth = 1
        except (ValueError, TypeError):
            depth = 1
        
        ap_level = request.args.get('ap_level')
        
        # Build node filter
        where_clauses = []
        params = {'limit': limit}
        
        if node_types:
            # Filter by specific node types (already validated against whitelist)
            type_conditions = ' OR '.join([f"'{nt}' IN labels(n)" for nt in node_types])
            where_clauses.append(f"({type_conditions})")
        
        if ap_level:
            where_clauses.append("n.ap_level = $ap_level")
            params['ap_level'] = int(ap_level)
        
        where_clause = ' AND '.join(where_clauses) if where_clauses else '1=1'
        
        # Fetch nodes
        node_query = f"""
        MATCH (n)
        WHERE {where_clause}
        RETURN n.id AS id,
               labels(n) AS labels,
               n.name AS name,
               n.description AS description,
               n.status AS status,
               n.priority AS priority,
               n.part_number AS part_number,
               n.ap_level AS ap_level,
               n.ap_schema AS ap_schema
        LIMIT $limit
        """
        
        nodes_result = neo4j.execute_query(node_query, params)
        
        # Create node lookup and format nodes
        node_ids = set()
        nodes = []
        
        for r in nodes_result:
            if not r:
                continue
            node_id = r.get('id')
            if not node_id:
                continue
                
            node_ids.add(node_id)
            
            # Determine node type (primary label)
            labels = r['labels'] or []
            node_type = labels[0] if labels else 'Unknown'
            
            # Format node for visualization
            node = {
                'id': node_id,
                'name': r['name'] or r['part_number'] or node_id,
                'type': node_type,
                'group': node_type,  # For coloring
                'labels': labels,
                'description': r['description'],
                'status': r['status'],
                'priority': r['priority'],
                'ap_level': r['ap_level'],
                'ap_schema': r['ap_schema']
            }
            nodes.append(node)
        
        # Fetch relationships between selected nodes
        if node_ids:
            # Convert set to list for Cypher
            node_id_list = list(node_ids)
            
            rel_query = """
            MATCH (source)-[r]->(target)
            WHERE source.id IN $node_ids AND target.id IN $node_ids
            RETURN source.id AS source,
                   target.id AS target,
                   type(r) AS type,
                   id(r) AS rel_id
            """
            
            rels_result = neo4j.execute_query(rel_query, {'node_ids': node_id_list})
            
            # Format relationships
            links = []
            for r in rels_result:
                link = {
                    'source': r['source'],
                    'target': r['target'],
                    'type': r['type'],
                    'id': str(r['rel_id'])
                }
                links.append(link)
        else:
            links = []
        
        # Return graph data
        return jsonify({
            'nodes': nodes,
            'links': links,
            'metadata': {
                'node_count': len(nodes),
                'link_count': len(links),
                'node_types': list(set(n['type'] for n in nodes)),
                'relationship_types': list(set(l['type'] for l in links)),
                'filters_applied': {
                    'node_types': node_types or 'all',
                    'ap_level': ap_level or 'all',
                    'limit': limit,
                    'depth': depth
                }
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching graph data: {e}")
        return jsonify({'error': str(e)}), 500


@graph_bp.route('/node-types', methods=['GET'])
def get_node_types():
    """
    Get list of all node types (labels) in the graph.
    
    Returns:
        JSON array of node type objects with counts
    """
    try:
        neo4j = get_neo4j_service()
        
        query = """
        CALL db.labels() YIELD label
        CALL {
            WITH label
            MATCH (n)
            WHERE label IN labels(n)
            RETURN count(n) AS count
        }
        RETURN label AS type, count
        ORDER BY count DESC, type
        """
        
        results = neo4j.execute_query(query)
        
        node_types = [
            {
                'type': r['type'],
                'count': r['count']
            }
            for r in results
        ]
        
        return jsonify({
            'node_types': node_types,
            'total_types': len(node_types)
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching node types: {e}")
        return jsonify({'error': str(e)}), 500


@graph_bp.route('/relationship-types', methods=['GET'])
def get_relationship_types():
    """
    Get list of all relationship types in the graph.
    
    Returns:
        JSON array of relationship type objects with counts
    """
    try:
        neo4j = get_neo4j_service()
        
        query = """
        CALL db.relationshipTypes() YIELD relationshipType
        CALL {
            WITH relationshipType
            MATCH ()-[r]->()
            WHERE type(r) = relationshipType
            RETURN count(r) AS count
        }
        RETURN relationshipType AS type, count
        ORDER BY count DESC, type
        """
        
        results = neo4j.execute_query(query)
        
        rel_types = [
            {
                'type': r['type'],
                'count': r['count']
            }
            for r in results
        ]
        
        return jsonify({
            'relationship_types': rel_types,
            'total_types': len(rel_types)
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching relationship types: {e}")
        return jsonify({'error': str(e)}), 500
