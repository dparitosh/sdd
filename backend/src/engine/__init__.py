"""
MBSE Knowledge Graph – Ingestion Engine
========================================
A modular, backend-agnostic ingestion engine for MBSE schema data.

The engine is composed of three layers:

1. **GraphStore protocol** – abstract interface for any Cypher-compatible graph
   database (Neo4j, Apache Spark Cypher, Memgraph, etc.).
2. **Ingesters** – independent, self-registering components that parse a specific
   schema format (XMI, XSD, OWL/RDF, STEP) and write to a *GraphStore*.
3. **Pipeline** – an orchestrator that wires ingesters together with a *GraphStore*
   and executes them in dependency order.

Quick start::

    from src.engine import Neo4jGraphStore, IngestionPipeline, registry

    store = Neo4jGraphStore(uri="bolt://localhost:7687", user="neo4j", password="secret")
    pipeline = IngestionPipeline(store=store, registry=registry)
    pipeline.run(sources={"xmi": "data/raw/Domain_model.xmi"})

For Apache Spark Cypher::

    from src.engine import SparkCypherGraphStore, IngestionPipeline, registry

    store = SparkCypherGraphStore(spark_session=spark, catalog="neo4j")
    pipeline = IngestionPipeline(store=store, registry=registry)
    pipeline.run(sources={"xmi": "data/raw/Domain_model.xmi"})
"""

from src.engine.protocol import GraphStore, BaseIngester, IngestionResult
from src.engine.registry import IngesterRegistry, registry
from src.engine.pipeline import IngestionPipeline
from src.engine.stores.neo4j_store import Neo4jGraphStore
from src.engine.stores.spark_store import SparkCypherGraphStore

# Import ingesters so they auto-register with the global registry on import.
import src.engine.ingesters.xmi_ingester as _xmi   # noqa: F401
import src.engine.ingesters.oslc_ingester as _oslc  # noqa: F401

__all__ = [
    "GraphStore",
    "BaseIngester",
    "IngestionResult",
    "IngesterRegistry",
    "registry",
    "IngestionPipeline",
    "Neo4jGraphStore",
    "SparkCypherGraphStore",
]
