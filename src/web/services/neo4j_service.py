"""
Neo4j Service Layer - Centralized database operations
Provides connection pooling, query execution, and common database patterns
"""

import os
from typing import Any, Dict, List, Optional

from loguru import logger
from neo4j import GraphDatabase, Session
from neo4j.exceptions import ServiceUnavailable, AuthError, Neo4jError


class Neo4jService:
    """
    Centralized Neo4j database service with connection pooling.
    Provides common query patterns and error handling.
    """

    def __init__(self, uri: str = None, user: str = None, password: str = None, database: str = None):
        """
        Initialize Neo4j service with connection pooling.

        Args:
            uri: Neo4j connection URI (defaults to NEO4J_URI env var)
            user: Neo4j username (defaults to NEO4J_USER env var)
            password: Neo4j password (defaults to NEO4J_PASSWORD env var)
            database: Neo4j database name (defaults to NEO4J_DATABASE env var or 'neo4j')
        """
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "password")
        self.database = database or os.getenv("NEO4J_DATABASE", "neo4j")
        self._driver = None
        self._connection_verified = False

        logger.info(f"Neo4j service configuration: uri={self.uri}, database={self.database}")

    @property
    def driver(self):
        """Lazy driver initialization - creates driver on first access"""
        if self._driver is None:
            try:
                logger.debug(f"Creating Neo4j driver for {self.uri}")
                self._driver = GraphDatabase.driver(
                    self.uri,
                    auth=(self.user, self.password),
                    max_connection_pool_size=50,
                    connection_acquisition_timeout=30,  # Reduced from 60s to fail faster
                    max_transaction_retry_time=15,
                    connection_timeout=10,  # Add explicit connection timeout
                )
                logger.info("Neo4j driver created successfully")
            except Exception as e:
                logger.error(f"Failed to create Neo4j driver: {e}")
                raise ServiceUnavailable(f"Cannot connect to Neo4j at {self.uri}: {e}")
        return self._driver

    def verify_connectivity(self) -> bool:
        """
        Verify connection to Neo4j database.
        Should be called after initialization to ensure database is accessible.
        
        Returns:
            True if connection successful
            
        Raises:
            ServiceUnavailable: If connection fails
            AuthError: If authentication fails
        """
        if self._connection_verified:
            return True
            
        try:
            logger.debug("Verifying Neo4j connectivity...")
            with self.driver.session(database=self.database) as session:
                result = session.run("RETURN 1 AS test")
                record = result.single()
                if record and record["test"] == 1:
                    self._connection_verified = True
                    logger.info(f"✓ Connected to Neo4j database '{self.database}'")
                    return True
                else:
                    raise ServiceUnavailable("Invalid response from Neo4j")
        except AuthError as e:
            logger.error(f"Authentication failed for Neo4j at {self.uri}: {e}")
            raise
        except ServiceUnavailable as e:
            logger.error(f"Neo4j service unavailable at {self.uri}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to verify Neo4j connectivity: {e}")
            raise ServiceUnavailable(f"Cannot verify connection to Neo4j: {e}")

    def __enter__(self):
        """Context manager entry"""
        self.verify_connectivity()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

    def close(self):
        """Close driver and connection pool"""
        if self._driver:
            self._driver.close()
            self._driver = None
            self._connection_verified = False
            logger.info("Neo4j service closed")

    def execute_query(self, query: str, parameters: Dict[str, Any] = None, database: str = None) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query and return results as list of dictionaries.

        Args:
            query: Cypher query string
            parameters: Query parameters
            database: Database name (defaults to instance database)

        Returns:
            List of record dictionaries
        """
        parameters = parameters or {}
        db = database or self.database

        try:
            with self.driver.session(database=db) as session:
                result = session.run(query, parameters)
                # Consume result within context manager to prevent resource leaks
                records = list(result)
                return [dict(record) for record in records]
        except Neo4jError as e:
            logger.error(f"Neo4j Error: {e.code} - {e.message}")
            logger.error(f"Query: {query}")
            logger.error(f"Parameters: {parameters}")
            raise
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Parameters: {parameters}")
            raise

    def execute_write(self, query: str, parameters: Dict[str, Any] = None, database: str = None) -> List[Dict[str, Any]]:
        """
        Execute a write transaction (CREATE, UPDATE, DELETE).

        Args:
            query: Cypher write query
            parameters: Query parameters
            database: Database name (defaults to instance database)

        Returns:
            List of record dictionaries
        """
        parameters = parameters or {}
        db = database or self.database

        try:
            with self.driver.session(database=db) as session:
                result = session.write_transaction(lambda tx: list(tx.run(query, parameters)))
                return [dict(record) for record in result]
        except Neo4jError as e:
            logger.error(f"Neo4j Error: {e.code} - {e.message}")
            logger.error(f"Query: {query}")
            raise
        except Exception as e:
            logger.error(f"Write transaction failed: {e}")
            logger.error(f"Query: {query}")
            raise

    # ============================================================================
    # Common Query Patterns
    # ============================================================================

    def get_node_by_id(self, label: str, node_id: str) -> Optional[Dict[str, Any]]:
        """Get a single node by ID"""
        query = f"MATCH (n:{label} {{id: $id}}) RETURN n"
        results = self.execute_query(query, {"id": node_id})

        if results:
            return dict(results[0]["n"])
        return None

    def get_node_by_uid(self, label: str, uid: str) -> Optional[Dict[str, Any]]:
        """Get a single node by SMRL UID"""
        query = f"MATCH (n:{label} {{uid: $uid}}) RETURN n"
        results = self.execute_query(query, {"uid": uid})

        if results:
            return dict(results[0]["n"])
        return None

    def list_nodes(
        self, label: str, limit: int = 100, skip: int = 0, filters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        List nodes of a specific type with pagination.

        Args:
            label: Node label
            limit: Maximum results
            skip: Number of results to skip
            filters: Optional filters (e.g., {'name': 'Person', 'status': 'APPROVED'})

        Returns:
            List of node dictionaries
        """
        # Build WHERE clause
        where_clauses = []
        params = {"limit": limit, "skip": skip}

        if filters:
            for i, (key, value) in enumerate(filters.items()):
                param_name = f"filter_{i}"
                where_clauses.append(f"n.{key} = ${param_name}")
                params[param_name] = value

        where_clause = " AND " + " AND ".join(where_clauses) if where_clauses else ""

        query = f"""
            MATCH (n:{label})
            {where_clause}
            RETURN n
            SKIP $skip
            LIMIT $limit
        """

        results = self.execute_query(query, params)
        return [dict(r["n"]) for r in results]

    def count_nodes(self, label: str, filters: Dict[str, Any] = None) -> int:
        """Count nodes of a specific type with optional filters"""
        where_clauses = []
        params = {}

        if filters:
            for i, (key, value) in enumerate(filters.items()):
                param_name = f"filter_{i}"
                where_clauses.append(f"n.{key} = ${param_name}")
                params[param_name] = value

        where_clause = " AND " + " AND ".join(where_clauses) if where_clauses else ""

        query = f"""
            MATCH (n:{label})
            {where_clause}
            RETURN count(n) as count
        """

        results = self.execute_query(query, params)
        return results[0]["count"] if results else 0

    def create_node(self, label: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new node with given properties.

        Args:
            label: Node label
            properties: Node properties

        Returns:
            Created node properties
        """
        # Build property string
        prop_string = ", ".join([f"{k}: ${k}" for k in properties.keys()])

        query = f"""
            CREATE (n:{label} {{{prop_string}}})
            RETURN n
        """

        results = self.execute_write(query, properties)
        return dict(results[0]["n"]) if results else {}

    def update_node(self, label: str, uid: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing node's properties.

        Args:
            label: Node label
            uid: Node UID
            properties: Properties to update

        Returns:
            Updated node properties
        """
        # Build SET clause
        set_clauses = [f"n.{k} = ${k}" for k in properties.keys()]
        set_clause = ", ".join(set_clauses)

        query = f"""
            MATCH (n:{label} {{uid: $uid}})
            SET {set_clause}, n.last_modified = datetime()
            RETURN n
        """

        params = {"uid": uid, **properties}
        results = self.execute_write(query, params)
        return dict(results[0]["n"]) if results else {}

    def delete_node(self, label: str, uid: str) -> bool:
        """
        Delete a node by UID.

        Args:
            label: Node label
            uid: Node UID

        Returns:
            True if deleted, False otherwise
        """
        query = f"""
            MATCH (n:{label} {{uid: $uid}})
            DETACH DELETE n
            RETURN count(n) as deleted
        """

        results = self.execute_write(query, {"uid": uid})
        return results[0]["deleted"] > 0 if results else False

    def search_nodes(
        self, label: str, search_term: str, fields: List[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search nodes by text in specified fields.

        Args:
            label: Node label
            search_term: Search term
            fields: Fields to search in (default: ['name'])
            limit: Maximum results

        Returns:
            List of matching nodes
        """
        fields = fields or ["name"]

        # Build WHERE clause with OR conditions
        where_clauses = [f"toLower(n.{field}) CONTAINS toLower($search)" for field in fields]
        where_clause = " OR ".join(where_clauses)

        query = f"""
            MATCH (n:{label})
            WHERE {where_clause}
            RETURN n
            LIMIT $limit
        """

        results = self.execute_query(query, {"search": search_term, "limit": limit})
        return [dict(r["n"]) for r in results]

    def get_relationships(
        self, node_label: str, node_uid: str, rel_type: str = None, direction: str = "both"
    ) -> List[Dict[str, Any]]:
        """
        Get relationships for a node.

        Args:
            node_label: Source node label
            node_uid: Source node UID
            rel_type: Relationship type filter (optional)
            direction: 'outgoing', 'incoming', or 'both'

        Returns:
            List of relationships with related nodes
        """
        rel_pattern = f"-[r:{rel_type}]-" if rel_type else "-[r]-"

        if direction == "outgoing":
            pattern = f"(n:{node_label} {{uid: $uid}}){rel_pattern}>(m)"
        elif direction == "incoming":
            pattern = f"(n:{node_label} {{uid: $uid}})<{rel_pattern}(m)"
        else:  # both
            pattern = f"(n:{node_label} {{uid: $uid}}){rel_pattern}(m)"

        query = f"""
            MATCH {pattern}
            RETURN n, r, m, labels(m) as target_labels, type(r) as rel_type
        """

        results = self.execute_query(query, {"uid": node_uid})

        return [
            {
                "source": dict(r["n"]),
                "relationship": dict(r["r"]),
                "relationship_type": r["rel_type"],
                "target": dict(r["m"]),
                "target_labels": r["target_labels"],
            }
            for r in results
        ]

    # ============================================================================
    # Statistics
    # ============================================================================

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        stats = {}

        # Total nodes
        query = "MATCH (n) RETURN count(n) as total"
        results = self.execute_query(query)
        stats["total_nodes"] = results[0]["total"] if results else 0

        # Total relationships
        query = "MATCH ()-[r]->() RETURN count(r) as total"
        results = self.execute_query(query)
        stats["total_relationships"] = results[0]["total"] if results else 0

        # Node types
        query = "MATCH (n) RETURN labels(n)[0] as label, count(*) as count ORDER BY count DESC"
        results = self.execute_query(query)
        stats["node_types"] = {r["label"]: r["count"] for r in results}

        # Relationship types
        query = "MATCH ()-[r]->() RETURN type(r) as type, count(*) as count ORDER BY count DESC"
        results = self.execute_query(query)
        stats["relationship_types"] = {r["type"]: r["count"] for r in results}

        return stats


# Singleton instance with thread safety
import threading

_neo4j_service = None
_service_lock = threading.Lock()


def get_neo4j_service() -> Neo4jService:
    """
    Get singleton Neo4j service instance with thread-safe lazy initialization.
    Uses double-checked locking pattern to minimize lock contention.
    
    Returns:
        Neo4jService: Singleton service instance
    """
    global _neo4j_service

    # First check without lock (fast path)
    if _neo4j_service is None:
        # Acquire lock only if instance doesn't exist
        with _service_lock:
            # Double-check after acquiring lock
            if _neo4j_service is None:
                _neo4j_service = Neo4jService()
                logger.info("Neo4j service singleton initialized")

    return _neo4j_service


def reset_neo4j_service():
    """
    Reset singleton instance (useful for testing or reconnection).
    Thread-safe operation.
    """
    global _neo4j_service
    
    with _service_lock:
        if _neo4j_service is not None:
            _neo4j_service.close()
            _neo4j_service = None
            logger.info("Neo4j service singleton reset")
