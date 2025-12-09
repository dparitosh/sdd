"""
PLM Integration Blueprint
Endpoints for Product Lifecycle Management operations:
- Requirements traceability
- Composition/BOM hierarchy
- Change impact analysis
- Parameter extraction
- Constraint validation
"""

from flask import Blueprint, jsonify, request
from loguru import logger

from src.web.middleware import DatabaseError, NotFoundError, ValidationError
from src.web.services import get_neo4j_service

plm_bp = Blueprint("plm", __name__, url_prefix="/api/v1")


@plm_bp.route("/traceability", methods=["GET"])
def get_traceability():
    """
    Get traceability matrix showing relationships between elements
    Query params: source_type, target_type, relationship_type, depth
    """
    service = get_neo4j_service()

    try:
        source_type = request.args.get("source_type")
        target_type = request.args.get("target_type")
        relationship_type = request.args.get("relationship_type")
        depth = request.args.get("depth", default=2, type=int)

        if depth < 1 or depth > 10:
            raise ValidationError("Depth must be between 1 and 10")

        # Build dynamic query
        query_parts = []
        params = {}

        # Source node filter
        if source_type:
            query_parts.append(f"MATCH (source:{source_type})")
            params["source_type"] = source_type
        else:
            query_parts.append("MATCH (source)")

        # Relationship filter with depth
        if relationship_type:
            query_parts.append(f"-[r:{relationship_type}*1..{depth}]->")
        else:
            query_parts.append(f"-[r*1..{depth}]->")

        # Target node filter
        if target_type:
            query_parts.append(f"(target:{target_type})")
        else:
            query_parts.append("(target)")

        query = (
            " ".join(query_parts)
            + """
        RETURN source.id as source_id,
               source.name as source_name,
               labels(source)[0] as source_type,
               [rel in r | type(rel)] as relationship_chain,
               target.id as target_id,
               target.name as target_name,
               labels(target)[0] as target_type,
               length(r) as path_length
        ORDER BY path_length, source_name, target_name
        LIMIT 1000
        """
        )

        result = service.execute_query(query, params)

        traces = [
            {
                "source": {
                    "id": r["source_id"],
                    "name": r["source_name"],
                    "type": r["source_type"],
                },
                "relationship_chain": r["relationship_chain"],
                "target": {
                    "id": r["target_id"],
                    "name": r["target_name"],
                    "type": r["target_type"],
                },
                "path_length": r["path_length"],
            }
            for r in result
        ]

        return jsonify(
            {
                "total": len(traces),
                "filters": {
                    "source_type": source_type,
                    "target_type": target_type,
                    "relationship_type": relationship_type,
                    "depth": depth,
                },
                "traceability": traces,
            }
        )
    except ValidationError as e:
        raise
    except Exception as e:
        logger.error(f"Traceability query error: {str(e)}")
        raise DatabaseError(f"Failed to retrieve traceability data: {str(e)}")


@plm_bp.route("/composition/<node_id>", methods=["GET"])
def get_composition(node_id):
    """
    Get Bill of Materials (BOM) composition hierarchy for a node
    Shows complete containment tree with all children at all levels
    """
    service = get_neo4j_service()

    try:
        depth = request.args.get("depth", default=10, type=int)

        if depth < 1 or depth > 20:
            raise ValidationError("Depth must be between 1 and 20")

        query = f"""
        MATCH path = (root {{id: $node_id}})-[:CONTAINS*1..{depth}]->(child)
        RETURN root.id as root_id,
               root.name as root_name,
               labels(root)[0] as root_type,
               [node in nodes(path) | {{
                   id: node.id,
                   name: node.name,
                   type: labels(node)[0],
                   visibility: node.visibility,
                   aggregation: node.aggregation
               }}] as path_nodes,
               length(path) as depth
        ORDER BY depth, child.name
        LIMIT 1000
        """

        result = service.execute_query(query, {"node_id": node_id})

        if not result:
            raise NotFoundError(f"Node with ID '{node_id}' not found or has no composition")

        # Build hierarchical tree structure
        composition = {
            "root": {
                "id": result[0]["root_id"],
                "name": result[0]["root_name"],
                "type": result[0]["root_type"],
            },
            "children": [{"path": r["path_nodes"], "depth": r["depth"]} for r in result],
            "total_children": len(result),
        }

        return jsonify(composition)
    except (ValidationError, NotFoundError) as e:
        raise
    except Exception as e:
        logger.error(f"Composition query error for {node_id}: {str(e)}")
        raise DatabaseError(f"Failed to retrieve composition data: {str(e)}")


