"""
Dataloader — Semantic layer augmentation router.

Augments the existing knowledge graph with derived semantic knowledge:
  - Domain Concepts extracted from entity names
  - Cross-schema equivalence (XMI ↔ XSD SAME_AS)
  - Type resolution (TYPED_AS relationships)
  - Semantic similarity links
  - Documentation nodes
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks
from loguru import logger
from pydantic import BaseModel, Field

from src.dataloader.dependencies import BACKEND_ROOT
from src.dataloader.job_manager import job_manager, JobStatus

router = APIRouter(prefix="/semantic", tags=["Semantic Layer"])


class SemanticLayerRequest(BaseModel):
    dry_run: bool = Field(False, description="Show what would be created without writing")


def _run_semantic_layer_job(job_id: str, dry_run: bool):
    """Background semantic layer augmentation."""
    try:
        job_manager.update(job_id, status=JobStatus.RUNNING, message="Augmenting semantic layer...")

        script = str(BACKEND_ROOT / "scripts" / "ingest_semantic_layer.py")
        if not Path(script).exists():
            job_manager.update(job_id, status=JobStatus.FAILED,
                               error=f"Script not found: {script}")
            return

        cmd = [sys.executable, script]
        if dry_run:
            cmd.append("--dry-run")

        job_manager.update(job_id, progress=10, message="Running semantic layer script...")

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=600,
            cwd=str(BACKEND_ROOT.parent),  # Run from project root
        )

        if result.returncode == 0:
            # Extract stats from stdout if available
            lines = result.stdout.strip().split("\n")
            tail = lines[-20:] if len(lines) > 20 else lines

            job_manager.update(
                job_id, status=JobStatus.COMPLETED, progress=100,
                message="Semantic layer augmentation complete",
                result={"output_tail": tail, "dry_run": dry_run},
            )
        else:
            job_manager.update(
                job_id, status=JobStatus.FAILED,
                error=result.stderr or f"Exit code {result.returncode}",
                result={"stdout_tail": result.stdout[-500:] if result.stdout else ""},
            )
    except subprocess.TimeoutExpired:
        job_manager.update(job_id, status=JobStatus.FAILED, error="Timed out after 600s")
    except Exception as e:
        logger.exception(f"Semantic layer job {job_id} failed")
        job_manager.update(job_id, status=JobStatus.FAILED, error=str(e))


@router.post("/augment", summary="Run semantic layer augmentation")
async def augment_semantic_layer(req: SemanticLayerRequest, background_tasks: BackgroundTasks):
    """
    Augment the knowledge graph with semantic relationships:
    - Domain concept extraction
    - Cross-schema equivalence mapping (XMI ↔ XSD)
    - Type resolution (TYPED_AS)
    - Semantic similarity (SIMILAR_TO)
    - Documentation linking (DOCUMENTED_BY)
    """
    job = job_manager.create("semantic_layer", req.model_dump())
    background_tasks.add_task(_run_semantic_layer_job, job.job_id, req.dry_run)
    return {"job_id": job.job_id, "dry_run": req.dry_run}
