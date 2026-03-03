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


@router.get("/", response_class=Neo4jJSONResponse)
async def list_ontologies(
    api_key: str = Depends(get_api_key),
):
    """List all ingested ontologies from Neo4j.

    Returns a summary array with name, class/property counts, and creation date.
    """
    from src.web.services import get_neo4j_service

    try:
        neo4j = get_neo4j_service()
        query = """
        MATCH (o:Ontology)
        OPTIONAL MATCH (o)-[:DEFINES_CLASS]->(c:OWLClass)
        OPTIONAL MATCH (o)-[:DEFINES_PROPERTY]->(p:OWLProperty)
        RETURN o.id AS id,
               o.name AS name,
               o.uri AS uri,
               o.createdAt AS created_at,
               count(DISTINCT c) AS class_count,
               count(DISTINCT p) AS property_count
        ORDER BY o.name
        """
        results = neo4j.execute_query(query)
        ontologies = [
            {
                "id": r.get("id") or r.get("name"),
                "name": r.get("name"),
                "uri": r.get("uri"),
                "created_at": str(r.get("created_at", "")),
                "class_count": r.get("class_count", 0),
                "property_count": r.get("property_count", 0),
            }
            for r in results
        ]
        return ontologies
    except Exception as e:
        logger.error(f"Failed to list ontologies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
    ap_level: Optional[str] = Field(
        None,
        description="AP level tag for all ingested nodes (e.g. 'AP239', 'AP242', 'AP243'). Defaults to 'AP243'.",
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

        cfg_kwargs = {}
        if req.ap_level:
            cfg_kwargs["ap_level"] = req.ap_level
            cfg_kwargs["ap_schema"] = req.ap_level
            cfg_kwargs["ap_standard"] = req.ap_level
        service = OntologyIngestService(OntologyIngestConfig(**cfg_kwargs))
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


@router.post("/ingest-standard", response_class=Neo4jJSONResponse)
async def ingest_standard_ontologies(
    api_key: str = Depends(get_api_key),
):
    """Ingest the three standard MoSSEC ontologies (AP243, STEP-Core, PLCS-4439).

    Delegates to OntologyAgent.ingest_standard_ontologies().
    """
    from src.agents.ontology_agent import OntologyAgent

    try:
        agent = OntologyAgent()
        results = agent.ingest_standard_ontologies()
        return {"status": "ok", "results": results}
    except Exception as e:
        logger.error(f"Standard ontology ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_class=Neo4jJSONResponse)
async def ontology_classification_stats(
    api_key: str = Depends(get_api_key),
):
    """Return classified / unclassified counts per node label."""
    from src.web.services import get_neo4j_service

    try:
        neo4j = get_neo4j_service()
        labels = ["PLMXMLItem", "PLMXMLRevision", "PLMXMLBOMLine", "PLMXMLDataSet", "StepFile"]
        stats = []
        for lbl in labels:
            q = f"""
            MATCH (n:{lbl})
            OPTIONAL MATCH (n)-[:CLASSIFIED_AS]->()
            WITH n, count(*) > 0 AS has_class
            RETURN
              '{lbl}' AS label,
              count(CASE WHEN has_class THEN 1 END) AS classified,
              count(CASE WHEN NOT has_class THEN 1 END) AS unclassified
            """
            rows = neo4j.execute_query(q)
            if rows:
                stats.append(rows[0])
            else:
                stats.append({"label": lbl, "classified": 0, "unclassified": 0})
        return stats
    except Exception as e:
        logger.error(f"Classification stats query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
