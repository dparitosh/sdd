"""
Web UI for MBSE Neo4j Knowledge Graph with REST API
ISO 10303-4443 SMRL Compliant
"""

import json
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, request, send_file
from flask_cors import CORS
from flask_socketio import SocketIO

from src.graph.connection import Neo4jConnection
from src.utils.config import Config
from src.web.middleware import register_error_handlers
from src.web.middleware.security_utils import SecurityHeaders, rate_limit
from src.web.middleware.metrics import metrics_endpoint, MetricsCollector
from src.web.services import cache_stats, get_neo4j_service, reset_neo4j_service, invalidate_stats_cache

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for external integrations
config = Config()

# Initialize SocketIO for real-time updates
socketio = SocketIO(app, cors_allowed_origins="*")

# Add security headers to all responses
@app.after_request
def add_security_headers(response):
    return SecurityHeaders.add_security_headers(response)

# Register cleanup handler for graceful shutdown
@app.teardown_appcontext
def cleanup_neo4j_service(exception=None):
    """
    Cleanup Neo4j service on application context teardown.
    This ensures proper connection pool closure.
    """
    if exception:
        from loguru import logger
        logger.error(f"Application context ended with exception: {exception}")

# Register error handlers for standardized error responses
register_error_handlers(app)
print("✓ Registered error handlers")

# Register SMRL v1 API routes
try:
    from src.web.routes.smrl_v1 import smrl_bp

    app.register_blueprint(smrl_bp)
    print("✓ Registered SMRL v1 API routes (/api/v1/)")
except Exception as e:
    print(f"Warning: Could not register SMRL v1 routes: {e}")

# Register Core API routes (Package, Class, Property, etc.)
try:
    from src.web.routes.core import core_bp

    app.register_blueprint(core_bp)
    print("✓ Registered Core API routes (/api/)")
except Exception as e:
    print(f"Warning: Could not register Core routes: {e}")

# Register PLM Integration routes
try:
    from src.web.routes.plm import plm_bp

    app.register_blueprint(plm_bp)
    print("✓ Registered PLM Integration routes (/api/v1/)")
except Exception as e:
    print(f"Warning: Could not register PLM routes: {e}")

# Register Simulation Integration routes
try:
    from src.web.routes.simulation import simulation_bp

    app.register_blueprint(simulation_bp)
    print("✓ Registered Simulation Integration routes (/api/v1/simulation/)")
except Exception as e:
    print(f"Warning: Could not register Simulation routes: {e}")

# Register Export routes
try:
    from src.web.routes.export import export_bp

    app.register_blueprint(export_bp)
    print("✓ Registered Export routes (/api/v1/export/)")
except Exception as e:
    print(f"Warning: Could not register Export routes: {e}")

# Register Graph Visualization routes
try:
    from src.web.routes.graph import graph_bp

    app.register_blueprint(graph_bp)
    print("✓ Registered Graph Visualization routes (/api/graph/)")
except Exception as e:
    print(f"Warning: Could not register Graph routes: {e}")

# Register Version Control routes
try:
    from src.web.routes.version import version_bp

    app.register_blueprint(version_bp)
    print("✓ Registered Version Control routes (/api/v1/)")
except Exception as e:
    print(f"Warning: Could not register Version routes: {e}")

# Register Authentication routes
try:
    from src.web.routes.auth import auth_bp

    app.register_blueprint(auth_bp, url_prefix='/api')
    print("✓ Registered Authentication routes (/api/auth/)")
except Exception as e:
    print(f"Warning: Could not register Auth routes: {e}")

# Register AP239 routes (Requirements, Analysis, Approvals, Documents)
try:
    from src.web.routes.ap239 import ap239_bp

    app.register_blueprint(ap239_bp)
    print("✓ Registered AP239 routes (/api/ap239/)")
except Exception as e:
    print(f"Warning: Could not register AP239 routes: {e}")

# Register AP242 routes (Parts, Materials, CAD Geometry, Assemblies)
try:
    from src.web.routes.ap242 import ap242_bp

    app.register_blueprint(ap242_bp)
    print("✓ Registered AP242 routes (/api/ap242/)")
except Exception as e:
    print(f"Warning: Could not register AP242 routes: {e}")

# Register AP243 routes (Ontologies, Units, Value Types, Classifications)
try:
    from src.web.routes.ap243 import ap243_bp

    app.register_blueprint(ap243_bp)
    print("✓ Registered AP243 routes (/api/ap243/)")
except Exception as e:
    print(f"Warning: Could not register AP243 routes: {e}")

# Register Hierarchy Navigation routes (Traceability, Cross-Level Search)
try:
    from src.web.routes.hierarchy import hierarchy_bp

    app.register_blueprint(hierarchy_bp)
    print("✓ Registered Hierarchy Navigation routes (/api/hierarchy/)")
except Exception as e:
    print(f"Warning: Could not register Hierarchy routes: {e}")


def get_connection():
    """Get Neo4j connection"""
    try:
        conn = Neo4jConnection(config.neo4j_uri, config.neo4j_user, config.neo4j_password)
        conn.connect()
        return conn
    except Exception as e:
        print(f"Error connecting to Neo4j: {e}")
        raise


@app.route("/")
def index():
    """
    Redirect root to React frontend dashboard.
    The modern React UI runs on port 3001 and provides a unified interface.
    This Flask backend serves only REST APIs under /api/*
    """
    from flask import redirect
    import os
    
    # Get frontend URL from environment or use default
    frontend_url = os.getenv('FRONTEND_URL', 'https://vigilant-space-goldfish-5x6rp4rvpxg244wj-3001.app.github.dev')
    
    # Redirect to React frontend dashboard
    return redirect(f"{frontend_url}/dashboard", code=302)


@app.route("/info")
def info():
    """
    API information and architecture overview.
    Provides guidance on how to use the system.
    """
    import os
    frontend_url = os.getenv('FRONTEND_URL', 'https://vigilant-space-goldfish-5x6rp4rvpxg244wj-3001.app.github.dev')
    
    return jsonify({
        "name": "MBSE Knowledge Graph REST API",
        "version": "2.0.0",
        "architecture": {
            "frontend": {
                "url": frontend_url,
                "description": "Modern React dashboard with ISO AP239/AP242/AP243 support",
                "routes": [
                    "/dashboard - Main system overview",
                    "/ap239/requirements - Requirements management (AP239)",
                    "/ap242/parts - Parts & materials explorer (AP242)",
                    "/search - Advanced search",
                    "/query-editor - Cypher query interface"
                ]
            },
            "backend": {
                "url": "This server (port 5000)",
                "description": "REST API server for Neo4j knowledge graph",
                "endpoints": [
                    "/api/health - System health check",
                    "/api/stats - Graph statistics",
                    "/api/ap239/* - ISO 10303-239 PLCS endpoints",
                    "/api/ap242/* - ISO 10303-242 CAD endpoints",
                    "/api/ap243/* - ISO 10303-243 Reference data endpoints",
                    "/api/hierarchy/* - Cross-schema navigation",
                    "/api/openapi.json - OpenAPI specification"
                ]
            }
        },
        "database": {
            "type": "Neo4j Aura",
            "nodes": "3,275+ nodes across AP239/AP242/AP243 schemas",
            "relationships": "Cross-level traceability with 10+ relationship types"
        },
        "standards": [
            "ISO 10303-239 (Product Life Cycle Support)",
            "ISO 10303-242 (3D Engineering)",
            "ISO 10303-243 (Reference Data)",
            "ISO 10303-4443 (SMRL)"
        ],
        "documentation": {
            "api": "/api/openapi.json",
            "health": "/api/health",
            "metrics": "/metrics"
        }
    }), 200


