"""
Cache Management API - FastAPI Routes
Endpoints for monitoring and controlling Redis query cache
"""

from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from src.web.services.neo4j_service import get_neo4j_service
from src.web.services.query_cache import get_query_cache
from src.web.dependencies import get_api_key


router = APIRouter(prefix="/cache", tags=["Cache Management"], dependencies=[Depends(get_api_key)])


# ============================================================================
# CACHE STATISTICS
# ============================================================================


@router.get("/stats", summary="Get cache statistics")
async def get_cache_statistics():
    """
    Get query cache performance statistics

    Returns:
    - enabled: Whether caching is enabled
    - hits: Number of cache hits
    - misses: Number of cache misses
    - total_requests: Total cache requests
    - hit_rate_percent: Cache hit rate percentage
    - cached_queries: Number of cached query results
    - redis_memory_used: Redis memory usage

    Example:
    ```json
    {
        "enabled": true,
        "hits": 1523,
        "misses": 487,
        "total_requests": 2010,
        "hit_rate_percent": 75.77,
        "cached_queries": 342,
        "redis_memory_used": "12.5M"
    }
    ```
    """
    try:
        cache = await get_query_cache()

        if not cache or not cache.enabled:
            return {
                "enabled": False,
                "message": "Query caching disabled - Redis not available",
            }

        stats = await cache.get_statistics()

        return {"status": "success", "cache": stats}

    except Exception as e:
        logger.error(f"Error getting cache statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cache statistics: {str(e)}",
        )


@router.post("/stats/reset", summary="Reset cache statistics")
async def reset_cache_statistics():
    """
    Reset cache hit/miss counters

    Note: This only resets statistics counters, not cached data
    """
    try:
        cache = await get_query_cache()

        if not cache or not cache.enabled:
            return {"success": False, "message": "Caching disabled"}

        success = await cache.reset_statistics()

        return {"success": success, "message": "Cache statistics reset"}

    except Exception as e:
        logger.error(f"Error resetting cache statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset statistics: {str(e)}",
        )


# ============================================================================
# CACHE INVALIDATION
# ============================================================================


@router.post("/clear", summary="Clear all cached queries")
async def clear_cache():
    """
    Clear all cached query results

    This will force all subsequent queries to hit the database until results
    are cached again. Use with caution in production.

    Returns:
    - cleared: Number of cache keys cleared
    """
    try:
        cache = await get_query_cache()

        if not cache or not cache.enabled:
            return {"success": False, "message": "Caching disabled"}

        cleared = await cache.clear_all()

        logger.warning(f"⚠️  Cache cleared: {cleared} keys deleted")

        return {
            "success": True,
            "cleared": cleared,
            "message": f"Cleared {cleared} cached queries",
        }

    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache: {str(e)}",
        )


@router.post("/invalidate/{pattern}", summary="Invalidate cache by pattern")
async def invalidate_cache_pattern(pattern: str):
    """
    Invalidate cached queries matching a pattern

    Args:
        pattern: Key pattern to match (e.g., "node:*", "requirement:*")

    Examples:
    - `/cache/invalidate/*` - Clear all cached queries
    - `/cache/invalidate/node:*` - Clear all node queries
    - `/cache/invalidate/requirement:*` - Clear requirement queries

    Returns:
    - invalidated: Number of cache keys invalidated
    """
    try:
        cache = await get_query_cache()

        if not cache or not cache.enabled:
            return {"success": False, "message": "Caching disabled"}

        invalidated = await cache.invalidate_pattern(pattern)

        logger.info(f"Cache pattern invalidated: {pattern} ({invalidated} keys)")

        return {
            "success": True,
            "invalidated": invalidated,
            "pattern": pattern,
            "message": f"Invalidated {invalidated} cached queries matching '{pattern}'",
        }

    except Exception as e:
        logger.error(f"Error invalidating cache pattern: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to invalidate cache: {str(e)}",
        )


# ============================================================================
# CACHE CONFIGURATION
# ============================================================================


@router.get("/config", summary="Get cache configuration")
async def get_cache_config():
    """
    Get cache configuration and TTL policies

    Returns cache TTL presets and configuration details
    """
    try:
        from src.web.services.query_cache import QueryCache

        cache = await get_query_cache()

        config = {
            "enabled": cache is not None and cache.enabled,
            "prefix": cache.prefix if cache else "mbse:qcache",
            "ttl_policies": {
                "query_short": {
                    "seconds": QueryCache.TTL_QUERY_SHORT,
                    "description": "5 minutes - Frequently changing data",
                    "use_case": "Real-time queries, user-specific data",
                },
                "query_medium": {
                    "seconds": QueryCache.TTL_QUERY_MEDIUM,
                    "description": "15 minutes - Moderately stable data",
                    "use_case": "General queries, list operations",
                },
                "query_long": {
                    "seconds": QueryCache.TTL_QUERY_LONG,
                    "description": "1 hour - Static/reference data",
                    "use_case": "Metadata, schema, configurations",
                },
                "aggregation": {
                    "seconds": QueryCache.TTL_AGGREGATION,
                    "description": "15 minutes - Statistics and counts",
                    "use_case": "Dashboard metrics, analytics",
                },
                "metadata": {
                    "seconds": QueryCache.TTL_METADATA,
                    "description": "1 hour - Database metadata",
                    "use_case": "Labels, indexes, constraints",
                },
                "search": {
                    "seconds": QueryCache.TTL_SEARCH,
                    "description": "5 minutes - Search results",
                    "use_case": "Full-text search, filters",
                },
            },
        }

        return {"status": "success", "config": config}

    except Exception as e:
        logger.error(f"Error getting cache config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cache config: {str(e)}",
        )


# ============================================================================
# HEALTH CHECK
# ============================================================================


@router.get("/health", summary="Cache health check")
async def cache_health():
    """
    Check cache system health

    Returns:
    - healthy: Boolean indicating cache health
    - enabled: Whether caching is enabled
    - redis_connected: Whether Redis is connected
    """
    try:
        cache = await get_query_cache()

        if not cache:
            return {
                "healthy": False,
                "enabled": False,
                "message": "Cache not initialized",
            }

        if not cache.enabled:
            return {
                "healthy": False,
                "enabled": False,
                "message": "Redis not available",
            }

        # Test Redis connectivity
        try:
            await cache.redis.client.ping()
            redis_connected = True
        except Exception:
            redis_connected = False

        return {
            "healthy": redis_connected,
            "enabled": cache.enabled,
            "redis_connected": redis_connected,
            "message": (
                "Cache system healthy" if redis_connected else "Redis connection failed"
            ),
        }

    except Exception as e:
        logger.error(f"Error checking cache health: {e}")
        return {"healthy": False, "error": str(e)}
