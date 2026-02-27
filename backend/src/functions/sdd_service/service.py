"""
SDD service layer.

Business logic for dossier CRUD and versioning.
Will be populated in Phase 1c when dossier logic is extracted
from simulation_service.
"""
from src.core.models.sdd_types import (  # noqa: F401
    DossierStatus,
    DossierSummary,
    DossierDetail,
    CreateDossierInput,
    UpdateDossierInput,
)
