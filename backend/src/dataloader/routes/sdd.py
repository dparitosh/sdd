"""
Dataloader — SDD (Simulation Data Dossier) ingestion router.

Loads SimulationDossier, SimulationArtifact, EvidenceCategory nodes
and MOSSEC relationship links into the knowledge graph.
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks
from loguru import logger
from pydantic import BaseModel, Field

from src.dataloader.dependencies import get_neo4j_connection
from src.dataloader.job_manager import job_manager, JobStatus

router = APIRouter(prefix="/sdd", tags=["SDD Data Ingestion"])


class SDDIngestRequest(BaseModel):
    clear_existing: bool = Field(False, description="Clear existing SDD data before ingesting")
    dry_run: bool = Field(False, description="Show what would be created without writing")


def _ingest_sdd_job(job_id: str, clear_existing: bool, dry_run: bool):
    """Background SDD data ingestion."""
    try:
        job_manager.update(job_id, status=JobStatus.RUNNING, message="Preparing SDD ingestion...")

        import sys
        from pathlib import Path
        project_root = str(Path(__file__).resolve().parent.parent.parent.parent)
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        from backend.scripts.ingest_sdd_data import SDDDataIngester

        conn = get_neo4j_connection()
        try:
            ingester = SDDDataIngester(conn)

            if clear_existing:
                job_manager.update(job_id, progress=10, message="Clearing existing SDD data...")
                conn.execute_query(
                    "MATCH (n) WHERE n:SimulationDossier OR n:SimulationArtifact "
                    "OR n:EvidenceCategory DETACH DELETE n"
                )

            if dry_run:
                job_manager.update(
                    job_id, status=JobStatus.COMPLETED, progress=100,
                    message="Dry run complete (no changes made)",
                    result={"dry_run": True, "would_create": {
                        "dossiers": 5, "artifacts_per_dossier": 9,
                        "evidence_categories_per_dossier": 8,
                        "mossec_links_per_dossier": 13,
                    }},
                )
                return

            job_manager.update(job_id, progress=20, message="Creating SDD nodes...")
            ingester.ingest_all()

            # Count what was created
            counts = conn.execute_query(
                "MATCH (d:SimulationDossier) "
                "OPTIONAL MATCH (d)-[:HAS_ARTIFACT]->(a:SimulationArtifact) "
                "OPTIONAL MATCH (d)-[:HAS_EVIDENCE]->(e:EvidenceCategory) "
                "RETURN count(DISTINCT d) as dossiers, "
                "count(DISTINCT a) as artifacts, "
                "count(DISTINCT e) as evidence"
            )

            result = counts[0] if counts else {"dossiers": 0, "artifacts": 0, "evidence": 0}
            job_manager.update(
                job_id, status=JobStatus.COMPLETED, progress=100,
                message="SDD data ingestion complete",
                result=result,
            )
        finally:
            conn.close()
    except Exception as e:
        logger.exception(f"SDD job {job_id} failed")
        job_manager.update(job_id, status=JobStatus.FAILED, error=str(e))


@router.post("/ingest", summary="Ingest SDD sample data")
async def ingest_sdd(req: SDDIngestRequest, background_tasks: BackgroundTasks):
    """
    Load SimulationDossier, SimulationArtifact, and EvidenceCategory nodes
    with MOSSEC relationships into the knowledge graph.

    Creates:
    - 5 SimulationDossier nodes
    - 9 SimulationArtifact nodes per dossier (45 total)
    - 8 EvidenceCategory nodes per dossier (40 total)
    - 13 MOSSEC relationship links per dossier
    """
    job = job_manager.create("sdd_ingest", req.model_dump())
    background_tasks.add_task(_ingest_sdd_job, job.job_id, req.clear_existing, req.dry_run)
    return {"job_id": job.job_id, "clear_existing": req.clear_existing}


@router.get("/status", summary="Get SDD data status in graph")
async def sdd_status():
    """Check current SDD node counts in the graph."""
    conn = get_neo4j_connection()
    try:
        result = conn.execute_query("""
            OPTIONAL MATCH (d:SimulationDossier)
            WITH count(d) as dossiers
            OPTIONAL MATCH (a:SimulationArtifact)
            WITH dossiers, count(a) as artifacts
            OPTIONAL MATCH (e:EvidenceCategory)
            RETURN dossiers, artifacts, count(e) as evidence_categories
        """)
        return result[0] if result else {"dossiers": 0, "artifacts": 0, "evidence_categories": 0}
    finally:
        conn.close()