@plm_bp.route("/impact/<node_id>", methods=["GET"])
def get_impact_analysis(node_id):
    """
    Analyze change impact - find all nodes that would be affected by changes to this node
    Shows upstream (depends on this) and downstream (this depends on) dependencies
    """
    service = get_neo4j_service()

    try:
        depth = request.args.get("depth", default=3, type=int)

        if depth < 1 or depth > 10:
            raise ValidationError("Depth must be between 1 and 10")

        # Get node info first
        node_query = """
        MATCH (n {id: $node_id})
        RETURN n.id as id, n.name as name, labels(n)[0] as type
        """
        node_info = service.execute_query(node_query, {"node_id": node_id})

        if not node_info:
            raise NotFoundError(f"Node with ID '{node_id}' not found")

        # Find upstream impact (who references/depends on this node)
        upstream_query = f"""
        MATCH path = (dependent)-[r*1..{depth}]->(node {{id: $node_id}})
        WHERE type(r[0]) IN ['TYPED_BY', 'GENERALIZES', 'DEPENDS_ON', 'USES', 'ASSOCIATES_WITH']
        RETURN DISTINCT
               dependent.id as dependent_id,
               dependent.name as dependent_name,
               labels(dependent)[0] as dependent_type,
               [rel in relationships(path) | type(rel)] as relationship_chain,
               length(path) as distance
        ORDER BY distance, dependent_name
        LIMIT 500
        """

        upstream_result = service.execute_query(upstream_query, {"node_id": node_id})

        # Find downstream impact (what this node references/depends on)
        downstream_query = f"""
        MATCH path = (node {{id: $node_id}})-[r*1..{depth}]->(dependency)
        WHERE type(r[0]) IN ['TYPED_BY', 'GENERALIZES', 'DEPENDS_ON', 'USES', 'ASSOCIATES_WITH']
        RETURN DISTINCT
               dependency.id as dependency_id,
               dependency.name as dependency_name,
               labels(dependency)[0] as dependency_type,
               [rel in relationships(path) | type(rel)] as relationship_chain,
               length(path) as distance
        ORDER BY distance, dependency_name
        LIMIT 500
        """

        downstream_result = service.execute_query(downstream_query, {"node_id": node_id})

        return jsonify(
            {
                "node": {
                    "id": node_info[0]["id"],
                    "name": node_info[0]["name"],
                    "type": node_info[0]["type"],
                },
                "upstream_impact": {
                    "count": len(upstream_result),
                    "affected_nodes": [
                        {
                            "id": r["dependent_id"],
                            "name": r["dependent_name"],
                            "type": r["dependent_type"],
                            "relationship_chain": r["relationship_chain"],
                            "distance": r["distance"],
                        }
                        for r in upstream_result
                    ],
                },
                "downstream_impact": {
                    "count": len(downstream_result),
                    "dependencies": [
                        {
                            "id": r["dependency_id"],
                            "name": r["dependency_name"],
                            "type": r["dependency_type"],
                            "relationship_chain": r["relationship_chain"],
                            "distance": r["distance"],
                        }
                        for r in downstream_result
                    ],
                },
                "total_impact": len(upstream_result) + len(downstream_result),
            }
        )
    except (ValidationError, NotFoundError) as e:
        raise
    except Exception as e:
        logger.error(f"Impact analysis error for {node_id}: {str(e)}")
        raise DatabaseError(f"Failed to analyze impact: {str(e)}")


