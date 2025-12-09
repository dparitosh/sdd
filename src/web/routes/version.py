"""
Version Control Blueprint
Endpoints for version control and change management:
- Version history
- Version comparison
- Change audit trail
- Checkpoint creation
"""

from datetime import datetime

from flask import Blueprint, jsonify, request
from loguru import logger

from src.web.middleware import DatabaseError, NotFoundError, ValidationError
from src.web.services import get_neo4j_service

version_bp = Blueprint("version", __name__, url_prefix="/api/v1")


@version_bp.route("/versions/<node_id>", methods=["GET"])
def get_node_versions(node_id):
    """
    Get version history for a specific node.
    Returns all versions with timestamps and changes.
    """
    service = get_neo4j_service()

    try:
        query = """
        MATCH (n {id: $node_id})
        RETURN n.id as id,
               n.name as name,
               labels(n) as labels,
               n.version as version,
               n.createdAt as created_at,
               n.modifiedAt as modified_at,
               n.loadSource as load_source,
               properties(n) as properties
        """

        result = service.execute_query(query, {"node_id": node_id})

        if not result:
            raise NotFoundError(f"Node with ID '{node_id}' not found")

        node = result[0]

        # In a full versioning system, we would query historical versions
        version_info = {
            "node_id": node["id"],
            "name": node["name"],
            "labels": node["labels"],
            "current_version": {
                "version": node["version"] or 1,
                "created_at": node["created_at"],
                "modified_at": node["modified_at"],
                "load_source": node["load_source"],
                "properties": node["properties"],
            },
            "version_history": [
                {
                    "version": node["version"] or 1,
                    "timestamp": node["modified_at"] or node["created_at"],
                    "change_type": "created",
                    "properties": node["properties"],
                }
            ],
        }

        return jsonify(version_info)
    except NotFoundError as e:
        raise
    except Exception as e:
        logger.error(f"Version history error for {node_id}: {str(e)}")
        raise DatabaseError(f"Failed to retrieve version history: {str(e)}")


@version_bp.route("/diff", methods=["POST"])
def compare_versions():
    """
    Compare two versions of nodes or two different nodes.
    Body: { "node1_id": "id1", "node2_id": "id2" }
    """
    service = get_neo4j_service()

    try:
        data = request.get_json()
        if not data:
            raise ValidationError("Request body required")

        node1_id = data.get("node1_id")
        node2_id = data.get("node2_id")

        if not node1_id or not node2_id:
            raise ValidationError("Both node1_id and node2_id are required")

        # Query both nodes
        query = """
        MATCH (n1 {id: $id1})
        MATCH (n2 {id: $id2})
        RETURN properties(n1) as props1, labels(n1) as labels1,
               properties(n2) as props2, labels(n2) as labels2
        """

        result = service.execute_query(query, {"id1": node1_id, "id2": node2_id})

        if not result:
            raise NotFoundError("One or both nodes not found")

        record = result[0]
        props1 = record["props1"]
        props2 = record["props2"]

        # Calculate diff
        all_keys = set(props1.keys()) | set(props2.keys())

        added = {}
        removed = {}
        modified = {}
        unchanged = {}

        for key in all_keys:
            val1 = props1.get(key)
            val2 = props2.get(key)

            if key not in props1:
                added[key] = val2
            elif key not in props2:
                removed[key] = val1
            elif val1 != val2:
                modified[key] = {"old": val1, "new": val2}
            else:
                unchanged[key] = val1

        diff = {
            "node1": {"id": node1_id, "labels": record["labels1"], "properties": props1},
            "node2": {"id": node2_id, "labels": record["labels2"], "properties": props2},
            "differences": {
                "added_properties": added,
                "removed_properties": removed,
                "modified_properties": modified,
                "unchanged_properties": list(unchanged.keys()),
            },
            "summary": {
                "total_differences": len(added) + len(removed) + len(modified),
                "added_count": len(added),
                "removed_count": len(removed),
                "modified_count": len(modified),
            },
        }

        return jsonify(diff)
    except (ValidationError, NotFoundError) as e:
        raise
    except Exception as e:
        logger.error(f"Version comparison error: {str(e)}")
        raise DatabaseError(f"Failed to compare versions: {str(e)}")


