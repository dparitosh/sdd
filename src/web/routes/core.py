"""
Core REST API endpoints for Package, Class, Property, Port, and Association entities
Refactored from app.py to improve modularity and maintainability
"""

from flask import Blueprint, jsonify, request

from src.web.services import cache_stats, get_neo4j_service, invalidate_stats_cache

core_bp = Blueprint("core", __name__, url_prefix="/api")


@core_bp.route("/packages")
def get_packages():
    """Get all packages"""
    try:
        neo4j = get_neo4j_service()

        query = """
        MATCH (p:Package)
        OPTIONAL MATCH (p)-[:CONTAINS]->(child)
        RETURN p.id AS id,
               p.name AS name,
               p.comment AS comment,
               count(child) AS child_count
        ORDER BY p.name
        """
        result = neo4j.execute_query(query)

        packages = [
            {
                "id": r["id"],
                "name": r["name"],
                "comment": r["comment"],
                "child_count": r["child_count"],
            }
            for r in result
        ]

        return jsonify(packages)
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500


@core_bp.route("/package/<package_id>")
def get_package_contents(package_id):
    """Get package contents"""
    try:
        neo4j = get_neo4j_service()

        query = """
        MATCH (p:Package {id: $package_id})
        OPTIONAL MATCH (p)-[:CONTAINS]->(child)
        RETURN p.id AS package_id,
               p.name AS package_name,
               p.comment AS package_comment,
               collect({
                   id: child.id,
                   name: CASE 
                       WHEN labels(child)[0] = 'Association' AND child.member_ends IS NOT NULL 
                       THEN replace(replace(child.member_ends, '[', ''), ']', '') + ' relationship'
                       WHEN labels(child)[0] = 'Association' AND child.display_name IS NOT NULL 
                       THEN replace(replace(child.display_name, '[', ''), ']', '')
                       ELSE child.name 
                   END,
                   type: labels(child)[0],
                   comment: child.comment,
                   display_name: child.display_name,
                   member_ends: child.member_ends
               }) AS contents
        """
        result = neo4j.execute_query(query, {"package_id": package_id})

        if result:
            return jsonify(result[0])
        return jsonify({"error": "Package not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500


@core_bp.route("/classes")
def get_classes():
    """Get all classes"""
    try:
        neo4j = get_neo4j_service()

        query = """
        MATCH (c:Class)
        OPTIONAL MATCH (c)-[:HAS_ATTRIBUTE]->(p:Property)
        RETURN c.id AS id,
               c.name AS name,
               c.comment AS comment,
               count(p) AS property_count
        ORDER BY c.name
        LIMIT 100
        """
        result = neo4j.execute_query(query)

        classes = [
            {
                "id": r["id"],
                "name": r["name"],
                "comment": r["comment"],
                "property_count": r["property_count"],
            }
            for r in result
        ]

        return jsonify(classes)
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500


@core_bp.route("/class/<class_id>")
def get_class_details(class_id):
    """Get class details with properties"""
    try:
        neo4j = get_neo4j_service()

        query = """
        MATCH (c:Class {id: $class_id})
        OPTIONAL MATCH (c)-[:HAS_ATTRIBUTE]->(p:Property)
        OPTIONAL MATCH (p)-[:TYPED_BY]->(t:Class)
        OPTIONAL MATCH (c)-[:GENERALIZES]->(parent:Class)
        RETURN c.id AS id,
               c.name AS name,
               c.comment AS comment,
               collect(DISTINCT {
                   id: p.id,
                   name: p.name,
                   type: t.name,
                   type_id: t.id
               }) AS properties,
               collect(DISTINCT {
                   id: parent.id,
                   name: parent.name
               }) AS parents
        """
        result = neo4j.execute_query(query, {"class_id": class_id})

        if result:
            data = result[0]
            # Clean up None values
            data["properties"] = [p for p in data["properties"] if p["id"]]
            data["parents"] = [p for p in data["parents"] if p["id"]]
            return jsonify(data)
        return jsonify({"error": "Class not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500


@core_bp.route("/search")
def search():
    """Search for entities"""
    query_text = request.args.get("q", "")

    if not query_text or len(query_text) < 2:
        return jsonify([])

    try:
        neo4j = get_neo4j_service()

        # Use optimized search query
        query = """
        MATCH (n)
        WHERE n.name =~ ('(?i).*' + $query + '.*')
        RETURN n.id AS id,
               n.name AS name,
               labels(n)[0] AS type,
               n.comment AS comment
        ORDER BY n.name
        LIMIT 50
        """
        result = neo4j.execute_query(query, {"query": query_text})

        results = [
            {"id": r["id"], "name": r["name"], "type": r["type"], "comment": r["comment"]}
            for r in result
        ]

        return jsonify(results)
    except Exception as e:
        return jsonify({"error": f"Search error: {str(e)}"}), 500


@core_bp.route("/stats")
@cache_stats(ttl=60)  # Cache for 1 minute
def get_stats():
    """Get graph statistics (cached)"""
    try:
        neo4j = get_neo4j_service()
        stats = neo4j.get_statistics()

        # Return flat structure matching frontend expectations
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
