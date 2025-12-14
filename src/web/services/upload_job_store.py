"""
Upload Job Storage Service - Persistent job tracking
Stores upload job status in Redis for persistence across server restarts
Falls back to in-memory storage if Redis is unavailable
"""

import json
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from loguru import logger

from src.web.services.redis_service import get_redis_service


class UploadJobStore:
    """
    Persistent storage for upload job status.
    Uses Redis for persistence with automatic cleanup of old jobs.
    Falls back to in-memory dict if Redis unavailable.
    """
    
    JOB_PREFIX = "upload_job:"
    JOB_TTL = 86400  # 24 hours in seconds
    
    def __init__(self):
        """Initialize job store"""
        self._memory_store: Dict[str, dict] = {}
        self._redis_available = False
        self._redis_client = None
    
    async def _get_redis(self):
        """Get Redis client if available"""
        if self._redis_client is None:
            try:
                redis_service = await get_redis_service()
                if redis_service and await redis_service.is_connected():
                    self._redis_client = redis_service.client
                    self._redis_available = True
                    logger.info("Upload job store using Redis for persistence")
                else:
                    logger.warning("Redis unavailable, using in-memory job store")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}, using in-memory job store")
        
        return self._redis_client
    
    async def save_job(self, job_id: str, job_data: dict) -> bool:
        """
        Save job status to storage
        
        Args:
            job_id: Unique job identifier
            job_data: Job status data dictionary
            
        Returns:
            True if saved successfully
        """
        try:
            # Add timestamp
            job_data["updated_at"] = datetime.utcnow().isoformat()
            
            redis = await self._get_redis()
            if redis and self._redis_available:
                # Save to Redis with TTL
                key = f"{self.JOB_PREFIX}{job_id}"
                await redis.setex(
                    key,
                    self.JOB_TTL,
                    json.dumps(job_data)
                )
                logger.debug(f"Saved job {job_id} to Redis")
            else:
                # Fallback to memory
                self._memory_store[job_id] = job_data
                logger.debug(f"Saved job {job_id} to memory")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save job {job_id}: {e}")
            # Fallback to memory on error
            self._memory_store[job_id] = job_data
            return False
    
    async def get_job(self, job_id: str) -> Optional[dict]:
        """
        Get job status from storage
        
        Args:
            job_id: Unique job identifier
            
        Returns:
            Job data dictionary or None if not found
        """
        try:
            redis = await self._get_redis()
            if redis and self._redis_available:
                # Try Redis first
                key = f"{self.JOB_PREFIX}{job_id}"
                data = await redis.get(key)
                if data:
                    return json.loads(data)
                logger.debug(f"Job {job_id} not found in Redis")
            
            # Fallback to memory
            return self._memory_store.get(job_id)
            
        except Exception as e:
            logger.error(f"Failed to get job {job_id}: {e}")
            return self._memory_store.get(job_id)
    
    async def update_job(self, job_id: str, updates: dict) -> bool:
        """
        Update job status (partial update)
        
        Args:
            job_id: Unique job identifier
            updates: Dictionary of fields to update
            
        Returns:
            True if updated successfully
        """
        try:
            # Get existing job
            job_data = await self.get_job(job_id)
            if not job_data:
                logger.warning(f"Job {job_id} not found for update")
                return False
            
            # Apply updates
            job_data.update(updates)
            
            # Save back
            return await self.save_job(job_id, job_data)
            
        except Exception as e:
            logger.error(f"Failed to update job {job_id}: {e}")
            return False
    
    async def delete_job(self, job_id: str) -> bool:
        """
        Delete job from storage
        
        Args:
            job_id: Unique job identifier
            
        Returns:
            True if deleted successfully
        """
        try:
            redis = await self._get_redis()
            if redis and self._redis_available:
                key = f"{self.JOB_PREFIX}{job_id}"
                await redis.delete(key)
                logger.debug(f"Deleted job {job_id} from Redis")
            
            # Also remove from memory
            if job_id in self._memory_store:
                del self._memory_store[job_id]
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete job {job_id}: {e}")
            return False
    
    async def list_jobs(self) -> List[dict]:
        """
        List all jobs
        
        Returns:
            List of job data dictionaries
        """
        try:
            redis = await self._get_redis()
            if redis and self._redis_available:
                # Get all job keys from Redis
                pattern = f"{self.JOB_PREFIX}*"
                keys = await redis.keys(pattern)
                
                jobs = []
                for key in keys:
                    data = await redis.get(key)
                    if data:
                        jobs.append(json.loads(data))
                
                return jobs
            else:
                # Return from memory
                return list(self._memory_store.values())
                
        except Exception as e:
            logger.error(f"Failed to list jobs: {e}")
            return list(self._memory_store.values())
    
    async def cleanup_old_jobs(self, older_than_hours: int = 24) -> int:
        """
        Clean up jobs older than specified hours
        
        Args:
            older_than_hours: Delete jobs older than this many hours
            
        Returns:
            Number of jobs deleted
        """
        try:
            cutoff = datetime.utcnow() - timedelta(hours=older_than_hours)
            deleted_count = 0
            
            jobs = await self.list_jobs()
            for job in jobs:
                if "updated_at" in job:
                    try:
                        updated_at = datetime.fromisoformat(job["updated_at"])
                        if updated_at < cutoff:
                            job_id = job.get("job_id")
                            if job_id and await self.delete_job(job_id):
                                deleted_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to parse timestamp for job: {e}")
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old upload jobs")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old jobs: {e}")
            return 0


# Global instance
_job_store: Optional[UploadJobStore] = None


async def get_job_store() -> UploadJobStore:
    """Get or create upload job store instance"""
    global _job_store
    if _job_store is None:
        _job_store = UploadJobStore()
    return _job_store
