"""
ISO SMRL v1 API Routes - /api/v1/ endpoints
Backward compatible with existing /api/ routes
"""

from pathlib import Path
from typing import Any, Dict, List

from flask import Blueprint, jsonify, request

from src.graph.connection import Neo4jConnection
from src.utils.config import Config
from src.web.services.smrl_adapter import SMRLAdapter, neo4j_list_to_smrl, neo4j_to_smrl

# Create blueprint
smrl_bp = Blueprint("smrl_v1", __name__, url_prefix="/api/v1")

config = Config()


def get_connection():
    """Get Neo4j connection"""
    conn = Neo4jConnection(config.neo4j_uri, config.neo4j_user, config.neo4j_password)
    conn.connect()
    return conn


def node_to_dict_with_labels(record):
    """Convert Neo4j record to (dict, labels) tuple."""
    node = record["n"]
    return (dict(node), list(node.labels))


# ============================================================================
# Generic SMRL Resource Endpoints
# ============================================================================


@smrl_bp.route("/<resource_type>", methods=["GET"])
def get_resources(resource_type: str):
    """
    Get all resources of a specific type.
    GET /api/v1/{ResourceType}
    """
    conn = get_connection()

    try:
        # Map SMRL type back to Neo4j label
        reverse_mapping = {v: k for k, v in SMRLAdapter.SMRL_TYPE_MAPPING.items()}
        node_label = reverse_mapping.get(resource_type, resource_type)

        # Query with pagination support
        limit = request.args.get("limit", 100, type=int)
        skip = request.args.get("skip", 0, type=int)

        query = f"""
        MATCH (n:{node_label})
        RETURN n
        ORDER BY n.name
        SKIP $skip
        LIMIT $limit
        """

        result = conn.execute_query(query, {"skip": skip, "limit": limit})

        # Convert to SMRL format
        nodes = [(dict(r["n"]), list(r["n"].labels)) for r in result]
        response = neo4j_list_to_smrl(nodes)

        return jsonify(response), 200

    except Exception as e:
        error = SMRLAdapter.create_smrl_error_response(500, "Internal server error", str(e))
        return jsonify(error), 500
    finally:
        conn.close()


@smrl_bp.route("/<resource_type>/<uid>", methods=["GET"])
def get_resource(resource_type: str, uid: str):
    """
    Get a specific resource by UID.
    GET /api/v1/{ResourceType}/{uid}
    """
    conn = get_connection()

    try:
        # Map SMRL type to Neo4j label
        reverse_mapping = {v: k for k, v in SMRLAdapter.SMRL_TYPE_MAPPING.items()}
        node_label = reverse_mapping.get(resource_type, resource_type)

        query = f"""
        MATCH (n:{node_label})
        WHERE n.uid = $uid OR n.id = $uid OR n.xmi_id = $uid
        RETURN n
        LIMIT 1
        """

        result = conn.execute_query(query, {"uid": uid})

        if not result:
            error = SMRLAdapter.create_smrl_error_response(
                404, f"Resource not found: {resource_type}/{uid}"
            )
            return jsonify(error), 404

        # Convert to SMRL format
        node_data = dict(result[0]["n"])
        node_labels = list(result[0]["n"].labels)
        resource = neo4j_to_smrl(node_data, node_labels)

        return jsonify(resource), 200

    except Exception as e:
        error = SMRLAdapter.create_smrl_error_response(500, "Internal server error", str(e))
        return jsonify(error), 500
    finally:
        conn.close()


