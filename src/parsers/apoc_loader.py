"""
XMI to Neo4j loader using local XML parsing with lxml
Parses XMI using XPath and loads data into Neo4j with proper UML/SysML labels
"""

from pathlib import Path

import pandas as pd
from loguru import logger
from lxml import etree

from graph.connection import Neo4jConnection


class APOCXMILoader:
    """Load XMI files into Neo4j by parsing locally with lxml"""

    def __init__(self, connection: Neo4jConnection):
        """Initialize loader"""
        self.conn = connection
        self.namespaces = {
            "xmi": "http://www.omg.org/XMI",
            "uml": "http://www.eclipse.org/uml2/5.0.0/UML",
            "xsi": "http://www.w3.org/2001/XMLSchema-instance",
        }

    def load_xmi_file(self, xmi_file_path: Path) -> dict:
        """
        Load XMI file into Neo4j by parsing with lxml

        Args:
            xmi_file_path: Path to XMI file

        Returns:
            Statistics about loaded data
        """
        logger.info(f"Parsing XMI file: {xmi_file_path}")

        # Parse XML
        tree = etree.parse(str(xmi_file_path))
        root = tree.getroot()

        stats = {}

        # Step 1: Extract and create element nodes
        logger.info("Extracting elements from XMI...")
        elements_df = self._extract_elements(root)
        logger.info(f"Found {len(elements_df)} elements")

        nodes_created = self._create_element_nodes(elements_df)
        stats["nodes_created"] = nodes_created
        logger.info(f"Created {nodes_created} nodes in Neo4j")

        # Step 2: Extract and create relationships
        logger.info("Extracting relationships from XMI...")
        relationships_df = self._extract_relationships(root)
        logger.info(f"Found {len(relationships_df)} relationships")

        rels_created = self._create_relationships(relationships_df)
        stats["relationships_created"] = rels_created
        logger.info(f"Created {rels_created} relationships in Neo4j")

        return stats

    def _extract_elements(self, root: etree.Element) -> pd.DataFrame:
        """Extract all elements including nested ones with proper name extraction"""
        elements = []

        ns = {
            "xmi": "http://www.omg.org/spec/XMI/20131001",
            "uml": "http://www.omg.org/spec/UML/20131001",
        }

        # Find all elements with xmi:type attribute (top-level and nested)
        xpath_query = "//*[@xmi:type]"
        all_elements = root.xpath(xpath_query, namespaces=ns)

        logger.info(f"Found {len(all_elements)} elements with xmi:type")

        for elem in all_elements:
            element_type = elem.get("{http://www.omg.org/spec/XMI/20131001}type")
            element_id = elem.get("{http://www.omg.org/spec/XMI/20131001}id")

            # Try to get name from attribute first
            element_name = elem.get("name", "")

            # If no name attribute, check for child <name> element
            if not element_name:
                name_elem = elem.find("name")
                if name_elem is not None and name_elem.text:
                    element_name = name_elem.text.strip()

            if element_id and element_type:
                # Extract all attributes
                element_data = {
                    "id": element_id,
                    "type": element_type,
                    "name": element_name if element_name else "Unnamed",
                }

                # Add other scalar attributes
                for key, value in elem.attrib.items():
                    clean_key = key.split("}")[-1]  # Remove namespace
                    if clean_key not in ["id", "type", "name"] and isinstance(value, str):
                        element_data[clean_key] = value

                elements.append(element_data)

        df = pd.DataFrame(elements)
        logger.info(f"Extracted {len(df)} valid elements")
        return df

    def _extract_relationships(self, root: etree.Element) -> pd.DataFrame:
        """Extract relationships from XMI - handles both attributes and child reference elements"""
        relationships = []

        ns = {
            "xmi": "http://www.omg.org/spec/XMI/20131001",
            "uml": "http://www.omg.org/spec/UML/20131001",
        }

        # Extract Associations (memberEnd child elements)
        logger.debug("Extracting Associations...")
        assocs = root.xpath("//*[@xmi:type='uml:Association']", namespaces=ns)
        for assoc in assocs:
            assoc_id = assoc.get("{http://www.omg.org/spec/XMI/20131001}id")

            # Find memberEnd child elements with xmi:idref
            member_ends = assoc.findall("memberEnd")
            member_ids = []
            for member in member_ends:
                idref = member.get("{http://www.omg.org/spec/XMI/20131001}idref")
                if idref:
                    member_ids.append(idref)

            # Create relationships between each pair of members
            if len(member_ids) >= 2:
                # Create bidirectional association
                for i in range(len(member_ids) - 1):
                    relationships.append(
                        {
                            "id": f"{assoc_id}_pair_{i}",
                            "type": "uml:Association",
                            "source_id": member_ids[i],
                            "target_id": member_ids[i + 1],
                        }
                    )

        logger.info(f"Found {len(relationships)} Association relationships")

        # Extract Generalizations (general child element)
        logger.debug("Extracting Generalizations...")
        gens = root.xpath("//*[@xmi:type='uml:Generalization']", namespaces=ns)
        for gen in gens:
            gen_id = gen.get("{http://www.omg.org/spec/XMI/20131001}id")

            # Find general child element with xmi:idref
            general_elem = gen.find("general")
            general_id = None
            if general_elem is not None:
                general_id = general_elem.get("{http://www.omg.org/spec/XMI/20131001}idref")

            # The specific (child class) is the parent of this generalization element
            parent = gen.getparent()
            specific_id = None
            if parent is not None:
                specific_id = parent.get("{http://www.omg.org/spec/XMI/20131001}id")

            if gen_id and specific_id and general_id:
                relationships.append(
                    {
                        "id": gen_id,
                        "type": "uml:Generalization",
                        "source_id": specific_id,  # child class
                        "target_id": general_id,  # parent class
                    }
                )

        logger.info(f"Found {len(gens)} Generalization relationships")

        # Extract Dependencies (client/supplier attributes or child elements)
        logger.debug("Extracting Dependencies...")
        deps = root.xpath("//*[@xmi:type='uml:Dependency']", namespaces=ns)
        for dep in deps:
            dep_id = dep.get("{http://www.omg.org/spec/XMI/20131001}id")

            # Try attributes first
            client_id = dep.get("client")
            supplier_id = dep.get("supplier")

            # If not found, try child elements
            if not client_id:
                client_elem = dep.find("client")
                if client_elem is not None:
                    client_id = client_elem.get("{http://www.omg.org/spec/XMI/20131001}idref")

            if not supplier_id:
                supplier_elem = dep.find("supplier")
                if supplier_elem is not None:
                    supplier_id = supplier_elem.get("{http://www.omg.org/spec/XMI/20131001}idref")

            if dep_id and client_id and supplier_id:
                relationships.append(
                    {
                        "id": dep_id,
                        "type": "uml:Dependency",
                        "source_id": client_id,
                        "target_id": supplier_id,
                    }
                )

        logger.info(f"Found {len(deps)} Dependency relationships")

        df = pd.DataFrame(relationships)
        logger.info(f"Extracted {len(df)} total valid relationships")
        return df

    def _create_element_nodes(self, elements_df: pd.DataFrame) -> int:
        """Create UML/SysML entity nodes in Neo4j from DataFrame"""
        if elements_df.empty:
            return 0

        # Map UML types to node labels
        type_to_label = {
            "uml:Package": "Package",
            "uml:Class": "Class",
            "uml:Interface": "Interface",
            "uml:Component": "Component",
            "uml:Port": "Port",
            "uml:Property": "Property",
            "uml:Operation": "Operation",
            "uml:Parameter": "Parameter",
            "uml:Association": "Association",
            "uml:Generalization": "Generalization",
            "uml:Dependency": "Dependency",
            "uml:Realization": "Realization",
            "uml:Usage": "Usage",
            "uml:Abstraction": "Abstraction",
            "uml:DataType": "DataType",
            "uml:Enumeration": "Enumeration",
            "uml:PrimitiveType": "PrimitiveType",
            "uml:Constraint": "Constraint",
            "uml:Comment": "Comment",
            "uml:Connector": "Connector",
            "uml:ConnectorEnd": "ConnectorEnd",
            "uml:LiteralInteger": "LiteralInteger",
            "uml:LiteralUnlimitedNatural": "LiteralUnlimitedNatural",
            "uml:LiteralString": "LiteralString",
            "uml:LiteralBoolean": "LiteralBoolean",
            "uml:InstanceValue": "InstanceValue",
            "uml:Slot": "Slot",
            "uml:InstanceSpecification": "InstanceSpecification",
            "uml:UseCase": "UseCase",
            "uml:Actor": "Actor",
            "uml:Activity": "Activity",
            "uml:Action": "Action",
            "uml:State": "State",
            "uml:Transition": "Transition",
            "sysml:Block": "Block",
            "sysml:Requirement": "Requirement",
            "sysml:ValueType": "ValueType",
        }

        query = """
        UNWIND $elements AS element
        CALL apoc.create.node([element.label], {
            id: element.id,
            name: element.name,
            umlType: element.umlType
        }) YIELD node
        SET node += element.properties
        RETURN count(node) AS nodesCreated
        """

        try:
            # Prepare data with proper labels
            elements_data = []
            for _, row in elements_df.iterrows():
                uml_type = row["type"]
                label = type_to_label.get(uml_type, "UMLElement")

                # Separate id, name, type from other properties
                properties = {
                    k: v for k, v in row.items() if k not in ["id", "name", "type"] and pd.notna(v)
                }

                elements_data.append(
                    {
                        "id": row["id"],
                        "name": row["name"],
                        "umlType": uml_type,
                        "label": label,
                        "properties": properties,
                    }
                )

            # Execute in batches
            batch_size = 1000
            total_created = 0

            for i in range(0, len(elements_data), batch_size):
                batch = elements_data[i : i + batch_size]
                result = self.conn.execute_query(query, {"elements": batch})
                if result:
                    total_created += result[0].get("nodesCreated", 0)
                logger.debug(
                    f"Processed batch {i//batch_size + 1}, created {result[0].get('nodesCreated', 0)} nodes"
                )

            return total_created
        except Exception as e:
            logger.error(f"Error creating nodes: {e}")
            return 0

    def _create_relationships(self, relationships_df: pd.DataFrame) -> int:
        """Create relationships in Neo4j from DataFrame"""
        if relationships_df.empty:
            return 0

        # Map relationship types to relationship names
        rel_type_map = {
            "uml:Dependency": "DEPENDS_ON",
            "uml:Realization": "REALIZES",
            "uml:Association": "ASSOCIATED_WITH",
            "uml:Generalization": "GENERALIZES",
            "uml:Usage": "USES",
            "uml:Abstraction": "ABSTRACTS",
        }

        query = """
        UNWIND $relationships AS rel
        MATCH (source {id: rel.source_id})
        MATCH (target {id: rel.target_id})
        CALL apoc.create.relationship(source, rel.relType, {
            id: rel.id,
            umlType: rel.umlType
        }, target) YIELD rel AS relationship
        SET relationship += rel.properties
        RETURN count(relationship) AS relationshipsCreated
        """

        try:
            # Prepare data
            relationships_data = []
            for _, row in relationships_df.iterrows():
                uml_type = row["type"]
                rel_type = rel_type_map.get(uml_type, "RELATES_TO")

                properties = {
                    k: v
                    for k, v in row.items()
                    if k not in ["id", "type", "source_id", "target_id"] and pd.notna(v)
                }

                relationships_data.append(
                    {
                        "id": row["id"],
                        "umlType": uml_type,
                        "relType": rel_type,
                        "source_id": row["source_id"],
                        "target_id": row["target_id"],
                        "properties": properties,
                    }
                )

            # Execute in batches
            batch_size = 1000
            total_created = 0

            for i in range(0, len(relationships_data), batch_size):
                batch = relationships_data[i : i + batch_size]
                result = self.conn.execute_query(query, {"relationships": batch})
                if result:
                    total_created += result[0].get("relationshipsCreated", 0)
                logger.debug(f"Processed relationship batch {i//batch_size + 1}")

            return total_created
        except Exception as e:
            logger.error(f"Error creating relationships: {e}")
            return 0

    def clear_graph(self):
        """Clear all nodes and relationships"""
        logger.warning("Clearing graph...")
        query = "MATCH (n) DETACH DELETE n"
        self.conn.execute_write(query)
        logger.info("Graph cleared")
