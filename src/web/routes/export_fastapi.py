"""
Export Routes (FastAPI)
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
from typing import List, Optional
from xml.dom import minidom

from fastapi import APIRouter, HTTPException, Query, Response, status
from loguru import logger
from pydantic import BaseModel

from src.web.services import get_neo4j_service

# ============================================================================
# ROUTER CONFIGURATION
# ============================================================================

router = APIRouter(prefix="/export", tags=["Data Export"])


# ============================================================================
# PYDANTIC MODELS (for documentation)
# ============================================================================


class ExportFormat(BaseModel):
    format: str
    description: str
    mime_type: str
    extension: str


# ============================================================================
# GRAPHML EXPORT ENDPOINT
# ============================================================================


@router.get("/graphml")
async def export_graphml(
    node_types: Optional[str] = Query(None, description="Comma-separated list of node types to include"),
    include_properties: bool = Query(True, description="Include node properties in export"),
    limit: int = Query(10000, ge=1, le=50000, description="Maximum number of nodes")
):
    """
    Export graph as GraphML XML format
    
    GraphML is an XML-based format for graphs, widely supported by graph visualization tools.
    
    Args:
        node_types: Comma-separated node types to filter (e.g., "Class,Package")
        include_properties: Include node properties in export
        limit: Maximum nodes to export (1-50000)
        
    Returns:
        GraphML XML file as downloadable attachment
    """
    try:
        neo4j = get_neo4j_service()

        node_types_list = node_types.split(",") if node_types else []

        # Build query
        node_match = "MATCH (n)"
        if node_types_list and node_types_list[0]:
            labels_filter = " OR ".join([f"'{nt}' IN labels(n)" for nt in node_types_list])
            node_match += f" WHERE {labels_filter}"

        # Get nodes
        node_query = f"{node_match} RETURN n.id as id, labels(n) as labels, properties(n) as props LIMIT $limit"
        nodes = neo4j.execute_query(node_query, {"limit": limit})

        # Get relationships
        rel_query = f"{node_match} MATCH (n)-[r]->(m) RETURN n.id as source, m.id as target, type(r) as type, properties(r) as props LIMIT $limit"
        relationships = neo4j.execute_query(rel_query, {"limit": limit})

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
            content=xml_str,
            media_type="application/xml",
            headers={"Content-Disposition": "attachment; filename=graph_export.graphml"},
        )

    except Exception as e:
        logger.error(f"GraphML export error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export GraphML: {str(e)}"
        )


# ============================================================================
# JSON-LD EXPORT ENDPOINT
# ============================================================================


@router.get("/jsonld")
async def export_jsonld(
    node_types: Optional[str] = Query(None, description="Comma-separated list of node types to include"),
    limit: int = Query(5000, ge=1, le=50000, description="Maximum number of nodes")
):
    """
    Export graph as JSON-LD with semantic annotations
    
    JSON-LD (Linked Data) provides semantic web compatibility with RDF standards.
    
    Args:
        node_types: Comma-separated node types to filter
        limit: Maximum nodes to export (1-50000)
        
    Returns:
        JSON-LD file as downloadable attachment
    """
    try:
        neo4j = get_neo4j_service()

        node_types_list = node_types.split(",") if node_types else []

        node_match = "MATCH (n)"
        if node_types_list and node_types_list[0]:
            labels_filter = " OR ".join([f"'{nt}' IN labels(n)" for nt in node_types_list])
            node_match += f" WHERE {labels_filter}"

        query = f"""
        {node_match}
        OPTIONAL MATCH (n)-[r]->(m)
        RETURN n.id as id, labels(n) as labels, properties(n) as props,
               COLLECT({{type: type(r), target: m.id, target_name: m.name}}) as relationships
        LIMIT $limit
        """

        result = neo4j.execute_query(query, {"limit": limit})

        # Build JSON-LD with proper serialization
        graph_data = []
        for r in result:
            # Convert datetime objects to ISO format strings
            props = {}
            for key, value in r["props"].items():
                if hasattr(value, 'isoformat'):
                    props[key] = value.isoformat()
                else:
                    props[key] = value
            
            graph_data.append({
                "@id": f"urn:uuid:{r['id']}",
                "@type": r["labels"],
                "properties": props,
                "relationships": [rel for rel in r["relationships"] if rel.get("target")],
            })

        jsonld = {
            "@context": {
                "@vocab": "http://www.omg.org/spec/UML/20131001/",
                "uml": "http://www.omg.org/spec/UML/20131001/",
                "id": "@id",
                "type": "@type",
            },
            "@graph": graph_data,
        }

        return Response(
            content=json.dumps(jsonld, indent=2),
            media_type="application/ld+json",
            headers={"Content-Disposition": "attachment; filename=graph_export.jsonld"},
        )

    except Exception as e:
        logger.error(f"JSON-LD export error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export JSON-LD: {str(e)}"
        )


# ============================================================================
# CSV EXPORT ENDPOINT
# ============================================================================


@router.get("/csv")
async def export_csv(
    node_type: Optional[str] = Query(None, description="Node type to export (optional, exports all if not specified)"),
    properties: Optional[str] = Query(None, description="Comma-separated list of properties to include"),
    limit: int = Query(10000, ge=1, le=50000, description="Maximum number of nodes")
):
    """
    Export nodes as CSV
    
    Exports nodes of a specific type as a CSV file in a ZIP archive.
    
    Args:
        node_type: Node type to export (e.g., "Class", "Package")
        properties: Comma-separated properties to include (if not specified, includes all)
        limit: Maximum nodes to export (1-50000)
        
    Returns:
        ZIP file containing CSV as downloadable attachment
        
    Raises:
        HTTPException 404: No nodes of the specified type found
    """
    try:
        neo4j = get_neo4j_service()

        if node_type:
            query = f"MATCH (n:{node_type}) RETURN properties(n) as props, labels(n)[0] as label LIMIT $limit"
        else:
            query = "MATCH (n) RETURN properties(n) as props, labels(n)[0] as label LIMIT $limit"
        
        result = neo4j.execute_query(query, {"limit": limit})

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No nodes found"
            )

        # Determine columns
        all_keys = set()
        for record in result:
            all_keys.update(record["props"].keys())
        columns = sorted(list(all_keys))
        
        if properties:
            properties_list = properties.split(",")
            columns = [c for c in columns if c in properties_list]

        # Create CSV
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        for record in result:
            props = record["props"]
            row = {col: props.get(col, "") for col in columns}
            writer.writerow(row)

        # Create ZIP file
        filename_base = node_type if node_type else "all_nodes"
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr(f"{filename_base}_export.csv", output.getvalue())
        zip_buffer.seek(0)

        return Response(
            content=zip_buffer.getvalue(),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={filename_base}_export.zip"},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"CSV export error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export CSV: {str(e)}"
        )


# ============================================================================
# STEP EXPORT ENDPOINT
# ============================================================================


@router.get("/step")
async def export_step(
    limit: int = Query(1000, ge=1, le=10000, description="Maximum number of classes to export")
):
    """
    Export as STEP AP242 format (ISO 10303-242)
    
    Exports classes with attributes in ISO STEP format for CAD/PLM interoperability.
    
    Args:
        limit: Maximum classes to export (1-10000)
        
    Returns:
        STEP file (.stp) as downloadable attachment
    """
    try:
        neo4j = get_neo4j_service()

        query = """
        MATCH (c:Class)
        OPTIONAL MATCH (c)-[:HAS_ATTRIBUTE]->(p:Property)
        OPTIONAL MATCH (p)-[:TYPED_BY]->(type)
        RETURN c.id as class_id, c.name as class_name,
               COLLECT({name: p.name, type: type.name, lower: p.lower, upper: p.upper}) as attributes
        ORDER BY c.name
        LIMIT $limit
        """

        result = neo4j.execute_query(query, {"limit": limit})

        step_lines = [
            "ISO-10303-21;",
            "HEADER;",
            "FILE_DESCRIPTION(('MBSE Model Export'), '2;1');",
            "FILE_NAME('model_export.stp', '2025-12-13T00:00:00', ('Author'), ('Organization'), 'Neo4j MBSE Exporter', 'Neo4j', '');",
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
            content=step_content,
            media_type="application/step",
            headers={"Content-Disposition": "attachment; filename=model_export.stp"},
        )

    except Exception as e:
        logger.error(f"STEP export error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export STEP: {str(e)}"
        )
