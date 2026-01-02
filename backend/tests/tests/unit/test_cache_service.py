"""
Unit tests for CacheService
Tests TTL caching, decorators, and cache invalidation
"""

import sys
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from web.services.cache_service import (
    TTLCache,
    cache_node,
    cache_search,
    cache_stats,
    cached,
    get_cache,
    get_cache_stats,
    invalidate_cache,
)


class TestTTLCache:
    """Test suite for TTLCache class"""

    @pytest.fixture
    def cache(self):
        """Create a fresh TTLCache instance"""
        return TTLCache(default_ttl_seconds=60)

    def test_initialization(self):
        """Test cache initialization with custom TTL"""
        cache = TTLCache(default_ttl_seconds=120)
        assert cache.default_ttl == 120
        assert len(cache.cache) == 0

    def test_set_and_get(self, cache):
        """Test basic set and get operations"""
        cache.set("test_key", "test_value")
        assert cache.get("test_key") == "test_value"

    def test_get_nonexistent_key(self, cache):
        """Test getting a key that doesn't exist"""
        assert cache.get("nonexistent") is None
        assert cache.get("nonexistent", default="default_value") == "default_value"

    def test_ttl_expiration(self, cache):
        """Test that cache entries expire after TTL"""
        cache.set("short_lived", "value", ttl=1)  # 1 second TTL
        assert cache.get("short_lived") == "value"

        time.sleep(1.1)  # Wait for expiration
        assert cache.get("short_lived") is None

    def test_custom_ttl(self, cache):
        """Test setting custom TTL per entry"""
        cache.set("key1", "value1", ttl=10)
        cache.set("key2", "value2", ttl=20)

        # Both should be valid immediately
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"

    def test_delete(self, cache):
        """Test deleting cache entries"""
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        cache.delete("key1")
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"

    def test_clear(self, cache):
        """Test clearing entire cache"""
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None
        assert len(cache.cache) == 0

    def test_cleanup(self, cache):
        """Test cleanup of expired entries"""
        cache.set("key1", "value1", ttl=1)
        cache.set("key2", "value2", ttl=100)

        time.sleep(1.1)
        cache.cleanup_expired()

        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"


class TestCachedDecorator:
    """Test suite for @cached decorator"""

    def test_cached_function(self):
        """Test that function results are cached"""
        call_count = {"count": 0}

        @cached(ttl=60)
        def expensive_function(x):
            call_count["count"] += 1
            return x * 2

        # First call - function should be called
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count["count"] == 1

        # Second call with same args - should use cache
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count["count"] == 1  # Not called again

        # Call with different args - function should be called
        result3 = expensive_function(10)
        assert result3 == 20
        assert call_count["count"] == 2

    def test_cached_with_kwargs(self):
        """Test caching with keyword arguments"""
        call_count = {"count": 0}

        @cached(ttl=60)
        def func_with_kwargs(a, b=10):
            call_count["count"] += 1
            return a + b

        result1 = func_with_kwargs(5, b=15)
        assert result1 == 20
        assert call_count["count"] == 1

        result2 = func_with_kwargs(5, b=15)
        assert result2 == 20
        assert call_count["count"] == 1  # Cached

        result3 = func_with_kwargs(5, b=20)
        assert result3 == 25
        assert call_count["count"] == 2  # Different args

    def test_cache_expiration(self):
        """Test that cache expires after TTL"""
        call_count = {"count": 0}

        @cached(ttl=1)
        def short_ttl_function(x):
            call_count["count"] += 1
            return x * 2

        result1 = short_ttl_function(5)
        assert call_count["count"] == 1

        time.sleep(1.1)

        result2 = short_ttl_function(5)
        assert call_count["count"] == 2  # Cache expired, called again


