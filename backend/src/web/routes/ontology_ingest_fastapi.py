"""Ontology ingestion routes (FastAPI).

These endpoints exist primarily so AI agents can use the backend as a tool:
- Agents can call an HTTP endpoint to ingest ontology reference data
- The same logic is reusable in scripts/tests via OntologyIngestService

Security:
- Requires API key (same dependency used elsewhere)
- Restricts file paths to known safe roots inside the repo
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from loguru import logger

from src.web.dependencies import get_api_key
from src.web.utils.responses import Neo4jJSONResponse
from src.web.services.ontology_ingest_service import (
    OntologyIngestService,
    OntologyIngestConfig,
)


router = APIRouter(prefix="/api/ontology", tags=["Ontology Ingestion"])


class OntologyIngestRequest(BaseModel):
    """Request to ingest an ontology file from disk."""

    # Relative path from repo root OR an absolute path under allowed roots.
    path: str = Field(
        ..., description="Path to .owl/.ttl/.rdf/.xml file (restricted to allowed roots)"
    )
    ontology_name: Optional[str] = Field(
        None,
        description="Override displayed ontology name (defaults to owl:Ontology title/label or file stem)",
    )
    rdf_format: Optional[str] = Field(
        None,
        description="Optional rdflib format hint (e.g., 'xml', 'turtle', 'json-ld')",
    )


class OntologyIngestResponse(BaseModel):
    success: bool
    message: str
    stats: dict


def _repo_root() -> Path:
    # backend/src/web/routes -> backend/src/web -> backend/src -> backend -> repo
    return Path(__file__).resolve().parents[4]


def _resolve_safe_path(user_path: str) -> Path:
    root = _repo_root()
    p = Path(user_path)

    if not p.is_absolute():
        p = (root / p).resolve()
    else:
        p = p.resolve()

    allowed_roots = [
        (root / "smrlv12").resolve(),
        (root / "data" / "uploads").resolve(),
        (root / "data" / "raw").resolve(),
    ]

    if not any(str(p).startswith(str(ar)) for ar in allowed_roots):
        raise HTTPException(
            status_code=400,
            detail=(
                "Path is not under an allowed root. Allowed roots: "
                + ", ".join(str(ar) for ar in allowed_roots)
            ),
        )

    if p.suffix.lower() not in {".owl", ".ttl", ".rdf", ".xml", ".jsonld", ".json"}:
        raise HTTPException(
            status_code=400,
            detail="Unsupported ontology file extension. Use .owl/.ttl/.rdf/.xml/.jsonld/.json",
        )

    if not p.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {p}")

    return p


@router.post("/ingest", response_model=OntologyIngestResponse, response_class=Neo4jJSONResponse)
async def ingest_ontology(
    req: OntologyIngestRequest,
    api_key: str = Depends(get_api_key),
):
    """Ingest an ontology file (OWL/RDF) into Neo4j reference-data labels.

    This is intended to be callable by AI agents as a tool endpoint.
    """

    try:
        rdf_path = _resolve_safe_path(req.path)

        service = OntologyIngestService(OntologyIngestConfig())
        stats = service.ingest_file(
            rdf_path,
            ontology_name=req.ontology_name,
            rdf_format=req.rdf_format,
        )

        return {
            "success": True,
            "message": f"Ingested ontology: {stats.ontology_name}",
            "stats": stats.__dict__,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ontology ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
