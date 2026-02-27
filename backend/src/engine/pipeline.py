"""
IngestionPipeline – orchestrates ingesters over a GraphStore.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from src.engine.protocol import BaseIngester, GraphStore, IngestionResult
from src.engine.registry import IngesterRegistry, registry as _default_registry


class IngestionPipeline:
    """
    High-level orchestrator that:

    1. Optionally clears the graph.
    2. Runs ``create_constraints`` for every activated ingester.
    3. Runs ``ingest`` for every activated ingester (in registration order).
    4. Runs ``create_cross_links`` for every activated ingester.
    5. Returns a consolidated list of ``IngestionResult``.

    Usage::

        store = Neo4jGraphStore(uri=..., user=..., password=...)
        pipeline = IngestionPipeline(store)
        results = pipeline.run(sources={"xmi": "data/raw/Domain_model.xmi",
                                         "oslc": "backend/data/seed/oslc"})
    """

    def __init__(
        self,
        store: GraphStore,
        registry: Optional[IngesterRegistry] = None,
    ) -> None:
        self.store = store
        self.registry = registry or _default_registry

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        sources: Dict[str, str | Path],
        *,
        clear_first: bool = True,
        options: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> List[IngestionResult]:
        """
        Execute the full pipeline.

        Parameters
        ----------
        sources : dict
            Mapping of ``ingester_name → file_or_directory_path``.
            Only ingesters present in *sources* will be activated.
        clear_first : bool
            If True, ``MATCH (n) DETACH DELETE n`` before loading.
        options : dict, optional
            Per-ingester options: ``{ingester_name: {key: value}}``.

        Returns
        -------
        list[IngestionResult]
        """
        options = options or {}
        results: List[IngestionResult] = []

        # Resolve ingester instances
        active: List[tuple[BaseIngester, Path]] = []
        for name, path in sources.items():
            cls = self.registry.get(name)
            if cls is None:
                logger.warning(f"No ingester registered for '{name}' – skipping")
                results.append(
                    IngestionResult(ingester_name=name, errors=[f"Unknown ingester: {name}"])
                )
                continue
            active.append((cls(), Path(path)))

        if not active:
            logger.error("No active ingesters – nothing to do")
            return results

        # Step 0 – clear
        if clear_first:
            logger.info("Clearing graph …")
            self.store.execute_write("MATCH (n) DETACH DELETE n")
            logger.info("Graph cleared.")

        # Step 1 – constraints
        logger.info("Creating constraints & indexes …")
        for ingester, _ in active:
            res = ingester.create_constraints(self.store)
            results.append(res)
            logger.info(f"  [{ingester.name}] constraints: {res.constraints_created} created")

        # Step 2 – ingest
        for ingester, path in active:
            logger.info(f"Ingesting [{ingester.name}] from {path} …")
            ing_opts = options.get(ingester.name, {})
            res = ingester.ingest(self.store, path, options=ing_opts)
            results.append(res)
            if res.ok:
                logger.info(
                    f"  [{ingester.name}] OK – {res.nodes_created} nodes, "
                    f"{res.relationships_created} rels"
                )
            else:
                logger.error(f"  [{ingester.name}] errors: {res.errors}")

        # Step 3 – cross-schema links
        logger.info("Creating cross-schema links …")
        for ingester, _ in active:
            res = ingester.create_cross_links(self.store)
            results.append(res)
            if res.relationships_created:
                logger.info(
                    f"  [{ingester.name}] cross-links: {res.relationships_created}"
                )

        logger.info("Pipeline complete.")
        return results
