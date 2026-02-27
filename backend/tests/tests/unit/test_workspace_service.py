"""
Unit tests for WorkspaceService — Interactive Simulation Execution [G8].

Tests use a mock Neo4jPool so no live Neo4j instance is required.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.functions.workspace_service.service import WorkspaceService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pool(read_return=None):
    pool = MagicMock()
    pool.execute_read = MagicMock(return_value=read_return or [])
    return pool


def _execute_row(
    job_id: str = "RUN-abc123",
    status: str = "Running",
    dossier_id: str = "DOS-1",
    model_id: str = "MDL-1",
):
    return {
        "result": {
            "job_id": job_id,
            "status": status,
            "dossier_id": dossier_id,
            "model_id": model_id,
        }
    }


def _run_row(
    job_id: str = "RUN-abc123",
    status: str = "Complete",
    start_time: str = "2025-01-15T10:00:00+00:00",
    end_time: str = "2025-01-15T10:05:00+00:00",
):
    return {
        "run": {
            "job_id": job_id,
            "status": status,
            "start_time": start_time,
            "end_time": end_time,
        }
    }


# ---------------------------------------------------------------------------
# Tests: execute — happy path
# ---------------------------------------------------------------------------

class TestExecuteHappyPath:
    def test_execute_returns_job_id_and_status(self):
        pool = _make_pool(read_return=[_execute_row()])
        svc = WorkspaceService(pool=pool)

        result = svc.execute(dossier_id="DOS-1", model_id="MDL-1")

        assert "job_id" in result
        assert result["status"] == "running"
        assert result["job_id"].startswith("RUN-")

    def test_execute_registers_job_in_memory(self):
        pool = _make_pool(read_return=[_execute_row()])
        svc = WorkspaceService(pool=pool)

        result = svc.execute(dossier_id="DOS-1", model_id="MDL-1")
        job_id = result["job_id"]

        status = svc.get_status(job_id)
        assert status is not None
        assert status["status"] == "running"
        assert status["progress"] == 0.0
        assert len(status["logs"]) >= 1

    def test_execute_with_parameters(self):
        pool = _make_pool(read_return=[_execute_row()])
        svc = WorkspaceService(pool=pool)

        result = svc.execute(
            dossier_id="DOS-1",
            model_id="MDL-1",
            parameters={"sim_type": "FEA", "mesh_size": 0.01},
        )

        assert result["status"] == "running"
        pool.execute_read.assert_called_once()

    def test_execute_calls_neo4j(self):
        pool = _make_pool(read_return=[_execute_row()])
        svc = WorkspaceService(pool=pool)

        svc.execute(dossier_id="DOS-1", model_id="MDL-1")

        pool.execute_read.assert_called_once()
        args = pool.execute_read.call_args[0]
        params = args[1]
        assert params["dossier_id"] == "DOS-1"
        assert params["model_id"] == "MDL-1"


# ---------------------------------------------------------------------------
# Tests: execute — dossier not found
# ---------------------------------------------------------------------------

class TestExecuteDossierNotFound:
    def test_raises_value_error(self):
        pool = _make_pool(read_return=[])
        svc = WorkspaceService(pool=pool)

        with pytest.raises(ValueError, match="not found"):
            svc.execute(dossier_id="MISSING-1", model_id="MDL-1")


# ---------------------------------------------------------------------------
# Tests: get_status — in-memory
# ---------------------------------------------------------------------------

class TestGetStatusInMemory:
    def test_returns_tracked_job(self):
        pool = _make_pool(read_return=[_execute_row()])
        svc = WorkspaceService(pool=pool)

        result = svc.execute(dossier_id="DOS-1", model_id="MDL-1")
        job_id = result["job_id"]

        status = svc.get_status(job_id)
        assert status is not None
        assert status["job_id"] == job_id
        assert status["status"] == "running"

    def test_returns_copy_not_reference(self):
        pool = _make_pool(read_return=[_execute_row()])
        svc = WorkspaceService(pool=pool)

        result = svc.execute(dossier_id="DOS-1", model_id="MDL-1")
        job_id = result["job_id"]

        status1 = svc.get_status(job_id)
        status2 = svc.get_status(job_id)
        assert status1 is not status2  # different dict objects


# ---------------------------------------------------------------------------
# Tests: get_status — Neo4j fallback
# ---------------------------------------------------------------------------

class TestGetStatusNeo4jFallback:
    def test_falls_back_to_neo4j(self):
        pool = MagicMock()
        # First call: execute query; Second call: get_status fallback query
        pool.execute_read = MagicMock(side_effect=[
            [_execute_row()],
            [_run_row(status="Complete")],
        ])
        svc = WorkspaceService(pool=pool)

        result = svc.execute(dossier_id="DOS-1", model_id="MDL-1")
        job_id = result["job_id"]

        # Remove from memory to force fallback
        with svc._lock:
            svc._jobs.clear()

        status = svc.get_status(job_id)
        assert status is not None
        assert status["status"] == "complete"
        assert status["progress"] == 100.0

    def test_neo4j_fallback_running_status(self):
        pool = MagicMock()
        pool.execute_read = MagicMock(side_effect=[
            [_execute_row()],
            [_run_row(status="Running", end_time=None)],
        ])
        svc = WorkspaceService(pool=pool)

        result = svc.execute(dossier_id="DOS-1", model_id="MDL-1")
        job_id = result["job_id"]

        with svc._lock:
            svc._jobs.clear()

        status = svc.get_status(job_id)
        assert status is not None
        assert status["status"] == "running"
        assert status["progress"] == 0.0


# ---------------------------------------------------------------------------
# Tests: get_status — unknown job
# ---------------------------------------------------------------------------

class TestGetStatusUnknown:
    def test_returns_none_for_unknown_job(self):
        pool = _make_pool(read_return=[])
        svc = WorkspaceService(pool=pool)

        status = svc.get_status("NONEXISTENT-123")
        assert status is None


# ---------------------------------------------------------------------------
# Tests: _update_job
# ---------------------------------------------------------------------------

class TestUpdateJob:
    def _setup_svc_with_job(self):
        pool = _make_pool(read_return=[_execute_row()])
        svc = WorkspaceService(pool=pool)
        result = svc.execute(dossier_id="DOS-1", model_id="MDL-1")
        return svc, result["job_id"]

    def test_update_status(self):
        svc, job_id = self._setup_svc_with_job()
        svc._update_job(job_id, status="complete")

        status = svc.get_status(job_id)
        assert status["status"] == "complete"

    def test_update_progress(self):
        svc, job_id = self._setup_svc_with_job()
        svc._update_job(job_id, progress=50.0)

        status = svc.get_status(job_id)
        assert status["progress"] == 50.0

    def test_append_log(self):
        svc, job_id = self._setup_svc_with_job()
        original_logs = len(svc.get_status(job_id)["logs"])
        svc._update_job(job_id, log_message="Step 1 done")

        status = svc.get_status(job_id)
        assert len(status["logs"]) == original_logs + 1
        assert "Step 1 done" in status["logs"][-1]

    def test_update_completed_at(self):
        svc, job_id = self._setup_svc_with_job()
        svc._update_job(job_id, completed_at="2025-01-15T12:00:00Z")

        status = svc.get_status(job_id)
        assert status["completed_at"] == "2025-01-15T12:00:00Z"

    def test_update_error(self):
        svc, job_id = self._setup_svc_with_job()
        svc._update_job(job_id, error="Simulation diverged")

        status = svc.get_status(job_id)
        assert status["error"] == "Simulation diverged"

    def test_update_nonexistent_job_no_op(self):
        pool = _make_pool()
        svc = WorkspaceService(pool=pool)
        # Should not raise
        svc._update_job("GHOST-1", status="complete")

    def test_multiple_updates(self):
        svc, job_id = self._setup_svc_with_job()
        svc._update_job(job_id, progress=25.0, log_message="Quarter done")
        svc._update_job(job_id, progress=50.0, log_message="Half done")
        svc._update_job(job_id, progress=100.0, status="complete", completed_at="2025-01-15T12:00:00Z")

        status = svc.get_status(job_id)
        assert status["status"] == "complete"
        assert status["progress"] == 100.0
        assert status["completed_at"] is not None