@smrl_bp.route("/<resource_type>", methods=["POST"])
def create_resource(resource_type: str):
    """
    Create a new resource.
    POST /api/v1/{ResourceType}
    """
    conn = get_connection()

    try:
        data = request.get_json()

        if not data:
            error = SMRLAdapter.create_smrl_error_response(400, "Request body required")
            return jsonify(error), 400

        # Map SMRL type to Neo4j label
        reverse_mapping = {v: k for k, v in SMRLAdapter.SMRL_TYPE_MAPPING.items()}
        node_label = reverse_mapping.get(resource_type, resource_type)

        # Generate UID if not provided
        from uuid import uuid4

        uid = data.get("uid", f"{resource_type}-{uuid4()}")
        href = f"/api/v1/{resource_type}/{uid}"

        # Build node properties
        properties = {
            "uid": uid,
            "href": href,
            "smrl_type": resource_type,
            "name": data.get("name", ""),
            "created_on": "datetime()",
            "last_modified": "datetime()",
            "created_by": data.get("created_by", "api_user"),
            "modified_by": data.get("modified_by", "api_user"),
        }

        # Add custom properties
        for key, value in data.items():
            if key not in ["uid", "href", "smrl_type"] and not key.startswith("_"):
                properties[key] = value

        # Create node
        query = f"""
        CREATE (n:{node_label} $properties)
        RETURN n
        """

        result = conn.execute_query(query, {"properties": properties})

        # Convert to SMRL format
        node_data = dict(result[0]["n"])
        node_labels = list(result[0]["n"].labels)
        resource = neo4j_to_smrl(node_data, node_labels)

        return jsonify(resource), 201

    except Exception as e:
        error = SMRLAdapter.create_smrl_error_response(500, "Internal server error", str(e))
        return jsonify(error), 500
    finally:
        conn.close()


@smrl_bp.route("/<resource_type>/<uid>", methods=["PUT"])
def replace_resource(resource_type: str, uid: str):
    """
    Replace an existing resource (full update).
    PUT /api/v1/{ResourceType}/{uid}
    """
    conn = get_connection()

    try:
        data = request.get_json()

        if not data:
            error = SMRLAdapter.create_smrl_error_response(400, "Request body required")
            return jsonify(error), 400

        # Map SMRL type to Neo4j label
        reverse_mapping = {v: k for k, v in SMRLAdapter.SMRL_TYPE_MAPPING.items()}
        node_label = reverse_mapping.get(resource_type, resource_type)

        # Check if resource exists
        check_query = f"""
        MATCH (n:{node_label})
        WHERE n.uid = $uid
        RETURN count(n) as exists
        """
        result = conn.execute_query(check_query, {"uid": uid})

        if result[0]["exists"] == 0:
            error = SMRLAdapter.create_smrl_error_response(
                404, f"Resource not found: {resource_type}/{uid}"
            )
            return jsonify(error), 404

        # Replace all properties (except uid)
        properties = {"modified_by": data.get("modified_by", "api_user")}
        for key, value in data.items():
            if key != "uid" and not key.startswith("_"):
                properties[key] = value

        # Update node
        query = f"""
        MATCH (n:{node_label})
        WHERE n.uid = $uid
        SET n = $properties
        SET n.uid = $uid
        SET n.last_modified = datetime()
        RETURN n
        """

        result = conn.execute_query(query, {"uid": uid, "properties": properties})

        # Convert to SMRL format
        node_data = dict(result[0]["n"])
        node_labels = list(result[0]["n"].labels)
        resource = neo4j_to_smrl(node_data, node_labels)

        return jsonify(resource), 200

    except Exception as e:
        error = SMRLAdapter.create_smrl_error_response(500, "Internal server error", str(e))
        return jsonify(error), 500
    finally:
        conn.close()


@smrl_bp.route("/<resource_type>/<uid>", methods=["PATCH"])
def update_resource(resource_type: str, uid: str):
    """
    Update specific fields of a resource (partial update).
    PATCH /api/v1/{ResourceType}/{uid}
    """
    conn = get_connection()

    try:
        data = request.get_json()

        if not data:
            error = SMRLAdapter.create_smrl_error_response(400, "Request body required")
            return jsonify(error), 400

        # Map SMRL type to Neo4j label
        reverse_mapping = {v: k for k, v in SMRLAdapter.SMRL_TYPE_MAPPING.items()}
        node_label = reverse_mapping.get(resource_type, resource_type)

        # Build SET clause for partial update
        set_clauses = ["n.last_modified = datetime()"]
        params = {"uid": uid}

        for key, value in data.items():
            if key != "uid" and not key.startswith("_"):
                set_clauses.append(f"n.`{key}` = ${key}")
                params[key] = value

        query = f"""
        MATCH (n:{node_label})
        WHERE n.uid = $uid
        SET {', '.join(set_clauses)}
        RETURN n
        """

        result = conn.execute_query(query, params)

        if not result:
            error = SMRLAdapter.create_smrl_error_response(
                404, f"Resource not found: {resource_type}/{uid}"
            )
            return jsonify(error), 404

        # Convert to SMRL format
        node_data = dict(result[0]["n"])
        node_labels = list(result[0]["n"].labels)
        resource = neo4j_to_smrl(node_data, node_labels)

        return jsonify(resource), 200

    except Exception as e:
        error = SMRLAdapter.create_smrl_error_response(500, "Internal server error", str(e))
        return jsonify(error), 500
    finally:
        conn.close()


