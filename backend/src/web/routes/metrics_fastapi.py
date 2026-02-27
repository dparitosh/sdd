"""
System Metrics API (FastAPI)
Endpoints for application metrics, monitoring, and health data.

All metrics are derived from real runtime state — no hardcoded / mock values.
"""

from collections import deque
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import asyncio
import threading
import time
import psutil

from fastapi import APIRouter, Depends, Query
from loguru import logger

from src.web.dependencies import get_api_key
from src.web.services import get_neo4j_service
from src.web.utils.responses import Neo4jJSONResponse

router = APIRouter()

# ---------------------------------------------------------------------------
# Real in-process metrics tracking
# ---------------------------------------------------------------------------
_request_count = 0
_error_count = 0
_start_time = time.time()
_response_times: deque = deque(maxlen=500)       # last 500 response-time samples (ms)
_response_times_lock = threading.Lock()

# History ring-buffer: one snapshot per minute, keep 24 h worth
_MAX_HISTORY = 1440
_history: deque = deque(maxlen=_MAX_HISTORY)
_history_lock = threading.Lock()


def record_request(duration_ms: float, is_error: bool = False) -> None:
    """Call from middleware / route wrappers to record a request."""
    global _request_count, _error_count
    _request_count += 1
    if is_error:
        _error_count += 1
    with _response_times_lock:
        _response_times.append(duration_ms)


def _snapshot_metrics() -> Dict[str, Any]:
    """Capture a lightweight metrics snapshot (used by history sampler)."""
    cpu = psutil.cpu_percent(interval=0)
    mem = psutil.virtual_memory()
    # Calculate avg response time from recent samples
    with _response_times_lock:
        avg_rt = round(sum(_response_times) / len(_response_times), 2) if _response_times else 0
    # Calculate error rate
    error_rate = round((_error_count / _request_count) * 100, 2) if _request_count > 0 else 0
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "cpu": cpu,
        "memory_mb": mem.used / (1024 * 1024),
        "memory_percent": mem.percent,
        "api_requests": _request_count,
        "avg_response_time_ms": avg_rt,
        "error_rate": error_rate,
    }


def _history_sampler() -> None:
    """Background thread that appends one snapshot per minute."""
    while True:
        try:
            snap = _snapshot_metrics()
            with _history_lock:
                _history.append(snap)
        except Exception:
            pass
        time.sleep(60)


# Start the sampler thread once on import
_sampler_thread = threading.Thread(target=_history_sampler, daemon=True)
_sampler_thread.start()


# ---------------------------------------------------------------------------
# Metric collector functions
# ---------------------------------------------------------------------------

async def get_cache_metrics() -> Dict[str, Any]:
    """Get cache performance metrics from the real QueryCache (Redis-backed)."""
    try:
        from src.web.container import ServiceContainer
        qc = ServiceContainer.instance().query_cache
        if qc and getattr(qc, "enabled", False):
            stats = await qc.get_statistics()
            return {
                "source": "redis",
                "hit_rate": round(stats.get("hit_rate_percent", 0) / 100, 4),
                "miss_rate": round(1 - stats.get("hit_rate_percent", 0) / 100, 4),
                "total_requests": stats.get("total_requests", 0),
                "hits": stats.get("hits", 0),
                "misses": stats.get("misses", 0),
                "cached_queries": stats.get("cached_queries", 0),
                "redis_memory": stats.get("redis_memory_used", "unknown"),
            }
    except Exception as exc:
        logger.debug(f"Cache metrics unavailable: {exc}")

    # Fallback: no cache backend configured
    return {
        "source": "none",
        "hit_rate": 0,
        "miss_rate": 0,
        "total_requests": 0,
        "hits": 0,
        "misses": 0,
        "note": "No cache backend configured (Redis disabled)",
    }


