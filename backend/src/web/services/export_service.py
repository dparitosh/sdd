"""
Advanced export service for multiple formats
Supports JSON, XML, CSV, GraphML, RDF, and SysML/PlantUML
"""

import json
import csv
from io import StringIO
from typing import Dict, Any, Optional
from datetime import datetime
from xml.etree import ElementTree as ET
from xml.dom import minidom


class ExportService:
    """Service for exporting graph data in various formats"""

    def __init__(self, neo4j_service):
        self.neo4j_service = neo4j_service

    def export_json(self, query: str, params: Optional[Dict] = None) -> str:
        """
        Export query results as JSON

        Args:
            query: Cypher query
            params: Query parameters

        Returns:
            JSON string
        """
        results = self.neo4j_service.execute_query(query, params or {})

        export_data = {
            "metadata": {
                "exported_at": datetime.now().isoformat(),
                "format": "json",
                "query": query,
            },
            "data": results,
        }

        return json.dumps(export_data, indent=2)

    def export_csv(self, query: str, params: Optional[Dict] = None) -> str:
        """
        Export query results as CSV

        Args:
            query: Cypher query
            params: Query parameters

        Returns:
            CSV string
        """
        results = self.neo4j_service.execute_query(query, params or {})

        if not results:
            return ""

        # Get column names from first result
        columns = list(results[0].keys())

        # Create CSV
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()

        for row in results:
            # Convert complex objects to strings
            clean_row = {}
            for key, value in row.items():
                if isinstance(value, (dict, list)):
                    clean_row[key] = json.dumps(value)
                else:
                    clean_row[key] = value
            writer.writerow(clean_row)

        return output.getvalue()

    def export_xml(self, query: str, params: Optional[Dict] = None) -> str:
        """
        Export query results as XML

        Args:
            query: Cypher query
            params: Query parameters

        Returns:
            XML string
        """
        results = self.neo4j_service.execute_query(query, params or {})

        # Create root element
        root = ET.Element("export")
        metadata = ET.SubElement(root, "metadata")
        ET.SubElement(metadata, "exported_at").text = datetime.now().isoformat()
        ET.SubElement(metadata, "format").text = "xml"
        ET.SubElement(metadata, "count").text = str(len(results))

        # Add data
        data = ET.SubElement(root, "data")

        for idx, record in enumerate(results):
            record_elem = ET.SubElement(data, "record", id=str(idx))

            for key, value in record.items():
                field = ET.SubElement(record_elem, "field", name=key)

                if isinstance(value, (dict, list)):
                    field.text = json.dumps(value)
                else:
                    field.text = str(value) if value is not None else ""

        # Pretty print
        xml_str = ET.tostring(root, encoding="unicode")
        dom = minidom.parseString(xml_str)
        return dom.toprettyxml(indent="  ")

    def export_graphml(self) -> str:
        """
        Export entire graph as GraphML format
        GraphML is widely supported by graph visualization tools

        Returns:
            GraphML string
        """
        # Get all nodes
        nodes_query = """
        MATCH (n)
        RETURN id(n) as id, labels(n) as labels, properties(n) as properties
        """
        nodes = self.neo4j_service.execute_query(nodes_query)

        # Get all relationships
        rels_query = """
        MATCH (a)-[r]->(b)
        RETURN id(a) as source, id(b) as target, type(r) as type, properties(r) as properties
        """
        relationships = self.neo4j_service.execute_query(rels_query)

        # Create GraphML
        root = ET.Element("graphml", xmlns="http://graphml.graphdrawing.org/xmlns")
        graph = ET.SubElement(root, "graph", id="G", edgedefault="directed")

        # Add nodes
        for node in nodes:
            node_elem = ET.SubElement(graph, "node", id=str(node["id"]))

            # Add labels
            if node["labels"]:
                ET.SubElement(node_elem, "data", key="labels").text = ",".join(
                    node["labels"]
                )

            # Add properties
            for prop_key, prop_value in (node["properties"] or {}).items():
                ET.SubElement(node_elem, "data", key=prop_key).text = str(prop_value)

        # Add edges
        for rel in relationships:
            edge_elem = ET.SubElement(
                graph, "edge", source=str(rel["source"]), target=str(rel["target"])
            )
            ET.SubElement(edge_elem, "data", key="type").text = rel["type"]

            # Add properties
            for prop_key, prop_value in (rel["properties"] or {}).items():
                ET.SubElement(edge_elem, "data", key=prop_key).text = str(prop_value)

        xml_str = ET.tostring(root, encoding="unicode")
        dom = minidom.parseString(xml_str)
        return dom.toprettyxml(indent="  ")

    def export_rdf(self) -> str:
        """
        Export graph as RDF/Turtle format
        Useful for semantic web applications

        Returns:
            RDF Turtle string
        """
        # Get all nodes and relationships
        query = """
        MATCH (n)-[r]->(m)
        RETURN 
            id(n) as subject_id,
            labels(n) as subject_labels,
            properties(n) as subject_props,
            type(r) as predicate,
            properties(r) as predicate_props,
            id(m) as object_id,
            labels(m) as object_labels,
            properties(m) as object_props
        """
        results = self.neo4j_service.execute_query(query)

        # Build RDF
        rdf_lines = [
            "@prefix mbse: <http://mbse.example.org/ontology#> .",
            "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
            "",
        ]

        for record in results:
            subject = f"mbse:node{record['subject_id']}"
            predicate = f"mbse:{record['predicate']}"
            obj = f"mbse:node{record['object_id']}"

            rdf_lines.append(f"{subject} {predicate} {obj} .")

            # Add type information
            if record["subject_labels"]:
                for label in record["subject_labels"]:
                    rdf_lines.append(f"{subject} rdf:type mbse:{label} .")

            # Add properties as literals
            for key, value in (record["subject_props"] or {}).items():
                rdf_lines.append(f'{subject} mbse:{key} "{value}" .')

        return "\n".join(rdf_lines)

    def export_plantuml(self, package_name: Optional[str] = None) -> str:
        """
        Export as PlantUML class diagram

        Args:
            package_name: Optional package to filter by

        Returns:
            PlantUML string
        """
        # Get classes and their properties
        if package_name:
            query = """
            MATCH (p:Package {name: $package})-[:contains]->(c:Class)
            OPTIONAL MATCH (c)-[:hasProperty]->(prop:Property)
            RETURN c.name as class_name, collect(prop.name) as properties
            """
            params = {"package": package_name}
        else:
            query = """
            MATCH (c:Class)
            OPTIONAL MATCH (c)-[:hasProperty]->(prop:Property)
            RETURN c.name as class_name, collect(prop.name) as properties
            LIMIT 50
            """
            params = {}

        results = self.neo4j_service.execute_query(query, params)

        # Build PlantUML
        lines = ["@startuml", ""]

        for record in results:
            class_name = record["class_name"]
            properties = record["properties"] or []

            lines.append(f"class {class_name} {{")
            for prop in properties:
                if prop:  # Skip None values
                    lines.append(f"  + {prop}")
            lines.append("}")
            lines.append("")

        # Get relationships
        rel_query = """
        MATCH (c1:Class)-[r]->(c2:Class)
        RETURN c1.name as from, type(r) as rel_type, c2.name as to
        LIMIT 100
        """
        relationships = self.neo4j_service.execute_query(rel_query)

        for rel in relationships:
            from_class = rel["from"]
            to_class = rel["to"]
            rel_type = rel["rel_type"]

            # Map relationship types to PlantUML arrows
            if rel_type == "extends":
                lines.append(f"{from_class} --|> {to_class}")
            elif rel_type == "implements":
                lines.append(f"{from_class} ..|> {to_class}")
            elif rel_type == "contains":
                lines.append(f"{from_class} *-- {to_class}")
            else:
                lines.append(f"{from_class} --> {to_class} : {rel_type}")

        lines.append("")
        lines.append("@enduml")

        return "\n".join(lines)

    def export_cytoscape(self) -> Dict[str, Any]:
        """
        Export in Cytoscape.js format
        Ready for web-based graph visualization

        Returns:
            Cytoscape JSON structure
        """
        # Get nodes
        nodes_query = """
        MATCH (n)
        RETURN id(n) as id, labels(n) as labels, properties(n) as properties
        LIMIT 1000
        """
        nodes = self.neo4j_service.execute_query(nodes_query)

        # Get edges
        edges_query = """
        MATCH (a)-[r]->(b)
        RETURN id(r) as id, id(a) as source, id(b) as target, type(r) as type
        LIMIT 5000
        """
        edges = self.neo4j_service.execute_query(edges_query)

        # Build Cytoscape format
        elements = []

        # Add nodes
        for node in nodes:
            elements.append(
                {
                    "data": {
                        "id": str(node["id"]),
                        "label": node["properties"].get("name", f"Node {node['id']}"),
                        "type": ",".join(node["labels"]) if node["labels"] else "Node",
                        **node["properties"],
                    }
                }
            )

        # Add edges
        for edge in edges:
            elements.append(
                {
                    "data": {
                        "id": str(edge["id"]),
                        "source": str(edge["source"]),
                        "target": str(edge["target"]),
                        "label": edge["type"],
                    }
                }
            )

        return {"elements": elements}


# Example FastAPI routes for export:
#
# from fastapi import APIRouter
# from pydantic import BaseModel
# from starlette.responses import Response
#
# from src.web.services.export_service import ExportService
# from src.web.services.services import get_neo4j_service
#
#
# router = APIRouter(prefix="/api/export", tags=["export"])
#
#
# class ExportRequest(BaseModel):
#     query: str
#     params: dict = {}
#
#
# @router.post("/json")
# def export_json(req: ExportRequest):
#     service = ExportService(get_neo4j_service())
#     result = service.export_json(req.query, req.params)
#     return Response(result, media_type="application/json")
#
#
# @router.post("/csv")
# def export_csv(req: ExportRequest):
#     service = ExportService(get_neo4j_service())
#     result = service.export_csv(req.query, req.params)
#     return Response(
#         result,
#         media_type="text/csv",
#         headers={"Content-Disposition": "attachment; filename=export.csv"},
#     )