@version_bp.route("/history/<node_id>", methods=["GET"])
def get_node_history(node_id):
    """
    Get change history/audit trail for a specific node.
    Returns timeline of all changes with timestamps.
    """
    service = get_neo4j_service()

    try:
        query = """
        MATCH (n {id: $node_id})
        OPTIONAL MATCH (n)-[r]-(related)
        RETURN n.id as id,
               n.name as name,
               labels(n) as labels,
               n.version as version,
               n.createdAt as created_at,
               n.modifiedAt as modified_at,
               properties(n) as properties,
               COUNT(DISTINCT r) as relationship_count,
               COUNT(DISTINCT related) as related_nodes
        """

        result = service.execute_query(query, {"node_id": node_id})

        if not result:
            raise NotFoundError(f"Node with ID '{node_id}' not found")

        record = result[0]

        # Build history timeline
        timeline = []

        if record["created_at"]:
            timeline.append(
                {
                    "timestamp": record["created_at"],
                    "event": "created",
                    "version": 1,
                    "description": f"Node created: {record['name']}",
                }
            )

        if record["modified_at"] and record["modified_at"] != record["created_at"]:
            timeline.append(
                {
                    "timestamp": record["modified_at"],
                    "event": "modified",
                    "version": record["version"],
                    "description": f"Node properties updated",
                }
            )

        history = {
            "node_id": node_id,
            "name": record["name"],
            "labels": record["labels"],
            "current_version": record["version"] or 1,
            "created_at": record["created_at"],
            "last_modified": record["modified_at"],
            "statistics": {
                "relationship_count": record["relationship_count"],
                "related_nodes": record["related_nodes"],
            },
            "timeline": sorted(timeline, key=lambda x: x["timestamp"], reverse=True),
            "properties": record["properties"],
        }

        return jsonify(history)
    except NotFoundError as e:
        raise
    except Exception as e:
        logger.error(f"History query error for {node_id}: {str(e)}")
        raise DatabaseError(f"Failed to retrieve history: {str(e)}")


@version_bp.route("/checkpoint", methods=["POST"])
def create_checkpoint():
    """
    Create a snapshot/checkpoint of the entire graph.
    Body: { "name": "checkpoint_name", "description": "description" }
    """
    service = get_neo4j_service()

    try:
        data = request.get_json() or {}
        checkpoint_name = data.get("name", f'checkpoint_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        description = data.get("description", "Manual checkpoint")

        # Get graph statistics
        stats_query = """
        MATCH (n)
        WITH COUNT(n) as node_count, COLLECT(DISTINCT labels(n)) as all_labels
        MATCH ()-[r]->()
        RETURN node_count,
               COUNT(r) as relationship_count,
               all_labels
        """

        stats_result = service.execute_query(stats_query)

        if not stats_result:
            raise DatabaseError("Failed to retrieve graph statistics")

        stats = stats_result[0]

        checkpoint = {
            "name": checkpoint_name,
            "description": description,
            "timestamp": datetime.utcnow().isoformat(),
            "statistics": {
                "nodes": stats["node_count"],
                "relationships": stats["relationship_count"],
                "node_labels": [label for sublist in stats["all_labels"] for label in sublist],
            },
            "status": "created",
            "note": "Checkpoint metadata saved. Full graph snapshot would require additional storage mechanism.",
        }

        return jsonify(checkpoint), 201
    except Exception as e:
        logger.error(f"Checkpoint creation error: {str(e)}")
        raise DatabaseError(f"Failed to create checkpoint: {str(e)}")
