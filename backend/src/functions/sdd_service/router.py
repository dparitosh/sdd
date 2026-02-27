"""
SDD Dossier CRUD + Versioning router.

Phase 1b: Stub router — dossier endpoints are currently served by
simulation_service (via simulation_fastapi.py). The actual split
happens in Phase 1c when dedicated dossier logic is extracted.

Endpoints planned:
  GET    /api/v1/sdd/dossiers
  GET    /api/v1/sdd/dossiers/{dossier_id}
  POST   /api/v1/sdd/dossiers
  PATCH  /api/v1/sdd/dossiers/{dossier_id}
  GET    /api/v1/sdd/dossiers/{dossier_id}/artifacts
"""
from fastapi import APIRouter

router = APIRouter(prefix="/sdd", tags=["SDD - Simulation Data Dossier"])


@router.get("/status")
async def sdd_status():
    """SDD service health / info endpoint."""
    return {
        "service": "sdd_service",
        "status": "stub",
        "message": "Dossier CRUD endpoints pending Phase 1c split from simulation_service.",
    }
