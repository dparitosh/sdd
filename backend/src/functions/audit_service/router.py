"""Audit service router — ISO-CASCO Compliance Audit Engine [G2, G14].

Endpoints:
  GET /api/v1/audit/dossier/{dossier_id}  — Run full audit, return ``AuditReport``
"""
from fastapi import APIRouter, HTTPException

from src.core.models.sdd_types import AuditReport
from .service import AuditService

router = APIRouter(tags=["Audit Trail"])

# Lazily instantiated (requires Neo4j driver to be up)
_service: AuditService | None = None


def _get_service() -> AuditService:
    global _service
    if _service is None:
        _service = AuditService()
    return _service


@router.get("/dossier/{dossier_id}", response_model=AuditReport)
async def run_dossier_audit(dossier_id: str):
    """Run a full compliance audit on a dossier.

    Returns an ``AuditReport`` containing:
      - ``health_score`` (0–100)
      - ``findings`` — list of ``AuditFinding`` items
      - ``summary`` — counts of critical / warning / pass findings
    """
    try:
        svc = _get_service()
        report = svc.run_audit(dossier_id)
        return report
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
