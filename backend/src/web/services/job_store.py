"""
Persistent Job Store Service
Stores upload job status in Redis with automatic expiration
"""

import json
from typing import Optional, Dict, Any
from datetime import timedelta
from loguru import logger

from src.web.services.redis_service import get_redis_service


class JobStore:
    """
    Persistent storage for upload jobs using Redis.
    Provides CRUD operations with automatic expiration.
    """

    def __init__(self, ttl_hours: int = 24):
        """
        Initialize job store

        Args:
            ttl_hours: Time to live for job data in hours (default: 24)
        """
        self.ttl = timedelta(hours=ttl_hours)
        self.key_prefix = "upload_job:"

    async def _get_redis(self):
        """Get Redis service instance"""
        return await get_redis_service()

    def _make_key(self, job_id: str) -> str:
        """Create Redis key for job"""
        return f"{self.key_prefix}{job_id}"

    async def create(self, job_id: str, job_data: Dict[str, Any]) -> bool:
        """
        Create a new job entry

        Args:
            job_id: Unique job identifier
            job_data: Job status data (status, filename, progress, etc.)

        Returns:
            True if created successfully
        """
        try:
            redis = await self._get_redis()
            if not redis or not await redis.is_connected():
                logger.warning("Redis not available, job will not persist")
                return False

            key = self._make_key(job_id)
            value = json.dumps(job_data)

            await redis.client.setex(key, self.ttl, value)
            logger.debug(f"Created job {job_id} in Redis")
            return True

        except Exception as e:
            logger.error(f"Failed to create job in Redis: {e}")
            return False

    async def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job status

        Args:
            job_id: Job identifier

        Returns:
            Job data dict or None if not found
        """
        try:
            redis = await self._get_redis()
            if not redis or not await redis.is_connected():
                return None

            key = self._make_key(job_id)
            value = await redis.client.get(key)

            if value:
                return json.loads(value)
            return None

        except Exception as e:
            logger.error(f"Failed to get job from Redis: {e}")
            return None

    async def update(self, job_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update job status (partial update)

        Args:
            job_id: Job identifier
            updates: Fields to update

        Returns:
            True if updated successfully
        """
        try:
            redis = await self._get_redis()
            if not redis or not await redis.is_connected():
                return False

            # Get existing data
            current = await self.get(job_id)
            if not current:
                logger.warning(f"Job {job_id} not found for update")
                return False

            # Merge updates
            current.update(updates)

            # Save back
            key = self._make_key(job_id)
            value = json.dumps(current)
            await redis.client.setex(key, self.ttl, value)

            logger.debug(f"Updated job {job_id} in Redis")
            return True

        except Exception as e:
            logger.error(f"Failed to update job in Redis: {e}")
            return False

    async def delete(self, job_id: str) -> bool:
        """
        Delete job entry

        Args:
            job_id: Job identifier

        Returns:
            True if deleted
        """
        try:
            redis = await self._get_redis()
            if not redis or not await redis.is_connected():
                return False

            key = self._make_key(job_id)
            await redis.client.delete(key)

            logger.debug(f"Deleted job {job_id} from Redis")
            return True

        except Exception as e:
            logger.error(f"Failed to delete job from Redis: {e}")
            return False

    async def list_all(self) -> Dict[str, Dict[str, Any]]:
        """
        List all active jobs

        Returns:
            Dictionary of job_id -> job_data
        """
        try:
            redis = await self._get_redis()
            if not redis or not await redis.is_connected():
                return {}

            pattern = f"{self.key_prefix}*"
            keys = await redis.client.keys(pattern)

            jobs = {}
            for key in keys:
                job_id = key.decode("utf-8").replace(self.key_prefix, "")
                job_data = await self.get(job_id)
                if job_data:
                    jobs[job_id] = job_data

            return jobs

        except Exception as e:
            logger.error(f"Failed to list jobs from Redis: {e}")
            return {}


# Global job store instance
_job_store: Optional[JobStore] = None


def get_job_store() -> JobStore:
    """Get or create job store instance"""
    global _job_store
    if _job_store is None:
        _job_store = JobStore(ttl_hours=24)
    return _job_store