@app.route("/favicon.ico")
def favicon():
    """Serve favicon"""
    return send_file("static/favicon.ico", mimetype="image/x-icon")


@app.route("/api/health")
def health_check():
    """
    Health check endpoint with database connectivity test and connection pool stats.
    
    Returns:
        JSON with status, database connection state, connection pool metrics, and basic stats
    """
    from neo4j.exceptions import ServiceUnavailable, AuthError
    import time
    
    health = {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0",
        "database": {
            "connected": False,
            "latency_ms": None,
            "node_count": None,
            "error": None
        },
        "connection_pool": {
            "max_size": 50,
            "in_use": None,
            "idle": None
        }
    }
    
    try:
        neo4j_service = get_neo4j_service()
        
        # Measure connection latency
        start = time.time()
        result = neo4j_service.execute_query("MATCH (n) RETURN count(n) as count LIMIT 1")
        latency = (time.time() - start) * 1000
        
        health["database"]["connected"] = True
        health["database"]["latency_ms"] = round(latency, 2)
        health["database"]["node_count"] = result[0]["count"] if result else 0
        
        # Get connection pool stats if available
        try:
            if hasattr(neo4j_service._driver, 'get_server_info'):
                # Note: Neo4j driver doesn't expose pool stats directly
                # This is a placeholder for future enhancement
                health["connection_pool"]["status"] = "active"
        except:
            pass
        
        return jsonify(health), 200
        
    except AuthError as e:
        health["status"] = "unhealthy"
        health["database"]["error"] = f"Authentication failed: {str(e)}"
        return jsonify(health), 503
        
    except ServiceUnavailable as e:
        health["status"] = "unhealthy"
        health["database"]["error"] = f"Database unavailable: {str(e)}"
        return jsonify(health), 503
        
    except Exception as e:
        health["status"] = "unhealthy"
        health["database"]["error"] = str(e)
        return jsonify(health), 500


# NOTE: Core API endpoints moved to routes/core.py
# /api/stats, /api/packages, /api/package/<id>, /api/classes, /api/class/<id>, /api/search
# are now served by core_bp blueprint

# @app.route('/api/stats')
# @cache_stats(ttl=60)  # Cache for 1 minute
# def get_stats():
#     """Get graph statistics (cached) - MOVED TO core.py"""
#     pass

# @app.route('/api/packages')
# def get_packages():
#     """Get all packages - MOVED TO core.py"""
#     pass

# @app.route('/api/package/<package_id>')
# def get_package_contents(package_id):
#     """Get package contents - MOVED TO core.py"""
#     pass

# @app.route('/api/classes')
# def get_classes():
#     """Get all classes - MOVED TO core.py"""
#     pass

# @app.route('/api/class/<class_id>')
# def get_class_details(class_id):
#     """Get class details with properties - MOVED TO core.py"""
#     pass

# @app.route('/api/search')
# def search():
#     """Search for entities (cached) - MOVED TO core.py"""
#     pass


@app.route("/api/visualize")
def visualize():
    """Get graph data for visualization"""
    limit = int(request.args.get("limit", 50))
    entity_type = request.args.get("type", "Class")

    conn = get_connection()

    try:
        query = f"""
        MATCH (n:{entity_type})
        WITH n LIMIT $limit
        OPTIONAL MATCH (n)-[r]->(m)
        RETURN n, r, m
        LIMIT 200
        """
        result = conn.execute_query(query, {"limit": limit})

        nodes = {}
        edges = []

        for record in result:
            # Add source node
            if record["n"]:
                node_id = record["n"]["id"]
                if node_id not in nodes:
                    nodes[node_id] = {
                        "id": node_id,
                        "label": record["n"].get("name", "Unnamed"),
                        "type": (
                            list(record["n"].labels)[0]
                            if hasattr(record["n"], "labels")
                            else entity_type
                        ),
                    }

                # Add target node and relationship
                if record["m"] and record["r"]:
                    target_id = record["m"]["id"]
                    if target_id not in nodes:
                        nodes[target_id] = {
                            "id": target_id,
                            "label": record["m"].get("name", "Unnamed"),
                            "type": (
                                list(record["m"].labels)[0]
                                if hasattr(record["m"], "labels")
                                else "Unknown"
                            ),
                        }

                    edges.append(
                        {
                            "source": node_id,
                            "target": target_id,
                            "label": (
                                record["r"].type if hasattr(record["r"], "type") else "RELATED"
                            ),
                        }
                    )

        return jsonify({"nodes": list(nodes.values()), "edges": edges})
    finally:
        conn.close()


@app.route("/api/cypher", methods=["POST"])
def execute_cypher():
    """Execute custom Cypher query"""
    data = request.get_json()
    cypher_query = data.get("query", "")

    if not cypher_query:
        return jsonify({"error": "No query provided"}), 400

    conn = get_connection()

    try:
        result = conn.execute_query(cypher_query)

        # Convert result to JSON-serializable format
        results = []
        for record in result[:100]:  # Limit to 100 results
            results.append(dict(record))

        return jsonify({"results": results, "count": len(results)})
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        conn.close()


# REST API Endpoints for Simulation Integration


@app.route("/api/openapi.json")
def get_openapi_spec():
    """Serve OpenAPI specification"""
    # Get absolute path from current file location
    current_dir = Path(__file__).parent
    openapi_path = current_dir.parent.parent / "smrlv12/data/domain_models/mossec/DomainModel.json"
    if openapi_path.exists():
        return send_file(str(openapi_path), mimetype="application/json")
    return jsonify({"error": "OpenAPI spec not found"}), 404


@app.route("/api/v1/Class", methods=["GET"])
def get_all_classes_rest():
    """REST API: Get all Classes"""
    package = request.args.get("package")
    search = request.args.get("search")
    limit = int(request.args.get("limit", 100))

    conn = get_connection()
    try:
        query = "MATCH (c:Class)\n"
        params = {"limit": limit}

        if package:
            query += "MATCH (p:Package {name: $package})-[:CONTAINS]->(c)\n"
            params["package"] = package

        if search:
            query += "WHERE c.name =~ ('(?i).*' + $search + '.*')\n"
            params["search"] = search

        query += """
        OPTIONAL MATCH (c)-[:HAS_ATTRIBUTE]->(prop:Property)
        OPTIONAL MATCH (c)-[:GENERALIZES]->(parent:Class)
        RETURN c.id AS id,
               c.name AS name,
               c.comment AS description,
               count(DISTINCT prop) AS property_count,
               collect(DISTINCT parent.name) AS parent_classes
        ORDER BY c.name
        LIMIT $limit
        """

        result = conn.execute_query(query, params)
        return jsonify({"data": [dict(r) for r in result], "count": len(result)})
    finally:
        conn.close()


