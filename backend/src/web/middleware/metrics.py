"""src.web.middleware.metrics

Prometheus metrics helpers.

This module is framework-agnostic and can be used with FastAPI/Starlette.
"""

from __future__ import annotations

import time
from functools import wraps
from typing import Any

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.responses import Response


# Define metrics
REQUEST_COUNT = Counter(
    "mbse_http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)

REQUEST_DURATION = Histogram(
    "mbse_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)

NEO4J_QUERY_COUNT = Counter(
    "mbse_neo4j_queries_total", "Total Neo4j queries executed", ["query_type", "status"]
)

NEO4J_QUERY_DURATION = Histogram(
    "mbse_neo4j_query_duration_seconds",
    "Neo4j query duration in seconds",
    ["query_type"],
)

ACTIVE_CONNECTIONS = Gauge(
    "mbse_active_connections", "Number of active database connections"
)

CACHE_HITS = Counter("mbse_cache_hits_total", "Total cache hits", ["cache_type"])

CACHE_MISSES = Counter("mbse_cache_misses_total", "Total cache misses", ["cache_type"])

AGENT_QUERIES = Counter(
    "mbse_agent_queries_total", "Total AI agent queries", ["status"]
)

AGENT_QUERY_DURATION = Histogram(
    "mbse_agent_query_duration_seconds", "AI agent query duration in seconds"
)

PLM_SYNC_COUNT = Counter(
    "mbse_plm_sync_total",
    "Total PLM synchronizations",
    ["plm_system", "direction", "status"],
)

PLM_SYNC_DURATION = Histogram(
    "mbse_plm_sync_duration_seconds", "PLM sync duration in seconds", ["plm_system"]
)


def track_request_metrics(f):
    """
    Decorator to track HTTP request metrics

    Usage:
        @app.route('/api/endpoint')
        @track_request_metrics
        def endpoint():
            return {'status': 'ok'}
    """

    @wraps(f)
    def decorated(*args: Any, **kwargs: Any):
        start_time = time.time()

        # Get endpoint name
        endpoint = f.__name__
        method = "GET"  # Default, will be overridden by Flask context if available

        # Execute the function
        result = f(*args, **kwargs)

        # Determine status code
        if isinstance(result, tuple):
            status = result[1] if len(result) > 1 else 200
        else:
            status = 200

        # Record metrics
        duration = time.time() - start_time
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
        REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)

        return result

    return decorated


def track_neo4j_query(query_type: str = "read"):
    """
    Decorator to track Neo4j query metrics

    Usage:
        @track_neo4j_query('read')
        def get_nodes():
            # Execute query
            pass
    """

    def decorator(f):
        @wraps(f)
        def decorated(*args: Any, **kwargs: Any):
            start_time = time.time()

            try:
                result = f(*args, **kwargs)
            except Exception:
                duration = time.time() - start_time
                NEO4J_QUERY_COUNT.labels(query_type=query_type, status="error").inc()
                NEO4J_QUERY_DURATION.labels(query_type=query_type).observe(duration)
                raise

            duration = time.time() - start_time
            NEO4J_QUERY_COUNT.labels(query_type=query_type, status="success").inc()
            NEO4J_QUERY_DURATION.labels(query_type=query_type).observe(duration)
            return result

        return decorated

    return decorator


def track_agent_query(f):
    """Decorator to track AI agent query metrics"""

    @wraps(f)
    def decorated(*args: Any, **kwargs: Any):
        start_time = time.time()

        try:
            result = f(*args, **kwargs)
        except Exception:
            duration = time.time() - start_time
            AGENT_QUERIES.labels(status="error").inc()
            AGENT_QUERY_DURATION.observe(duration)
            raise

        duration = time.time() - start_time
        AGENT_QUERIES.labels(status="success").inc()
        AGENT_QUERY_DURATION.observe(duration)
        return result

    return decorated


def metrics_endpoint():
    """Create a Starlette Response containing Prometheus metrics."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


class MetricsCollector:
    """Helper class for manual metrics collection"""

    @staticmethod
    def record_cache_hit(cache_type: str = "default"):
        """Record a cache hit"""
        CACHE_HITS.labels(cache_type=cache_type).inc()

    @staticmethod
    def record_cache_miss(cache_type: str = "default"):
        """Record a cache miss"""
        CACHE_MISSES.labels(cache_type=cache_type).inc()

    @staticmethod
    def set_active_connections(count: int):
        """Set the number of active database connections"""
        ACTIVE_CONNECTIONS.set(count)

    @staticmethod
    def record_plm_sync(
        plm_system: str, direction: str, success: bool, duration: float
    ):
        """Record PLM synchronization metrics"""
        status = "success" if success else "error"
        PLM_SYNC_COUNT.labels(
            plm_system=plm_system, direction=direction, status=status
        ).inc()
        PLM_SYNC_DURATION.labels(plm_system=plm_system).observe(duration)


__all__ = [
    "REQUEST_COUNT",
    "REQUEST_DURATION",
    "NEO4J_QUERY_COUNT",
    "NEO4J_QUERY_DURATION",
    "ACTIVE_CONNECTIONS",
    "CACHE_HITS",
    "CACHE_MISSES",
    "AGENT_QUERIES",
    "AGENT_QUERY_DURATION",
    "PLM_SYNC_COUNT",
    "PLM_SYNC_DURATION",
    "track_request_metrics",
    "track_neo4j_query",
    "track_agent_query",
    "metrics_endpoint",
    "MetricsCollector",
]
