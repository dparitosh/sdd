"""Neo4j database connection management"""

import os
from typing import Any, Dict, List, Optional

from loguru import logger
from neo4j import Driver, GraphDatabase, Session


class Neo4jConnection:
    """Neo4j database connection manager"""

    def __init__(self, uri: str, user: str, password: str, database: Optional[str] = None):
        """
        Initialize Neo4j connection

        Args:
            uri: Neo4j connection URI
            user: Neo4j username
            password: Neo4j password
            database: Neo4j database name (defaults to NEO4J_DATABASE env var or 'neo4j')
        """
        self.uri = uri
        self.user = user
        self.password = password
        self.database = database or os.getenv('NEO4J_DATABASE', 'neo4j')
        self._driver: Optional[Driver] = None

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

    def connect(self):
        """Establish connection to Neo4j"""
        try:
            self._driver = GraphDatabase.driver(
                self.uri, auth=(self.user, self.password)
            )
            logger.debug("Neo4j driver created")
        except Exception as e:
            logger.error(f"Failed to create Neo4j driver: {e}")
            raise

    def close(self):
        """Close the Neo4j connection"""
        if self._driver:
            self._driver.close()
            logger.debug("Neo4j connection closed")

    def verify_connection(self) -> bool:
        """
        Verify the connection to Neo4j

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            with self._driver.session(database=self.database) as session:
                result = session.run("RETURN 1 AS num")
                record = result.single()
                return record["num"] == 1
        except Exception as e:
            logger.error(f"Connection verification failed: {e}")
            return False

    def execute_query(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict]:
        """
        Execute a Cypher query

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            List of result records as dictionaries
        """
        if not self._driver:
            raise RuntimeError("Not connected to Neo4j")

        with self._driver.session(database=self.database) as session:
            result = session.run(query, parameters or {})
            return [dict(record) for record in result]

    def execute_write(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Execute a write transaction

        Args:
            query: Cypher query string
            parameters: Query parameters
        """
        if not self._driver:
            raise RuntimeError("Not connected to Neo4j")

        def _write_tx(tx, query, parameters):
            tx.run(query, parameters)

        with self._driver.session(database=self.database) as session:
            session.execute_write(_write_tx, query, parameters or {})

    def create_node(self, label: str, properties: Dict[str, Any]) -> None:
        """
        Create a node in Neo4j

        Args:
            label: Node label
            properties: Node properties
        """
        props_str = ", ".join([f"{k}: ${k}" for k in properties.keys()])
        query = f"CREATE (n:{label} {{{props_str}}})"
        self.execute_write(query, properties)

    def create_relationship(
        self,
        from_label: str,
        from_props: Dict[str, Any],
        rel_type: str,
        to_label: str,
        to_props: Dict[str, Any],
        rel_props: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Create a relationship between two nodes

        Args:
            from_label: Source node label
            from_props: Source node properties for matching
            rel_type: Relationship type
            to_label: Target node label
            to_props: Target node properties for matching
            rel_props: Relationship properties
        """
        from_match = " AND ".join([f"from.{k} = $from_{k}" for k in from_props.keys()])
        to_match = " AND ".join([f"to.{k} = $to_{k}" for k in to_props.keys()])

        rel_props_str = ""
        if rel_props:
            props_str = ", ".join([f"{k}: $rel_{k}" for k in rel_props.keys()])
            rel_props_str = f" {{{props_str}}}"

        query = f"""
        MATCH (from:{from_label}) WHERE {from_match}
        MATCH (to:{to_label}) WHERE {to_match}
        CREATE (from)-[r:{rel_type}{rel_props_str}]->(to)
        """

        parameters = {}
        parameters.update({f"from_{k}": v for k, v in from_props.items()})
        parameters.update({f"to_{k}": v for k, v in to_props.items()})
        if rel_props:
            parameters.update({f"rel_{k}": v for k, v in rel_props.items()})

        self.execute_write(query, parameters)

    @property
    def driver(self) -> Driver:
        """Get the Neo4j driver instance"""
        if not self._driver:
            raise RuntimeError("Not connected to Neo4j")
        return self._driver
