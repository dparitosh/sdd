"""
GraphStore protocol and BaseIngester abstract base class.

These define the contracts that make the engine backend-agnostic.
Any Cypher-compatible graph database (Neo4j, Apache Spark Cypher,
Memgraph, Amazon Neptune w/ openCypher, etc.) can implement GraphStore.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# GraphStore – the only thing an Ingester needs to talk to a database
# ---------------------------------------------------------------------------

@runtime_checkable
class GraphStore(Protocol):
    """
    Minimal interface for a Cypher-compatible graph database.

    Every method accepts standard Cypher + parameters.  Implementations are
    responsible for session/transaction management.

    Compatible backends:
      - Neo4j (bolt / neo4j protocol)
      - Apache Spark Cypher (via spark-cypher or Neo4j Spark Connector)
      - Memgraph
      - Amazon Neptune (openCypher)
      - RedisGraph (openCypher subset)
    """

    def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Execute a Cypher query and return rows as dicts."""
        ...

    def execute_write(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Execute a write-only Cypher statement (no return needed)."""
        ...

    def close(self) -> None:
        """Release underlying resources (driver, session, spark context)."""
        ...


# ---------------------------------------------------------------------------
# IngestionResult – standardised return value from every ingester
# ---------------------------------------------------------------------------

@dataclass
class IngestionResult:
    """Statistics returned by an ingester after processing one source."""

    ingester_name: str
    source_file: str = ""
    nodes_created: int = 0
    relationships_created: int = 0
    constraints_created: int = 0
    indexes_created: int = 0
    errors: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0


# ---------------------------------------------------------------------------
# BaseIngester – the contract every parser must fulfil
# ---------------------------------------------------------------------------

class BaseIngester(abc.ABC):
    """
    Abstract base for all schema ingesters (XMI, XSD, OWL/RDF, STEP …).

    Subclasses must implement:
      - ``name``   – unique identifier used by the registry / pipeline
      - ``ingest`` – parse a file and write to the given *GraphStore*

    Optionally override:
      - ``create_constraints`` – DDL needed before data loading
      - ``create_cross_links`` – post-load linking across schemas
    """

    # -- identity ----------------------------------------------------------

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Short unique name, e.g. ``'xmi'``, ``'oslc'``, ``'xsd'``."""
        ...

    @property
    def description(self) -> str:
        """Human-readable one-liner shown in logs / CLI help."""
        return self.__class__.__doc__ or self.name

    # -- lifecycle ---------------------------------------------------------

    def create_constraints(self, store: GraphStore) -> IngestionResult:
        """Create uniqueness constraints / indexes (called before ``ingest``)."""
        return IngestionResult(ingester_name=self.name)

    @abc.abstractmethod
    def ingest(
        self,
        store: GraphStore,
        source: Path | str,
        *,
        options: Optional[Dict[str, Any]] = None,
    ) -> IngestionResult:
        """
        Parse *source* and write nodes/relationships via *store*.

        Parameters
        ----------
        store : GraphStore
            Backend-agnostic graph handle.
        source : Path | str
            Path to the file to ingest (XMI, TTL, XSD, …).
        options : dict, optional
            Ingester-specific knobs (e.g. ``enable_versioning``).
        """
        ...

    def create_cross_links(self, store: GraphStore) -> IngestionResult:
        """Post-load: link nodes across schemas (called after all ingesters)."""
        return IngestionResult(ingester_name=self.name)
