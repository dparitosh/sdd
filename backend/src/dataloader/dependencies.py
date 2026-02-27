"""
Dataloader — Shared dependencies and connection management.

Provides a Neo4j connection factory and engine GraphStore that all
loader routes share. This is the only place Neo4j credentials are managed.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from loguru import logger

from src.utils.config import Config
from src.graph.connection import Neo4jConnection
from src.engine.stores.neo4j_store import Neo4jGraphStore
from src.engine.registry import registry
from src.engine.pipeline import IngestionPipeline

# Ensure ingesters are registered on import
import src.engine.ingesters.xmi_ingester as _xmi      # noqa: F401
import src.engine.ingesters.oslc_ingester as _oslc     # noqa: F401


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = BACKEND_ROOT.parent
SEED_DIR = BACKEND_ROOT / "data" / "seed" / "oslc"
MIGRATIONS_DIR = BACKEND_ROOT / "scripts" / "migrations"
DEFAULT_XMI_PATHS = [
    PROJECT_ROOT / "smrlv12" / "data" / "domain_models" / "mossec",
    PROJECT_ROOT / "data" / "raw",
]
UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"


# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

@lru_cache()
def get_config() -> Config:
    return Config()


def get_neo4j_connection() -> Neo4jConnection:
    """Create a fresh Neo4jConnection (caller must manage lifecycle)."""
    cfg = get_config()
    conn = Neo4jConnection(cfg.neo4j_uri, cfg.neo4j_user, cfg.neo4j_password)
    conn.connect()
    return conn


def get_graph_store() -> Neo4jGraphStore:
    """Create a Neo4jGraphStore for engine-based operations."""
    cfg = get_config()
    return Neo4jGraphStore(
        uri=cfg.neo4j_uri,
        user=cfg.neo4j_user,
        password=cfg.neo4j_password,
    )


def get_pipeline(store: Optional[Neo4jGraphStore] = None) -> IngestionPipeline:
    """Create a pipeline with the default registry."""
    s = store or get_graph_store()
    return IngestionPipeline(store=s, registry=registry)
