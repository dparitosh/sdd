"""Approval service router — Quality Head Sign-off [G5, G6].

Endpoints:
  POST /api/v1/approvals/dossier/{dossier_id}        — Submit approval decision
  GET  /api/v1/approvals/dossier/{dossier_id}/history — Decision log
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from src.core.models.sdd_types import ApprovalRecord, DecisionLog
from .service import ApprovalService

router = APIRouter(tags=["Approval Workflow"])

_service: ApprovalService | None = None


def _get_service() -> ApprovalService:
    global _service
    if _service is None:
        _service = ApprovalService()
    return _service


# --- Request body ---
class ApprovalInput(BaseModel):
    status: str  # "Approved" or "Rejected"
    comment: str = ""
    reviewer: str
    signature_id: Optional[str] = None
    role: str = ""


# --- Endpoints ---

@router.post("/dossier/{dossier_id}", response_model=ApprovalRecord)
async def approve_dossier(dossier_id: str, body: ApprovalInput):
    """Submit an approval/rejection decision for a dossier.

    Creates an immutable ``ApprovalRecord`` and a ``DecisionLog`` entry,
    and updates the dossier status accordingly.
    """
    try:
        svc = _get_service()
        record = svc.approve(
            dossier_id=dossier_id,
            status=body.status,
            reviewer=body.reviewer,
            comment=body.comment,
            signature_id=body.signature_id,
            role=body.role,
        )
        return record
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/dossier/{dossier_id}/history", response_model=list[DecisionLog])
async def get_approval_history(dossier_id: str):
    """Return all decision-log entries for a dossier, ordered by timestamp."""
    try:
        svc = _get_service()
        return svc.get_history(dossier_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
