"""
Dataloader — STEP (ISO 10303-21/28) ingestion router.

Ingests STEP Part 21 clear-text and Part 28 STEP-XML files.
Produces: StepFile, StepInstance nodes and STEP_REF relationships.
Supports single-file and bulk folder ingestion.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File
from loguru import logger
from pydantic import BaseModel, Field

from src.dataloader.dependencies import UPLOAD_DIR
from src.dataloader.job_manager import job_manager, JobStatus

router = APIRouter(prefix="/step", tags=["STEP Ingestion"])

STEP_EXTENSIONS = {".stp", ".step", ".stpx", ".p21"}


class STEPIngestRequest(BaseModel):
    file_path: str = Field(..., description="Path to STEP file (.stp/.step/.stpx)")
    batch_size: int = Field(500, description="Neo4j batch size")


class STEPFolderRequest(BaseModel):
    folder_path: str = Field(..., description="Path to directory containing STEP files")
    recursive: bool = Field(True, description="Search subdirectories")
    batch_size: int = Field(500, description="Neo4j batch size")


def _ingest_step_job(job_id: str, file_path: str, batch_size: int):
    """Background STEP file ingestion."""
    from src.web.services.step_ingest_service import StepIngestService, StepIngestConfig

    try:
        job_manager.update(job_id, status=JobStatus.RUNNING, message=f"Ingesting {file_path}...")
        svc = StepIngestService(StepIngestConfig(batch_size=batch_size))
        stats = svc.ingest_file(Path(file_path))

        job_manager.update(
            job_id, status=JobStatus.COMPLETED, progress=100,
            message="STEP ingestion complete",
            result={
                "file_uri": stats.file_uri,
                "format": stats.format,
                "file_schema": stats.file_schema,
                "instances_upserted": stats.instances_upserted,
                "refs_upserted": stats.refs_upserted,
            },
        )
    except Exception as e:
        logger.exception(f"STEP job {job_id} failed")
        job_manager.update(job_id, status=JobStatus.FAILED, error=str(e))


def _ingest_step_folder_job(job_id: str, folder_path: str, recursive: bool, batch_size: int):
    """Background STEP folder ingestion."""
    from src.web.services.step_ingest_service import StepIngestService, StepIngestConfig

    try:
        job_manager.update(job_id, status=JobStatus.RUNNING, message=f"Scanning {folder_path}...")
        folder = Path(folder_path)

        if recursive:
            files = [f for f in folder.rglob("*") if f.suffix.lower() in STEP_EXTENSIONS]
        else:
            files = [f for f in folder.glob("*") if f.suffix.lower() in STEP_EXTENSIONS]

        if not files:
            job_manager.update(job_id, status=JobStatus.COMPLETED, progress=100,
                               message="No STEP files found", result={"files_processed": 0})
            return

        svc = StepIngestService(StepIngestConfig(batch_size=batch_size))
        results = []
        for i, f in enumerate(files, 1):
            pct = int(i / len(files) * 100)
            job_manager.update(job_id, progress=pct, message=f"Processing {f.name} ({i}/{len(files)})")
            try:
                stats = svc.ingest_file(f)
                results.append({"file": str(f), "instances": stats.instances_upserted, "ok": True})
            except Exception as e:
                results.append({"file": str(f), "error": str(e), "ok": False})

        job_manager.update(
            job_id, status=JobStatus.COMPLETED, progress=100,
            message=f"Processed {len(files)} STEP files",
            result={"files_processed": len(files), "details": results},
        )
    except Exception as e:
        logger.exception(f"STEP folder job {job_id} failed")
        job_manager.update(job_id, status=JobStatus.FAILED, error=str(e))


@router.post("/ingest", summary="Ingest single STEP file")
async def ingest_step(req: STEPIngestRequest, background_tasks: BackgroundTasks):
    p = Path(req.file_path)
    if not p.exists():
        raise HTTPException(404, f"File not found: {req.file_path}")
    if p.suffix.lower() not in STEP_EXTENSIONS:
        raise HTTPException(400, f"Not a STEP file. Allowed: {STEP_EXTENSIONS}")

    job = job_manager.create("step_ingest", req.model_dump())
    background_tasks.add_task(_ingest_step_job, job.job_id, req.file_path, req.batch_size)
    return {"job_id": job.job_id, "file": req.file_path}


@router.post("/ingest-folder", summary="Batch ingest STEP files from folder")
async def ingest_step_folder(req: STEPFolderRequest, background_tasks: BackgroundTasks):
    folder = Path(req.folder_path)
    if not folder.is_dir():
        raise HTTPException(404, f"Directory not found: {req.folder_path}")

    job = job_manager.create("step_folder_ingest", req.model_dump())
    background_tasks.add_task(
        _ingest_step_folder_job, job.job_id, req.folder_path, req.recursive, req.batch_size,
    )
    return {"job_id": job.job_id, "folder": req.folder_path}


@router.post("/upload", summary="Upload and ingest STEP file")
async def upload_step(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    if not any(file.filename.lower().endswith(ext) for ext in STEP_EXTENSIONS):
        raise HTTPException(400, f"File must be one of: {STEP_EXTENSIONS}")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = UPLOAD_DIR / file.filename
    content = await file.read()
    dest.write_bytes(content)

    job = job_manager.create("step_upload", {"filename": file.filename})
    background_tasks.add_task(_ingest_step_job, job.job_id, str(dest), 500)
    return {"job_id": job.job_id, "filename": file.filename, "size": len(content)}