@app.route("/api/v1/Class/<uid>", methods=["GET"])
def get_class_by_id_rest(uid):
    """REST API: Get Class by ID"""
    conn = get_connection()
    try:
        query = """
        MATCH (c:Class {id: $uid})
        OPTIONAL MATCH (c)-[:HAS_ATTRIBUTE]->(prop:Property)
        OPTIONAL MATCH (prop)-[:TYPED_BY]->(type)
        OPTIONAL MATCH (c)-[:GENERALIZES]->(parent:Class)
        RETURN c.id AS id,
               c.name AS name,
               c.comment AS description,
               collect(DISTINCT {
                   name: prop.name,
                   id: prop.id,
                   type: type.name
               }) AS properties,
               collect(DISTINCT parent.name) AS parent_classes
        """
        result = conn.execute_query(query, {"uid": uid})
        if result:
            data = dict(result[0])
            data["properties"] = [p for p in data["properties"] if p["id"]]
            data["parent_classes"] = [p for p in data["parent_classes"] if p]
            return jsonify(data)
        return jsonify({"error": "Not found"}), 404
    finally:
        conn.close()


@app.route("/api/v1/Package", methods=["GET"])
def get_all_packages_rest():
    """REST API: Get all Packages"""
    conn = get_connection()
    try:
        query = """
        MATCH (p:Package)
        OPTIONAL MATCH (p)-[:CONTAINS]->(child)
        RETURN p.id AS id,
               p.name AS name,
               p.comment AS description,
               count(child) AS child_count
        ORDER BY p.name
        """
        result = conn.execute_query(query)
        return jsonify({"data": [dict(r) for r in result], "count": len(result)})
    finally:
        conn.close()


@app.route("/api/v1/Package/<uid>", methods=["GET"])
def get_package_by_id_rest(uid):
    """REST API: Get Package by ID"""
    conn = get_connection()
    try:
        query = """
        MATCH (p:Package {id: $uid})
        OPTIONAL MATCH (p)-[:CONTAINS]->(child)
        RETURN p.id AS id,
               p.name AS name,
               p.comment AS description,
               collect({
                   id: child.id,
                   name: child.name,
                   type: labels(child)[0]
               }) AS contents
        """
        result = conn.execute_query(query, {"uid": uid})
        if result:
            data = dict(result[0])
            data["contents"] = [c for c in data["contents"] if c["id"]]
            return jsonify(data)
        return jsonify({"error": "Not found"}), 404
    finally:
        conn.close()


@app.route("/api/v1/query", methods=["POST"])
def execute_simulation_query():
    """REST API: Execute custom query for simulation integration"""
    data = request.get_json()
    cypher_query = data.get("query", "")
    params = data.get("params", {})

    if not cypher_query:
        return jsonify({"error": "No query provided"}), 400

    conn = get_connection()
    try:
        result = conn.execute_query(cypher_query, params)
        return jsonify({"data": [dict(r) for r in result[:1000]], "count": len(result)})
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        conn.close()


@app.route("/api/v1/Port", methods=["GET"])
def get_all_ports_rest():
    """REST API: Get all Ports"""
    search = request.args.get("search")
    limit = int(request.args.get("limit", 100))

    conn = get_connection()
    try:
        query = "MATCH (p:Port)\n"
        params = {"limit": limit}

        if search:
            query += "WHERE p.name =~ ('(?i).*' + $search + '.*')\n"
            params["search"] = search

        query += """
        OPTIONAL MATCH (owner)-[:HAS_ATTRIBUTE]->(p)
        OPTIONAL MATCH (p)-[:TYPED_BY]->(type)
        RETURN p.id AS id,
               p.name AS name,
               p.comment AS description,
               type.name AS type,
               owner.name AS owner
        ORDER BY p.name
        LIMIT $limit
        """

        result = conn.execute_query(query, params)
        return jsonify({"data": [dict(r) for r in result], "count": len(result)})
    finally:
        conn.close()


@app.route("/api/v1/Port/<uid>", methods=["GET"])
def get_port_by_id_rest(uid):
    """REST API: Get Port by ID"""
    conn = get_connection()
    try:
        query = """
        MATCH (p:Port {id: $uid})
        OPTIONAL MATCH (owner)-[:HAS_ATTRIBUTE]->(p)
        OPTIONAL MATCH (p)-[:TYPED_BY]->(type)
        RETURN p.id AS id,
               p.name AS name,
               p.comment AS description,
               type.name AS type,
               owner.name AS owner,
               owner.id AS owner_id,
               labels(owner)[0] AS owner_type
        """
        result = conn.execute_query(query, {"uid": uid})
        if result:
            return jsonify(dict(result[0]))
        return jsonify({"error": "Not found"}), 404
    finally:
        conn.close()


@app.route("/api/v1/Property", methods=["GET"])
def get_all_properties_rest():
    """REST API: Get all Properties"""
    search = request.args.get("search")
    owner = request.args.get("owner")  # Filter by owner class
    limit = int(request.args.get("limit", 100))

    conn = get_connection()
    try:
        query = "MATCH (prop:Property)\n"
        params = {"limit": limit}

        if owner:
            query += "MATCH (o {name: $owner})-[:HAS_ATTRIBUTE]->(prop)\n"
            params["owner"] = owner

        if search:
            query += "WHERE prop.name =~ ('(?i).*' + $search + '.*')\n"
            params["search"] = search

        query += """
        OPTIONAL MATCH (owner)-[:HAS_ATTRIBUTE]->(prop)
        OPTIONAL MATCH (prop)-[:TYPED_BY]->(type)
        RETURN prop.id AS id,
               prop.name AS name,
               prop.comment AS description,
               type.name AS type,
               owner.name AS owner
        ORDER BY prop.name
        LIMIT $limit
        """

        result = conn.execute_query(query, params)
        return jsonify({"data": [dict(r) for r in result], "count": len(result)})
    finally:
        conn.close()


@app.route("/api/v1/Constraint", methods=["GET"])
def get_all_constraints_rest():
    """REST API: Get all Constraints"""
    search = request.args.get("search")
    limit = int(request.args.get("limit", 100))

    conn = get_connection()
    try:
        query = "MATCH (c:Constraint)\n"
        params = {"limit": limit}

        if search:
            query += "WHERE c.name =~ ('(?i).*' + $search + '.*')\n"
            params["search"] = search

        query += """
        OPTIONAL MATCH (owner)-[:HAS_RULE]->(c)
        RETURN c.id AS id,
               c.name AS name,
               c.comment AS description,
               owner.name AS constrained_element
        ORDER BY c.name
        LIMIT $limit
        """

        result = conn.execute_query(query, params)
        return jsonify({"data": [dict(r) for r in result], "count": len(result)})
    finally:
        conn.close()


