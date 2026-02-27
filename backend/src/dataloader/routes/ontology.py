"""
Dataloader — OWL/RDF ontology ingestion router.

Ingests OWL, RDF, Turtle, N-Quads ontology files into Neo4j.
Produces: ExternalOntology, ExternalOwlClass, ExternalUnit, ValueType,
Classification (SKOS) nodes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File
from loguru import logger
from pydantic import BaseModel, Field

from src.dataloader.dependencies import UPLOAD_DIR
from src.dataloader.job_manager import job_manager, JobStatus

router = APIRouter(prefix="/ontology", tags=["Ontology Ingestion"])

ONTOLOGY_EXTENSIONS = {".owl", ".rdf", ".ttl", ".nq", ".nt", ".jsonld", ".n3"}


class OntologyIngestRequest(BaseModel):
    file_path: str = Field(..., description="Path to ontology file")
    ontology_name: Optional[str] = Field(None, description="Human-readable name override")
    rdf_format: Optional[str] = Field(None, description="RDF format: turtle, xml, n3, nquads, etc.")
    batch_size: int = Field(200, description="Batch size for Neo4j writes")


class OntologyFolderRequest(BaseModel):
    folder_path: str = Field(..., description="Directory containing ontology files")
    rdf_format: Optional[str] = Field(None, description="Force format (auto-detects if not set)")


def _ingest_ontology_job(
    job_id: str, file_path: str, ontology_name: Optional[str],
    rdf_format: Optional[str], batch_size: int,
):
    """Background ontology ingestion."""
    from src.web.services.ontology_ingest_service import (
        OntologyIngestService, OntologyIngestConfig,
    )

    try:
        job_manager.update(job_id, status=JobStatus.RUNNING, message=f"Ingesting {file_path}...")
        config = OntologyIngestConfig(batch_size=batch_size)
        svc = OntologyIngestService(config)
        stats = svc.ingest_file(file_path, ontology_name=ontology_name, rdf_format=rdf_format)

        job_manager.update(
            job_id, status=JobStatus.COMPLETED, progress=100,
            message="Ontology ingestion complete",
            result={
                "ontology_uri": stats.ontology_uri,
                "classes_upserted": stats.classes_upserted,
                "properties_upserted": getattr(stats, "properties_upserted", 0),
                "units_upserted": getattr(stats, "units_upserted", 0),
            },
        )
    except Exception as e:
        logger.exception(f"Ontology job {job_id} failed")
        job_manager.update(job_id, status=JobStatus.FAILED, error=str(e))


def _ingest_ontology_folder_job(
    job_id: str, folder_path: str, rdf_format: Optional[str],
):
    """Background ontology folder ingestion."""
    from src.web.services.ontology_ingest_service import (
        OntologyIngestService, OntologyIngestConfig,
    )

    try:
        job_manager.update(job_id, status=JobStatus.RUNNING, message=f"Scanning {folder_path}...")
        folder = Path(folder_path)
        files = [f for f in folder.rglob("*") if f.suffix.lower() in ONTOLOGY_EXTENSIONS]

        if not files:
            job_manager.update(job_id, status=JobStatus.COMPLETED, progress=100,
                               message="No ontology files found", result={"files_processed": 0})
            return

        svc = OntologyIngestService(OntologyIngestConfig())
        results = []
        for i, f in enumerate(files, 1):
            pct = int(i / len(files) * 100)
            job_manager.update(job_id, progress=pct, message=f"Processing {f.name} ({i}/{len(files)})")
            try:
                stats = svc.ingest_file(str(f), ontology_name=f.stem, rdf_format=rdf_format)
                results.append({"file": str(f), "classes": stats.classes_upserted, "ok": True})
            except Exception as e:
                results.append({"file": str(f), "error": str(e), "ok": False})

        job_manager.update(
            job_id, status=JobStatus.COMPLETED, progress=100,
            message=f"Processed {len(files)} ontology files",
            result={"files_processed": len(files), "details": results},
        )
    except Exception as e:
        logger.exception(f"Ontology folder job {job_id} failed")
        job_manager.update(job_id, status=JobStatus.FAILED, error=str(e))


@router.post("/ingest", summary="Ingest OWL/RDF ontology file")
async def ingest_ontology(req: OntologyIngestRequest, background_tasks: BackgroundTasks):
    p = Path(req.file_path)
    if not p.exists():
        raise HTTPException(404, f"File not found: {req.file_path}")

    job = job_manager.create("ontology_ingest", req.model_dump())
    background_tasks.add_task(
        _ingest_ontology_job, job.job_id, req.file_path,
        req.ontology_name, req.rdf_format, req.batch_size,
    )
    return {"job_id": job.job_id, "file": req.file_path}


@router.post("/ingest-folder", summary="Batch ingest ontology files from folder")
async def ingest_ontology_folder(req: OntologyFolderRequest, background_tasks: BackgroundTasks):
    folder = Path(req.folder_path)
    if not folder.is_dir():
        raise HTTPException(404, f"Directory not found: {req.folder_path}")

    job = job_manager.create("ontology_folder_ingest", req.model_dump())
    background_tasks.add_task(
        _ingest_ontology_folder_job, job.job_id, req.folder_path, req.rdf_format,
    )
    return {"job_id": job.job_id, "folder": req.folder_path}


@router.post("/upload", summary="Upload and ingest ontology file")
async def upload_ontology(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    if not any(file.filename.lower().endswith(ext) for ext in ONTOLOGY_EXTENSIONS):
        raise HTTPException(400, f"File must be one of: {ONTOLOGY_EXTENSIONS}")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = UPLOAD_DIR / file.filename
    content = await file.read()
    dest.write_bytes(content)

    job = job_manager.create("ontology_upload", {"filename": file.filename})
    background_tasks.add_task(
        _ingest_ontology_job, job.job_id, str(dest), file.filename, None, 200,
    )
    return {"job_id": job.job_id, "filename": file.filename, "size": len(content)}
