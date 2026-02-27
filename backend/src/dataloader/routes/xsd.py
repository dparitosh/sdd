"""
Dataloader — XSD ingestion router.

Ingests W3C XML Schema (.xsd) files producing:
  XSDSchema, XSDComplexType, XSDSimpleType, XSDElement, XSDAttribute, XSDGroup nodes.
Supports both v1 and v2 ingestion modes.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

from src.dataloader.dependencies import get_neo4j_connection, PROJECT_ROOT, BACKEND_ROOT
from src.dataloader.job_manager import job_manager, JobStatus

router = APIRouter(prefix="/xsd", tags=["XSD Ingestion"])


class XSDIngestRequest(BaseModel):
    file_path: str = Field(..., description="Path to .xsd file")
    version: str = Field("v2", description="Ingester version: v1 | v2")
    schema_name: Optional[str] = Field(None, description="Optional override for schema name")


def _ingest_xsd_job(job_id: str, file_path: str, version: str, schema_name: Optional[str]):
    """Background XSD ingestion."""
    try:
        job_manager.update(job_id, status=JobStatus.RUNNING, message=f"Ingesting XSD ({version})...")

        # Add scripts to path for v1/v2 ingesters
        scripts_dir = str(BACKEND_ROOT / "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)

        conn = get_neo4j_connection()
        try:
            if version == "v2":
                from ingest_xsd_v2 import XSDIngesterV2
                ingester = XSDIngesterV2(conn)
            else:
                from ingest_xsd import XSDIngester
                ingester = XSDIngester(conn)

            job_manager.update(job_id, progress=20, message="Parsing schema...")
            stats = ingester.ingest_file(file_path, schema_name=schema_name)

            job_manager.update(
                job_id, status=JobStatus.COMPLETED, progress=100,
                message="XSD ingestion complete",
                result=stats if isinstance(stats, dict) else {"stats": str(stats)},
            )
        finally:
            conn.close()
    except Exception as e:
        logger.exception(f"XSD job {job_id} failed")
        job_manager.update(job_id, status=JobStatus.FAILED, error=str(e))


@router.post("/ingest", summary="Ingest XSD schema file")
async def ingest_xsd(req: XSDIngestRequest, background_tasks: BackgroundTasks):
    """Parse a W3C XML Schema file and load into Neo4j."""
    p = Path(req.file_path)
    if not p.exists():
        raise HTTPException(404, f"File not found: {req.file_path}")
    if not p.suffix.lower() == ".xsd":
        raise HTTPException(400, "File must be .xsd")

    job = job_manager.create("xsd_ingest", req.model_dump())
    background_tasks.add_task(
        _ingest_xsd_job, job.job_id, req.file_path, req.version, req.schema_name,
    )
    return {"job_id": job.job_id, "file": req.file_path, "version": req.version}
