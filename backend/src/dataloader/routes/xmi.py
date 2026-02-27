"""
Dataloader — XMI ingestion router.

Ingests UML/SysML XMI files via SemanticXMILoader (1,320-line parser).
Produces ~175 node types following OMG UML 2.5.1 + SysML 1.6 metamodel.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File
from loguru import logger
from pydantic import BaseModel, Field

from src.dataloader.dependencies import get_neo4j_connection, DEFAULT_XMI_PATHS, UPLOAD_DIR
from src.dataloader.job_manager import job_manager, JobStatus

router = APIRouter(prefix="/xmi", tags=["XMI Ingestion"])


class XMIIngestRequest(BaseModel):
    file_path: Optional[str] = Field(None, description="Path to .xmi file on disk")
    create_constraints: bool = Field(True, description="Create indexes/constraints first")
    enable_versioning: bool = Field(True, description="Track element versions")


def _ingest_xmi_job(job_id: str, xmi_path: str, create_constraints: bool, enable_versioning: bool):
    """Background XMI ingestion."""
    from src.parsers.semantic_loader import SemanticXMILoader

    try:
        job_manager.update(job_id, status=JobStatus.RUNNING, message=f"Loading {xmi_path}...")
        conn = get_neo4j_connection()
        try:
            loader = SemanticXMILoader(conn, enable_versioning=enable_versioning)

            if create_constraints:
                job_manager.update(job_id, progress=10, message="Creating constraints...")
                loader.create_constraints_and_indexes()

            job_manager.update(job_id, progress=20, message="Parsing XMI...")
            stats = loader.load_xmi_file(Path(xmi_path))

            job_manager.update(
                job_id, status=JobStatus.COMPLETED, progress=100,
                message="XMI ingestion complete",
                result=stats if isinstance(stats, dict) else {"stats": str(stats)},
            )
        finally:
            conn.close()
    except Exception as e:
        logger.exception(f"XMI job {job_id} failed")
        job_manager.update(job_id, status=JobStatus.FAILED, error=str(e))


@router.post("/ingest", summary="Ingest XMI file from disk path")
async def ingest_xmi(req: XMIIngestRequest, background_tasks: BackgroundTasks):
    """
    Parse a UML/SysML XMI file and load nodes into Neo4j.

    If no file_path is provided, auto-discovers from default locations:
    - smrlv12/data/domain_models/mossec/*.xmi
    - data/raw/*.xmi
    """
    if req.file_path:
        p = Path(req.file_path)
        if not p.exists():
            raise HTTPException(404, f"File not found: {req.file_path}")
        xmi_path = str(p)
    else:
        # Auto-discover
        xmi_path = None
        for base in DEFAULT_XMI_PATHS:
            if base.exists():
                files = list(base.glob("*.xmi"))
                if files:
                    xmi_path = str(files[0])
                    break
        if not xmi_path:
            raise HTTPException(404, "No XMI file found in default locations")

    job = job_manager.create("xmi_ingest", {"file_path": xmi_path})
    background_tasks.add_task(
        _ingest_xmi_job, job.job_id, xmi_path,
        req.create_constraints, req.enable_versioning,
    )
    return {"job_id": job.job_id, "file": xmi_path, "status": "pending"}


@router.post("/upload", summary="Upload and ingest XMI file")
async def upload_xmi(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """Upload an XMI file and ingest it."""
    if not file.filename.endswith((".xmi", ".xml")):
        raise HTTPException(400, "File must be .xmi or .xml")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = UPLOAD_DIR / file.filename
    content = await file.read()
    dest.write_bytes(content)

    job = job_manager.create("xmi_upload", {"filename": file.filename})
    background_tasks.add_task(
        _ingest_xmi_job, job.job_id, str(dest), True, True,
    )
    return {"job_id": job.job_id, "filename": file.filename, "size": len(content)}


@router.get("/discover", summary="Discover available XMI files")
async def discover_xmi():
    """List XMI files found in default locations."""
    found = []
    for base in DEFAULT_XMI_PATHS:
        if base.exists():
            for f in base.glob("*.xmi"):
                found.append({"path": str(f), "name": f.name, "size": f.stat().st_size})
    return {"files": found}
