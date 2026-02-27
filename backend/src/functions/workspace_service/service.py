"""Workspace service business logic — Interactive Simulation Execution [G8].

Implements:
  - ``execute(dossier_id, model_id, parameters)`` — create SimulationRun node,
    link to dossier and model, track as background job.
  - ``get_status(job_id)`` — return progress, logs, and completion info.
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger

from src.core.database import get_pool, Neo4jPool


class WorkspaceService:
    """Interactive simulation workspace.

    Uses ``core.database.Neo4jPool`` for Neo4j and an in-memory dict for
    lightweight job tracking (production would use Redis or a task queue).
    """

    def __init__(self, pool: Optional[Neo4jPool] = None) -> None:
        self._pool = pool or get_pool()
        self._jobs: Dict[str, Dict[str, Any]] = {}  # job_id -> state
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # execute
    # ------------------------------------------------------------------

    def execute(
        self,
        dossier_id: str,
        model_id: str,
        parameters: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """Start a simulation execution.

        Steps:
            1. Generate a unique job_id (== SimulationRun id).
            2. Create a ``SimulationRun`` node in Neo4j.
            3. Link the run to the dossier (``[:GENERATED_FROM]``) and
               the model (``[:USES_MODEL]``).
            4. Register the job in the in-memory tracker.
            5. Return ``{job_id, status: 'running'}``.
        """
        job_id = f"RUN-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        # Create SimulationRun + relationships in Neo4j
        query = """
        MATCH (d:SimulationDossier {id: $dossier_id})
        OPTIONAL MATCH (m:SimulationModel {id: $model_id})

        CREATE (sr:SimulationRun {
            id:         $job_id,
            status:     'Running',
            start_time: datetime($now),
            sim_type:   $sim_type,
            parameters: $params_json
        })
        CREATE (d)-[:GENERATED_FROM]->(sr)

        // Link to model only if it exists
        FOREACH (_ IN CASE WHEN m IS NOT NULL THEN [1] ELSE [] END |
            CREATE (sr)-[:USES_MODEL]->(m)
        )

        RETURN {
            job_id:     sr.id,
            status:     sr.status,
            dossier_id: d.id,
            model_id:   COALESCE(m.id, $model_id)
        } AS result
        """
        import json

        params = {
            "dossier_id": dossier_id,
            "model_id": model_id,
            "job_id": job_id,
            "now": now,
            "sim_type": (parameters or {}).get("sim_type", "General"),
            "params_json": json.dumps(parameters or {}),
        }

        rows = self._pool.execute_read(query, params)
        if not rows:
            raise ValueError(f"Dossier '{dossier_id}' not found.")

        # Register in local tracker
        with self._lock:
            self._jobs[job_id] = {
                "job_id": job_id,
                "status": "running",
                "progress": 0.0,
                "logs": [
                    f"[{now}] Job {job_id} created.",
                    f"[{now}] Linked to dossier {dossier_id}.",
                    f"[{now}] Model: {model_id}.",
                    f"[{now}] Execution started.",
                ],
                "completed_at": None,
                "error": None,
            }

        logger.info(
            f"Workspace job {job_id} started: dossier={dossier_id}, model={model_id}"
        )
        return {"job_id": job_id, "status": "running"}

    # ------------------------------------------------------------------
    # get_status
    # ------------------------------------------------------------------

    def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Return current status of a workspace job.

        Checks the in-memory tracker first.  Falls back to Neo4j for
        jobs that were created in a previous process lifetime.
        """
        # Check local tracker
        with self._lock:
            if job_id in self._jobs:
                return dict(self._jobs[job_id])

        # Fallback: query Neo4j
        query = """
        MATCH (sr:SimulationRun {id: $job_id})
        RETURN {
            job_id:       sr.id,
            status:       sr.status,
            start_time:   toString(sr.start_time),
            end_time:     toString(sr.end_time)
        } AS run
        """
        rows = self._pool.execute_read(query, {"job_id": job_id})
        if not rows:
            return None

        run = rows[0]["run"]
        status_val = (run.get("status") or "unknown").lower()
        return {
            "job_id": run["job_id"],
            "status": status_val,
            "progress": 100.0 if status_val == "complete" else 0.0,
            "logs": [],
            "completed_at": run.get("end_time"),
            "error": None,
        }

    # ------------------------------------------------------------------
    # Internal helpers (for future background task integration)
    # ------------------------------------------------------------------

    def _update_job(
        self,
        job_id: str,
        *,
        status: Optional[str] = None,
        progress: Optional[float] = None,
        log_message: Optional[str] = None,
        completed_at: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """Update an in-memory job entry (called by background workers)."""
        with self._lock:
            if job_id not in self._jobs:
                return
            job = self._jobs[job_id]
            if status is not None:
                job["status"] = status
            if progress is not None:
                job["progress"] = progress
            if log_message is not None:
                job["logs"].append(log_message)
            if completed_at is not None:
                job["completed_at"] = completed_at
            if error is not None:
                job["error"] = error
