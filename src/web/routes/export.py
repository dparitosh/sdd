"""
Export Blueprint
Endpoints for exporting graph data in various formats:
- GraphML (XML format)
- JSON-LD (Linked Data)
- CSV (tabular data)
- STEP AP242 (ISO 10303)
"""

import csv
import io
import json
import xml.etree.ElementTree as ET
import zipfile
from xml.dom import minidom

from flask import Blueprint, Response, jsonify, request
from loguru import logger

from src.web.middleware import DatabaseError, NotFoundError, ValidationError
from src.web.services import get_neo4j_service

export_bp = Blueprint("export", __name__, url_prefix="/api/v1/export")


@export_bp.route("/graphml", methods=["GET"])
def export_graphml():
    """
    Export graph as GraphML XML format.
    Query params: node_types (comma-separated), include_properties (true/false), limit
    """
    service = get_neo4j_service()

    try:
        node_types = (
            request.args.get("node_types", "").split(",") if request.args.get("node_types") else []
        )
        include_properties = request.args.get("include_properties", "true").lower() == "true"
        limit = request.args.get("limit", default=10000, type=int)

        if limit < 1 or limit > 50000:
            raise ValidationError("Limit must be between 1 and 50000")

        # Build query
        node_match = "MATCH (n)"
        if node_types and node_types[0]:
            labels_filter = " OR ".join([f"'{nt}' IN labels(n)" for nt in node_types])
            node_match += f" WHERE {labels_filter}"

        # Get nodes
        node_query = f"{node_match} RETURN n.id as id, labels(n) as labels, properties(n) as props LIMIT $limit"
        nodes = service.execute_query(node_query, {"limit": limit})

        # Get relationships
        rel_query = f"{node_match} MATCH (n)-[r]->(m) RETURN n.id as source, m.id as target, type(r) as type, properties(r) as props LIMIT $limit"
        relationships = service.execute_query(rel_query, {"limit": limit})

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
            ET.SubElement(
                graphml,
                "key",
                {"id": "d0", "for": "node", "attr.name": "id", "attr.type": "string"},
            )
            ET.SubElement(
                graphml,
                "key",
                {"id": "d1", "for": "node", "attr.name": "name", "attr.type": "string"},
            )
            ET.SubElement(
                graphml,
                "key",
                {"id": "d2", "for": "node", "attr.name": "type", "attr.type": "string"},
            )
            ET.SubElement(
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
        for edge_id, rel in enumerate(relationships):
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

        # Pretty print XML
        xml_str = minidom.parseString(ET.tostring(graphml)).toprettyxml(indent="  ")

        return Response(
            xml_str,
            mimetype="application/xml",
            headers={"Content-Disposition": "attachment; filename=graph_export.graphml"},
        )
    except ValidationError as e:
        raise
    except Exception as e:
        logger.error(f"GraphML export error: {str(e)}")
        raise DatabaseError(f"Failed to export GraphML: {str(e)}")


@export_bp.route("/jsonld", methods=["GET"])
def export_jsonld():
    """Export graph as JSON-LD with semantic annotations."""
    service = get_neo4j_service()

    try:
        node_types = (
            request.args.get("node_types", "").split(",") if request.args.get("node_types") else []
        )
        limit = request.args.get("limit", default=5000, type=int)

        if limit < 1 or limit > 50000:
            raise ValidationError("Limit must be between 1 and 50000")

        node_match = "MATCH (n)"
        if node_types and node_types[0]:
            labels_filter = " OR ".join([f"'{nt}' IN labels(n)" for nt in node_types])
            node_match += f" WHERE {labels_filter}"

        query = f"""
        {node_match}
        OPTIONAL MATCH (n)-[r]->(m)
        RETURN n.id as id, labels(n) as labels, properties(n) as props,
               COLLECT({{type: type(r), target: m.id, target_name: m.name}}) as relationships
        LIMIT $limit
        """

        result = service.execute_query(query, {"limit": limit})

        jsonld = {
            "@context": {
                "@vocab": "http://www.omg.org/spec/UML/20131001/",
                "uml": "http://www.omg.org/spec/UML/20131001/",
                "id": "@id",
                "type": "@type",
            },
            "@graph": [
                {
                    "@id": f"urn:uuid:{r['id']}",
                    "@type": r["labels"],
                    "properties": r["props"],
                    "relationships": [rel for rel in r["relationships"] if rel.get("target")],
                }
                for r in result
            ],
        }

        return Response(
            json.dumps(jsonld, indent=2),
            mimetype="application/ld+json",
            headers={"Content-Disposition": "attachment; filename=graph_export.jsonld"},
        )
    except ValidationError as e:
        raise
    except Exception as e:
        logger.error(f"JSON-LD export error: {str(e)}")
        raise DatabaseError(f"Failed to export JSON-LD: {str(e)}")


@export_bp.route("/csv", methods=["GET"])
def export_csv():
    """Export nodes as CSV. Query params: node_type (required), properties (comma-separated, optional)"""
    service = get_neo4j_service()

    try:
        node_type = request.args.get("node_type")
        if not node_type:
            raise ValidationError("node_type parameter is required")

        properties = (
            request.args.get("properties", "").split(",") if request.args.get("properties") else []
        )
        limit = request.args.get("limit", default=10000, type=int)

        if limit < 1 or limit > 50000:
            raise ValidationError("Limit must be between 1 and 50000")

        query = f"MATCH (n:{node_type}) RETURN properties(n) as props LIMIT $limit"
        result = service.execute_query(query, {"limit": limit})

        if not result:
            raise NotFoundError(f"No {node_type} nodes found")

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
    except (ValidationError, NotFoundError) as e:
        raise
    except Exception as e:
        logger.error(f"CSV export error: {str(e)}")
        raise DatabaseError(f"Failed to export CSV: {str(e)}")


@export_bp.route("/step", methods=["GET"])
def export_step():
    """Export as STEP AP242 format (ISO 10303-242)."""
    service = get_neo4j_service()

    try:
        limit = request.args.get("limit", default=1000, type=int)

        if limit < 1 or limit > 10000:
            raise ValidationError("Limit must be between 1 and 10000")

        query = """
        MATCH (c:Class)
        OPTIONAL MATCH (c)-[:HAS_ATTRIBUTE]->(p:Property)
        OPTIONAL MATCH (p)-[:TYPED_BY]->(type)
        RETURN c.id as class_id, c.name as class_name,
               COLLECT({name: p.name, type: type.name, lower: p.lower, upper: p.upper}) as attributes
        ORDER BY c.name
        LIMIT $limit
        """

        result = service.execute_query(query, {"limit": limit})

        step_lines = [
            "ISO-10303-21;",
            "HEADER;",
            "FILE_DESCRIPTION(('MBSE Model Export'), '2;1');",
            "FILE_NAME('model_export.stp', '2025-12-07T00:00:00', ('Author'), ('Organization'), 'Neo4j MBSE Exporter', 'Neo4j', '');",
            "FILE_SCHEMA(('AP242'));",
            "ENDSEC;",
            "DATA;",
        ]

        for entity_id, record in enumerate(result, start=1):
            class_name = (record["class_name"] or "UNNAMED_CLASS").replace(" ", "_").upper()
            attributes = [attr for attr in record["attributes"] if attr.get("name")]
            attr_values = [f"'{attr['name']}'" for attr in attributes]
            step_lines.append(
                f"#{entity_id} = {class_name}({', '.join(attr_values) if attr_values else ''});"
            )

        step_lines.extend(["ENDSEC;", "END-ISO-10303-21;"])
        step_content = "\n".join(step_lines)

        return Response(
            step_content,
            mimetype="application/step",
            headers={"Content-Disposition": "attachment; filename=model_export.stp"},
        )
    except ValidationError as e:
        raise
    except Exception as e:
        logger.error(f"STEP export error: {str(e)}")
        raise DatabaseError(f"Failed to export STEP: {str(e)}")
