"""
Hierarchy Navigation REST API Routes
====================================
Endpoints for cross-level traceability and navigation across AP239/AP242/AP243

Provides capabilities to explore the hierarchical relationships and
traceability chains connecting requirements, parts, and ontologies.
"""

from flask import Blueprint, jsonify, request
from loguru import logger

from src.web.services import get_neo4j_service

hierarchy_bp = Blueprint("hierarchy", __name__, url_prefix="/api/hierarchy")


# ============================================================================
# TRACEABILITY MATRIX ENDPOINT
# ============================================================================


@hierarchy_bp.route("/traceability-matrix", methods=["GET"])
def get_traceability_matrix():
    """
    Get complete traceability matrix showing relationships across all AP levels.

    Returns:
        Matrix of requirements → parts → ontologies with relationship chains
    """
    try:
        neo4j = get_neo4j_service()

        query = """
        MATCH (req:Requirement)
        WHERE req.ap_level = 1
        OPTIONAL MATCH (req)-[*1..3]->(part:Part)
        WHERE part.ap_level = 2
        OPTIONAL MATCH (part)-[*1..3]->(owl:ExternalOwlClass)
        WHERE owl.ap_level = 3
        WITH req, part, owl
        RETURN req.id AS requirement_id,
               req.name AS requirement_name,
               req.type AS requirement_type,
               req.status AS requirement_status,
               COLLECT(DISTINCT {
                   part_id: part.id,
                   part_name: part.name,
                   ontology_name: owl.name
               }) AS traceability
        ORDER BY req.name
        """

        results = neo4j.execute_query(query)

        matrix = [
            {
                "requirement": {
                    "id": r["requirement_id"],
                    "name": r["requirement_name"],
                    "type": r["requirement_type"],
                    "status": r["requirement_status"],
                },
                "traceability": [t for t in r["traceability"] if t.get("part_id")],
            }
            for r in results
        ]

        return jsonify({"count": len(matrix), "matrix": matrix}), 200

    except Exception as e:
        logger.error(f"Error fetching traceability matrix: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# HIERARCHY NAVIGATION ENDPOINT
# ============================================================================


@hierarchy_bp.route("/navigate/<node_type>/<node_id>", methods=["GET"])
def navigate_hierarchy(node_type: str, node_id: str):
    """
    Navigate from any node to see upstream and downstream connections.

    Parameters:
        node_type: Type of node (Requirement, Part, Material, etc.)
        node_id: ID or name of the node

    Query Parameters:
        direction: 'upstream' (to higher levels) or 'downstream' (to lower levels) or 'both'
        depth: Maximum depth to traverse (default: 2)

    Returns:
        Navigation tree showing related nodes at other levels
    """
    try:
        neo4j = get_neo4j_service()

        # Validate and sanitize direction parameter
        direction = request.args.get("direction", "both")
        if direction not in ["upstream", "downstream", "both"]:
            direction = "both"

        # Validate and sanitize depth parameter with proper error handling
        try:
            depth = min(int(request.args.get("depth", 2)), 5)
            if depth < 1:
                depth = 2
        except (ValueError, TypeError):
            depth = 2

        # Validate node_type against whitelist
        VALID_NODE_TYPES = {
            "Requirement",
            "Part",
            "Material",
            "Assembly",
            "ExternalOwlClass",
            "Class",
            "Package",
        }
        if node_type not in VALID_NODE_TYPES:
            return jsonify({"error": f"Invalid node type: {node_type}"}), 400

        # Determine label and property to match on
        id_prop = "id" if node_type in ["Requirement", "Part"] else "name"

        # Build query based on direction
        if direction == "upstream":
            path_pattern = f"(downstream)<-[*1..{depth}]-(target)"
            where_clause = "target.ap_level < downstream.ap_level"
        elif direction == "downstream":
            path_pattern = f"(upstream)-[*1..{depth}]->(target)"
            where_clause = "target.ap_level > upstream.ap_level"
        else:  # both
            query_up = f"""
            MATCH (node:{node_type} {{{id_prop}: $node_id}})
            MATCH path = (node)<-[*1..{depth}]-(target)
            WHERE target.ap_level < node.ap_level
            RETURN DISTINCT target, labels(target)[0] AS target_type, 
                   target.ap_level AS level, 'upstream' AS direction
            """

            query_down = f"""
            MATCH (node:{node_type} {{{id_prop}: $node_id}})
            MATCH path = (node)-[*1..{depth}]->(target)
            WHERE target.ap_level > node.ap_level
            RETURN DISTINCT target, labels(target)[0] AS target_type,
                   target.ap_level AS level, 'downstream' AS direction
            """

            results_up = neo4j.execute_query(query_up, {"node_id": node_id})
            results_down = neo4j.execute_query(query_down, {"node_id": node_id})
            results = results_up + results_down

            navigation = {
                "source": {"type": node_type, "id": node_id},
                "upstream": [],
                "downstream": [],
            }

            for r in results:
                target = r["target"]
                target_info = {
                    "type": r["target_type"],
                    "id": target.get("id", target.get("name")),
                    "name": target.get("name"),
                    "level": r["level"],
                }

                if r["direction"] == "upstream":
                    navigation["upstream"].append(target_info)
                else:
                    navigation["downstream"].append(target_info)

            return jsonify(navigation), 200

        # Single direction query (upstream or downstream only)
        if direction != "both":
            query = f"""
            MATCH (node:{node_type} {{{id_prop}: $node_id}})
            MATCH path = {path_pattern}
            WHERE {where_clause}
            RETURN DISTINCT target, labels(target)[0] AS target_type, target.ap_level AS level
            """

            results = neo4j.execute_query(query, {"node_id": node_id})

            navigation = {
                "source": {"type": node_type, "id": node_id},
                direction: [
                    {
                        "type": r["target_type"],
                        "id": r["target"].get("id", r["target"].get("name")),
                        "name": r["target"].get("name"),
                        "level": r["level"],
                    }
                    for r in results
                ],
            }

            return jsonify(navigation), 200

    except Exception as e:
        logger.error(f"Error navigating hierarchy from {node_type}:{node_id}: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# CROSS-LEVEL SEARCH ENDPOINT
# ============================================================================


@hierarchy_bp.route("/search", methods=["GET"])
def cross_level_search():
    """
    Search across all AP levels simultaneously.

    Query Parameters:
        q: Search query (searches name and description fields)
        levels: Comma-separated AP levels to search (1,2,3)

    Returns:
        Search results grouped by AP level
    """
    try:
        neo4j = get_neo4j_service()

        search_query = request.args.get("query") or request.args.get("q")
        if not search_query:
            return jsonify({"error": "Search query required (use ?query= or ?q=)"}), 400

        levels = request.args.get("levels", "1,2,3").split(",")
        levels = [int(l.strip()) for l in levels if l.strip().isdigit()]

        query = """
        MATCH (n)
        WHERE n.ap_level IN $levels
          AND (n.name =~ $search OR n.description =~ $search)
        RETURN n, labels(n)[0] AS node_type, n.ap_level AS level, n.ap_schema AS schema
        ORDER BY n.ap_level, node_type, n.name
        LIMIT 100
        """

        results = neo4j.execute_query(
            query, {"levels": levels, "search": f"(?i).*{search_query}.*"}
        )

        # Group results by level
        by_level = {1: [], 2: [], 3: []}

        for r in results:
            node = r["n"]
            result_info = {
                "type": r["node_type"],
                "id": node.get("id", node.get("name")),
                "name": node.get("name"),
                "description": node.get("description"),
                "schema": r["schema"],
            }
            by_level[r["level"]].append(result_info)

        total_count = sum(len(v) for v in by_level.values())

        return (
            jsonify(
                {
                    "query": search_query,
                    "levels_searched": levels,
                    "results": {"ap239": by_level[1], "ap242": by_level[2], "ap243": by_level[3]},
                    "count": total_count,  # For consistency with other endpoints
                    "total": total_count,  # Keep for backward compatibility
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error in cross-level search: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# LEVEL STATISTICS ENDPOINT
# ============================================================================


@hierarchy_bp.route("/statistics", methods=["GET"])
def get_hierarchy_statistics():
    """
    Get statistics about the entire hierarchy structure.

    Returns:
        Node counts by level, relationship counts, and connectivity metrics
    """
    try:
        neo4j = get_neo4j_service()

        # Node counts by level
        node_query = """
        MATCH (n)
        WHERE n.ap_level IS NOT NULL
        RETURN n.ap_level AS level, n.ap_schema AS schema, 
               labels(n)[0] AS node_type, count(*) AS count
        ORDER BY level, node_type
        """

        # Cross-level relationship counts
        rel_query = """
        MATCH (n1)-[r]->(n2)
        WHERE n1.ap_level IS NOT NULL AND n2.ap_level IS NOT NULL
          AND n1.ap_level <> n2.ap_level
        RETURN n1.ap_level AS from_level, n2.ap_level AS to_level,
               type(r) AS relationship_type, count(*) AS count
        ORDER BY from_level, to_level
        """

        node_results = neo4j.execute_query(node_query)
        rel_results = neo4j.execute_query(rel_query)

        # Organize results
        by_level = {}
        for r in node_results:
            level_key = f"Level {r['level']} ({r['schema']})"
            if level_key not in by_level:
                by_level[level_key] = {}
            by_level[level_key][r["node_type"]] = r["count"]

        cross_level_rels = [
            {
                "from": f"AP{r['from_level']}",
                "to": f"AP{r['to_level']}",
                "relationship": r["relationship_type"],
                "count": r["count"],
            }
            for r in rel_results
        ]

        return (
            jsonify(
                {
                    "nodes_by_level": by_level,
                    "cross_level_relationships": cross_level_rels,
                    "total_cross_level_links": sum(r["count"] for r in cross_level_rels),
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error fetching hierarchy statistics: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# IMPACT ANALYSIS ENDPOINT
# ============================================================================


@hierarchy_bp.route("/impact/<node_type>/<node_id>", methods=["GET"])
def analyze_impact(node_type: str, node_id: str):
    """
    Analyze the impact of changes to a specific node across all levels.

    Returns:
        All nodes that would be affected by changes to the specified node
    """
    try:
        neo4j = get_neo4j_service()

        id_prop = "id" if node_type in ["Requirement", "Part"] else "name"

        query = f"""
        MATCH (source:{node_type} {{{id_prop}: $node_id}})
        MATCH path = (source)-[*1..4]->(affected)
        WHERE affected.ap_level IS NOT NULL
        RETURN DISTINCT affected, labels(affected)[0] AS affected_type,
               affected.ap_level AS level, length(path) AS distance
        ORDER BY distance, level, affected_type
        """

        results = neo4j.execute_query(query, {"node_id": node_id})

        impact = {
            "source": {"type": node_type, "id": node_id},
            "affected_nodes": [
                {
                    "type": r["affected_type"],
                    "id": r["affected"].get("id", r["affected"].get("name")),
                    "name": r["affected"].get("name"),
                    "level": r["level"],
                    "distance": r["distance"],
                }
                for r in results
            ],
        }

        return jsonify(impact), 200

    except Exception as e:
        logger.error(f"Error analyzing impact for {node_type}:{node_id}: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# ERROR HANDLERS
# ============================================================================


@hierarchy_bp.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Resource not found"}), 404


@hierarchy_bp.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500
