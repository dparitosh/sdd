"""XMI file parser for ISO 10303 SMRL"""

from pathlib import Path
from typing import Any, Dict, List

from loguru import logger
from lxml import etree


class XMIParser:
    """Parser for XMI files following ISO 10303 SMRL specification"""

    def __init__(self):
        """Initialize XMI parser"""
        self.namespaces = {
            "xmi": "http://www.omg.org/XMI",
            "uml": "http://www.omg.org/spec/UML/20131001",
            "smrl": "http://www.omg.org/spec/SysML/20150301/SysML",
        }

    def parse(self, file_path: Path) -> Dict[str, Any]:
        """
        Parse an XMI file

        Args:
            file_path: Path to the XMI file

        Returns:
            Parsed data structure with nodes and relationships
        """
        logger.info(f"Parsing XMI file: {file_path}")

        try:
            tree = etree.parse(str(file_path))
            root = tree.getroot()

            # Extract nodes and relationships
            nodes = self._extract_nodes(root)
            relationships = self._extract_relationships(root)

            logger.info(f"Extracted {len(nodes)} nodes and {len(relationships)} relationships")

            return {"source_file": str(file_path), "nodes": nodes, "relationships": relationships}

        except Exception as e:
            logger.error(f"Failed to parse XMI file {file_path}: {e}")
            raise

    def _extract_nodes(self, root: etree.Element) -> List[Dict[str, Any]]:
        """
        Extract nodes from XMI root element

        Args:
            root: XMI root element

        Returns:
            List of node dictionaries
        """
        nodes = []

        # Find all UML/SysML elements with xmi:type
        for element in root.xpath(".//*[@*[local-name()='type']]"):
            xmi_type = element.get("{http://www.omg.org/spec/XMI/20131001}type")

            # Filter for main modeling elements
            if xmi_type and any(
                t in xmi_type
                for t in [
                    "Class",
                    "Package",
                    "Property",
                    "Association",
                    "Port",
                    "InstanceSpecification",
                    "Component",
                    "Block",
                ]
            ):
                node = self._element_to_node(element)
                if node:
                    nodes.append(node)

        # Also find elements by tag name (for elements without xmi:type)
        try:
            for element in root.xpath(
                ".//uml:Class | .//uml:Package | .//uml:Component",
                namespaces={"uml": "http://www.omg.org/spec/UML/20131001"},
            ):
                node = self._element_to_node(element)
                if node and not any(
                    n["properties"].get("id") == node["properties"].get("id") for n in nodes
                ):
                    nodes.append(node)
        except Exception:
            pass  # Namespace not found

        return nodes

    def _element_to_node(self, element: etree.Element) -> Dict[str, Any]:
        """
        Convert XML element to node dictionary

        Args:
            element: XML element

        Returns:
            Node dictionary
        """
        # Get element attributes
        xmi_id = element.get("{http://www.omg.org/spec/XMI/20131001}id") or element.get("id")
        xmi_type = (
            element.get("{http://www.omg.org/spec/XMI/20131001}type") or element.tag.split("}")[-1]
        )
        name = element.get("name", "")

        # Generate ID if missing
        if not xmi_id:
            # Use a combination of type and name as fallback
            xmi_id = f"{xmi_type}_{name}" if name else f"{xmi_type}_{id(element)}"

        # Determine node label based on type
        label = self._determine_label(xmi_type)

        # Extract properties
        properties = {"id": xmi_id, "type": xmi_type, "name": name}

        # Add additional attributes
        for key, value in element.attrib.items():
            if key not in ["id", "type", "name"] and not key.startswith("{"):
                properties[key] = value

        return {"label": label, "properties": properties}

    def _determine_label(self, xmi_type: str) -> str:
        """
        Determine Neo4j node label from XMI type

        Args:
            xmi_type: XMI element type

        Returns:
            Neo4j node label
        """
        type_lower = xmi_type.lower()

        if "system" in type_lower:
            return "System"
        elif "component" in type_lower or "block" in type_lower:
            return "Component"
        elif "requirement" in type_lower:
            return "Requirement"
        elif "interface" in type_lower or "port" in type_lower:
            return "Interface"
        elif "parameter" in type_lower or "property" in type_lower:
            return "Parameter"
        else:
            return "Element"

    def _extract_relationships(self, root: etree.Element) -> List[Dict[str, Any]]:
        """
        Extract relationships from XMI root element

        Args:
            root: XMI root element

        Returns:
            List of relationship dictionaries
        """
        relationships = []

        # Find elements with references to other elements
        for element in root.xpath(
            ".//*[@*[local-name()='idref'] or @*[contains(local-name(), 'ref')]]"
        ):
            rels = self._element_to_relationships(element)
            relationships.extend(rels)

        return relationships

    def _element_to_relationships(self, element: etree.Element) -> List[Dict[str, Any]]:
        """
        Convert XML element to relationship dictionaries

        Args:
            element: XML element

        Returns:
            List of relationship dictionaries
        """
        relationships = []
        source_id = element.get("{http://www.omg.org/XMI}id") or element.get("id")

        if not source_id:
            return relationships

        # Check for idref or other reference attributes
        for key, value in element.attrib.items():
            if "idref" in key.lower() or "ref" in key.lower():
                rel_type = self._determine_relationship_type(key)
                relationships.append(
                    {
                        "from_label": "Element",
                        "from_props": {"id": source_id},
                        "type": rel_type,
                        "to_label": "Element",
                        "to_props": {"id": value},
                        "properties": {},
                    }
                )

        return relationships

    def _determine_relationship_type(self, attr_name: str) -> str:
        """
        Determine relationship type from attribute name

        Args:
            attr_name: Attribute name

        Returns:
            Relationship type
        """
        attr_lower = attr_name.lower()

        if "component" in attr_lower or "part" in attr_lower:
            return "HAS_COMPONENT"
        elif "requirement" in attr_lower:
            return "SATISFIES"
        elif "interface" in attr_lower or "port" in attr_lower:
            return "CONNECTS_TO"
        elif "parameter" in attr_lower or "property" in attr_lower:
            return "HAS_PARAMETER"
        else:
            return "RELATES_TO"
