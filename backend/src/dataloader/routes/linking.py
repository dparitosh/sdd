"""
Dataloader — Cross-schema linking router.

Creates AP239↔AP242↔AP243 cross-level relationships via
name matching, specification references, and semantic matching.
"""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks
from loguru import logger
from pydantic import BaseModel, Field

from src.dataloader.dependencies import BACKEND_ROOT
from src.dataloader.job_manager import job_manager, JobStatus

router = APIRouter(prefix="/linking", tags=["Cross-Schema Linking"])


class LinkingRequest(BaseModel):
    dry_run: bool = Field(False, description="Show what would be linked without writing")
    verbose: bool = Field(False, description="Enable verbose matching output")


def _run_linking_job(job_id: str, dry_run: bool, verbose: bool):
    """Background cross-schema linking."""
    try:
        job_manager.update(job_id, status=JobStatus.RUNNING, message="Starting cross-schema linking...")

        # Import the linker
        backend_str = str(BACKEND_ROOT)
        if backend_str not in sys.path:
            sys.path.insert(0, backend_str)

        from scripts.link_ap_hierarchy import APHierarchyLinker
        from src.web.services import get_neo4j_service

        neo4j_svc = get_neo4j_service()
        linker = APHierarchyLinker(neo4j_svc, dry_run=dry_run)

        job_manager.update(job_id, progress=20, message="Running AP hierarchy linker...")
        linker.run()

        stats = linker.stats if hasattr(linker, "stats") else {}
        job_manager.update(
            job_id, status=JobStatus.COMPLETED, progress=100,
            message="Cross-schema linking complete",
            result={"stats": stats, "dry_run": dry_run},
        )
    except Exception as e:
        logger.exception(f"Linking job {job_id} failed")
        job_manager.update(job_id, status=JobStatus.FAILED, error=str(e))


@router.post("/run", summary="Run cross-schema AP hierarchy linking")
async def run_linking(req: LinkingRequest, background_tasks: BackgroundTasks):
    """
    Create cross-level relationships between AP239, AP242, and AP243 nodes.

    Linking strategies:
    1. Name-based matching (requirement ↔ part name similarity)
    2. Specification reference extraction (IDs in descriptions)
    3. Material-to-ontology classification
    4. Property-to-unit associations
    5. Analysis-to-geometry validation chains
    """
    job = job_manager.create("cross_linking", req.model_dump())
    background_tasks.add_task(_run_linking_job, job.job_id, req.dry_run, req.verbose)
    return {"job_id": job.job_id, "dry_run": req.dry_run}


@router.get("/status", summary="Show cross-schema link counts")
async def linking_status():
    """Count existing cross-level relationships."""
    from src.dataloader.dependencies import get_neo4j_connection

    conn = get_neo4j_connection()
    try:
        # Count cross-AP relationships
        result = conn.execute_query("""
            MATCH (a)-[r]->(b)
            WHERE a.ap_level IS NOT NULL AND b.ap_level IS NOT NULL
              AND a.ap_level <> b.ap_level
            RETURN a.ap_level + ' -> ' + b.ap_level AS direction,
                   type(r) AS rel_type,
                   count(r) AS count
            ORDER BY direction, count DESC
        """)
        return {"cross_level_links": result}
    finally:
        conn.close()