@app.route("/api/v1/nodes", methods=["GET"])
def get_all_nodes_rest():
    """REST API: Get all nodes with optional type filter"""
    node_type = request.args.get("type")  # Filter by node type (label)
    search = request.args.get("search")
    limit = int(request.args.get("limit", 100))

    conn = get_connection()
    try:
        if node_type:
            query = f"MATCH (n:{node_type})\n"
        else:
            query = "MATCH (n)\n"

        params = {"limit": limit}

        if search:
            query += "WHERE n.name =~ ('(?i).*' + $search + '.*')\n"
            params["search"] = search

        query += """
        RETURN n.id AS id,
               n.name AS name,
               labels(n)[0] AS type,
               n.comment AS description
        ORDER BY n.name
        LIMIT $limit
        """

        result = conn.execute_query(query, params)
        return jsonify({"data": [dict(r) for r in result], "count": len(result)})
    finally:
        conn.close()


@app.route("/api/v1/relationship/<rel_type>", methods=["GET"])
def get_relationships_rest(rel_type):
    """REST API: Get relationships by type"""
    limit = int(request.args.get("limit", 100))

    conn = get_connection()
    try:
        query = f"""
        MATCH (source)-[r:{rel_type}]->(target)
        RETURN source.id AS source_id,
               source.name AS source_name,
               labels(source)[0] AS source_type,
               target.id AS target_id,
               target.name AS target_name,
               labels(target)[0] AS target_type
        LIMIT $limit
        """
        result = conn.execute_query(query, {"limit": limit})
        return jsonify({"data": [dict(r) for r in result], "count": len(result)})
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        conn.close()


@app.route("/api/artifacts", methods=["GET"])
def get_artifacts_summary():
    """Search for artifacts with filters or get summary if no filters provided"""
    # Check if search parameters are provided
    artifact_type = request.args.get("type")
    name = request.args.get("name", "")
    comment = request.args.get("comment", "")
    limit = int(request.args.get("limit", 100))
    
    conn = get_connection()
    try:
        # If any search parameters provided, do a search
        if artifact_type or name or comment:
            # Build dynamic query
            conditions = []
            params = {"limit": limit}
            
            # Handle "All" as no filter
            if artifact_type and artifact_type != "All":
                label_filter = f"n:{artifact_type}"
            else:
                label_filter = "n"
            
            query = f"MATCH ({label_filter})\nWHERE 1=1\n"
            
            if name:
                conditions.append("n.name =~ ('(?i).*' + $name + '.*')")
                params["name"] = name
            
            if comment:
                conditions.append("n.comment =~ ('(?i).*' + $comment + '.*')")
                params["comment"] = comment
            
            if conditions:
                query += "AND " + " AND ".join(conditions) + "\n"
            
            query += """
            RETURN n.id AS id,
                   n.uid AS uid,
                   n.name AS name,
                   labels(n)[0] AS type,
                   n.comment AS comment,
                   n.qualified_name AS qualified_name
            ORDER BY n.name
            LIMIT $limit
            """
            
            result = conn.execute_query(query, params)
            # Return array directly for frontend compatibility
            return jsonify([dict(r) for r in result])
        else:
            # No search parameters - return summary
            query = """
            MATCH (n)
            WITH labels(n)[0] AS artifact_type, 
                 n.type AS xmi_type,
                 count(n) AS count
            RETURN artifact_type, xmi_type, count
            ORDER BY count DESC
            """
            result = conn.execute_query(query, {})
            return jsonify({"data": [dict(r) for r in result]})
    finally:
        conn.close()


@app.route("/api/artifacts/<artifact_type>", methods=["GET"])
def get_artifacts_by_type(artifact_type):
    """Get all artifacts of a specific type with their properties"""
    search = request.args.get("search", "")
    limit = int(request.args.get("limit", 100))

    conn = get_connection()
    try:
        query = f"""
        MATCH (n:{artifact_type})
        """
        params = {"limit": limit}

        if search:
            query += "WHERE n.name =~ ('(?i).*' + $search + '.*') OR n.comment =~ ('(?i).*' + $search + '.*')\n"
            params["search"] = search

        query += """
        RETURN n.id AS id,
               n.uid AS uid,
               n.name AS name,
               n.type AS xmi_type,
               n.comment AS description,
               labels(n)[0] AS artifact_type,
               n.href AS href,
               n.smrl_type AS smrl_type,
               toString(n.created_on) AS created_on,
               toString(n.last_modified) AS last_modified,
               n.created_by AS created_by
        ORDER BY n.name
        LIMIT $limit
        """

        result = conn.execute_query(query, params)

        # Clean up None values for better JSON
        data = []
        for record in result:
            item = {k: v for k, v in dict(record).items() if v is not None}
            data.append(item)

        return jsonify({"data": data, "count": len(data)})
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        conn.close()


