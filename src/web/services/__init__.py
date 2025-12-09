"""
Web Services - Reusable service layer for MBSE Knowledge Graph
"""

from .cache_service import (
    cache_node,
    cache_search,
    cache_stats,
    cached,
    get_cache,
    get_cache_stats,
    invalidate_cache,
    invalidate_node_cache,
    invalidate_stats_cache,
)
from .neo4j_service import Neo4jService, get_neo4j_service, reset_neo4j_service
from .smrl_adapter import SMRLAdapter

__all__ = [
    "Neo4jService",
    "get_neo4j_service",
    "reset_neo4j_service",
    "get_cache",
    "cached",
    "cache_stats",
    "cache_node",
    "cache_search",
    "invalidate_cache",
    "invalidate_node_cache",
    "invalidate_stats_cache",
    "get_cache_stats",
    "SMRLAdapter",
]
