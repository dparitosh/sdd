"""
Dataloader — Job manager for tracking batch processing jobs.

Provides an in-memory job store with status tracking so long-running
ingestion tasks can be launched asynchronously and polled for progress.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class JobRecord:
    """A single batch job."""
    job_id: str
    job_type: str
    status: JobStatus = JobStatus.PENDING
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress: int = 0          # 0-100
    message: str = ""
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "status": self.status.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "progress": self.progress,
            "message": self.message,
            "result": self.result,
            "error": self.error,
            "parameters": self.parameters,
        }


class JobManager:
    """Thread-safe in-memory job store for batch processing."""

    def __init__(self):
        self._jobs: Dict[str, JobRecord] = {}

    def create(self, job_type: str, parameters: Optional[Dict[str, Any]] = None) -> JobRecord:
        job_id = uuid.uuid4().hex[:12]
        job = JobRecord(
            job_id=job_id,
            job_type=job_type,
            parameters=parameters or {},
        )
        self._jobs[job_id] = job
        return job

    def get(self, job_id: str) -> Optional[JobRecord]:
        return self._jobs.get(job_id)

    def update(
        self,
        job_id: str,
        *,
        status: Optional[JobStatus] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ):
        job = self._jobs.get(job_id)
        if not job:
            return
        now = datetime.now(timezone.utc).isoformat()
        if status is not None:
            job.status = status
            if status == JobStatus.RUNNING and not job.started_at:
                job.started_at = now
            if status in (JobStatus.COMPLETED, JobStatus.FAILED):
                job.completed_at = now
        if progress is not None:
            job.progress = progress
        if message is not None:
            job.message = message
        if result is not None:
            job.result = result
        if error is not None:
            job.error = error

    def list_all(self, job_type: Optional[str] = None) -> List[JobRecord]:
        jobs = list(self._jobs.values())
        if job_type:
            jobs = [j for j in jobs if j.job_type == job_type]
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)

    def delete(self, job_id: str) -> bool:
        return self._jobs.pop(job_id, None) is not None

    def clear(self):
        self._jobs.clear()


# Global singleton
job_manager = JobManager()