@app.route("/api/artifacts/<artifact_type>/<uid>", methods=["GET"])
def get_artifact_details(artifact_type, uid):
    """Get detailed information about a specific artifact including relationships"""
    from neo4j.time import DateTime

    from web.middleware import DatabaseError, NotFoundError

    def serialize_value(value):
        """Convert Neo4j types to JSON-serializable types"""
        if isinstance(value, DateTime):
            return value.iso_format()
        elif isinstance(value, dict):
            return {k: serialize_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [serialize_value(item) for item in value]
        return value

    conn = get_connection()
    try:
        query = f"""
        MATCH (n:{artifact_type} {{id: $uid}})
        OPTIONAL MATCH (n)-[r]->(related)
        WITH n, 
             collect({{
                 relationship: type(r),
                 target_id: related.id,
                 target_name: related.name,
                 target_type: labels(related)[0]
             }}) AS outgoing_relationships
        OPTIONAL MATCH (related2)-[r2]->(n)
        RETURN n.id AS id,
               n.name AS name,
               n.type AS xmi_type,
               n.comment AS description,
               labels(n)[0] AS artifact_type,
               properties(n) AS all_properties,
               outgoing_relationships,
               collect({{
                   relationship: type(r2),
                   source_id: related2.id,
                   source_name: related2.name,
                   source_type: labels(related2)[0]
               }}) AS incoming_relationships
        """

        result = conn.execute_query(query, {"uid": uid})
        if result:
            data = dict(result[0])
            # Serialize Neo4j types (DateTime, etc.)
            data = serialize_value(data)
            # Filter out null relationships
            data["outgoing_relationships"] = [
                r for r in data["outgoing_relationships"] if r.get("target_id")
            ]
            data["incoming_relationships"] = [
                r for r in data["incoming_relationships"] if r.get("source_id")
            ]
            return jsonify(data)

        # Use error handler for 404
        raise NotFoundError(resource_type=artifact_type, resource_id=uid)

    except NotFoundError:
        raise  # Re-raise to be handled by error handler
    except Exception as e:
        # Log the actual error for debugging
        import traceback

        print(f"Error fetching artifact {artifact_type}/{uid}: {str(e)}")
        print(traceback.format_exc())
        raise DatabaseError(f"Failed to fetch {artifact_type}", original_error=e)
    finally:
        conn.close()


@app.route("/api/admin/fix-comments", methods=["POST"])
def fix_comments():
    """Admin endpoint to fix comment newlines (replace | with \\n)"""
    conn = get_connection()
    try:
        with conn._driver.session() as session:
            # Count nodes needing update
            count_result = session.run(
                """
                MATCH (n)
                WHERE n.comment IS NOT NULL AND n.comment CONTAINS ' | '
                RETURN count(n) as total
            """
            )
            total = count_result.single()["total"]

            # Update all comments
            update_result = session.run(
                """
                MATCH (n)
                WHERE n.comment IS NOT NULL AND n.comment CONTAINS ' | '
                SET n.comment = replace(n.comment, ' | ', '\n')
                RETURN count(n) as updated
            """
            )
            updated = update_result.single()["updated"]

            return jsonify(
                {
                    "success": True,
                    "total_found": total,
                    "updated": updated,
                    "message": f'Successfully updated {updated} nodes - replaced " | " with newlines',
                }
            )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


# ===== PLM INTEGRATION ENDPOINTS =====


@app.route("/api/v1/traceability", methods=["GET"])
def get_traceability():
    """
    Get traceability matrix showing relationships between elements
    Query params: source_type, target_type, relationship_type
    """
    try:
        conn = get_connection()
    except Exception as e:
        return jsonify({"error": f"Database connection error: {str(e)}"}), 500

    try:
        source_type = request.args.get("source_type")
        target_type = request.args.get("target_type")
        relationship_type = request.args.get("relationship_type")

        # Build dynamic query
        query_parts = []
        params = {}

        # Source node filter
        if source_type:
            query_parts.append(f"MATCH (source:{source_type})")
            params["source_type"] = source_type
        else:
            query_parts.append("MATCH (source)")

        # Relationship filter
        if relationship_type:
            query_parts.append(f"-[r:{relationship_type}]->")
        else:
            query_parts.append("-[r]->")

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
               type(r) as relationship,
               target.id as target_id,
               target.name as target_name,
               labels(target)[0] as target_type,
               properties(r) as rel_properties
        LIMIT 1000
        """
        )

        result = conn.execute_query(query, params)

        traces = [
            {
                "source": {
                    "id": r["source_id"],
                    "name": r["source_name"],
                    "type": r["source_type"],
                },
                "relationship": {"type": r["relationship"], "properties": r["rel_properties"]},
                "target": {
                    "id": r["target_id"],
                    "name": r["target_name"],
                    "type": r["target_type"],
                },
            }
            for r in result
        ]

        return jsonify({"total": len(traces), "traceability": traces})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/v1/composition/<node_id>", methods=["GET"])
def get_composition(node_id):
    """
    Get Bill of Materials (BOM) composition hierarchy for a node
    Shows complete containment tree with all children at all levels
    """
    try:
        conn = get_connection()
    except Exception as e:
        return jsonify({"error": f"Database connection error: {str(e)}"}), 500

    try:
        depth = request.args.get("depth", default=10, type=int)

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

        result = conn.execute_query(query, {"node_id": node_id})

        # Build hierarchical tree structure
        composition = {
            "root": {
                "id": result[0]["root_id"] if result else node_id,
                "name": result[0]["root_name"] if result else "Unknown",
                "type": result[0]["root_type"] if result else "Unknown",
            },
            "children": [],
        }

        for r in result:
            composition["children"].append({"path": r["path_nodes"], "depth": r["depth"]})

        return jsonify(composition)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/v1/impact/<node_id>", methods=["GET"])
def get_impact_analysis(node_id):
    """
    Analyze change impact - find all nodes that would be affected by changes to this node
    Shows upstream (depends on this) and downstream (this depends on) dependencies
    """
    try:
        conn = get_connection()
    except Exception as e:
        return jsonify({"error": f"Database connection error: {str(e)}"}), 500

    try:
        depth = request.args.get("depth", default=3, type=int)

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

        upstream_result = conn.execute_query(upstream_query, {"node_id": node_id})

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

        downstream_result = conn.execute_query(downstream_query, {"node_id": node_id})

        # Get node info
        node_query = """
        MATCH (n {id: $node_id})
        RETURN n.id as id, n.name as name, labels(n)[0] as type
        """
        node_info = conn.execute_query(node_query, {"node_id": node_id})

        return jsonify(
            {
                "node": {
                    "id": node_info[0]["id"] if node_info else node_id,
                    "name": node_info[0]["name"] if node_info else "Unknown",
                    "type": node_info[0]["type"] if node_info else "Unknown",
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
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/v1/parameters", methods=["GET"])
def get_parameters():
    """
    Get system parameters from Properties with their types, multiplicity, and constraints
    Useful for design/simulation integration
    """
    try:
        conn = get_connection()
    except Exception as e:
        return jsonify({"error": f"Database connection error: {str(e)}"}), 500

    try:
        class_name = request.args.get("class")

        query_parts = ["MATCH (p:Property)"]
        params = {}

        if class_name:
            query_parts.append("MATCH (c:Class {name: $class_name})-[:HAS_ATTRIBUTE]->(p)")
            params["class_name"] = class_name

        query_parts.append(
            """
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
        LIMIT 1000
        """
        )

        query = " ".join(query_parts)
        result = conn.execute_query(query, params)

        parameters = [
            {
                "id": r["id"],
                "name": r["name"],
                "owner": {"name": r["owner_name"], "type": r["owner_type"]},
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

        return jsonify({"total": len(parameters), "parameters": parameters})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/v1/constraints", methods=["GET"])
def get_constraints():
    """
    Get validation constraints for design/simulation validation
    Returns OCL or other constraint specifications
    """
    try:
        conn = get_connection()
    except Exception as e:
        return jsonify({"error": f"Database connection error: {str(e)}"}), 500

    try:
        element_id = request.args.get("element_id")

        query_parts = ["MATCH (c:Constraint)"]
        params = {}

        if element_id:
            query_parts.append("MATCH (e {id: $element_id})-[:HAS_RULE]->(c)")
            params["element_id"] = element_id

        query_parts.append(
            """
        OPTIONAL MATCH (owner)-[:HAS_RULE]->(c)
        RETURN c.id as id,
               c.name as name,
               c.body as body,
               c.language as language,
               owner.id as owner_id,
               owner.name as owner_name,
               labels(owner)[0] as owner_type
        ORDER BY owner_name, c.name
        LIMIT 1000
        """
        )

        query = " ".join(query_parts)
        result = conn.execute_query(query, params)

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

        return jsonify({"total": len(constraints), "constraints": constraints})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


# ============================================================================
# TASK 4: SIMULATION SYSTEM INTEGRATION API
# ============================================================================


@app.route("/api/v1/simulation/parameters", methods=["GET"])
def get_simulation_parameters():
    """
    Extract parameters for simulation with types, defaults, units, and constraints.
    Query params: class_name, property_name, data_type, include_constraints
    """
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        class_name = request.args.get("class_name")
        property_name = request.args.get("property_name")
        data_type = request.args.get("data_type")
        include_constraints = request.args.get("include_constraints", "true").lower() == "true"

        # Build query to extract properties with full simulation metadata
        query = """
        MATCH (p:Property)
        OPTIONAL MATCH (p)-[:TYPED_BY]->(type)
        OPTIONAL MATCH (owner)-[:HAS_ATTRIBUTE]->(p)
        OPTIONAL MATCH (p)-[r:HAS_RULE]->(constraint:Constraint)
        """

        # Add filters
        where_clauses = []
        params = {}

        if class_name:
            where_clauses.append("owner.name = $class_name")
            params["class_name"] = class_name

        if property_name:
            where_clauses.append("p.name =~ $property_pattern")
            params["property_pattern"] = f"(?i).*{property_name}.*"

        if data_type:
            where_clauses.append("type.name = $data_type")
            params["data_type"] = data_type

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)

        query += """
        RETURN p.id as id,
               p.name as name,
               p.type as property_type,
               type.name as data_type,
               type.id as type_id,
               p.visibility as visibility,
               p.lower as multiplicity_lower,
               p.upper as multiplicity_upper,
               p.default as default_value,
               p.defaultValue as default_value_alt,
               p.aggregation as aggregation,
               p.isDerived as is_derived,
               p.isReadOnly as is_read_only,
               owner.name as owner_class,
               owner.id as owner_id,
               COLLECT(DISTINCT {
                   id: constraint.id,
                   name: constraint.name,
                   body: constraint.body,
                   type: constraint.type
               }) as constraints
        ORDER BY owner.name, p.name
        """

        result = conn.execute_query(query, params)

        parameters = []
        for record in result:
            param = {
                "id": record["id"],
                "name": record["name"],
                "property_type": record["property_type"],
                "data_type": record["data_type"],
                "type_id": record["type_id"],
                "visibility": record["visibility"],
                "multiplicity": {
                    "lower": record["multiplicity_lower"],
                    "upper": record["multiplicity_upper"],
                },
                "default_value": record["default_value"] or record["default_value_alt"],
                "aggregation": record["aggregation"],
                "is_derived": record["is_derived"],
                "is_read_only": record["is_read_only"],
                "owner": {"name": record["owner_class"], "id": record["owner_id"]},
            }

            # Add constraints if requested
            if include_constraints:
                constraints = record["constraints"]
                param["constraints"] = [c for c in constraints if c.get("id")]

            parameters.append(param)

        return jsonify({"total": len(parameters), "parameters": parameters})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/v1/simulation/validate", methods=["POST"])
def validate_simulation_parameters():
    """
    Validate parameter values against constraints.
    Body: { "parameters": [{"id": "prop_id", "value": 123}] }
    """
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        data = request.get_json()
        if not data or "parameters" not in data:
            return jsonify({"error": "Missing parameters in request body"}), 400

        parameters = data["parameters"]
        validation_results = []

        for param in parameters:
            param_id = param.get("id")
            param_value = param.get("value")

            if not param_id:
                continue

            # Get constraints for this parameter
            query = """
            MATCH (p:Property {id: $param_id})
            OPTIONAL MATCH (p)-[:HAS_RULE]->(c:Constraint)
            RETURN p.id as id,
                   p.name as name,
                   p.lower as lower,
                   p.upper as upper,
                   COLLECT({
                       id: c.id,
                       name: c.name,
                       body: c.body
                   }) as constraints
            """

            result = conn.execute_query(query, {"param_id": param_id})

            if not result:
                validation_results.append(
                    {"parameter_id": param_id, "valid": False, "error": "Parameter not found"}
                )
                continue

            record = result[0]
            violations = []

            # Check multiplicity constraints
            lower = record["lower"]
            upper = record["upper"]

            if lower is not None:
                if isinstance(param_value, list):
                    if len(param_value) < lower:
                        violations.append(
                            f"Value count {len(param_value)} is less than lower bound {lower}"
                        )
                elif lower > 0 and param_value is None:
                    violations.append(f"Value is required (lower bound: {lower})")

            if upper is not None and upper != -1:  # -1 means unlimited
                if isinstance(param_value, list) and len(param_value) > upper:
                    violations.append(f"Value count {len(param_value)} exceeds upper bound {upper}")

            # Check constraints (basic validation - can be extended)
            constraints = [c for c in record["constraints"] if c.get("id")]
            for constraint in constraints:
                body = constraint.get("body", "")
                # Simple constraint checks (extend for OCL parsing)
                if "not null" in body.lower() and param_value is None:
                    violations.append(f"Constraint violation: {constraint['name']} - {body}")

            validation_results.append(
                {
                    "parameter_id": param_id,
                    "parameter_name": record["name"],
                    "value": param_value,
                    "valid": len(violations) == 0,
                    "violations": violations,
                    "constraints_checked": len(constraints),
                }
            )

        return jsonify(
            {
                "total_parameters": len(validation_results),
                "valid_count": sum(1 for r in validation_results if r["valid"]),
                "invalid_count": sum(1 for r in validation_results if not r["valid"]),
                "results": validation_results,
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/v1/units", methods=["GET"])
def get_units():
    """
    Extract unit definitions from the model.
    Returns data types that represent units and their conversion factors if available.
    """
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        # Query for DataTypes and Enumerations that may represent units
        query = """
        MATCH (dt)
        WHERE dt:DataType OR dt:Enumeration OR dt:PrimitiveType
        OPTIONAL MATCH (dt)-[:HAS_LITERAL]->(lit:EnumerationLiteral)
        OPTIONAL MATCH (dt)<-[:TYPED_BY]-(prop:Property)
        RETURN dt.id as id,
               dt.name as name,
               dt.type as type,
               labels(dt) as labels,
               COLLECT(DISTINCT lit.name) as literals,
               COUNT(DISTINCT prop) as usage_count
        ORDER BY dt.name
        """

        result = conn.execute_query(query)

        units = []
        for record in result:
            unit = {
                "id": record["id"],
                "name": record["name"],
                "type": record["type"],
                "labels": record["labels"],
                "usage_count": record["usage_count"],
            }

            # Include literals for enumerations
            literals = record["literals"]
            if literals and any(literals):
                unit["literals"] = [lit for lit in literals if lit]

            units.append(unit)

        # Also query for properties with unit-related names
        unit_query = """
        MATCH (p:Property)
        WHERE p.name =~ '(?i).*(unit|dimension|quantity|measure).*'
        OPTIONAL MATCH (p)-[:TYPED_BY]->(type)
        OPTIONAL MATCH (owner)-[:HAS_ATTRIBUTE]->(p)
        RETURN p.id as id,
               p.name as name,
               type.name as data_type,
               owner.name as owner_class
        ORDER BY p.name
        LIMIT 50
        """

        unit_properties = []
        result = conn.execute_query(unit_query)
        for record in result:
            unit_properties.append(
                {
                    "id": record["id"],
                    "name": record["name"],
                    "data_type": record["data_type"],
                    "owner_class": record["owner_class"],
                }
            )

        return jsonify(
            {
                "unit_types": {"total": len(units), "types": units},
                "unit_properties": {"total": len(unit_properties), "properties": unit_properties},
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


# ============================================================================
# TASK 6: EXPORT CAPABILITIES API
# ============================================================================


@app.route("/api/v1/export/graphml", methods=["GET"])
def export_graphml():
    """
    Export graph as GraphML XML format.
    Query params: node_types (comma-separated), include_properties (true/false)
    """
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        import xml.etree.ElementTree as ET
        from xml.dom import minidom

        node_types = (
            request.args.get("node_types", "").split(",") if request.args.get("node_types") else []
        )
        include_properties = request.args.get("include_properties", "true").lower() == "true"

        # Build query
        node_match = "MATCH (n)"
        if node_types and node_types[0]:
            labels_filter = " OR ".join([f"'{nt}' IN labels(n)" for nt in node_types])
            node_match += f" WHERE {labels_filter}"

        # Get nodes
        node_query = f"""
        {node_match}
        RETURN n.id as id, labels(n) as labels, properties(n) as props
        LIMIT 10000
        """

        nodes = conn.execute_query(node_query)

        # Get relationships
        rel_query = f"""
        {node_match}
        MATCH (n)-[r]->(m)
        RETURN n.id as source, m.id as target, type(r) as type, properties(r) as props
        LIMIT 10000
        """

        relationships = conn.execute_query(rel_query)

        # Build GraphML XML
        graphml = ET.Element(
            "graphml",
            {
                "xmlns": "http://graphml.graphdrawing.org/xmlns",
                "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                "xsi:schemaLocation": "http://graphml.graphdrawing.org/xmlns http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd",
            },
        )

        # Define keys for attributes
        if include_properties:
            key_id = ET.SubElement(
                graphml,
                "key",
                {"id": "d0", "for": "node", "attr.name": "id", "attr.type": "string"},
            )
            key_name = ET.SubElement(
                graphml,
                "key",
                {"id": "d1", "for": "node", "attr.name": "name", "attr.type": "string"},
            )
            key_type = ET.SubElement(
                graphml,
                "key",
                {"id": "d2", "for": "node", "attr.name": "type", "attr.type": "string"},
            )
            key_labels = ET.SubElement(
                graphml,
                "key",
                {"id": "d3", "for": "node", "attr.name": "labels", "attr.type": "string"},
            )

        graph = ET.SubElement(graphml, "graph", {"id": "G", "edgedefault": "directed"})

        # Add nodes
        for node in nodes:
            node_elem = ET.SubElement(graph, "node", {"id": str(node["id"])})

            if include_properties:
                props = node["props"]
                if props.get("id"):
                    ET.SubElement(node_elem, "data", {"key": "d0"}).text = str(props["id"])
                if props.get("name"):
                    ET.SubElement(node_elem, "data", {"key": "d1"}).text = str(props["name"])
                if props.get("type"):
                    ET.SubElement(node_elem, "data", {"key": "d2"}).text = str(props["type"])
                if node["labels"]:
                    ET.SubElement(node_elem, "data", {"key": "d3"}).text = ",".join(node["labels"])

        # Add edges
        edge_id = 0
        for rel in relationships:
            ET.SubElement(
                graph,
                "edge",
                {
                    "id": f"e{edge_id}",
                    "source": str(rel["source"]),
                    "target": str(rel["target"]),
                    "label": rel["type"],
                },
            )
            edge_id += 1

        # Pretty print XML
        xml_str = minidom.parseString(ET.tostring(graphml)).toprettyxml(indent="  ")

        return Response(
            xml_str,
            mimetype="application/xml",
            headers={"Content-Disposition": "attachment; filename=graph_export.graphml"},
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/v1/export/jsonld", methods=["GET"])
def export_jsonld():
    """
    Export graph as JSON-LD with semantic annotations.
    Query params: node_types (comma-separated)
    """
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        node_types = (
            request.args.get("node_types", "").split(",") if request.args.get("node_types") else []
        )

        # Build query
        node_match = "MATCH (n)"
        if node_types and node_types[0]:
            labels_filter = " OR ".join([f"'{nt}' IN labels(n)" for nt in node_types])
            node_match += f" WHERE {labels_filter}"

        # Get nodes with relationships
        query = f"""
        {node_match}
        OPTIONAL MATCH (n)-[r]->(m)
        RETURN n.id as id, 
               labels(n) as labels, 
               properties(n) as props,
               COLLECT({{
                   type: type(r),
                   target: m.id,
                   target_name: m.name
               }}) as relationships
        LIMIT 5000
        """

        result = conn.execute_query(query)

        # Build JSON-LD document
        jsonld = {
            "@context": {
                "@vocab": "http://www.omg.org/spec/UML/20131001/",
                "uml": "http://www.omg.org/spec/UML/20131001/",
                "sysml": "http://www.omg.org/spec/SysML/20150709/",
                "id": "@id",
                "type": "@type",
                "name": "uml:name",
                "visibility": "uml:visibility",
                "isAbstract": "uml:isAbstract",
                "lower": "uml:lower",
                "upper": "uml:upper",
                "aggregation": "uml:aggregation",
                "containedElements": {"@id": "uml:packagedElement", "@type": "@id"},
            },
            "@graph": [],
        }

        for record in result:
            node = {
                "@id": f"urn:uuid:{record['id']}",
                "@type": record["labels"],
                "properties": record["props"],
            }

            # Add relationships
            rels = [r for r in record["relationships"] if r.get("target")]
            if rels:
                node["relationships"] = rels

            jsonld["@graph"].append(node)

        return Response(
            json.dumps(jsonld, indent=2),
            mimetype="application/ld+json",
            headers={"Content-Disposition": "attachment; filename=graph_export.jsonld"},
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/v1/export/csv", methods=["GET"])
def export_csv():
    """
    Export nodes as CSV files (one per node type).
    Query params: node_type (required), properties (comma-separated, optional)
    Returns ZIP file containing CSV files.
    """
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        import csv
        import io
        import zipfile

        node_type = request.args.get("node_type")
        if not node_type:
            return jsonify({"error": "node_type parameter is required"}), 400

        properties = (
            request.args.get("properties", "").split(",") if request.args.get("properties") else []
        )

        # Query nodes
        query = f"""
        MATCH (n:{node_type})
        RETURN properties(n) as props
        LIMIT 10000
        """

        result = conn.execute_query(query)

        if not result:
            return jsonify({"error": "No nodes found"}), 404

        # Determine columns
        all_keys = set()
        for record in result:
            all_keys.update(record["props"].keys())

        columns = sorted(list(all_keys))
        if properties and properties[0]:
            columns = [c for c in columns if c in properties]

        # Create CSV
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()

        for record in result:
            props = record["props"]
            row = {col: props.get(col, "") for col in columns}
            writer.writerow(row)

        # Create ZIP file
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr(f"{node_type}_export.csv", output.getvalue())

        zip_buffer.seek(0)

        return Response(
            zip_buffer.getvalue(),
            mimetype="application/zip",
            headers={"Content-Disposition": f"attachment; filename={node_type}_export.zip"},
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/v1/export/step", methods=["GET"])
def export_step():
    """
    Export as STEP AP242 format (ISO 10303-242).
    Note: This is a simplified STEP export. Full STEP compliance requires extensive mapping.
    """
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        # Query all classes and properties for STEP export
        query = """
        MATCH (c:Class)
        OPTIONAL MATCH (c)-[:HAS_ATTRIBUTE]->(p:Property)
        OPTIONAL MATCH (p)-[:TYPED_BY]->(type)
        RETURN c.id as class_id,
               c.name as class_name,
               COLLECT({
                   name: p.name,
                   type: type.name,
                   multiplicity_lower: p.lower,
                   multiplicity_upper: p.upper
               }) as attributes
        ORDER BY c.name
        LIMIT 1000
        """

        result = conn.execute_query(query)

        # Build STEP file content
        step_lines = [
            "ISO-10303-21;",
            "HEADER;",
            "FILE_DESCRIPTION(('MBSE Model Export'), '2;1');",
            "FILE_NAME('model_export.stp', '2025-12-06T00:00:00', ('Author'), ('Organization'), 'Neo4j MBSE Exporter', 'Neo4j', '');",
            "FILE_SCHEMA(('AP242'));",
            "ENDSEC;",
            "DATA;",
        ]

        entity_id = 1

        for record in result:
            class_name = record["class_name"] or "UNNAMED_CLASS"
            # Clean name for STEP format
            step_class_name = class_name.replace(" ", "_").upper()

            attributes = [attr for attr in record["attributes"] if attr.get("name")]

            # Create STEP entity
            attr_values = []
            for attr in attributes:
                attr_name = attr["name"]
                attr_type = attr.get("type", "STRING")
                attr_values.append(f"'{attr_name}'")

            if attr_values:
                step_lines.append(f"#{entity_id} = {step_class_name}({', '.join(attr_values)});")
            else:
                step_lines.append(f"#{entity_id} = {step_class_name}();")

            entity_id += 1

        step_lines.append("ENDSEC;")
        step_lines.append("END-ISO-10303-21;")

        step_content = "\n".join(step_lines)

        return Response(
            step_content,
            mimetype="application/step",
            headers={"Content-Disposition": "attachment; filename=model_export.stp"},
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


# ============================================================================
# TASK 5: VERSION CONTROL & CHANGE MANAGEMENT API
# ============================================================================


@app.route("/api/v1/versions/<node_id>", methods=["GET"])
def get_node_versions(node_id):
    """
    Get version history for a specific node.
    Returns all versions with timestamps and changes.
    """
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        # Query for node with version information
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

        result = conn.execute_query(query, {"node_id": node_id})

        if not result:
            return jsonify({"error": "Node not found"}), 404

        node = result[0]

        # In a full versioning system, we would query historical versions
        # For now, return current version info
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

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/v1/diff", methods=["POST"])
def compare_versions():
    """
    Compare two versions of nodes or two different nodes.
    Body: { "node1_id": "id1", "node2_id": "id2" } or { "node_id": "id", "version1": 1, "version2": 2 }
    """
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body required"}), 400

        node1_id = data.get("node1_id")
        node2_id = data.get("node2_id")

        if not node1_id or not node2_id:
            return jsonify({"error": "Both node1_id and node2_id are required"}), 400

        # Query both nodes
        query = """
        MATCH (n1 {id: $id1})
        MATCH (n2 {id: $id2})
        RETURN properties(n1) as props1, labels(n1) as labels1,
               properties(n2) as props2, labels(n2) as labels2
        """

        result = conn.execute_query(query, {"id1": node1_id, "id2": node2_id})

        if not result:
            return jsonify({"error": "One or both nodes not found"}), 404

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

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/v1/history/<node_id>", methods=["GET"])
def get_node_history(node_id):
    """
    Get change history/audit trail for a specific node.
    Returns timeline of all changes with timestamps.
    """
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        # Query node and its relationships (relationships can indicate changes)
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

        result = conn.execute_query(query, {"node_id": node_id})

        if not result:
            return jsonify({"error": "Node not found"}), 404

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

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/v1/checkpoint", methods=["POST"])
def create_checkpoint():
    """
    Create a snapshot/checkpoint of the entire graph.
    Body: { "name": "checkpoint_name", "description": "description" }
    """
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        from datetime import datetime

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

        stats_result = conn.execute_query(stats_query)

        if stats_result:
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
        else:
            return jsonify({"error": "Failed to create checkpoint"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


# Prometheus metrics endpoint
@app.route('/metrics')
def metrics():
    """Expose Prometheus metrics for monitoring"""
    return metrics_endpoint()


if __name__ == "__main__":
    import os
    from loguru import logger
    from src.web.middleware.websocket_handler import GraphUpdateNotifier
    
    FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))
    FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
    
    print("=" * 60)
    print("🚀 MBSE Knowledge Graph UI + REST API")
    print("=" * 60)
    
    # Verify Neo4j connection before starting server
    try:
        logger.info("Verifying Neo4j database connection...")
        neo4j_service = get_neo4j_service()
        neo4j_service.verify_connectivity()
        print("✓ Neo4j database connected")
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {e}")
        print(f"✗ Neo4j connection failed: {e}")
        print("  Please check your NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD in .env")
        exit(1)
    
    # Initialize WebSocket notifier
    notifier = GraphUpdateNotifier(socketio)
    app.config['NOTIFIER'] = notifier
    print("✓ WebSocket support enabled")
    
    print(f"📊 UI: http://127.0.0.1:{FLASK_PORT}")
    print(f"🔌 API: http://127.0.0.1:{FLASK_PORT}/api/v1/")
    print(f"📄 OpenAPI: http://127.0.0.1:{FLASK_PORT}/api/openapi.json")
    print(f"📈 Metrics: http://127.0.0.1:{FLASK_PORT}/metrics")
    print(f"🔍 Health: http://127.0.0.1:{FLASK_PORT}/api/health")
    print("💡 Press CTRL+C to stop")
    print("=" * 60)
    
    # Use socketio.run instead of app.run for WebSocket support
    socketio.run(app, debug=True, host=FLASK_HOST, port=FLASK_PORT, allow_unsafe_werkzeug=True)

