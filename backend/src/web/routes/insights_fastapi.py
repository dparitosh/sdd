"""
AI Insights & SmartAnalysis API Routes (FastAPI)

- ``GET /api/insights/{metric}``  — pre-computed insight metrics
- ``POST /api/smart-analysis/{uid}`` — per-node 5-step deep analysis
"""

from __future__ import annotations

import time as _time
from dataclasses import asdict
from typing import Any, Callable, Dict

from fastapi import APIRouter, Depends, HTTPException, Path
from loguru import logger

# ── Simple TTL cache for insight results (avoids repeated Neo4j full-scans) ──
_INSIGHT_RESULT_CACHE: dict[str, tuple[Any, float]] = {}
_INSIGHT_CACHE_TTL = 300  # 5 minutes


def _cached_metric(key: str, fn: Callable[[], Any]) -> Any:
    """Return a cached result if fresh, otherwise call fn() and cache it."""
    now = _time.time()
    if key in _INSIGHT_RESULT_CACHE:
        result, ts = _INSIGHT_RESULT_CACHE[key]
        if now - ts < _INSIGHT_CACHE_TTL:
            logger.debug(f"[insight cache hit] {key}")
            return result
    result = fn()
    _INSIGHT_RESULT_CACHE[key] = (result, now)
    return result

from src.web.dependencies import get_api_key
from src.web.services.insights_service import (
    SmartAnalysisResult,
    ai_narrative,
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
def get_insight(metric: str = Path(..., description="Insight metric name")):
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
        return _cached_metric(metric, fn)
    except Exception as exc:
        logger.exception(f"Insight '{metric}' failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/ai-narrative")
def get_ai_narrative():
    """
    Collect all insight metrics and ask the local LLM (Ollama) to produce
    a natural-language health assessment with priority issues and recommendations.
    """
    logger.info("AI Narrative: collecting snapshot & calling LLM")
    snapshot: Dict[str, Any] = {}
    for key, fn in _INSIGHT_MAP.items():
        try:
            snapshot[key] = _cached_metric(key, fn)
        except Exception as exc:
            logger.warning(f"AI Narrative: skipping '{key}' — {exc}")
    return ai_narrative(snapshot)


# ── SmartAnalysis per-node endpoint ──────────────────────────────────────────

@router.post("/smart-analysis/{uid}")
def run_smart_analysis(uid: str = Path(..., description="Node UID to analyse")):
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
