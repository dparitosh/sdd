"""
SHACL Validation Routes (FastAPI)
Validates RDF data against SHACL shape files for AP239/AP242 compliance.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from loguru import logger
from rdflib import Graph

from src.web.services.shacl_validator import SHACLValidator
from src.web.dependencies import get_api_key

router = APIRouter(prefix="/api/validate", tags=["SHACL Validation"], dependencies=[Depends(get_api_key)])


@router.post("/shacl")
async def validate_shacl(
    file: UploadFile = File(...),
    standard: str = Query("ap239", pattern="^(ap239|ap242)$"),
    format: str = Query("turtle", pattern="^(turtle|xml|json-ld)$"),
):
    """
    Validate an uploaded RDF file against SHACL shapes.

    - **file**: RDF file (Turtle, RDF/XML, or JSON-LD)
    - **standard**: Which shape set to validate against (`ap239` or `ap242`)
    - **format**: RDF serialization format of the uploaded file
    """
    body = await file.read()
    if not body:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    data_graph = Graph()
    try:
        data_graph.parse(data=body, format=format)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Cannot parse RDF: {exc}")

    logger.info(f"SHACL validate: {file.filename} against {standard} ({len(data_graph)} triples)")

    try:
        conforms = SHACLValidator.validate_graph(data_graph, standard=standard)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Validation error: {exc}")

    return {
        "conforms": conforms,
        "standard": standard,
        "triples": len(data_graph),
        "filename": file.filename,
    }


@router.post("/shacl/inline")
async def validate_shacl_inline(
    payload: dict,
    standard: str = Query("ap239", pattern="^(ap239|ap242)$"),
):
    """
    Validate inline RDF data (as Turtle string) against SHACL shapes.

    Request body: `{ "rdf": "<turtle-string>" }`
    """
    rdf_text = payload.get("rdf")
    if not rdf_text:
        raise HTTPException(status_code=400, detail="'rdf' field is required")

    data_graph = Graph()
    try:
        data_graph.parse(data=rdf_text, format="turtle")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Cannot parse Turtle: {exc}")

    conforms = SHACLValidator.validate_graph(data_graph, standard=standard)

    return {
        "conforms": conforms,
        "standard": standard,
        "triples": len(data_graph),
    }


# ---------------------------------------------------------------------------
# Graph-level SHACL validation (validates Neo4j nodes, not uploaded RDF)
# ---------------------------------------------------------------------------

from src.web.services.shacl_validation_service import SHACLValidationService

_validation_svc: SHACLValidationService | None = None


def _get_validation_svc() -> SHACLValidationService:
    global _validation_svc
    if _validation_svc is None:
        _validation_svc = SHACLValidationService()
    return _validation_svc


@router.get("/shacl/validate/{label}")
async def validate_label(label: str):
    """Batch-validate all nodes with the given Neo4j label.

    Returns the number of nodes checked and a list of violations.
    """
    svc = _get_validation_svc()
    result = svc.validate_batch(label)
    return {
        "label": result.label,
        "nodes_checked": result.nodes_checked,
        "violations_found": result.violations_found,
        "violations": [
            {
                "uid": v.uid,
                "shape_name": v.shape_name,
                "target_uid": v.target_uid,
                "property": v.property,
                "severity": v.severity,
                "message": v.message,
            }
            for v in result.violations
        ],
    }


@router.get("/shacl/violations/{uid}")
async def get_violations(uid: str):
    """Return existing SHACL violations for a specific node."""
    svc = _get_validation_svc()
    violations = svc.get_violations(uid)
    return {"uid": uid, "violations": violations}


@router.get("/shacl/report")
async def shacl_report():
    """Summary of all violations grouped by shape name and severity."""
    svc = _get_validation_svc()
    rows = svc.get_report()
    return {"summary": rows}
