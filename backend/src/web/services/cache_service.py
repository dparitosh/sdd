"""
Cache Service - In-memory caching for frequently accessed data
Uses Python's built-in functools.lru_cache and custom TTL cache
"""

import time
import threading
from datetime import datetime, timedelta
from functools import lru_cache, wraps
from typing import Any, Callable, Optional

from loguru import logger


class TTLCache:
    """
    Time-To-Live cache that expires entries after a specified duration.
    Thread-safe implementation using a reentrant lock.
    """

    def __init__(self, default_ttl_seconds: int = 300):
        """
        Initialize TTL cache.

        Args:
            default_ttl_seconds: Default TTL in seconds (default: 5 minutes)
        """
        self.default_ttl = default_ttl_seconds
        self.cache = {}
        self.timestamps = {}
        self.custom_ttls = {}  # Store per-key custom TTLs
        self._lock = threading.RLock()

    def get(self, key: str, default: Any = None) -> Optional[Any]:
        """
        Get value from cache if not expired.

        Args:
            key: Cache key
            default: Default value to return if key not found (default: None)

        Returns:
            Cached value, default value if expired/missing
        """
        with self._lock:
            if key not in self.cache:
                return default

            # Check if expired (use custom TTL if set, otherwise default)
            timestamp = self.timestamps.get(key, 0)
            ttl = self.custom_ttls.get(key, self.default_ttl)
            if time.time() - timestamp > ttl:
                self.delete(key)
                return default

            return self.cache[key]

    def set(self, key: str, value: Any, ttl: int = None):
        """
        Set value in cache with optional custom TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Custom TTL in seconds (optional, uses default if not provided)
        """
        with self._lock:
            self.cache[key] = value
            self.timestamps[key] = time.time()

            # Store custom TTL if provided
            if ttl is not None:
                self.custom_ttls[key] = ttl
            elif key in self.custom_ttls:
                # Remove custom TTL if key is being reset with default
                del self.custom_ttls[key]

    def delete(self, key: str):
        """Delete key from cache"""
        with self._lock:
            self.cache.pop(key, None)
            self.timestamps.pop(key, None)
            self.custom_ttls.pop(key, None)

    def clear(self):
        """Clear all cache entries"""
        with self._lock:
            self.cache.clear()
            self.timestamps.clear()
            self.custom_ttls.clear()
            logger.info("Cache cleared")

    def size(self) -> int:
        """Get number of cached entries"""
        with self._lock:
            return len(self.cache)

    def cleanup_expired(self):
        """Remove expired entries from cache"""
        with self._lock:
            current_time = time.time()
            expired_keys = []

            for key, timestamp in self.timestamps.items():
                ttl = self.custom_ttls.get(key, self.default_ttl)
                if current_time - timestamp > ttl:
                    expired_keys.append(key)

            for key in expired_keys:
                self.delete(key)

            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")


# Global cache instance
_cache = TTLCache(default_ttl_seconds=300)  # 5 minutes default


def get_cache() -> TTLCache:
    """Get global cache instance"""
    return _cache


def cached(ttl: int = 300, key_prefix: str = ""):
    """
    Decorator to cache function results with TTL.

    Args:
        ttl: Time-to-live in seconds
        key_prefix: Prefix for cache keys

    Usage:
        @cached(ttl=600, key_prefix="stats")
        def get_statistics():
            return expensive_computation()
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            key_parts = [key_prefix, func.__name__]
            key_parts.extend([str(arg) for arg in args])
            key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
            cache_key = ":".join(filter(None, key_parts))

            # Try to get from cache
            cached_value = _cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_value

            # Execute function and cache result
            logger.debug(f"Cache miss: {cache_key}")
            result = func(*args, **kwargs)
            _cache.set(cache_key, result, ttl=ttl)

            return result

        # Add cache control methods
        wrapper.cache_clear = lambda: _cache.clear()
        wrapper.cache_info = lambda: {"size": _cache.size(), "ttl": ttl}

        return wrapper

    return decorator


# Specialized cache decorators for common use cases


def cache_stats(ttl: int = 60):
    """Cache statistics queries (default: 1 minute)"""
    return cached(ttl=ttl, key_prefix="stats")


def cache_node(ttl: int = 300):
    """Cache node queries (default: 5 minutes)"""
    return cached(ttl=ttl, key_prefix="node")


def cache_search(ttl: int = 120):
    """Cache search results (default: 2 minutes)"""
    return cached(ttl=ttl, key_prefix="search")


# Cache invalidation helpers


def invalidate_cache(pattern: str = None):
    """
    Invalidate cache entries matching pattern.
    If no pattern provided, clears entire cache.

    Args:
        pattern: Key pattern to match (e.g., "stats:*", "node:Class:*")
    """
    if pattern is None:
        _cache.clear()
        logger.info("All cache invalidated")
    else:
        # Simple pattern matching
        keys_to_delete = [
            key for key in _cache.cache.keys() if pattern.replace("*", "") in key
        ]

        for key in keys_to_delete:
            _cache.delete(key)

        logger.info(
            f"Invalidated {len(keys_to_delete)} cache entries matching '{pattern}'"
        )


def invalidate_node_cache(label: str = None, uid: str = None):
    """
    Invalidate node-related cache entries.

    Args:
        label: Node label to invalidate (optional)
        uid: Specific node UID to invalidate (optional)
    """
    if uid:
        pattern = f"node:*:{uid}"
    elif label:
        pattern = f"node:{label}:*"
    else:
        pattern = "node:*"

    invalidate_cache(pattern)


def invalidate_stats_cache():
    """Invalidate all statistics cache"""
    invalidate_cache("stats:*")


# Background cache cleanup (optional)


def start_cache_cleanup_task(interval: int = 60):
    """
    Start background task to cleanup expired cache entries.

    Args:
        interval: Cleanup interval in seconds

    Note: This requires a background worker (e.g., APScheduler)
    """
    import threading

    def cleanup_loop():
        while True:
            time.sleep(interval)
            _cache.cleanup_expired()

    thread = threading.Thread(target=cleanup_loop, daemon=True)
    thread.start()
    logger.info(f"Cache cleanup task started (interval: {interval}s)")


# Cache statistics


def get_cache_stats() -> dict:
    """Get cache statistics"""
    return {
        "size": _cache.size(),
        "default_ttl": _cache.default_ttl,
        "entries": len(_cache.cache),
        "oldest_entry": min(_cache.timestamps.values()) if _cache.timestamps else None,
        "newest_entry": max(_cache.timestamps.values()) if _cache.timestamps else None,
    }