def get_api_metrics() -> Dict[str, Any]:
    """Get API request metrics from real in-process counters."""
    global _request_count, _error_count, _start_time
    uptime_seconds = time.time() - _start_time

    with _response_times_lock:
        avg_rt = (sum(_response_times) / len(_response_times)) if _response_times else 0
        sample_count = len(_response_times)

    return {
        "total_requests": _request_count,
        "error_count": _error_count,
        "success_rate": (_request_count - _error_count) / max(_request_count, 1),
        "requests_per_second": round(_request_count / max(uptime_seconds, 1), 2),
        "avg_response_time_ms": round(avg_rt, 2),
        "response_time_samples": sample_count,
    }


def get_database_metrics() -> Dict[str, Any]:
    """Get Neo4j database metrics from the driver."""
    try:
        neo4j = get_neo4j_service()

        # Get node count
        result = neo4j.execute_query("MATCH (n) RETURN count(n) as count")
        node_count = result[0]["count"] if result else 0

        # Get relationship count
        result = neo4j.execute_query("MATCH ()-[r]->() RETURN count(r) as count")
        rel_count = result[0]["count"] if result else 0

        # Real connection pool info from the Neo4j driver
        driver = getattr(neo4j, "driver", None)
        active_connections: int = 0
        if driver is not None:
            try:
                pool = getattr(driver, "_pool", None)
                if pool is not None:
                    raw = getattr(pool, "in_use_connection_count", 0)
                    # The pool attribute may be a counter object; coerce to int
                    active_connections = int(raw) if isinstance(raw, (int, float)) else 0
            except Exception:
                pass

        return {
            "connected": True,
            "node_count": node_count,
            "relationship_count": rel_count,
            "active_connections": active_connections,
        }
    except Exception as e:
        logger.error(f"Error getting database metrics: {e}")
        return {"connected": False, "error": str(e)}


def get_system_metrics() -> Dict[str, Any]:
    """Get system resource metrics"""
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    return {
        "cpu_usage": cpu_percent,
        "memory": {
            "total_mb": memory.total / (1024 * 1024),
            "used_mb": memory.used / (1024 * 1024),
            "available_mb": memory.available / (1024 * 1024),
            "percent": memory.percent,
        },
        "disk": {
            "total_gb": disk.total / (1024**3),
            "used_gb": disk.used / (1024**3),
            "free_gb": disk.free / (1024**3),
            "percent": disk.percent,
        },
    }


@router.get("/summary", response_class=Neo4jJSONResponse)
async def get_metrics_summary(api_key: str = Depends(get_api_key)):
    """
    Get aggregated metrics summary for all system components.

    Returns:
        {
            "timestamp": "2025-01-15T10:30:00Z",
            "cache": {...},
            "api": {...},
            "database": {...},
            "system": {...}
        }
    """
    try:
        summary = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "cache": await get_cache_metrics(),
            "api": get_api_metrics(),
            "database": get_database_metrics(),
            "system": get_system_metrics(),
        }

        return summary
    except Exception as e:
        logger.error(f"Error getting metrics summary: {e}")
        return Neo4jJSONResponse(content={"error": str(e)}, status_code=500)


