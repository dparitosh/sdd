"""
SDD (Simulation Data Dossier) shared types.

These are the canonical Pydantic schemas for dossier lifecycle,
compliance audit, approval workflow and evidence categories.

Based on the reference SDD app and gaps G2, G5, G6, G9, G14.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DossierStatus(str, Enum):
    DRAFT = "Draft"
    UNDER_REVIEW = "UnderReview"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    ARCHIVED = "Archived"


class ApprovalStatus(str, Enum):
    APPROVED = "Approved"
    REJECTED = "Rejected"


class AuditCategory(str, Enum):
    COMPLIANCE = "Compliance"
    INTEGRITY = "Integrity"
    TRACEABILITY = "Traceability"


class AuditSeverity(str, Enum):
    CRITICAL = "Critical"
    WARNING = "Warning"
    PASS = "Pass"


class CredibilityLevel(str, Enum):
    """ISO-CASCO credibility levels."""
    LEVEL_0 = "Level0"  # No evidence
    LEVEL_1 = "Level1"  # Minimal evidence
    LEVEL_2 = "Level2"  # Good evidence
    LEVEL_3 = "Level3"  # Comprehensive evidence
    LEVEL_4 = "Level4"  # Accredited evidence


class EvidenceCategoryCode(str, Enum):
    """MoSSEC 8-category evidence pipeline (A1–H1)."""
    A1 = "A1"  # Verification
    B1 = "B1"  # Validation
    C1 = "C1"  # Uncertainty Quantification
    D1 = "D1"  # Code Verification
    E1 = "E1"  # Solution Verification
    F1 = "F1"  # Model Calibration
    G1 = "G1"  # Prediction Assessment
    H1 = "H1"  # Adequacy Assessment


# ---------------------------------------------------------------------------
# Dossier models
# ---------------------------------------------------------------------------

class EvidenceCategory(BaseModel):
    """One evidence category for a dossier."""
    id: str
    code: EvidenceCategoryCode
    name: str
    status: str = "Pending"
    artifact_count: int = 0


class ArtifactSummary(BaseModel):
    """Summary of a simulation artifact inside a dossier."""
    id: str
    name: str
    type: str = ""
    format: str = ""
    status: str = "Draft"
    checksum: Optional[str] = None
    size_bytes: Optional[int] = None
    uploaded_at: Optional[datetime] = None


class DossierSummary(BaseModel):
    """List-level representation of a dossier."""
    id: str
    name: str
    status: DossierStatus = DossierStatus.DRAFT
    dossier_type: str = "General"
    engineer: str = ""
    artifact_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DossierDetail(BaseModel):
    """Full detail of a dossier."""
    id: str
    name: str
    description: str = ""
    status: DossierStatus = DossierStatus.DRAFT
    dossier_type: str = "General"
    engineer: str = ""
    artifacts: List[ArtifactSummary] = Field(default_factory=list)
    evidence_categories: List[EvidenceCategory] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CreateDossierInput(BaseModel):
    name: str
    description: str = ""
    dossier_type: str = "General"
    engineer: str = ""


class UpdateDossierInput(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[DossierStatus] = None


# ---------------------------------------------------------------------------
# Approval / Decision Log
# ---------------------------------------------------------------------------

class ApprovalRecord(BaseModel):
    """Immutable approval record (ISO-CASCO)."""
    id: str
    dossier_id: str
    status: ApprovalStatus
    reviewer: str
    comment: str = ""
    signature_id: Optional[str] = None
    role: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DecisionLog(BaseModel):
    """Lifecycle audit trail entry for a dossier."""
    id: str
    dossier_id: str
    status: str
    reviewer: str
    comment: str = ""
    signature_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Audit / Compliance
# ---------------------------------------------------------------------------

class AuditFinding(BaseModel):
    """Single finding from an automated compliance audit."""
    id: str
    category: AuditCategory
    severity: AuditSeverity
    message: str
    requirement: str = ""


class AuditSummary(BaseModel):
    critical: int = 0
    warnings: int = 0
    passed: int = 0


class AuditReport(BaseModel):
    """Complete audit report for a dossier."""
    dossier_id: str
    health_score: float = Field(ge=0, le=100)
    findings: List[AuditFinding] = Field(default_factory=list)
    summary: AuditSummary = Field(default_factory=AuditSummary)


# ---------------------------------------------------------------------------
# MoSSEC Link
# ---------------------------------------------------------------------------

class MOSSECLink(BaseModel):
    """Typed edge in the MoSSEC digital thread."""
    source_id: str
    source_name: str = ""
    source_type: str = ""
    relationship: str = ""
    target_id: str
    target_name: str = ""
    target_type: str = ""
    description: str = ""