@plm_bp.route("/parameters", methods=["GET"])
def get_parameters():
    """
    Get system parameters from Properties with their types, multiplicity, and constraints
    Useful for design/simulation integration
    """
    service = get_neo4j_service()

    try:
        class_name = request.args.get("class")
        limit = request.args.get("limit", default=1000, type=int)

        if limit < 1 or limit > 5000:
            raise ValidationError("Limit must be between 1 and 5000")

        query_parts = ["MATCH (p:Property)"]
        params = {"limit": limit}

        if class_name:
            query_parts.append("MATCH (c:Class {name: $class_name})-[:HAS_ATTRIBUTE]->(p)")
            params["class_name"] = class_name

        query_parts.append(
            f"""
        OPTIONAL MATCH (p)-[:TYPED_BY]->(type)
        OPTIONAL MATCH (p)<-[:HAS_ATTRIBUTE]-(owner)
        RETURN p.id as id,
               p.name as name,
               p.visibility as visibility,
               p.lower as lower,
               p.upper as upper,
               p.aggregation as aggregation,
               p.defaultValue as default_value,
               p.isDerived as is_derived,
               p.isReadOnly as is_read_only,
               type.name as type_name,
               owner.name as owner_name,
               labels(owner)[0] as owner_type
        ORDER BY owner_name, p.name
        LIMIT $limit
        """
        )

        query = " ".join(query_parts)
        result = service.execute_query(query, params)

        parameters = [
            {
                "id": r["id"],
                "name": r["name"],
                "owner": (
                    {"name": r["owner_name"], "type": r["owner_type"]}
                    if r.get("owner_name")
                    else None
                ),
                "type": r["type_name"],
                "multiplicity": {"lower": r["lower"], "upper": r["upper"]},
                "visibility": r["visibility"],
                "aggregation": r["aggregation"],
                "default_value": r["default_value"],
                "is_derived": r["is_derived"],
                "is_read_only": r["is_read_only"],
            }
            for r in result
        ]

        return jsonify(
            {
                "total": len(parameters),
                "filters": {"class": class_name, "limit": limit},
                "parameters": parameters,
            }
        )
    except ValidationError as e:
        raise
    except Exception as e:
        logger.error(f"Parameters query error: {str(e)}")
        raise DatabaseError(f"Failed to retrieve parameters: {str(e)}")


@plm_bp.route("/constraints", methods=["GET"])
def get_constraints():
    """
    Get validation constraints for design/simulation validation
    Returns OCL or other constraint specifications
    """
    service = get_neo4j_service()

    try:
        element_id = request.args.get("element_id")
        limit = request.args.get("limit", default=1000, type=int)

        if limit < 1 or limit > 5000:
            raise ValidationError("Limit must be between 1 and 5000")

        query_parts = ["MATCH (c:Constraint)"]
        params = {"limit": limit}

        if element_id:
            query_parts.append("MATCH (e {id: $element_id})-[:HAS_RULE]->(c)")
            params["element_id"] = element_id

        query_parts.append(
            f"""
        OPTIONAL MATCH (owner)-[:HAS_RULE]->(c)
        RETURN c.id as id,
               c.name as name,
               c.body as body,
               c.language as language,
               owner.id as owner_id,
               owner.name as owner_name,
               labels(owner)[0] as owner_type
        ORDER BY owner_name, c.name
        LIMIT $limit
        """
        )

        query = " ".join(query_parts)
        result = service.execute_query(query, params)

        constraints = [
            {
                "id": r["id"],
                "name": r["name"],
                "body": r["body"],
                "language": r["language"],
                "owner": (
                    {"id": r["owner_id"], "name": r["owner_name"], "type": r["owner_type"]}
                    if r.get("owner_id")
                    else None
                ),
            }
            for r in result
        ]

        return jsonify(
            {
                "total": len(constraints),
                "filters": {"element_id": element_id, "limit": limit},
                "constraints": constraints,
            }
        )
    except ValidationError as e:
        raise
    except Exception as e:
        logger.error(f"Constraints query error: {str(e)}")
        raise DatabaseError(f"Failed to retrieve constraints: {str(e)}")
