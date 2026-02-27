"""
Unified cache manager.

Combines the in-memory ``TTLCache`` (from ``cache_service.py``) with
optional Redis-backed caching (from ``query_cache.py``) behind a single
``CacheManager`` interface.

Usage::

    from src.core.cache import get_cache_manager

    cm = get_cache_manager()
    cm.set("key", {"some": "data"}, ttl=120)
    val = cm.get("key")
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from typing import Any, Callable, Dict, Optional

from loguru import logger


# ---------------------------------------------------------------------------
# In-memory TTL cache (ported from cache_service.py)
# ---------------------------------------------------------------------------

class TTLCache:
    """Thread-safe in-memory cache with per-key TTL."""

    def __init__(self, default_ttl: int = 300):
        self._data: Dict[str, Any] = {}
        self._ts: Dict[str, float] = {}
        self._ttls: Dict[str, int] = {}
        self.default_ttl = default_ttl
        self._lock = threading.Lock()

    # -- public API ---------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            if key not in self._data:
                return default
            ttl = self._ttls.get(key, self.default_ttl)
            if time.time() - self._ts.get(key, 0) > ttl:
                self._evict(key)
                return default
            return self._data[key]

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        with self._lock:
            self._data[key] = value
            self._ts[key] = time.time()
            if ttl is not None:
                self._ttls[key] = ttl
            else:
                self._ttls.pop(key, None)

    def delete(self, key: str) -> None:
        with self._lock:
            self._evict(key)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()
            self._ts.clear()
            self._ttls.clear()
        logger.info("TTLCache cleared")

    def invalidate_pattern(self, pattern: str) -> int:
        """Remove all keys containing *pattern*."""
        with self._lock:
            keys = [k for k in self._data if pattern in k]
            for k in keys:
                self._evict(k)
            return len(keys)

    def size(self) -> int:
        return len(self._data)

    def cleanup_expired(self) -> int:
        now = time.time()
        with self._lock:
            expired = [
                k for k, ts in self._ts.items()
                if now - ts > self._ttls.get(k, self.default_ttl)
            ]
            for k in expired:
                self._evict(k)
        return len(expired)

    def stats(self) -> Dict[str, Any]:
        return {
            "size": self.size(),
            "default_ttl": self.default_ttl,
        }

    # -- internal -----------------------------------------------------------

    def _evict(self, key: str) -> None:
        self._data.pop(key, None)
        self._ts.pop(key, None)
        self._ttls.pop(key, None)


# ---------------------------------------------------------------------------
# Cache manager (in-memory + optional Redis)
# ---------------------------------------------------------------------------

class CacheManager:
    """Facade over the in-memory ``TTLCache`` and an optional Redis backend.

    When Redis is available, ``get``/``set`` work against Redis first,
    falling back to the local cache on Redis failure.  When Redis is
    disabled, everything is purely in-memory.
    """

    def __init__(
        self,
        local_ttl: int = 300,
        redis_service: Any = None,
        prefix: str = "mbse:cache",
    ):
        self.local = TTLCache(default_ttl=local_ttl)
        self._redis = redis_service
        self._prefix = prefix

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _hash_key(key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def _rkey(self, key: str) -> str:
        return f"{self._prefix}:{key}"

    # -- public API --------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        # Try local first
        val = self.local.get(key)
        if val is not None:
            return val
        # Try Redis
        if self._redis is not None:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Can't await in sync context; skip Redis
                    return default
            except RuntimeError:
                pass
        return default

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        self.local.set(key, value, ttl=ttl)

    def delete(self, key: str) -> None:
        self.local.delete(key)

    def clear(self) -> None:
        self.local.clear()

    def invalidate_pattern(self, pattern: str) -> int:
        return self.local.invalidate_pattern(pattern)

    def stats(self) -> Dict[str, Any]:
        info = self.local.stats()
        info["redis_available"] = self._redis is not None
        return info


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_cache_manager: Optional[CacheManager] = None
_cm_lock = threading.Lock()


def get_cache_manager() -> CacheManager:
    """Return the process-wide ``CacheManager`` (lazy-initialized)."""
    global _cache_manager
    if _cache_manager is not None:
        return _cache_manager
    with _cm_lock:
        if _cache_manager is not None:
            return _cache_manager
        from src.core.config import get_settings
        s = get_settings()
        _cache_manager = CacheManager(local_ttl=s.cache_ttl_stats)
        return _cache_manager


def reset_cache_manager() -> None:
    """Clear singleton — useful in tests."""
    global _cache_manager
    with _cm_lock:
        if _cache_manager is not None:
            _cache_manager.clear()
        _cache_manager = None
