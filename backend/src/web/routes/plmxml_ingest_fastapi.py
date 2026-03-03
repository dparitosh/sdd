"""
PLMXML Ingestion Routes (FastAPI)

POST /api/plmxml/ingest        — ingest a Teamcenter PLMXML file by server path
POST /api/plmxml/upload        — upload a PLMXML file and ingest it immediately
GET  /api/plmxml/items         — list :PLMXMLItem nodes in the graph
GET  /api/plmxml/bom/{item_id} — reconstruct BOM tree for a TC item number
GET  /api/plmxml/datasets      — list :PLMXMLDataSet nodes
GET  /api/plmxml/step-links    — list PLMXMLDataSet->StepFile cross-reference edges
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from loguru import logger
from pydantic import BaseModel, Field

from src.web.services import get_neo4j_service
from src.web.services.plmxml_ingest_service import PLMXMLIngestConfig, PLMXMLIngestService
from src.web.dependencies import get_api_key

router = APIRouter(prefix="/api/plmxml", tags=["Teamcenter PLMXML"], dependencies=[Depends(get_api_key)])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class PLMXMLIngestRequest(BaseModel):
    path: str = Field(..., description="Absolute or repo-relative path to the PLMXML file")
    label: Optional[str] = Field(None, description="Optional display name override")
    create_step_links: bool = Field(True, description="Link DataSets to existing :StepFile nodes")
    batch_size: int = Field(200, ge=10, le=2000)


class PLMXMLIngestResponse(BaseModel):
    status: str
    file_uri: str
    schema_version: str
    items_upserted: int
    revisions_upserted: int
    bom_lines_upserted: int
    datasets_upserted: int
    step_links_created: int
    errors: List[str]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/ingest", response_model=PLMXMLIngestResponse, summary="Ingest PLMXML file by path")
def ingest_plmxml(req: PLMXMLIngestRequest):
    """
    Parse a Teamcenter PLMXML export and upsert its object graph into Neo4j.

    Creates:
    - **:PLMXMLItem** nodes for each TC Item (Part, Assembly, Document)
    - **:PLMXMLRevision** nodes per ItemRevision
    - **:PLMXMLBOMLine** nodes for each BOMViewOccurrence
    - **:PLMXMLDataSet** nodes for attached files (UGMASTER, DirectModel, PDF, …)
    - Cross-links to **:StepFile** nodes when dataset filenames match ingested STEP files
    """
    path = Path(req.path)
    repo_root = Path(__file__).resolve().parents[4]
    if not path.is_absolute():
        path = (repo_root / path).resolve()
    else:
        path = path.resolve()

    # Path-traversal guard: restrict to known directories
    allowed_roots = [
        (repo_root / "data").resolve(),
        (repo_root / "backend" / "data").resolve(),
        (repo_root / "smrlv12").resolve(),
    ]
    if not any(str(path).startswith(str(ar)) for ar in allowed_roots):
        raise HTTPException(
            status_code=400,
            detail=(
                "Path is not under an allowed root. "
                f"Allowed: {', '.join(str(ar) for ar in allowed_roots)}"
            ),
        )

    if not path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    if path.suffix.lower() not in (".xml", ".plmxml", ".plmxml5", ".plmxml6"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported extension '{path.suffix}'. Expected .xml / .plmxml",
        )

    cfg = PLMXMLIngestConfig(
        batch_size=req.batch_size,
        create_step_links=req.create_step_links,
    )
    try:
        svc = PLMXMLIngestService(cfg)
        result = svc.ingest_file(path, file_label=req.label)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception(f"PLMXML ingest failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    return PLMXMLIngestResponse(
        status="ok" if not result.errors else "partial",
        file_uri=result.file_uri,
        schema_version=result.schema_version,
        items_upserted=result.items_upserted,
        revisions_upserted=result.revisions_upserted,
        bom_lines_upserted=result.bom_lines_upserted,
        datasets_upserted=result.datasets_upserted,
        step_links_created=result.step_links_created,
        errors=result.errors,
    )


@router.post(
    "/upload",
    response_model=PLMXMLIngestResponse,
    summary="Upload and ingest a PLMXML file",
)
async def upload_and_ingest(
    file: UploadFile = File(..., description="PLMXML file (.xml / .plmxml)"),
    create_step_links: bool = True,
    batch_size: int = 200,
):
    """
    Upload a PLMXML file directly and ingest it into Neo4j immediately.
    The file is saved to a temp directory; the temp file is deleted after ingestion.
    """
    suffix = Path(file.filename or "upload.xml").suffix.lower()
    if suffix not in (".xml", ".plmxml", ".plmxml5", ".plmxml6"):
        raise HTTPException(status_code=400, detail=f"Unsupported extension '{suffix}'")

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    logger.info(f"PLMXML upload: saved {len(content)} bytes to {tmp_path}")

    try:
        cfg = PLMXMLIngestConfig(batch_size=batch_size, create_step_links=create_step_links)
        svc = PLMXMLIngestService(cfg)
        result = svc.ingest_file(tmp_path, file_label=file.filename)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception(f"PLMXML upload-ingest failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        tmp_path.unlink(missing_ok=True)

    return PLMXMLIngestResponse(
        status="ok" if not result.errors else "partial",
        file_uri=result.file_uri,
        schema_version=result.schema_version,
        items_upserted=result.items_upserted,
        revisions_upserted=result.revisions_upserted,
        bom_lines_upserted=result.bom_lines_upserted,
        datasets_upserted=result.datasets_upserted,
        step_links_created=result.step_links_created,
        errors=result.errors,
    )


# ---------------------------------------------------------------------------
# Query routes
# ---------------------------------------------------------------------------

def _neo4j_query(cypher: str, params: Dict[str, Any] | None = None, limit: int = 100) -> List[Dict]:
    neo4j = get_neo4j_service()
    with neo4j.driver.session(database=neo4j.database) as session:
        result = session.run(cypher, **(params or {}), limit=limit)
        return [dict(r) for r in result]


@router.get("/items", summary="List PLMXMLItem nodes")
def list_plmxml_items(limit: int = 100, item_type: Optional[str] = None):
    """
    Return all :PLMXMLItem nodes in the knowledge graph, optionally filtered by item_type
    (Part / Assembly / Document / …).
    """
    if item_type:
        rows = _neo4j_query(
            "MATCH (n:PLMXMLItem) WHERE n.item_type = $item_type "
            "RETURN n.uid AS uid, n.item_id AS item_id, n.name AS name, "
            "       n.item_type AS item_type ORDER BY n.item_id LIMIT $limit",
            {"item_type": item_type},
            limit=limit,
        )
    else:
        rows = _neo4j_query(
            "MATCH (n:PLMXMLItem) "
            "RETURN n.uid AS uid, n.item_id AS item_id, n.name AS name, "
            "       n.item_type AS item_type ORDER BY n.item_id LIMIT $limit",
            limit=limit,
        )
    return {"items": rows, "count": len(rows)}


@router.get("/bom/{item_id}", summary="Reconstruct BOM tree for a TC item number")
def get_bom(item_id: str, depth: int = 5):
    """
    Return the BOM tree rooted at the given TC Item number (item_id).
    Traverses :HAS_REVISION → :HAS_BOM_LINE → :REFERENCES up to `depth` levels.
    """
    cypher = """
    MATCH (root:PLMXMLItem {item_id: $item_id})
    OPTIONAL MATCH path = (root)-[:HAS_REVISION]->(:PLMXMLRevision)
                          -[:HAS_BOM_LINE*1..5]->(b:PLMXMLBOMLine)
                          -[:REFERENCES]->(child:PLMXMLItem)
    RETURN root.item_id AS root_id,
           root.name    AS root_name,
           b.uid        AS bom_line_uid,
           b.quantity   AS qty,
           b.find_num   AS find_num,
           child.item_id AS child_item_id,
           child.name    AS child_name,
           child.item_type AS child_type
    LIMIT 500
    """
    rows = _neo4j_query(cypher, {"item_id": item_id})
    if not rows:
        raise HTTPException(status_code=404, detail=f"No PLMXMLItem found for item_id '{item_id}'")
    return {"item_id": item_id, "bom_lines": rows, "count": len(rows)}


@router.get("/datasets", summary="List PLMXMLDataSet nodes")
def list_datasets(ds_type: Optional[str] = None, limit: int = 100):
    """Return dataset nodes, optionally filtered by dataset type (UGMASTER / PDF / …)."""
    if ds_type:
        rows = _neo4j_query(
            "MATCH (d:PLMXMLDataSet) WHERE d.ds_type = $ds_type "
            "RETURN d.uid AS uid, d.name AS name, d.ds_type AS ds_type, "
            "       d.member AS member LIMIT $limit",
            {"ds_type": ds_type},
            limit=limit,
        )
    else:
        rows = _neo4j_query(
            "MATCH (d:PLMXMLDataSet) "
            "RETURN d.uid AS uid, d.name AS name, d.ds_type AS ds_type, "
            "       d.member AS member LIMIT $limit",
            limit=limit,
        )
    return {"datasets": rows, "count": len(rows)}


@router.get("/step-links", summary="List PLMXML → STEP file cross-references")
def list_step_links(limit: int = 200):
    """
    Return all (:PLMXMLDataSet)-[:LINKED_STEP_FILE]->(:StepFile) edges.
    Useful for tracing from TC items to their CAD geometry in the graph.
    """
    rows = _neo4j_query(
        "MATCH (d:PLMXMLDataSet)-[:LINKED_STEP_FILE]->(sf:StepFile) "
        "RETURN d.uid AS ds_uid, d.name AS ds_name, d.ds_type AS ds_type, "
        "       sf.name AS step_name, sf.file_uri AS step_uri LIMIT $limit",
        limit=limit,
    )
    return {"links": rows, "count": len(rows)}