@smrl_bp.route("/<resource_type>/<uid>", methods=["DELETE"])
def delete_resource(resource_type: str, uid: str):
    """
    Delete a resource.
    DELETE /api/v1/{ResourceType}/{uid}
    """
    conn = get_connection()

    try:
        # Map SMRL type to Neo4j label
        reverse_mapping = {v: k for k, v in SMRLAdapter.SMRL_TYPE_MAPPING.items()}
        node_label = reverse_mapping.get(resource_type, resource_type)

        query = f"""
        MATCH (n:{node_label})
        WHERE n.uid = $uid
        DETACH DELETE n
        RETURN count(n) as deleted
        """

        result = conn.execute_query(query, {"uid": uid})

        if result[0]["deleted"] == 0:
            error = SMRLAdapter.create_smrl_error_response(
                404, f"Resource not found: {resource_type}/{uid}"
            )
            return jsonify(error), 404

        return jsonify({"message": f"Resource deleted: {resource_type}/{uid}"}), 200

    except Exception as e:
        error = SMRLAdapter.create_smrl_error_response(500, "Internal server error", str(e))
        return jsonify(error), 500
    finally:
        conn.close()


# ============================================================================
# SMRL Match Endpoint (Advanced Query)
# ============================================================================


@smrl_bp.route("/match", methods=["POST"])
def smrl_match():
    """
    Advanced query endpoint matching SMRL standard.
    POST /api/v1/match

    Request body:
    {
        "resource_type": "AccessibleModelTypeConstituent",
        "filters": {
            "name": "Vehicle",
            "visibility": "public"
        },
        "limit": 100
    }
    """
    conn = get_connection()

    try:
        data = request.get_json()

        if not data:
            error = SMRLAdapter.create_smrl_error_response(400, "Request body required")
            return jsonify(error), 400

        resource_type = data.get("resource_type")
        filters = data.get("filters", {})
        limit = data.get("limit", 100)

        if not resource_type:
            error = SMRLAdapter.create_smrl_error_response(400, "resource_type required")
            return jsonify(error), 400

        # Map SMRL type to Neo4j label
        reverse_mapping = {v: k for k, v in SMRLAdapter.SMRL_TYPE_MAPPING.items()}
        node_label = reverse_mapping.get(resource_type, resource_type)

        # Build WHERE clause
        where_clauses = []
        params = {"limit": limit}

        for key, value in filters.items():
            where_clauses.append(f"n.`{key}` = ${key}")
            params[key] = value

        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

        query = f"""
        MATCH (n:{node_label})
        WHERE {where_clause}
        RETURN n
        LIMIT $limit
        """

        result = conn.execute_query(query, params)

        # Convert to SMRL format
        nodes = [(dict(r["n"]), list(r["n"].labels)) for r in result]
        response = neo4j_list_to_smrl(nodes)

        return jsonify(response), 200

    except Exception as e:
        error = SMRLAdapter.create_smrl_error_response(500, "Internal server error", str(e))
        return jsonify(error), 500
    finally:
        conn.close()


# ============================================================================
# Health Check
# ============================================================================


@smrl_bp.route("/health", methods=["GET"])
def health_check():
    """API health check endpoint."""
    return (
        jsonify(
            {
                "status": "healthy",
                "version": "1.0.0",
                "smrl_compliance": "ISO 10303-4443",
                "api_version": "v1",
            }
        ),
        200,
    )
