"""
Neo4j Query Cache Service with Redis Backend
Implements cache-aside pattern for query result caching
"""

import hashlib
import json
from typing import Any, Callable, Dict, List, Optional

from loguru import logger


class QueryCache:
    """
    Redis-backed query result caching implementing cache-aside pattern

    Flow:
    1. Check cache (GET from Redis)
    2. If cache miss, execute query against Neo4j
    3. Store result in cache with TTL
    4. Return result

    Features:
    - Deterministic cache keys from query + parameters
    - Configurable TTL policies per query type
    - Pattern-based cache invalidation
    - Cache statistics tracking
    - Graceful degradation if Redis unavailable
    """

    # Cache TTL presets (seconds)
    TTL_QUERY_SHORT = 300  # 5 min - frequently changing data
    TTL_QUERY_MEDIUM = 900  # 15 min - moderately stable data
    TTL_QUERY_LONG = 3600  # 1 hour - static/reference data
    TTL_AGGREGATION = 900  # 15 min - statistics/counts
    TTL_METADATA = 3600  # 1 hour - schema/labels
    TTL_SEARCH = 300  # 5 min - search results

    def __init__(self, redis_service=None, prefix: str = "mbse:qcache"):
        """
        Initialize query cache

        Args:
            redis_service: RedisService instance
            prefix: Cache key prefix namespace
        """
        self.redis = redis_service
        self.prefix = prefix
        self.enabled = redis_service is not None and redis_service.client is not None

        if not self.enabled:
            logger.warning("⚠️  Query caching disabled - Redis unavailable")
        else:
            logger.info(f"✅ Query caching enabled (prefix: {prefix})")

    # =========================================================================
    # CACHE KEY GENERATION
    # =========================================================================

    def _generate_key(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: str = "neo4j",
    ) -> str:
        """
        Generate deterministic cache key from query + parameters

        Args:
            query: Cypher query string
            parameters: Query parameters dict
            database: Database name

        Returns:
            Cache key string
        """
        # Normalize query (strip extra whitespace)
        normalized = " ".join(query.split())

        # Create hash input
        cache_data = {"query": normalized, "params": parameters or {}, "db": database}

        # Generate SHA256 hash (16 char truncated)
        hash_input = json.dumps(cache_data, sort_keys=True)
        cache_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16]

        return f"{self.prefix}:{cache_hash}"

    # =========================================================================
    # CORE CACHE OPERATIONS
    # =========================================================================

    async def get(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: str = "neo4j",
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached query result

        Args:
            query: Cypher query
            parameters: Query parameters
            database: Database name

        Returns:
            Cached result list or None on cache miss
        """
        if not self.enabled:
            return None

        try:
            key = self._generate_key(query, parameters, database)
            cached = await self.redis.cache_get(key)

            if cached is not None:
                logger.debug(f"Cache HIT: {key[:40]}...")
                await self._record_stat("hits")
                return cached

            logger.debug(f"Cache MISS: {key[:40]}...")
            await self._record_stat("misses")
            return None

        except Exception as e:
            logger.error(f"Cache GET error: {e}")
            return None

    async def set(
        self,
        query: str,
        result: List[Dict[str, Any]],
        parameters: Optional[Dict[str, Any]] = None,
        database: str = "neo4j",
        ttl: int = TTL_QUERY_SHORT,
    ) -> bool:
        """
        Store query result in cache

        Args:
            query: Cypher query
            result: Query result to cache
            parameters: Query parameters
            database: Database name
            ttl: Time-to-live in seconds

        Returns:
            True if cached, False otherwise
        """
        if not self.enabled:
            return False

        try:
            key = self._generate_key(query, parameters, database)
            success = await self.redis.cache_set(key, result, ttl)

            if success:
                logger.debug(f"Cache SET: {key[:40]}... (TTL: {ttl}s)")

            return success

        except Exception as e:
            logger.error(f"Cache SET error: {e}")
            return False

    async def get_or_execute(
        self,
        query: str,
        execute_fn: Callable,
        parameters: Optional[Dict[str, Any]] = None,
        database: str = "neo4j",
        ttl: int = TTL_QUERY_SHORT,
    ) -> List[Dict[str, Any]]:
        """
        Cache-aside pattern: Get from cache or execute and cache

        Args:
            query: Cypher query
            execute_fn: Function to execute on cache miss
            parameters: Query parameters
            database: Database name
            ttl: Cache TTL

        Returns:
            Query results (cached or fresh)
        """
        # Check cache first
        cached = await self.get(query, parameters, database)

        if cached is not None:
            return cached

        # Cache miss - execute query
        result = execute_fn()

        # Store in cache
        await self.set(query, result, parameters, database, ttl)

        return result

    # =========================================================================
    # CACHE INVALIDATION
    # =========================================================================

    async def invalidate(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: str = "neo4j",
    ) -> bool:
        """
        Invalidate specific cached query

        Args:
            query: Cypher query
            parameters: Query parameters
            database: Database name

        Returns:
            True if invalidated
        """
        if not self.enabled:
            return False

        try:
            key = self._generate_key(query, parameters, database)
            deleted = await self.redis.delete(key)

            if deleted > 0:
                logger.debug(f"Cache INVALIDATE: {key[:40]}...")

            return deleted > 0

        except Exception as e:
            logger.error(f"Cache INVALIDATE error: {e}")
            return False

    async def invalidate_pattern(self, pattern: str = "*") -> int:
        """
        Invalidate all cache entries matching pattern

        Args:
            pattern: Key pattern (e.g., "mbse:qcache:*")

        Returns:
            Number of keys deleted
        """
        if not self.enabled:
            return 0

        try:
            full_pattern = f"{self.prefix}:{pattern}"
            deleted = await self.redis.cache_clear(full_pattern)

            logger.info(f"Cache INVALIDATE PATTERN: {pattern} ({deleted} keys)")

            return deleted

        except Exception as e:
            logger.error(f"Cache INVALIDATE PATTERN error: {e}")
            return 0

    async def clear_all(self) -> int:
        """
        Clear all cached queries

        Returns:
            Number of keys cleared
        """
        if not self.enabled:
            return 0

        try:
            pattern = f"{self.prefix}:*"
            deleted = await self.redis.cache_clear(pattern)

            logger.warning(f"⚠️  Cache CLEAR ALL: {deleted} keys")

            return deleted

        except Exception as e:
            logger.error(f"Cache CLEAR ALL error: {e}")
            return 0

    # =========================================================================
    # STATISTICS & MONITORING
    # =========================================================================

    async def _record_stat(self, stat_type: str):
        """Record cache statistic (hits/misses)"""
        try:
            stat_key = f"{self.prefix}:stats:{stat_type}"
            await self.redis.client.incr(stat_key)
        except Exception:
            pass

    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get cache performance statistics

        Returns:
            Stats dictionary
        """
        if not self.enabled:
            return {"enabled": False, "message": "Redis caching disabled"}

        try:
            hits_key = f"{self.prefix}:stats:hits"
            misses_key = f"{self.prefix}:stats:misses"

            hits = int(await self.redis.get(hits_key) or 0)
            misses = int(await self.redis.get(misses_key) or 0)

            total = hits + misses
            hit_rate = (hits / total * 100) if total > 0 else 0

            # Count cached queries
            pattern = f"{self.prefix}:*"
            keys = await self.redis.keys(pattern)
            # Filter out stats keys
            cached_count = len([k for k in keys if b":stats:" not in k])

            # Redis memory info
            info = await self.redis.info()

            return {
                "enabled": True,
                "hits": hits,
                "misses": misses,
                "total_requests": total,
                "hit_rate_percent": round(hit_rate, 2),
                "cached_queries": cached_count,
                "redis_memory_used": info.get("used_memory_human", "unknown"),
            }

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"enabled": True, "error": str(e)}

    async def reset_statistics(self) -> bool:
        """Reset cache statistics counters"""
        if not self.enabled:
            return False

        try:
            hits_key = f"{self.prefix}:stats:hits"
            misses_key = f"{self.prefix}:stats:misses"

            await self.redis.delete(hits_key, misses_key)
            logger.info("Cache statistics reset")
            return True

        except Exception as e:
            logger.error(f"Error resetting stats: {e}")
            return False


# ============================================================================
# GLOBAL CACHE INSTANCE
# ============================================================================

_query_cache: Optional[QueryCache] = None


async def get_query_cache() -> Optional[QueryCache]:
    """Get global query cache instance"""
    global _query_cache

    if _query_cache is None:
        from src.web.services.redis_service import get_redis_service

        redis = await get_redis_service()
        _query_cache = QueryCache(redis)

    return _query_cache


def set_query_cache(cache: QueryCache):
    """Set global query cache instance"""
    global _query_cache
    _query_cache = cache
