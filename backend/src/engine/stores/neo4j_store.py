"""
Neo4jGraphStore – GraphStore backed by the official Neo4j Python driver.

Wraps the existing :class:`src.graph.connection.Neo4jConnection` so that
all engine ingesters stay decoupled from the driver details.

Usage::

    store = Neo4jGraphStore(uri="bolt://localhost:7687",
                            user="neo4j", password="secret",
                            database="mossec")
    rows = store.execute_query("MATCH (n) RETURN count(n) AS cnt")
    store.close()

Or with a pre-existing connection::

    from src.graph.connection import Neo4jConnection
    conn = Neo4jConnection(uri, user, password, database)
    conn.connect()
    store = Neo4jGraphStore.from_connection(conn, owns_connection=False)
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from loguru import logger


class Neo4jGraphStore:
    """
    :class:`GraphStore` implementation backed by the Neo4j Python driver.

    Supports two construction modes:
      1. **Direct** – pass *uri / user / password / database* and the store
         manages the driver lifecycle.
      2. **Wrapper** – pass an existing ``Neo4jConnection`` via
         :meth:`from_connection`.  The caller keeps ownership unless
         ``owns_connection=True``.
    """

    # -- construction ------------------------------------------------------

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
    ) -> None:
        from src.graph.connection import Neo4jConnection

        self._uri = uri or os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
        self._user = user or os.getenv("NEO4J_USER", "neo4j")
        self._password = password or os.getenv("NEO4J_PASSWORD", "neo4j")
        self._database = database or os.getenv("NEO4J_DATABASE", "neo4j")

        self._conn = Neo4jConnection(
            self._uri, self._user, self._password, self._database
        )
        self._conn.connect()
        self._owns_connection = True
        logger.debug(
            f"Neo4jGraphStore connected to {self._uri} (db={self._database})"
        )

    @classmethod
    def from_connection(
        cls,
        connection: Any,  # Neo4jConnection – loose typing to avoid hard import
        *,
        owns_connection: bool = False,
    ) -> "Neo4jGraphStore":
        """
        Wrap an already-open :class:`Neo4jConnection`.

        Parameters
        ----------
        connection :
            An open ``Neo4jConnection`` instance.
        owns_connection : bool
            If True the store will close the connection on :meth:`close`.
        """
        instance = object.__new__(cls)
        instance._conn = connection
        instance._owns_connection = owns_connection
        instance._uri = getattr(connection, "uri", "unknown")
        instance._user = getattr(connection, "user", "unknown")
        instance._password = ""
        instance._database = getattr(connection, "database", "neo4j")
        return instance

    # -- GraphStore protocol -----------------------------------------------

    def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Execute a Cypher **read** query and return rows as dicts."""
        return self._conn.execute_query(query, parameters)

    def execute_write(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Execute a Cypher **write** statement (MERGE / CREATE / DELETE …)."""
        self._conn.execute_write(query, parameters)

    def close(self) -> None:
        """Release the underlying Neo4j driver (if we own it)."""
        if self._owns_connection and self._conn is not None:
            self._conn.close()
            logger.debug("Neo4jGraphStore closed")
        self._conn = None  # type: ignore[assignment]

    # -- convenience -------------------------------------------------------

    @property
    def driver(self):
        """Direct access to the underlying Neo4j driver (escape hatch)."""
        return self._conn.driver

    @property
    def connection(self):
        """Direct access to the underlying ``Neo4jConnection``."""
        return self._conn

    # -- context manager ---------------------------------------------------

    def __enter__(self) -> "Neo4jGraphStore":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def __repr__(self) -> str:
        return (
            f"Neo4jGraphStore(uri={self._uri!r}, "
            f"database={self._database!r})"
        )
