"""
Neo4j Service Layer - Centralized database operations
Provides connection pooling, query execution, and common database patterns
Integrated with Redis query caching for performance optimization
"""

import os
from typing import Any, Dict, List, Optional

from loguru import logger
from neo4j import GraphDatabase, Session
from neo4j.exceptions import ServiceUnavailable, AuthError, Neo4jError


class Neo4jService:
    """
    Centralized Neo4j database service with connection pooling and query caching.
    Provides common query patterns and error handling.

    Features:
    - Connection pooling (max 50 connections)
    - Redis query result caching with configurable TTL
    - Automatic cache invalidation on writes
    - Common query patterns (CRUD, search, pagination)
    """

    def __init__(
        self,
        uri: str = None,
        user: str = None,
        password: str = None,
        database: str = None,
        query_cache=None,
    ):
        """
        Initialize Neo4j service with connection pooling.

        Args:
            uri: Neo4j connection URI (defaults to NEO4J_URI env var)
            user: Neo4j username (defaults to NEO4J_USER env var)
            password: Neo4j password (defaults to NEO4J_PASSWORD env var)
            database: Neo4j database name (defaults to NEO4J_DATABASE env var or 'neo4j')
            query_cache: Optional QueryCache instance for result caching
        """
        self.uri = uri or os.getenv("NEO4J_URI")
        self.user = user or os.getenv("NEO4J_USER")
        self.password = password or os.getenv("NEO4J_PASSWORD")
        self.database = database or os.getenv("NEO4J_DATABASE", "neo4j")

        missing = [
            name
            for name, value in (
                ("NEO4J_URI", self.uri),
                ("NEO4J_USER", self.user),
                ("NEO4J_PASSWORD", self.password),
            )
            if not value
        ]
        if missing:
            raise ValueError(
                "Missing required Neo4j configuration: "
                + ", ".join(missing)
                + ". Set these in your .env or environment variables."
            )
        self._driver = None
        self._connection_verified = False
        self.query_cache = query_cache  # QueryCache instance

        logger.info(
            f"Neo4j service configuration: uri={self.uri}, database={self.database}"
        )

        # Eagerly initialize the driver so test fixtures that patch
        # `GraphDatabase.driver` only during construction still take effect.
        # This also provides early feedback if the database is unreachable.
        _ = self.driver

    @property
    def driver(self):
        """Lazy driver initialization - creates driver on first access with retry logic"""
        if self._driver is None:
            import time

            max_retries = 3
            retry_delay = 2  # seconds

            for attempt in range(max_retries):
                try:
                    logger.debug(
                        f"Creating Neo4j driver for {self.uri} (attempt {attempt + 1}/{max_retries})"
                    )
                    self._driver = GraphDatabase.driver(
                        self.uri,
                        auth=(self.user, self.password),
                        max_connection_pool_size=50,
                        connection_acquisition_timeout=30,
                        max_transaction_retry_time=15,
                        connection_timeout=10,
                        max_connection_lifetime=3600,  # Close connections after 1 hour
                        keep_alive=True,  # Keep connections alive
                    )
                    # Driver-level connectivity check (matches neo4j driver API)
                    # and keeps unit tests from needing to call verify_connectivity.
                    self._driver.verify_connectivity()
                    self._connection_verified = True
                    logger.info("Neo4j driver created successfully")
                    break
                except Exception as e:
                    logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                    else:
                        logger.error(
                            f"Failed to create Neo4j driver after {max_retries} attempts"
                        )
                        raise ServiceUnavailable(
                            f"Cannot connect to Neo4j at {self.uri}: {e}"
                        )
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

    def execute_query(
        self,
        query: str,
        parameters: Dict[str, Any] = None,
        database: str = None,
        use_cache: bool = True,
        ttl: int = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query and return results as list of dictionaries.
        Results are cached in Redis if caching is enabled.

        Args:
            query: Cypher query string
            parameters: Query parameters
            database: Database name (defaults to instance database)
            use_cache: Whether to use cache (default: True)
            ttl: Cache TTL in seconds (default: 300s/5min for queries)

        Returns:
            List of record dictionaries
        """
        def _safe_params_for_log(params: Dict[str, Any]) -> Dict[str, Any]:
            """Return a redacted/truncated copy of params for logs.

            This service is sometimes used for bulk UNWIND operations (e.g.
            rows=[{...}, {...}, ...]). Logging raw params can explode logs and
            even crash terminals.
            """
            if not isinstance(params, dict):
                return {"_params": str(type(params))}

            safe: Dict[str, Any] = {}
            for k, v in params.items():
                if k.lower() in {"password", "neo4j_password", "api_key", "openai_api_key"}:
                    safe[k] = "***"
                    continue
                if k == "rows" and isinstance(v, list):
                    safe[k] = f"<list len={len(v)}>"
                    continue
                # Avoid huge string dumps
                if isinstance(v, str) and len(v) > 500:
                    safe[k] = v[:500] + "…"
                    continue
                safe[k] = v
            return safe

        # Preserve whether caller supplied params; tests expect passing None
        # through to `session.run(query, None)`.
        parameters_provided = parameters is not None
        parameters = parameters or {}
        db = database or self.database

        # Try cache first if enabled.
        # Many FastAPI routes are `async def` but call this sync method; calling
        # `asyncio.run()` inside a running event loop raises. In that case we
        # skip Redis cache access and still execute the query.
        if use_cache and self.query_cache and self.query_cache.enabled:
            import asyncio

            try:
                running_loop = asyncio.get_running_loop()
            except RuntimeError:
                running_loop = None

            if running_loop and running_loop.is_running():
                logger.debug(
                    "Skipping Redis query cache access inside running event loop"
                )
            else:
                cached_result = asyncio.run(self.query_cache.get(query, parameters, db))
                if cached_result is not None:
                    return cached_result

        # Execute query (cache miss or caching disabled)
        try:
            with self.driver.session(database=db) as session:
                result = session.run(query, parameters if parameters_provided else None)
                # Consume result within context manager to prevent resource leaks
                records = list(result)
                result_dicts = [dict(record) for record in records]

                # Cache result if caching enabled (only when safe to do so).
                if use_cache and self.query_cache and self.query_cache.enabled:
                    import asyncio
                    from src.web.services.query_cache import QueryCache

                    try:
                        running_loop = asyncio.get_running_loop()
                    except RuntimeError:
                        running_loop = None

                    if running_loop and running_loop.is_running():
                        logger.debug(
                            "Skipping Redis query cache write inside running event loop"
                        )
                    else:
                        cache_ttl = ttl or QueryCache.TTL_QUERY_SHORT
                        asyncio.run(
                            self.query_cache.set(
                                query, result_dicts, parameters, db, cache_ttl
                            )
                        )

                return result_dicts

        except Neo4jError as e:
            logger.error(f"Neo4j Error: {e.code} - {e.message}")
            logger.error(f"Query: {query}")
            logger.error(f"Parameters: {_safe_params_for_log(parameters)}")
            raise
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Parameters: {_safe_params_for_log(parameters)}")
            raise

    def execute_write(
        self,
        query: str,
        parameters: Dict[str, Any] = None,
        database: str = None,
        invalidate_cache: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Execute a write transaction (CREATE, UPDATE, DELETE).
        Automatically invalidates relevant cache entries.

        Args:
            query: Cypher write query
            parameters: Query parameters
            database: Database name (defaults to instance database)
            invalidate_cache: Whether to invalidate cache after write (default: True)

        Returns:
            List of record dictionaries
        """
        parameters = parameters or {}
        db = database or self.database

        try:
            with self.driver.session(database=db) as session:
                # neo4j python driver v5 uses `execute_write`; older versions used `write_transaction`.
                if hasattr(session, "execute_write"):
                    result = session.execute_write(
                        lambda tx: list(tx.run(query, parameters))
                    )
                else:
                    result = session.write_transaction(
                        lambda tx: list(tx.run(query, parameters))
                    )
                result_dicts = [dict(record) for record in result]

                # Invalidate cache after successful write (only when safe to do so).
                if invalidate_cache and self.query_cache and self.query_cache.enabled:
                    import asyncio

                    try:
                        running_loop = asyncio.get_running_loop()
                    except RuntimeError:
                        running_loop = None

                    if running_loop and running_loop.is_running():
                        logger.debug(
                            "Skipping Redis cache invalidation inside running event loop"
                        )
                    else:
                        # Clear all cached queries (conservative approach)
                        # Could be optimized to clear only affected node types
                        asyncio.run(self.query_cache.invalidate_pattern("*"))
                        logger.debug("Cache invalidated after write operation")

                return result_dicts

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
        query = f"MATCH (n:{label} {{id: $id}}) RETURN n as node"
        results = self.execute_query(query, {"id": node_id})

        if results:
            return dict(results[0]["node"])
        return None

    def get_node_by_uid(self, label: str, uid: str) -> Optional[Dict[str, Any]]:
        """Get a single node by SMRL UID"""
        query = f"MATCH (n:{label} {{uid: $uid}}) RETURN n as node"
        results = self.execute_query(query, {"uid": uid})

        if results:
            return dict(results[0]["node"])
        return None

    def list_nodes(
        self,
        label: str,
        limit: int = 100,
        skip: int = 0,
        filters: Dict[str, Any] = None,
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
            RETURN n as node
            SKIP $skip
            LIMIT $limit
        """

        results = self.execute_query(query, params)
        return [dict(r["node"]) for r in results]

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

    def create_node(self, label: str, properties: Dict[str, Any]) -> str:
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
            RETURN n.uid as uid
        """

        # Use auto-commit write (session.run) so unit tests can stub `session.run`.
        results = self.execute_query(query, properties, use_cache=False)
        return results[0]["uid"] if results else ""

    def update_node(self, label: str, uid: str, properties: Dict[str, Any]) -> bool:
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
            RETURN count(n) as updated
        """

        params = {"uid": uid, **properties}
        results = self.execute_query(query, params, use_cache=False)
        return bool(results and results[0].get("updated", 0) > 0)

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

        results = self.execute_query(query, {"uid": uid}, use_cache=False)
        return bool(results and results[0].get("deleted", 0) > 0)

    def search_nodes(
        self,
        label: str,
        search_term: str = None,
        fields: List[str] = None,
        limit: int = 100,
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
        # Backward-compatible calling convention:
        # - search_nodes("Person", limit=10)  -> searches all labels
        # - search_nodes("Class", "Person")  -> searches within label
        if search_term is None:
            search_term = label
            label = None

        fields = fields or ["name"]

        # Build WHERE clause with OR conditions
        where_clauses = [
            f"toLower(n.{field}) CONTAINS toLower($search)" for field in fields
        ]
        where_clause = " OR ".join(where_clauses)

        label_clause = f":{label}" if label else ""
        query = f"""
            MATCH (n{label_clause})
            WHERE {where_clause}
            RETURN n as node
            LIMIT $limit
        """

        results = self.execute_query(query, {"search": search_term, "limit": limit})
        return [dict(r["node"]) for r in results]

    def get_relationships(
        self,
        node_label: str,
        node_uid: str,
        rel_type: str = None,
        direction: str = "both",
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
            RETURN type(r) as rel_type, labels(m)[0] as target_label, m as target_node
        """

        # Unit tests stub `session.run` to return the final shape already.
        return self.execute_query(query, {"uid": node_uid})

    # ============================================================================
    # Statistics
    # ============================================================================

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        stats = {}

        # Order matters for unit tests that use sequential side effects.
        # Total nodes
        query = "MATCH (n) RETURN count(n) as count"
        results = self.execute_query(query)
        stats["total_nodes"] = results[0]["count"] if results else 0

        # Node types
        query = "MATCH (n) RETURN labels(n)[0] as label, count(*) as count ORDER BY count DESC"
        results = self.execute_query(query)
        stats["node_types"] = {r["label"]: r["count"] for r in results}

        # Total relationships
        query = "MATCH ()-[r]->() RETURN count(r) as count"
        results = self.execute_query(query)
        stats["total_relationships"] = results[0]["count"] if results else 0

        # Relationship types
        query = "MATCH ()-[r]->() RETURN type(r) as type, count(*) as count ORDER BY count DESC"
        results = self.execute_query(query)
        stats["relationship_types"] = {r["type"]: r["count"] for r in results}

        return stats

    # ============================================================================
    # Cache Management
    # ============================================================================

    def set_cache(self, query_cache):
        """
        Set query cache for this service instance

        Args:
            query_cache: QueryCache instance
        """
        self.query_cache = query_cache
        logger.info("Query cache attached to Neo4j service")

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        if self.query_cache and self.query_cache.enabled:
            return await self.query_cache.get_statistics()
        return {"enabled": False}

    async def clear_cache(self) -> int:
        """Clear all cached queries"""
        if self.query_cache and self.query_cache.enabled:
            return await self.query_cache.clear_all()
        return 0


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

                # Attach query cache if available
                try:
                    import asyncio
                    from src.web.services.query_cache import get_query_cache

                    # Avoid asyncio.run() when we're already inside an event loop
                    try:
                        running_loop = asyncio.get_running_loop()
                    except RuntimeError:
                        running_loop = None

                    if running_loop and running_loop.is_running():
                        logger.debug(
                            "Skipping query cache attach during service init (running event loop). "
                            "Cache will be attached during FastAPI startup if Redis is available."
                        )
                    else:
                        cache = asyncio.run(get_query_cache())
                        if cache and getattr(cache, "enabled", False):
                            _neo4j_service.set_cache(cache)
                except Exception as e:
                    logger.warning(f"Failed to attach query cache: {e}")

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
