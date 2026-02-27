"""Workspace service router — Interactive Simulation Execution [G8].

Endpoints:
  POST /api/v1/workspace/execute          — Start a simulation run
  GET  /api/v1/workspace/status/{job_id}  — Poll job status + logs
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .service import WorkspaceService

router = APIRouter(tags=["Workspace Execution"])

_service: WorkspaceService | None = None


def _get_service() -> WorkspaceService:
    global _service
    if _service is None:
        _service = WorkspaceService()
    return _service


# --- Request / response bodies ---

class ExecuteInput(BaseModel):
    dossier_id: str = Field(..., alias="dossierId")
    model_id: str = Field(..., alias="modelId")
    parameters: dict = Field(default_factory=dict)

    class Config:
        populate_by_name = True


class ExecuteResponse(BaseModel):
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: float = 0.0
    logs: list[str] = Field(default_factory=list)
    completed_at: Optional[str] = None
    error: Optional[str] = None


# --- Endpoints ---

@router.post("/execute", response_model=ExecuteResponse)
async def execute_workspace(body: ExecuteInput):
    """Start a simulation execution.

    Creates a background job entry plus a ``SimulationRun`` node in Neo4j
    linked to the dossier via ``[:GENERATED_FROM]`` and to the model via
    ``[:USES_MODEL]``.
    """
    try:
        svc = _get_service()
        result = svc.execute(
            dossier_id=body.dossier_id,
            model_id=body.model_id,
            parameters=body.parameters,
        )
        return ExecuteResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Poll the execution status of a workspace job."""
    try:
        svc = _get_service()
        result = svc.get_status(job_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
        return JobStatusResponse(**result)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
