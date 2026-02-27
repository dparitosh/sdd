"""
Dataloader — OSLC vocabulary seeding router.

Seeds OSLC Core/RM/AP-specific Turtle vocabularies into Neo4j,
producing OntologyClass, OntologyProperty, and Ontology nodes.
Uses both OntologyIngestService (ExternalOwlClass layer) and
load_oslc_seed (OntologyClass/OntologyProperty layer).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

from src.dataloader.dependencies import SEED_DIR, BACKEND_ROOT
from src.dataloader.job_manager import job_manager, JobStatus

router = APIRouter(prefix="/oslc", tags=["OSLC Seeding"])

# Default OSLC seed files
DEFAULT_OSLC_FILES = [
    ("oslc-core.ttl", "OSLC-Core"),
    ("oslc-rm.ttl", "OSLC-RM"),
    ("oslc-ap239.ttl", "OSLC-AP239"),
    ("oslc-ap242.ttl", "OSLC-AP242"),
    ("oslc-ap243.ttl", "OSLC-AP243"),
]


class OSLCSeedRequest(BaseModel):
    seed_dir: Optional[str] = Field(None, description="OSLC seed directory (uses default if not set)")
    include_vocabulary: bool = Field(True, description="Also load OntologyClass/OntologyProperty nodes")
    files: Optional[list[str]] = Field(None, description="Specific .ttl filenames to load (all if not set)")


def _seed_oslc_job(job_id: str, seed_dir: str, include_vocabulary: bool, files: Optional[list[str]]):
    """Background OSLC seeding."""
    try:
        job_manager.update(job_id, status=JobStatus.RUNNING, message="Seeding OSLC ontologies...")
        seed_path = Path(seed_dir)

        if not seed_path.exists():
            job_manager.update(job_id, status=JobStatus.FAILED, error=f"Seed dir not found: {seed_dir}")
            return

        # Phase 1: OntologyIngestService (ExternalOwlClass layer)
        from src.web.services.ontology_ingest_service import OntologyIngestService, OntologyIngestConfig
        svc = OntologyIngestService(OntologyIngestConfig())

        results_ontology = []
        targets = [(f, n) for f, n in DEFAULT_OSLC_FILES if not files or f in files]

        for i, (fname, oname) in enumerate(targets, 1):
            fpath = seed_path / fname
            if fpath.exists():
                try:
                    stats = svc.ingest_file(str(fpath), ontology_name=oname)
                    results_ontology.append({
                        "file": fname, "ontology": oname,
                        "classes": stats.classes_upserted, "ok": True,
                    })
                except Exception as e:
                    results_ontology.append({"file": fname, "error": str(e), "ok": False})
            else:
                results_ontology.append({"file": fname, "error": "Not found", "ok": False})

            pct = int(i / (len(targets) * (2 if include_vocabulary else 1)) * 100)
            job_manager.update(job_id, progress=pct, message=f"Loaded {oname}")

        # Phase 2: load_oslc_seed (OntologyClass/OntologyProperty layer)
        results_vocab = []
        if include_vocabulary:
            try:
                backend_str = str(BACKEND_ROOT)
                if backend_str not in sys.path:
                    sys.path.insert(0, backend_str)
                from scripts.load_oslc_seed import load_turtle_file, ingest_graph
                from src.web.services import get_neo4j_service
                neo4j_svc = get_neo4j_service()

                for i, (fname, oname) in enumerate(targets, 1):
                    fpath = seed_path / fname
                    if fpath.exists():
                        try:
                            g = load_turtle_file(str(fpath))
                            seed_stats = ingest_graph(neo4j_svc, g, source_label=fname)
                            results_vocab.append({"file": fname, "stats": str(seed_stats), "ok": True})
                        except Exception as e:
                            results_vocab.append({"file": fname, "error": str(e), "ok": False})

                    pct = 50 + int(i / len(targets) * 50)
                    job_manager.update(job_id, progress=pct, message=f"Vocab: {oname}")
            except Exception as e:
                results_vocab.append({"error": f"Vocabulary loading failed: {e}", "ok": False})

        job_manager.update(
            job_id, status=JobStatus.COMPLETED, progress=100,
            message="OSLC seeding complete",
            result={
                "ontology_layer": results_ontology,
                "vocabulary_layer": results_vocab,
            },
        )
    except Exception as e:
        logger.exception(f"OSLC seed job {job_id} failed")
        job_manager.update(job_id, status=JobStatus.FAILED, error=str(e))


@router.post("/seed", summary="Seed OSLC vocabularies into Neo4j")
async def seed_oslc(req: OSLCSeedRequest, background_tasks: BackgroundTasks):
    """
    Load OSLC Core, RM, and AP-specific Turtle vocabularies.

    Two-phase loading:
    1. OntologyIngestService → ExternalOntology + ExternalOwlClass nodes
    2. load_oslc_seed → OntologyClass + OntologyProperty nodes
    """
    seed_dir = req.seed_dir or str(SEED_DIR)
    if not Path(seed_dir).exists():
        raise HTTPException(404, f"Seed directory not found: {seed_dir}")

    job = job_manager.create("oslc_seed", req.model_dump())
    background_tasks.add_task(
        _seed_oslc_job, job.job_id, seed_dir, req.include_vocabulary, req.files,
    )
    return {"job_id": job.job_id, "seed_dir": seed_dir}


@router.get("/seed-files", summary="List available OSLC seed files")
async def list_seed_files():
    """List .ttl files available in the OSLC seed directory."""
    found = []
    if SEED_DIR.exists():
        for f in sorted(SEED_DIR.glob("*.ttl")):
            found.append({"name": f.name, "size": f.stat().st_size, "path": str(f)})
    return {"seed_dir": str(SEED_DIR), "files": found}
