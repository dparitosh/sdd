"""
SHACL Validation Routes (FastAPI)
Validates RDF data against SHACL shape files for AP239/AP242 compliance.
"""

from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from loguru import logger
from rdflib import Graph

from src.web.services.shacl_validator import SHACLValidator

router = APIRouter(prefix="/api/validate", tags=["SHACL Validation"])


@router.post("/shacl")
async def validate_shacl(
    file: UploadFile = File(...),
    standard: str = Query("ap239", regex="^(ap239|ap242)$"),
    format: str = Query("turtle", regex="^(turtle|xml|json-ld)$"),
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
    standard: str = Query("ap239", regex="^(ap239|ap242)$"),
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