class TestCacheStatsDecorator:
    """Test suite for @cache_stats decorator"""

    def test_cache_stats_caching(self):
        """Test that stats are cached"""
        call_count = {"count": 0}

        @cache_stats(ttl=60)
        def get_statistics():
            call_count["count"] += 1
            return {"total_nodes": 3257, "total_relationships": 10027}

        result1 = get_statistics()
        assert result1["total_nodes"] == 3257
        assert call_count["count"] == 1

        result2 = get_statistics()
        assert result2["total_nodes"] == 3257
        assert call_count["count"] == 1  # Cached


class TestCacheNodeDecorator:
    """Test suite for @cache_node decorator"""

    def test_cache_node_by_id(self):
        """Test caching node retrieval by ID"""
        call_count = {"count": 0}

        @cache_node(ttl=60)
        def get_class(class_id):
            call_count["count"] += 1
            return {"id": class_id, "name": "TestClass"}

        result1 = get_class("123")
        assert result1["name"] == "TestClass"
        assert call_count["count"] == 1

        result2 = get_class("123")
        assert result2["name"] == "TestClass"
        assert call_count["count"] == 1  # Cached


class TestCacheSearchDecorator:
    """Test suite for @cache_search decorator"""

    def test_cache_search_results(self):
        """Test caching search results"""
        call_count = {"count": 0}

        @cache_search(ttl=60)
        def search_classes(query):
            call_count["count"] += 1
            return [{"id": "1", "name": f"{query}Class"}]

        result1 = search_classes("Person")
        assert len(result1) == 1
        assert call_count["count"] == 1

        result2 = search_classes("Person")
        assert len(result2) == 1
        assert call_count["count"] == 1  # Cached

        result3 = search_classes("Vehicle")
        assert call_count["count"] == 2  # Different query


class TestCacheManagement:
    """Test suite for cache management functions"""

    def test_get_cache(self):
        """Test getting cache instance"""
        cache1 = get_cache()
        cache2 = get_cache()
        assert cache1 is cache2  # Singleton pattern

    def test_invalidate_cache(self):
        """Test invalidating specific cache entries"""
        cache = get_cache()
        cache.set("test:key1", "value1")
        cache.set("test:key2", "value2")
        cache.set("other:key1", "value3")

        invalidate_cache("test:*")

        assert cache.get("test:key1") is None
        assert cache.get("test:key2") is None
        assert cache.get("other:key1") == "value3"

    def test_get_cache_stats(self):
        """Test retrieving cache statistics"""
        cache = get_cache()
        cache.clear()

        # Add some entries
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        stats = get_cache_stats()

        assert "entries" in stats
        assert "size" in stats
        assert "default_ttl" in stats
        assert stats["entries"] >= 2
        assert stats["size"] >= 2


class TestCacheIntegration:
    """Integration tests for cache system"""

    def test_multiple_decorators(self):
        """Test using multiple cache decorators"""
        stats_calls = {"count": 0}
        node_calls = {"count": 0}

        @cache_stats(ttl=60)
        def get_stats():
            stats_calls["count"] += 1
            return {"nodes": 100}

        @cache_node(ttl=60)
        def get_node(node_id):
            node_calls["count"] += 1
            return {"id": node_id}

        # Each decorator should have independent cache
        get_stats()
        get_stats()
        assert stats_calls["count"] == 1

        get_node("123")
        get_node("123")
        assert node_calls["count"] == 1

        # Different function, different cache
        get_node("456")
        assert node_calls["count"] == 2

    def test_cache_invalidation_scenarios(self):
        """Test various cache invalidation scenarios"""
        cache = get_cache()

        # Scenario 1: Invalidate stats cache
        cache.set("stats:get_stats", {"nodes": 100})
        invalidate_cache("stats:*")
        assert cache.get("stats:get_stats") is None

        # Scenario 2: Invalidate node cache
        cache.set("node:Class:123", {"id": "123"})
        invalidate_cache("node:*")
        assert cache.get("node:Class:123") is None

        # Scenario 3: Clear all
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
