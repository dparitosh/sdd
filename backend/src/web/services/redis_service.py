"""
Redis Service Client with Async Support
Provides connection pooling, caching, and session management
"""

import os
from typing import Any, Optional
from urllib.parse import urlparse

import redis.asyncio as aioredis
from loguru import logger
from redis.asyncio.connection import ConnectionPool


class RedisService:
    """
    Async Redis service client with connection pooling
    
    Features:
    - Async/await support
    - Connection pooling
    - Auto-reconnection
    - Health monitoring
    - Cache utilities
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        host: Optional[str] = None,
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        max_connections: int = 50
    ):
        """
        Initialize Redis service
        
        Args:
            redis_url: Redis URL (redis://host:port/db)
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password
            max_connections: Maximum connection pool size
        """
        # Allow env var override even when constructor args are not provided
        redis_url = redis_url or os.getenv("REDIS_URL")

        # Parse Redis URL if provided
        if redis_url:
            parsed = urlparse(redis_url)
            self.host = parsed.hostname or "localhost"
            self.port = parsed.port or 6379
            self.db = int(parsed.path.lstrip('/')) if parsed.path else 0
            self.password = parsed.password or password
        else:
            self.host = host or os.getenv("REDIS_HOST", "localhost")
            self.port = int(os.getenv("REDIS_PORT", str(port)))
            self.db = int(os.getenv("REDIS_DB", str(db)))
            self.password = password or os.getenv("REDIS_PASSWORD")

        self.max_connections = max_connections
        self.pool: Optional[ConnectionPool] = None
        self.client: Optional[aioredis.Redis] = None

        logger.info(f"Redis service configured: {self.host}:{self.port}/{self.db}")

    async def connect(self):
        """Establish Redis connection with pooling"""
        try:
            # Create connection pool
            self.pool = ConnectionPool(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                max_connections=self.max_connections,
                decode_responses=False,  # We'll handle decoding manually
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True
            )

            # Create Redis client
            self.client = aioredis.Redis(connection_pool=self.pool)

            # Test connection
            await self.client.ping()

            logger.info(f"✅ Connected to Redis at {self.host}:{self.port}")

        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            logger.warning("⚠️  Running without Redis - session management will be limited")
            self.client = None

    async def disconnect(self):
        """Close Redis connection"""
        try:
            if self.client:
                await self.client.close()
                logger.info("Disconnected from Redis")

            if self.pool:
                await self.pool.disconnect()

        except Exception as e:
            logger.error(f"Error disconnecting from Redis: {e}")

    async def is_connected(self) -> bool:
        """Check if Redis is connected and healthy"""
        try:
            if not self.client:
                return False

            await self.client.ping()
            return True

        except Exception:
            return False

    # =========================================================================
    # BASIC OPERATIONS
    # =========================================================================

    async def get(self, key: str) -> Optional[str]:
        """Get value by key"""
        try:
            if not self.client:
                return None

            value = await self.client.get(key)
            return value.decode('utf-8') if value else None

        except Exception as e:
            logger.error(f"Redis GET error: {e}")
            return None

    async def set(
        self,
        key: str,
        value: str,
        expire: Optional[int] = None
    ) -> bool:
        """Set key-value pair with optional expiration"""
        try:
            if not self.client:
                return False

            if expire:
                await self.client.setex(key, expire, value)
            else:
                await self.client.set(key, value)

            return True

        except Exception as e:
            logger.error(f"Redis SET error: {e}")
            return False

    async def setex(self, key: str, expire: int, value: str) -> bool:
        """Set key-value pair with expiration"""
        return await self.set(key, value, expire)

    async def delete(self, *keys: str) -> int:
        """Delete one or more keys"""
        try:
            if not self.client:
                return 0

            return await self.client.delete(*keys)

        except Exception as e:
            logger.error(f"Redis DELETE error: {e}")
            return 0

    async def exists(self, *keys: str) -> int:
        """Check if keys exist"""
        try:
            if not self.client:
                return 0

            return await self.client.exists(*keys)

        except Exception as e:
            logger.error(f"Redis EXISTS error: {e}")
            return 0

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on key"""
        try:
            if not self.client:
                return False

            return await self.client.expire(key, seconds)

        except Exception as e:
            logger.error(f"Redis EXPIRE error: {e}")
            return False

    async def ttl(self, key: str) -> int:
        """Get time-to-live for key"""
        try:
            if not self.client:
                return -2

            return await self.client.ttl(key)

        except Exception as e:
            logger.error(f"Redis TTL error: {e}")
            return -2

    # =========================================================================
    # SET OPERATIONS
    # =========================================================================

    async def sadd(self, key: str, *values: str) -> int:
        """Add members to set"""
        try:
            if not self.client:
                return 0

            return await self.client.sadd(key, *values)

        except Exception as e:
            logger.error(f"Redis SADD error: {e}")
            return 0

    async def srem(self, key: str, *values: str) -> int:
        """Remove members from set"""
        try:
            if not self.client:
                return 0

            return await self.client.srem(key, *values)

        except Exception as e:
            logger.error(f"Redis SREM error: {e}")
            return 0

    async def smembers(self, key: str) -> set:
        """Get all members of set"""
        try:
            if not self.client:
                return set()

            return await self.client.smembers(key)

        except Exception as e:
            logger.error(f"Redis SMEMBERS error: {e}")
            return set()

    async def sismember(self, key: str, value: str) -> bool:
        """Check if value is member of set"""
        try:
            if not self.client:
                return False

            return await self.client.sismember(key, value)

        except Exception as e:
            logger.error(f"Redis SISMEMBER error: {e}")
            return False

    # =========================================================================
    # HASH OPERATIONS
    # =========================================================================

    async def hset(self, key: str, field: str, value: str) -> int:
        """Set hash field"""
        try:
            if not self.client:
                return 0

            return await self.client.hset(key, field, value)

        except Exception as e:
            logger.error(f"Redis HSET error: {e}")
            return 0

    async def hget(self, key: str, field: str) -> Optional[str]:
        """Get hash field value"""
        try:
            if not self.client:
                return None

            value = await self.client.hget(key, field)
            return value.decode('utf-8') if value else None

        except Exception as e:
            logger.error(f"Redis HGET error: {e}")
            return None

    async def hgetall(self, key: str) -> dict:
        """Get all hash fields"""
        try:
            if not self.client:
                return {}

            data = await self.client.hgetall(key)
            return {
                k.decode('utf-8'): v.decode('utf-8')
                for k, v in data.items()
            }

        except Exception as e:
            logger.error(f"Redis HGETALL error: {e}")
            return {}

    async def hdel(self, key: str, *fields: str) -> int:
        """Delete hash fields"""
        try:
            if not self.client:
                return 0

            return await self.client.hdel(key, *fields)

        except Exception as e:
            logger.error(f"Redis HDEL error: {e}")
            return 0

    # =========================================================================
    # SCAN OPERATIONS
    # =========================================================================

    async def scan(
        self,
        cursor: int = 0,
        match: Optional[str] = None,
        count: int = 100
    ) -> tuple:
        """Scan keys with pattern matching"""
        try:
            if not self.client:
                return (0, [])

            return await self.client.scan(cursor, match=match, count=count)

        except Exception as e:
            logger.error(f"Redis SCAN error: {e}")
            return (0, [])

    async def keys(self, pattern: str = "*") -> list:
        """Get all keys matching pattern (use scan in production)"""
        try:
            if not self.client:
                return []

            keys = await self.client.keys(pattern)
            return [k.decode('utf-8') for k in keys]

        except Exception as e:
            logger.error(f"Redis KEYS error: {e}")
            return []

    # =========================================================================
    # CACHE UTILITIES
    # =========================================================================

    async def cache_get(self, key: str) -> Optional[Any]:
        """Get cached value (auto-deserialize JSON)"""
        import json

        try:
            value = await self.get(key)
            if value:
                return json.loads(value)
            return None

        except json.JSONDecodeError:
            return value
        except Exception as e:
            logger.error(f"Cache GET error: {e}")
            return None

    async def cache_set(
        self,
        key: str,
        value: Any,
        expire: int = 3600
    ) -> bool:
        """Set cached value (auto-serialize JSON)"""
        import json

        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            elif not isinstance(value, str):
                value = str(value)

            return await self.set(key, value, expire)

        except Exception as e:
            logger.error(f"Cache SET error: {e}")
            return False

    async def cache_delete(self, *keys: str) -> int:
        """Delete cached values"""
        return await self.delete(*keys)

    async def cache_clear(self, pattern: str = "*") -> int:
        """Clear all cache keys matching pattern"""
        try:
            keys = await self.keys(pattern)
            if keys:
                return await self.delete(*keys)
            return 0

        except Exception as e:
            logger.error(f"Cache CLEAR error: {e}")
            return 0

    # =========================================================================
    # MONITORING
    # =========================================================================

    async def info(self) -> dict:
        """Get Redis server info"""
        try:
            if not self.client:
                return {}

            info = await self.client.info()
            return info

        except Exception as e:
            logger.error(f"Redis INFO error: {e}")
            return {}

    async def dbsize(self) -> int:
        """Get number of keys in database"""
        try:
            if not self.client:
                return 0

            return await self.client.dbsize()

        except Exception as e:
            logger.error(f"Redis DBSIZE error: {e}")
            return 0

    async def flushdb(self) -> bool:
        """Flush current database (admin only)"""
        try:
            if not self.client:
                return False

            await self.client.flushdb()
            logger.warning("⚠️  Redis database flushed")
            return True

        except Exception as e:
            logger.error(f"Redis FLUSHDB error: {e}")
            return False


# ============================================================================
# GLOBAL REDIS INSTANCE
# ============================================================================

_redis_service: Optional[RedisService] = None


async def get_redis_service() -> Optional[RedisService]:
    """Get global Redis service instance"""
    global _redis_service

    if _redis_service is None:
        _redis_service = RedisService()
        await _redis_service.connect()

    return _redis_service


async def close_redis_service():
    """Close global Redis service"""
    global _redis_service

    if _redis_service:
        await _redis_service.disconnect()
        _redis_service = None