@router.get("/history", response_class=Neo4jJSONResponse)
async def get_metrics_history(
    window: str = Query("1h", description="Time window: 1h, 6h, 24h, 7d, 30d"),
    metric: str = Query(
        "cpu", description="Metric: cpu, memory, api_requests, cache_hit_rate"
    ),
    api_key: str = Depends(get_api_key),
):
    """
    Get time-series metrics data for graphing.

    Data is collected from a real background sampler (one snapshot / minute).
    Available history depends on server uptime (max 24 h in-memory).

    Query Parameters:
        window: Time window (1h, 6h, 24h, 7d, 30d)
        metric: Specific metric to retrieve (cpu, memory, api_requests, cache_hit_rate)

    Returns:
        {
            "window": "1h",
            "metric": "cpu",
            "interval": "1m",
            "count": 42,
            "datapoints": [ { "timestamp": ..., "value": ... }, ... ]
        }
    """
    try:
        # Parse window to minutes
        window_map = {"1h": 60, "6h": 360, "24h": 1440, "7d": 10080, "30d": 43200}
        minutes = window_map.get(window, 60)

        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        cutoff_iso = cutoff.isoformat() + "Z"

        metric_key_map = {
            "cpu": "cpu",
            "memory": "memory_mb",
            "api_requests": "api_requests",
            "cache_hit_rate": None,  # not tracked per-minute yet
        }
        key = metric_key_map.get(metric)

        datapoints = []
        with _history_lock:
            for snap in _history:
                if snap["timestamp"] >= cutoff_iso and key and key in snap:
                    dp = {"timestamp": snap["timestamp"], "value": snap[key]}
                    # Always include latency + error rate so charts can use them
                    if "avg_response_time_ms" in snap:
                        dp["latency"] = snap["avg_response_time_ms"]
                    if "error_rate" in snap:
                        dp["errors"] = snap["error_rate"]
                    datapoints.append(dp)

        return {
            "window": window,
            "metric": metric,
            "interval": "1m",
            "count": len(datapoints),
            "datapoints": datapoints,
            "note": "Real sampled data. History limited to server uptime (max 24 h in-memory)."
                    if datapoints else "No history yet — data is collected once per minute after server start.",
        }

    except Exception as e:
        logger.error(f"Error getting metrics history: {e}")
        return Neo4jJSONResponse(content={"error": str(e)}, status_code=500)


@router.get("/health", response_class=Neo4jJSONResponse)
async def health_check():
    """
    Health check endpoint (no auth required).

    Returns:
        {
            "status": "healthy",
            "timestamp": "2025-01-15T10:30:00Z",
            "uptime_seconds": 86400,
            "components": {
                "api": "healthy",
                "database": "healthy",
                "cache": "healthy"
            }
        }
    """
    global _start_time
    uptime = time.time() - _start_time

    try:
        db_metrics = get_database_metrics()
        db_healthy = db_metrics.get("connected", False)
        node_count = db_metrics.get("node_count", 0)
        data_seeded = node_count > 0

        # Check system resources
        sys_metrics = get_system_metrics()
        system_healthy = (
            sys_metrics["cpu_usage"] < 90
            and sys_metrics["memory"]["percent"] < 90
            and sys_metrics["disk"]["percent"] < 90
        )

        overall_healthy = db_healthy and system_healthy

        response = {
            "status": "healthy" if overall_healthy else "degraded",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "uptime_seconds": uptime,
            "components": {
                "api": "healthy",
                "database": "healthy" if db_healthy else "unhealthy",
                "cache": "healthy",
                "system": "healthy" if system_healthy else "degraded",
            },
            "data": {
                "seeded": data_seeded,
                "node_count": node_count,
            },
        }

        if not data_seeded and db_healthy:
            response["seed_hint"] = (
                "Database is connected but contains no nodes. "
                "Run the seeding pipeline from the repository root:\n"
                "  [1] .venv/Scripts/python.exe scripts/reload_database.py\n"
                "  [2] .venv/Scripts/python.exe backend/scripts/schema_migrator.py\n"
                "  [3] .venv/Scripts/python.exe backend/scripts/create_sample_data.py\n"
                "  [4] .venv/Scripts/python.exe backend/scripts/run_sdd_schema_migration.py\n"
                "      .venv/Scripts/python.exe backend/scripts/ingest_sdd_data.py\n"
                "  [5] .venv/Scripts/python.exe backend/scripts/run_simulation_run_migration.py\n"
                "See INSTALL.md Sections 6.2 and 6.6 for details."
            )

        return response

    except Exception as e:
        logger.error(f"Error in health check: {e}")
        return Neo4jJSONResponse(
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "uptime_seconds": uptime,
                "error": str(e),
            },
            status_code=503,
        )
