"""
SparkCypherGraphStore – GraphStore backed by the Neo4j Spark Connector.

Designed for the official **Neo4j Connector for Apache Spark**
(https://neo4j.com/docs/spark/current/).  This store translates the
:class:`GraphStore` protocol into Spark DataFrame read/write operations,
allowing the same ingesters to run at cluster scale without code changes.

Architecture
~~~~~~~~~~~~

┌─────────────┐      ┌──────────────────────┐      ┌─────────────┐
│  Ingester   │─────▶│ SparkCypherGraphStore │─────▶│   Neo4j     │
│ (XMI/OSLC)  │      │  (Spark Connector)    │      │  (Aura/CE)  │
└─────────────┘      └──────────────────────┘      └─────────────┘
                       │ spark.read/write    │
                       │ format("org.neo4j.  │
                       │ spark")             │
                       └─────────────────────┘

Usage::

    from pyspark.sql import SparkSession
    from src.engine.stores.spark_store import SparkCypherGraphStore

    spark = (SparkSession.builder
             .appName("MBSE-KG")
             .config("spark.jars.packages",
                     "org.neo4j:neo4j-connector-apache-spark_2.12:5.3.1_for_spark_3")
             .getOrCreate())

    store = SparkCypherGraphStore(
        spark_session=spark,
        url="neo4j://my-cluster:7687",
        user="neo4j",
        password="secret",
        database="mossec",
    )

    # Reads
    rows = store.execute_query("MATCH (n:MBSEElement) RETURN n.name AS name")

    # Writes (via Connector's query mode)
    store.execute_write(
        "MERGE (n:MBSEElement {uuid: $uuid}) SET n.name = $name",
        {"uuid": "abc-123", "name": "PartDefinition"},
    )

Configuration
~~~~~~~~~~~~~

The connector supports a rich option set. Pass extra options via the
``spark_options`` constructor argument::

    store = SparkCypherGraphStore(
        spark_session=spark,
        url="neo4j+s://aura-xyz.databases.neo4j.io",
        user="neo4j",
        password="…",
        spark_options={
            "partitions": "4",
            "batch.size": "5000",
            "node.keys": "uuid",
            "schema.flatten.limit": "1",
        },
    )

Refer to: https://neo4j.com/docs/spark/current/configuration/
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from loguru import logger


class SparkCypherGraphStore:
    """
    :class:`GraphStore` implementation backed by the Neo4j Spark Connector.

    Translates standard ``execute_query`` / ``execute_write`` calls into
    Spark DataFrame operations using ``org.neo4j.spark`` format so that
    MBSE ingesters can run unmodified on an Apache Spark cluster.

    The Neo4j Spark Connector handles all Bolt communication, batching,
    and parallelism internally – this class simply exposes the right Spark
    read/write patterns behind the ``GraphStore`` protocol.
    """

    # Neo4j Spark Connector format identifier
    _FORMAT = "org.neo4j.spark"

    # -- construction ------------------------------------------------------

    def __init__(
        self,
        spark_session: Any = None,
        url: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
        *,
        spark_options: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Parameters
        ----------
        spark_session :
            An active ``pyspark.sql.SparkSession``.  If *None*, the store
            will lazily create one (useful for local testing / notebooks).
        url : str, optional
            Neo4j connection URL (``neo4j://…`` or ``bolt://…``).
            Falls back to ``NEO4J_URI`` env var.
        user / password : str, optional
            Credentials.  Fall back to ``NEO4J_USER`` / ``NEO4J_PASSWORD``.
        database : str, optional
            Target database.  Falls back to ``NEO4J_DATABASE`` or ``"neo4j"``.
        spark_options : dict, optional
            Extra options forwarded to every Spark read/write call (e.g.
            ``{"batch.size": "5000", "partitions": "4"}``).
        """
        self._spark = spark_session
        self._url = url or os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
        self._user = user or os.getenv("NEO4J_USER", "neo4j")
        self._password = password or os.getenv("NEO4J_PASSWORD", "neo4j")
        self._database = database or os.getenv("NEO4J_DATABASE", "neo4j")
        self._extra: Dict[str, str] = spark_options or {}

        logger.info(
            f"SparkCypherGraphStore targeting {self._url} "
            f"(db={self._database})"
        )

    # -- lazy SparkSession -------------------------------------------------

    @property
    def spark(self):
        """
        Return the active ``SparkSession``, creating one lazily if needed.

        The lazy session is configured with the Neo4j Spark Connector
        package for Spark 3.x.
        """
        if self._spark is None:
            try:
                from pyspark.sql import SparkSession  # type: ignore[import-untyped]

                self._spark = (
                    SparkSession.builder.appName("MBSE-KG-Engine")
                    .config(
                        "spark.jars.packages",
                        "org.neo4j:neo4j-connector-apache-spark_2.12:"
                        "5.3.1_for_spark_3",
                    )
                    .getOrCreate()
                )
                logger.info("Created local SparkSession with Neo4j Connector")
            except ImportError:
                raise RuntimeError(
                    "PySpark is not installed.  "
                    "Install it with:  pip install pyspark"
                )
        return self._spark

    # -- shared option builder ---------------------------------------------

    def _base_options(self, reader_or_writer):
        """
        Apply common Neo4j Spark Connector options to a Spark reader/writer.

        See https://neo4j.com/docs/spark/current/configuration/
        """
        rw = (
            reader_or_writer.format(self._FORMAT)
            .option("url", self._url)
            .option("authentication.type", "basic")
            .option("authentication.basic.username", self._user)
            .option("authentication.basic.password", self._password)
            .option("database", self._database)
        )
        for k, v in self._extra.items():
            rw = rw.option(k, v)
        return rw

    # -- GraphStore protocol -----------------------------------------------

    def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute a **read** Cypher query via the Neo4j Spark Connector.

        The connector's ``query`` read mode sends the Cypher to Neo4j and
        returns the results as a Spark DataFrame, which we collect into a
        list of dicts to satisfy the ``GraphStore`` contract.

        Parameters
        ----------
        query : str
            A read-only Cypher query (MATCH / CALL / RETURN).
        parameters : dict, optional
            Query parameters.  The Spark Connector does **not** support
            parameterised queries natively; parameters are interpolated
            into the Cypher string via safe escaping.  Prefer using
            literal Cypher when possible.

        Returns
        -------
        list[dict]
            Rows returned by Neo4j, collected from the Spark DataFrame.
        """
        cypher = self._interpolate(query, parameters)

        reader = self._base_options(self.spark.read).option("query", cypher)
        df = reader.load()

        # Collect to driver (small result sets expected for DDL/inspection)
        return [row.asDict() for row in df.collect()]

    def execute_write(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Execute a **write** Cypher statement via the Neo4j Spark Connector.

        Uses the connector's *query* write mode: a single-row DataFrame is
        written with the Cypher statement attached as the ``query`` option.

        For bulk writes the preferred pattern is:

        1. Build a Spark DataFrame with the data to write.
        2. Use :meth:`write_dataframe` for label/relationship mode writes
           (much faster than row-by-row Cypher).

        Parameters
        ----------
        query : str
            A write Cypher statement (MERGE / CREATE / DELETE …).
        parameters : dict, optional
            Query parameters (interpolated – see :meth:`execute_query`).
        """
        cypher = self._interpolate(query, parameters)

        # Create a single-row "trigger" DataFrame
        trigger = self.spark.createDataFrame([{"__trigger": 1}])

        writer = self._base_options(trigger.write).option("query", cypher)
        writer.mode("Append").save()

    def close(self) -> None:
        """
        Stop the Spark session (if we created it ourselves).

        If the ``SparkSession`` was passed in from outside, we leave it
        alone – the caller is responsible for stopping it.
        """
        # Only stop sessions we created lazily
        if self._spark is not None:
            logger.info("SparkCypherGraphStore: leaving SparkSession open")
        self._spark = None

    # -- bulk helpers (Spark-native, bypasses row-by-row Cypher) -----------

    def write_dataframe(
        self,
        df: Any,
        *,
        labels: Optional[str] = None,
        node_keys: Optional[str] = None,
        relationship: Optional[str] = None,
        relationship_source_labels: Optional[str] = None,
        relationship_target_labels: Optional[str] = None,
        save_mode: str = "Append",
        extra_options: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Bulk-write a Spark DataFrame to Neo4j using connector-native modes.

        This is the **high-performance** path.  Instead of issuing one
        Cypher statement per row, the Neo4j Spark Connector batches the
        DataFrame and writes nodes or relationships directly.

        Parameters
        ----------
        df :
            ``pyspark.sql.DataFrame`` with columns matching Neo4j
            properties.
        labels : str, optional
            Colon-separated labels for node write mode, e.g.
            ``"MBSEElement:AP243Element"``.
        node_keys : str, optional
            Comma-separated property names used as MERGE keys, e.g.
            ``"uuid"``.
        relationship : str, optional
            Relationship type for relationship write mode.
        relationship_source_labels / relationship_target_labels : str
            Labels for source/target nodes of the relationship.
        save_mode : str
            Spark save mode: ``"Append"`` (CREATE), ``"Overwrite"``
            (MERGE), or ``"ErrorIfExists"``.
        extra_options : dict, optional
            Additional connector options for this write operation.

        See https://neo4j.com/docs/spark/current/writing/
        """
        writer = self._base_options(df.write)

        if labels:
            writer = writer.option("labels", labels)
        if node_keys:
            writer = writer.option("node.keys", node_keys)
        if relationship:
            writer = writer.option("relationship", relationship)
            writer = writer.option(
                "relationship.save.strategy", "keys"
            )
        if relationship_source_labels:
            writer = writer.option(
                "relationship.source.labels", relationship_source_labels
            )
        if relationship_target_labels:
            writer = writer.option(
                "relationship.target.labels", relationship_target_labels
            )

        for k, v in (extra_options or {}).items():
            writer = writer.option(k, v)

        writer.mode(save_mode).save()

    def read_dataframe(
        self,
        *,
        labels: Optional[str] = None,
        query: Optional[str] = None,
        relationship: Optional[str] = None,
        extra_options: Optional[Dict[str, str]] = None,
    ):
        """
        Read from Neo4j into a Spark DataFrame using connector-native modes.

        Parameters
        ----------
        labels : str, optional
            Read all nodes with these labels.
        query : str, optional
            A custom Cypher read query.
        relationship : str, optional
            Read all relationships of this type.

        Returns
        -------
        pyspark.sql.DataFrame

        See https://neo4j.com/docs/spark/current/reading/
        """
        reader = self._base_options(self.spark.read)

        if labels:
            reader = reader.option("labels", labels)
        if query:
            reader = reader.option("query", query)
        if relationship:
            reader = reader.option("relationship", relationship)

        for k, v in (extra_options or {}).items():
            reader = reader.option(k, v)

        return reader.load()

    # -- internals ---------------------------------------------------------

    @staticmethod
    def _interpolate(
        query: str,
        parameters: Optional[Dict[str, Any]],
    ) -> str:
        """
        Safely interpolate parameter placeholders in a Cypher string.

        The Neo4j Spark Connector does **not** support parameterised queries
        (``$param`` syntax) in its ``query`` option.  This method replaces
        ``$key`` references with properly escaped literal values.

        For production workloads prefer :meth:`write_dataframe` /
        :meth:`read_dataframe` which avoid interpolation entirely.
        """
        if not parameters:
            return query

        result = query
        for key, value in parameters.items():
            placeholder = f"${key}"
            if placeholder not in result:
                continue

            if value is None:
                literal = "NULL"
            elif isinstance(value, bool):
                literal = "true" if value else "false"
            elif isinstance(value, (int, float)):
                literal = str(value)
            elif isinstance(value, str):
                # Escape single quotes for safe Cypher string literals
                escaped = value.replace("\\", "\\\\").replace("'", "\\'")
                literal = f"'{escaped}'"
            elif isinstance(value, list):
                items = [
                    SparkCypherGraphStore._interpolate_value(v)
                    for v in value
                ]
                literal = "[" + ", ".join(items) + "]"
            else:
                escaped = str(value).replace("\\", "\\\\").replace("'", "\\'")
                literal = f"'{escaped}'"

            result = result.replace(placeholder, literal)

        return result

    @staticmethod
    def _interpolate_value(value: Any) -> str:
        """Convert a single value to a Cypher literal string."""
        if value is None:
            return "NULL"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        escaped = str(value).replace("\\", "\\\\").replace("'", "\\'")
        return f"'{escaped}'"

    # -- context manager ---------------------------------------------------

    def __enter__(self) -> "SparkCypherGraphStore":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def __repr__(self) -> str:
        return (
            f"SparkCypherGraphStore(url={self._url!r}, "
            f"database={self._database!r})"
        )
