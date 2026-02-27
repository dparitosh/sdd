"""
XMIIngester – BaseIngester wrapper around SemanticXMILoader.

Delegates all parsing to the battle-tested :class:`SemanticXMILoader` but
replaces the hard ``Neo4jConnection`` dependency with the
:class:`GraphStore` protocol, making the same loader runnable against
Neo4j, Apache Spark (via the Neo4j Spark Connector), Memgraph, etc.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger

from src.engine.protocol import BaseIngester, GraphStore, IngestionResult
from src.engine.registry import registry


class _GraphStoreConnectionShim:
    """
    Thin adapter that exposes the ``Neo4jConnection`` interface expected
    by :class:`SemanticXMILoader` while delegating to a :class:`GraphStore`.

    The existing loader calls:
      - ``self.conn.execute_query(cypher, params)``  → ``store.execute_query``
      - ``self.conn.execute_write(cypher, params)``  → ``store.execute_write``
      - ``self.conn.driver``                         → raises (APOC helpers)

    For APOC-based ``apoc.merge.node`` / ``apoc.merge.relationship`` the
    loader uses ``execute_query`` with those Cypher calls, which works fine
    because APOC procedures run inside regular Cypher queries.
    """

    def __init__(self, store: GraphStore) -> None:
        self._store = store

    # --- core API used by SemanticXMILoader ---

    def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        return self._store.execute_query(query, parameters)

    def execute_write(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._store.execute_write(query, parameters)

    # --- convenience helpers (may be called but less common) ---

    def create_node(self, label: str, properties: Dict[str, Any]) -> None:
        props_str = ", ".join(f"{k}: ${k}" for k in properties)
        query = f"CREATE (n:{label} {{{props_str}}})"
        self._store.execute_write(query, properties)

    def create_relationship(
        self,
        from_label: str,
        from_props: Dict[str, Any],
        rel_type: str,
        to_label: str,
        to_props: Dict[str, Any],
        rel_props: Optional[Dict[str, Any]] = None,
    ) -> None:
        from_match = " AND ".join(f"from.{k} = $from_{k}" for k in from_props)
        to_match = " AND ".join(f"to.{k} = $to_{k}" for k in to_props)
        rel_props_str = ""
        if rel_props:
            rps = ", ".join(f"{k}: $rel_{k}" for k in rel_props)
            rel_props_str = f" {{{rps}}}"
        query = (
            f"MATCH (from:{from_label}) WHERE {from_match}\n"
            f"MATCH (to:{to_label}) WHERE {to_match}\n"
            f"CREATE (from)-[r:{rel_type}{rel_props_str}]->(to)"
        )
        parameters: Dict[str, Any] = {}
        parameters.update({f"from_{k}": v for k, v in from_props.items()})
        parameters.update({f"to_{k}": v for k, v in to_props.items()})
        if rel_props:
            parameters.update({f"rel_{k}": v for k, v in rel_props.items()})
        self._store.execute_write(query, parameters)

    @property
    def driver(self):
        """Raise if caller tries to access the raw Neo4j driver.

        The Spark connector does not expose a bolt driver.
        If you see this error, the calling code needs to be refactored
        to use Cypher-only operations.
        """
        raise AttributeError(
            "GraphStore does not expose a raw Neo4j driver. "
            "Use execute_query / execute_write instead."
        )


# ── register ─────────────────────────────────────────────────────────────


@registry.register
class XMIIngester(BaseIngester):
    """Parse OMG XMI (UML/SysML/AP239/AP242/AP243) into the knowledge graph."""

    @property
    def name(self) -> str:
        return "xmi"

    # -- constraints -------------------------------------------------------

    def create_constraints(self, store: GraphStore) -> IngestionResult:
        from src.parsers.semantic_loader import SemanticXMILoader

        shim = _GraphStoreConnectionShim(store)
        loader = SemanticXMILoader(connection=shim, enable_versioning=False)  # type: ignore[arg-type]
        loader.create_constraints_and_indexes()

        # Count constraints + indexes created (best-effort)
        rows = store.execute_query(
            "SHOW CONSTRAINTS YIELD name RETURN count(name) AS cnt"
        )
        c_cnt = rows[0]["cnt"] if rows else 0
        rows = store.execute_query(
            "SHOW INDEXES YIELD name RETURN count(name) AS cnt"
        )
        i_cnt = rows[0]["cnt"] if rows else 0

        return IngestionResult(
            ingester_name=self.name,
            constraints_created=c_cnt,
            indexes_created=i_cnt,
        )

    # -- ingest ------------------------------------------------------------

    def ingest(
        self,
        store: GraphStore,
        source: Path | str,
        *,
        options: Optional[Dict[str, Any]] = None,
    ) -> IngestionResult:
        from src.parsers.semantic_loader import SemanticXMILoader

        opts = options or {}
        enable_versioning = opts.get("enable_versioning", True)

        shim = _GraphStoreConnectionShim(store)
        loader = SemanticXMILoader(
            connection=shim,  # type: ignore[arg-type]
            enable_versioning=enable_versioning,
        )

        source = Path(source)
        logger.info(f"[xmi] ingesting {source}")
        stats = loader.load_xmi_file(source)

        return IngestionResult(
            ingester_name=self.name,
            source_file=str(source),
            nodes_created=stats.get("nodes_created", 0),
            relationships_created=(
                stats.get("containment_relationships", 0)
                + stats.get("semantic_relationships", 0)
                + stats.get("reference_relationships", 0)
            ),
            extra=stats,
        )

    # -- cross-schema links ------------------------------------------------

    def create_cross_links(self, store: GraphStore) -> IngestionResult:
        from src.parsers.semantic_loader import SemanticXMILoader

        shim = _GraphStoreConnectionShim(store)
        loader = SemanticXMILoader(connection=shim, enable_versioning=False)  # type: ignore[arg-type]
        total = loader.create_cross_schema_links()

        return IngestionResult(
            ingester_name=self.name,
            relationships_created=total,
            extra={"cross_links": total},
        )
