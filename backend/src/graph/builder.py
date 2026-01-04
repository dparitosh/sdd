"""Graph building functionality"""

from typing import Any, Dict, List

from loguru import logger

from .connection import Neo4jConnection


class GraphBuilder:
    """Build knowledge graph in Neo4j from parsed data"""

    def __init__(self, connection: Neo4jConnection):
        """
        Initialize graph builder

        Args:
            connection: Neo4j connection instance
        """
        self.conn = connection

    def build_graph(self, data: Dict[str, Any]) -> None:
        """
        Build graph from parsed XMI data

        Args:
            data: Parsed XMI data structure
        """
        logger.info("Building knowledge graph...")

        # Create indexes for better performance
        self._create_indexes()

        # Process nodes
        if "nodes" in data:
            self._create_nodes(data["nodes"])

        # Process relationships
        if "relationships" in data:
            self._create_relationships(data["relationships"])

        logger.info("Knowledge graph built successfully")

    def _create_indexes(self) -> None:
        """Create database indexes for performance"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS FOR (n:System) ON (n.id)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Component) ON (n.id)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Requirement) ON (n.id)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Interface) ON (n.id)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Parameter) ON (n.id)",
        ]

        for index_query in indexes:
            try:
                self.conn.execute_write(index_query)
            except Exception as e:
                logger.warning(f"Index creation warning: {e}")

    def _create_nodes(self, nodes: List[Dict[str, Any]]) -> None:
        """
        Create nodes in the graph

        Args:
            nodes: List of node definitions
        """
        logger.info(f"Creating {len(nodes)} nodes...")

        for node in nodes:
            label = node.get("label", "Node")
            properties = node.get("properties", {})

            try:
                self.conn.create_node(label, properties)
            except Exception as e:
                logger.error(
                    f"Failed to create node {properties.get('id', 'unknown')}: {e}"
                )

    def _create_relationships(self, relationships: List[Dict[str, Any]]) -> None:
        """
        Create relationships in the graph

        Args:
            relationships: List of relationship definitions
        """
        logger.info(f"Creating {len(relationships)} relationships...")

        for rel in relationships:
            try:
                self.conn.create_relationship(
                    from_label=rel["from_label"],
                    from_props=rel["from_props"],
                    rel_type=rel["type"],
                    to_label=rel["to_label"],
                    to_props=rel["to_props"],
                    rel_props=rel.get("properties"),
                )
            except Exception as e:
                logger.error(f"Failed to create relationship: {e}")

    def clear_graph(self) -> None:
        """Clear all nodes and relationships from the graph"""
        logger.warning("Clearing all graph data...")
        self.conn.execute_write("MATCH (n) DETACH DELETE n")
        logger.info("Graph cleared")
