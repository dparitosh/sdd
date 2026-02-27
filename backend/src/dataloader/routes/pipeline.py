"""
Dataloader — Pipeline orchestration router.

Full database reload and multi-source pipeline runs.
Also provides DB clear, status checks, and health monitoring.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from loguru import logger
from pydantic import BaseModel, Field

from src.dataloader.dependencies import (
    get_config, get_graph_store, get_neo4j_connection, get_pipeline,
    DEFAULT_XMI_PATHS, SEED_DIR, PROJECT_ROOT,
)
from src.dataloader.job_manager import job_manager, JobStatus

router = APIRouter(prefix="/pipeline", tags=["Pipeline Orchestration"])


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class PipelineRequest(BaseModel):
    """Request body for a full pipeline run."""
    xmi_path: Optional[str] = Field(None, description="Path to XMI file (auto-discovers if not set)")
    oslc_dir: Optional[str] = Field(None, description="Path to OSLC seed directory")
    clear_first: bool = Field(True, description="Clear all data before loading")
    use_engine: bool = Field(True, description="Use engine pipeline (vs. legacy loader)")
    store_type: str = Field("neo4j", description="GraphStore type: neo4j | spark")
    seed_oslc: bool = Field(True, description="Seed OSLC vocabularies")
    cross_link: bool = Field(True, description="Run cross-schema linking after load")
    ingest_sdd: bool = Field(False, description="Also ingest SDD sample data")
    ingest_semantic_layer: bool = Field(False, description="Also augment with semantic layer")


class ClearRequest(BaseModel):
    confirm: bool = Field(..., description="Must be True to confirm destructive operation")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_xmi_file(custom_path: Optional[str] = None) -> Path:
    if custom_path:
        p = Path(custom_path)
        if p.exists():
            return p
        raise FileNotFoundError(f"XMI file not found: {custom_path}")

    for base_dir in DEFAULT_XMI_PATHS:
        if base_dir.exists():
            files = list(base_dir.glob("*.xmi"))
            if files:
                return files[0]

    raise FileNotFoundError(
        "No XMI file found. Place .xmi files in data/raw/ "
        "or smrlv12/data/domain_models/mossec/"
    )


def _run_pipeline_job(job_id: str, req: PipelineRequest):
    """Background task for pipeline execution."""
    try:
        job_manager.update(job_id, status=JobStatus.RUNNING, message="Starting pipeline...")

        xmi_path = _find_xmi_file(req.xmi_path)
        oslc_dir = Path(req.oslc_dir) if req.oslc_dir else SEED_DIR

        if req.use_engine:
            _run_engine_pipeline(job_id, xmi_path, oslc_dir, req)
        else:
            _run_legacy_pipeline(job_id, xmi_path, oslc_dir, req)

        job_manager.update(
            job_id, status=JobStatus.COMPLETED, progress=100,
            message="Pipeline complete",
        )
    except Exception as e:
        logger.exception(f"Pipeline job {job_id} failed")
        job_manager.update(job_id, status=JobStatus.FAILED, error=str(e))


def _run_engine_pipeline(job_id: str, xmi_path: Path, oslc_dir: Path, req: PipelineRequest):
    """Run via the modular IngestionPipeline."""
    store = get_graph_store()
    try:
        pipeline = get_pipeline(store)
        sources = {"xmi": str(xmi_path)}
        if req.seed_oslc and oslc_dir.exists():
            sources["oslc"] = str(oslc_dir)

        job_manager.update(job_id, progress=10, message="Running engine pipeline...")
        results = pipeline.run(sources=sources, clear_first=req.clear_first)

        summary = []
        for r in results:
            summary.append({
                "ingester": r.ingester_name,
                "nodes": r.nodes_created,
                "relationships": r.relationships_created,
                "ok": r.ok,
                "errors": r.errors,
            })

        job_manager.update(job_id, progress=70, result={"pipeline": summary})

        if req.cross_link:
            _run_cross_linking(job_id)

        if req.ingest_sdd:
            _run_sdd_ingestion(job_id)

        if req.ingest_semantic_layer:
            _run_semantic_layer(job_id)

    finally:
        store.close()


def _run_legacy_pipeline(job_id: str, xmi_path: Path, oslc_dir: Path, req: PipelineRequest):
    """Run via direct SemanticXMILoader (legacy path)."""
    from src.parsers.semantic_loader import SemanticXMILoader

    conn = get_neo4j_connection()
    try:
        if req.clear_first:
            job_manager.update(job_id, progress=5, message="Clearing database...")
            conn.execute_query("MATCH (n) DETACH DELETE n")

        loader = SemanticXMILoader(conn, enable_versioning=True)

        job_manager.update(job_id, progress=10, message="Creating constraints...")
        loader.create_constraints_and_indexes()

        job_manager.update(job_id, progress=20, message=f"Loading XMI: {xmi_path.name}...")
        stats = loader.load_xmi_file(xmi_path)
        job_manager.update(job_id, progress=50, result={"xmi_stats": stats})

        if req.seed_oslc and oslc_dir.exists():
            _seed_oslc_ontologies(job_id, oslc_dir)

        job_manager.update(job_id, progress=70, message="Creating cross-schema links...")
        if req.cross_link:
            try:
                cross = loader.create_cross_schema_links()
                job_manager.update(job_id, message=f"Cross-links: {cross}")
            except Exception as e:
                logger.warning(f"Cross-link error: {e}")

        if req.ingest_sdd:
            _run_sdd_ingestion(job_id)

        if req.ingest_semantic_layer:
            _run_semantic_layer(job_id)

    finally:
        conn.close()


def _seed_oslc_ontologies(job_id: str, oslc_dir: Path):
    """Seed OSLC vocabularies using OntologyIngestService."""
    try:
        from src.web.services.ontology_ingest_service import OntologyIngestService, OntologyIngestConfig

        job_manager.update(job_id, progress=55, message="Seeding OSLC ontologies...")
        svc = OntologyIngestService(OntologyIngestConfig())

        oslc_files = [
            ("oslc-core.ttl", "OSLC-Core"),
            ("oslc-rm.ttl", "OSLC-RM"),
            ("oslc-ap239.ttl", "OSLC-AP239"),
            ("oslc-ap242.ttl", "OSLC-AP242"),
            ("oslc-ap243.ttl", "OSLC-AP243"),
        ]
        for fname, oname in oslc_files:
            fpath = oslc_dir / fname
            if fpath.exists():
                stats = svc.ingest_file(str(fpath), ontology_name=oname)
                logger.info(f"Seeded {oname}: {stats.classes_upserted} classes")
    except Exception as e:
        logger.error(f"OSLC seeding error: {e}")


def _run_cross_linking(job_id: str):
    """Run the AP hierarchy cross-linking."""
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
        from scripts.link_ap_hierarchy import APHierarchyLinker
        from src.web.services import get_neo4j_service

        job_manager.update(job_id, progress=75, message="Cross-schema linking...")
        linker = APHierarchyLinker(get_neo4j_service())
        linker.run()
    except Exception as e:
        logger.warning(f"Cross-linking error: {e}")


def _run_sdd_ingestion(job_id: str):
    """Ingest SDD sample data."""
    try:
        job_manager.update(job_id, progress=80, message="Ingesting SDD data...")
        conn = get_neo4j_connection()
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
            from backend.scripts.ingest_sdd_data import SDDDataIngester
            ingester = SDDDataIngester(conn)
            ingester.ingest_all()
        finally:
            conn.close()
    except Exception as e:
        logger.warning(f"SDD ingestion error: {e}")


def _run_semantic_layer(job_id: str):
    """Augment with semantic layer."""
    try:
        job_manager.update(job_id, progress=85, message="Augmenting semantic layer...")
        # The semantic layer script uses its own connection internally
        import subprocess, sys
        script = str(Path(__file__).resolve().parent.parent.parent / "scripts" / "ingest_semantic_layer.py")
        subprocess.run([sys.executable, script], check=True, timeout=600)
    except Exception as e:
        logger.warning(f"Semantic layer error: {e}")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/run", summary="Execute full ingestion pipeline")
async def run_pipeline(req: PipelineRequest, background_tasks: BackgroundTasks):
    """
    Launch a full ingestion pipeline as a background job.

    Supports both the modular engine pipeline and legacy SemanticXMILoader path.
    Optionally includes OSLC seeding, SDD data, semantic layer, and cross-linking.
    """
    job = job_manager.create("pipeline", req.model_dump())
    background_tasks.add_task(_run_pipeline_job, job.job_id, req)
    return {"job_id": job.job_id, "status": "pending", "message": "Pipeline launched"}


@router.post("/clear", summary="Clear all data from Neo4j")
async def clear_database(req: ClearRequest):
    """Destructive: removes ALL nodes and relationships."""
    if not req.confirm:
        raise HTTPException(400, "Set confirm=true to clear the database")

    conn = get_neo4j_connection()
    try:
        conn.execute_query("MATCH (n) DETACH DELETE n")
        return {"message": "Database cleared", "success": True}
    finally:
        conn.close()


@router.get("/status/{job_id}", summary="Get pipeline job status")
async def get_job_status(job_id: str):
    job = job_manager.get(job_id)
    if not job:
        raise HTTPException(404, f"Job {job_id} not found")
    return job.to_dict()


@router.get("/jobs", summary="List all pipeline jobs")
async def list_jobs(
    job_type: Optional[str] = Query(None, description="Filter by job_type"),
):
    return [j.to_dict() for j in job_manager.list_all(job_type)]


@router.get("/health", summary="Database health check")
async def health_check():
    """Check Neo4j connectivity and return graph statistics."""
    conn = get_neo4j_connection()
    try:
        result = conn.execute_query(
            "MATCH (n) RETURN count(n) as node_count"
        )
        node_count = result[0]["node_count"] if result else 0

        result2 = conn.execute_query(
            "MATCH ()-[r]->() RETURN count(r) as rel_count"
        )
        rel_count = result2[0]["rel_count"] if result2 else 0

        labels = conn.execute_query(
            "CALL db.labels() YIELD label RETURN collect(label) as labels"
        )

        return {
            "status": "healthy",
            "neo4j": "connected",
            "node_count": node_count,
            "relationship_count": rel_count,
            "labels": labels[0]["labels"] if labels else [],
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
    finally:
        conn.close()


@router.get("/ingesters", summary="List registered ingesters")
async def list_ingesters():
    """List all ingesters available in the engine registry."""
    from src.engine.registry import registry as r
    return {
        "ingesters": [
            {"name": name, "class": cls.__name__}
            for name, cls in r.all().items()
        ]
    }
