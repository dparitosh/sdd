"""
Dataloader — EXPRESS schema ingestion router.

Parses ISO 10303 EXPRESS (.exp) files and loads schemas into Neo4j.
Uses both the lightweight express_parser and the advanced express/ package.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File
from loguru import logger
from pydantic import BaseModel, Field

from src.dataloader.dependencies import UPLOAD_DIR
from src.dataloader.job_manager import job_manager, JobStatus

router = APIRouter(prefix="/express", tags=["EXPRESS Ingestion"])


class ExpressIngestRequest(BaseModel):
    file_path: str = Field(..., description="Path to .exp file")
    load_to_neo4j: bool = Field(True, description="Also load parsed schema into Neo4j graph")


class ExpressFolderRequest(BaseModel):
    folder_path: str = Field(..., description="Path to directory containing .exp files")
    load_to_neo4j: bool = Field(True, description="Load all into Neo4j")


def _ingest_express_job(job_id: str, file_path: str, load_to_neo4j: bool):
    """Background EXPRESS parsing + optional Neo4j load."""
    from src.parsers.express import ExpressParser, ExpressNeo4jConverter

    try:
        job_manager.update(job_id, status=JobStatus.RUNNING, message=f"Parsing {file_path}...")

        parser = ExpressParser()
        schema = parser.parse_file(file_path)

        result = {
            "schema_name": schema.name if hasattr(schema, "name") else str(file_path),
            "entities": len(schema.entities) if hasattr(schema, "entities") else 0,
            "types": len(schema.types) if hasattr(schema, "types") else 0,
        }

        if load_to_neo4j:
            job_manager.update(job_id, progress=50, message="Loading into Neo4j...")
            converter = ExpressNeo4jConverter()
            neo4j_stats = converter.convert_and_load(schema)
            result["neo4j"] = neo4j_stats if isinstance(neo4j_stats, dict) else str(neo4j_stats)

        job_manager.update(
            job_id, status=JobStatus.COMPLETED, progress=100,
            message="EXPRESS ingestion complete", result=result,
        )
    except Exception as e:
        logger.exception(f"EXPRESS job {job_id} failed")
        job_manager.update(job_id, status=JobStatus.FAILED, error=str(e))


def _ingest_express_folder_job(job_id: str, folder_path: str, load_to_neo4j: bool):
    """Background EXPRESS folder ingestion."""
    from src.parsers.express import ExpressParser, ExpressNeo4jConverter

    try:
        job_manager.update(job_id, status=JobStatus.RUNNING, message=f"Scanning {folder_path}...")
        folder = Path(folder_path)
        files = list(folder.rglob("*.exp"))

        if not files:
            job_manager.update(job_id, status=JobStatus.COMPLETED, progress=100,
                               message="No .exp files found", result={"files_processed": 0})
            return

        parser = ExpressParser()
        converter = ExpressNeo4jConverter() if load_to_neo4j else None
        results = []

        for i, f in enumerate(files, 1):
            pct = int(i / len(files) * 100)
            job_manager.update(job_id, progress=pct, message=f"Processing {f.name} ({i}/{len(files)})")
            try:
                schema = parser.parse_file(str(f))
                entry = {"file": str(f), "ok": True}
                if converter:
                    converter.convert_and_load(schema)
                results.append(entry)
            except Exception as e:
                results.append({"file": str(f), "error": str(e), "ok": False})

        job_manager.update(
            job_id, status=JobStatus.COMPLETED, progress=100,
            message=f"Processed {len(files)} EXPRESS files",
            result={"files_processed": len(files), "details": results},
        )
    except Exception as e:
        logger.exception(f"EXPRESS folder job {job_id} failed")
        job_manager.update(job_id, status=JobStatus.FAILED, error=str(e))


@router.post("/ingest", summary="Ingest EXPRESS schema file")
async def ingest_express(req: ExpressIngestRequest, background_tasks: BackgroundTasks):
    p = Path(req.file_path)
    if not p.exists():
        raise HTTPException(404, f"File not found: {req.file_path}")

    job = job_manager.create("express_ingest", req.model_dump())
    background_tasks.add_task(_ingest_express_job, job.job_id, req.file_path, req.load_to_neo4j)
    return {"job_id": job.job_id, "file": req.file_path}


@router.post("/ingest-folder", summary="Batch ingest EXPRESS files from folder")
async def ingest_express_folder(req: ExpressFolderRequest, background_tasks: BackgroundTasks):
    folder = Path(req.folder_path)
    if not folder.is_dir():
        raise HTTPException(404, f"Directory not found: {req.folder_path}")

    job = job_manager.create("express_folder_ingest", req.model_dump())
    background_tasks.add_task(
        _ingest_express_folder_job, job.job_id, req.folder_path, req.load_to_neo4j,
    )
    return {"job_id": job.job_id, "folder": req.folder_path}


@router.post("/upload", summary="Upload and ingest EXPRESS file")
async def upload_express(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    if not file.filename.lower().endswith(".exp"):
        raise HTTPException(400, "File must be .exp")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = UPLOAD_DIR / file.filename
    content = await file.read()
    dest.write_bytes(content)

    job = job_manager.create("express_upload", {"filename": file.filename})
    background_tasks.add_task(_ingest_express_job, job.job_id, str(dest), True)
    return {"job_id": job.job_id, "filename": file.filename, "size": len(content)}
