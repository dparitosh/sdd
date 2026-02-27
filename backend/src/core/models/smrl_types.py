"""
ISO 10303-4443 SMRL shared types.

Canonical Pydantic schemas for SMRL resource types used across
the ``smrl_service`` FaaS function, ``smrl_adapter``, and
``smrl_validator``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Supported SMRL resource types
# ---------------------------------------------------------------------------

SUPPORTED_RESOURCE_TYPES: List[str] = [
    "Requirement",
    "Part",
    "Interface",
    "Function",
    "Verification",
    "Validation",
    "Person",
    "Organization",
    "ChangeRequest",
    "Document",
    "TestCase",
]


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class SMRLResource(BaseModel):
    """Generic SMRL resource returned by the ``/api/v1/{type}`` endpoints."""
    uid: str
    href: Optional[str] = None
    smrl_type: str = ""
    name: Optional[str] = None
    description: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SMRLMatchRequest(BaseModel):
    """Request body for the SMRL fuzzy-match endpoint."""
    query: str
    resource_type: Optional[str] = None
    limit: int = 20
    threshold: float = 0.5


class SMRLErrorResponse(BaseModel):
    """Standardised error shape for SMRL endpoints."""
    detail: str
    status_code: int = 400
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None


class HealthResponse(BaseModel):
    """Health-check shape used by the SMRL router."""
    status: str = "healthy"
    version: str = "v1"
    resource_types: List[str] = Field(default_factory=lambda: SUPPORTED_RESOURCE_TYPES.copy())
