"""
AI Insights & SmartAnalysis API Routes (FastAPI)

- ``GET /api/insights/{metric}``  — pre-computed insight metrics
- ``POST /api/smart-analysis/{uid}`` — per-node 5-step deep analysis
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Callable, Dict

from fastapi import APIRouter, Depends, HTTPException, Path
from loguru import logger

from src.web.dependencies import get_api_key
from src.web.services.insights_service import (
    SmartAnalysisResult,
    bom_completeness,
    classification_coverage,
    part_similarity,
    semantic_duplicates,
    shacl_compliance,
    simulation_run_status,
    simulation_workflow_coverage,
    simulation_parameter_health,
    simulation_dossier_health,
    simulation_digital_thread,
    smart_analysis,
    traceability_gaps,
)

router = APIRouter(
    prefix="/api/insights",
    tags=["AI Insights"],
    dependencies=[Depends(get_api_key)],
)


# ── Insight endpoints ────────────────────────────────────────────────────────

_INSIGHT_MAP: Dict[str, Callable[[], dict]] = {
    "bom-completeness":              bom_completeness,
    "traceability-gaps":             traceability_gaps,
    "classification-coverage":       classification_coverage,
    "semantic-duplicates":           semantic_duplicates,
    "part-similarity":               part_similarity,
    "shacl-compliance":              shacl_compliance,
    # Simulation insights
    "simulation-run-status":         simulation_run_status,
    "simulation-workflow-coverage":  simulation_workflow_coverage,
    "simulation-parameter-health":   simulation_parameter_health,
    "simulation-dossier-health":     simulation_dossier_health,
    "simulation-digital-thread":     simulation_digital_thread,
}


@router.get("/{metric}")
async def get_insight(metric: str = Path(..., description="Insight metric name")):
    """Return a pre-computed insight metric.

    Valid metrics: ``bom-completeness``, ``traceability-gaps``,
    ``classification-coverage``, ``semantic-duplicates``, ``shacl-compliance``.
    """
    fn = _INSIGHT_MAP.get(metric)
    if fn is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown metric '{metric}'. "
            f"Available: {list(_INSIGHT_MAP.keys())}",
        )

    logger.info(f"AI Insights: computing '{metric}'")
    try:
        return fn()
    except Exception as exc:
        logger.exception(f"Insight '{metric}' failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── SmartAnalysis per-node endpoint ──────────────────────────────────────────

@router.post("/smart-analysis/{uid}")
async def run_smart_analysis(uid: str = Path(..., description="Node UID to analyse")):
    """
    Execute the 5-step SmartAnalysis pipeline for a single node.

    Steps: Overview → Ontology → Similar → Violations → Graph
    """
    logger.info(f"SmartAnalysis: analysing node '{uid}'")
    try:
        result: SmartAnalysisResult = smart_analysis(uid)
        return asdict(result)
    except Exception as exc:
        logger.exception(f"SmartAnalysis for '{uid}' failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
