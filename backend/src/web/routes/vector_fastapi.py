from typing import Any, Dict
import os
import json
import pathlib

import requests as _requests
from fastapi import APIRouter, Depends, HTTPException

from loguru import logger

from src.agents.agent_tools import VectorStoreTool
from src.agents.vectorstore_es import ElasticsearchVectorStore
from src.web.dependencies import get_api_key

router = APIRouter(dependencies=[Depends(get_api_key)])

_vector: VectorStoreTool | None = None
_es: ElasticsearchVectorStore | None = None


def _get_vector() -> VectorStoreTool:
    """Lazy-initialize VectorStoreTool so app starts even if OpenSearch is down."""
    global _vector
    if _vector is None:
        _vector = VectorStoreTool()
    return _vector


def _get_es() -> ElasticsearchVectorStore:
    """Lazy-initialize ElasticsearchVectorStore so app starts even if OpenSearch is down."""
    global _es
    if _es is None:
        _es = ElasticsearchVectorStore()
    return _es

_PROGRESS_DIR = pathlib.Path(__file__).resolve().parents[3] / "data" / "vectorize_progress"


@router.post("/index")
def index_document(payload: Dict[str, Any]):
    """Index a document into the vectorstore.

    JSON body: {"index": "embeddings", "id": "doc1", "text": "...", "metadata": {...}}
    """
    try:
        index_name = payload.get("index") or _get_vector().index
        doc_id = payload["id"]
        text = payload["text"]
    except KeyError:
        raise HTTPException(status_code=400, detail="Missing required fields: id, text")

    metadata = payload.get("metadata")
    result = _get_vector().index_document(doc_id, text, metadata)
    logger.info(f"Indexed document {doc_id} into {index_name}")
    return {"ok": True, "result": result}


@router.post("/search")
def search(payload: Dict[str, Any]):
    """Search vectorstore by text query. Body: {"index":"embeddings", "query":"...", "k":10}
    """
    try:
        query_text = payload["query"]
    except KeyError:
        raise HTTPException(status_code=400, detail="Missing 'query' in body")

    k = int(payload.get("k", 10))
    results = _get_vector().search(query_text, k=k)
    return {"ok": True, "result": results}


@router.get("/stats")
def vector_stats():
    """Return vectorstore index stats and vectorization progress checkpoints."""
    host = _get_es().host
    index = os.getenv("VECTORSTORE_INDEX", "embeddings")

    # OpenSearch doc count
    try:
        r = _requests.get(f"{host}/{index}/_count", timeout=30)
        doc_count = r.json().get("count", 0) if r.ok else None
    except Exception as exc:
        doc_count = f"error: {exc}"

    # Vectorization progress files
    progress: Dict[str, Any] = {}
    if _PROGRESS_DIR.is_dir():
        for pf in _PROGRESS_DIR.glob("*.progress.json"):
            try:
                progress[pf.stem.replace(".progress", "")] = json.loads(pf.read_text())
            except Exception:
                progress[pf.stem] = {"error": "unreadable"}

    return {
        "ok": True,
        "index": index,
        "doc_count": doc_count,
        "vectorize_progress": progress,
    }


@router.get("/reconcile")
def vector_reconcile():
    """Compare Neo4j node counts with OpenSearch doc counts per label.

    Returns a per-label table showing neo4j_count, os_count, and gap.
    """
    from src.web.services.neo4j_service import get_neo4j_service

    neo4j = get_neo4j_service()
    host = _get_es().host
    index = os.getenv("VECTORSTORE_INDEX", "embeddings")

    # Get all labels + counts from Neo4j
    try:
        label_rows = neo4j.execute_query(
            "CALL db.labels() YIELD label "
            "CALL (label) { MATCH (n) WHERE label IN labels(n) RETURN count(n) AS cnt } "
            "RETURN label, cnt ORDER BY cnt DESC",
            {},
        )
        neo4j_counts = {r["label"]: r["cnt"] for r in label_rows if r["cnt"] > 0}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Neo4j query failed: {exc}")

    # Total docs in OpenSearch
    try:
        r = _requests.get(f"{host}/{index}/_count", timeout=30)
        total_os = r.json().get("count", 0) if r.ok else 0
    except Exception as exc:
        total_os = f"error: {exc}"

    # Neo4j total unique nodes and indexable (uuid-bearing) nodes
    try:
        neo4j_total_row = neo4j.execute_query("MATCH (n) RETURN count(n) AS cnt", {})
        neo4j_total = neo4j_total_row[0]["cnt"] if neo4j_total_row else 0
    except Exception:
        neo4j_total = None

    try:
        uuid_rows = neo4j.execute_query(
            "MATCH (n) WHERE n.uuid IS NOT NULL RETURN count(n) AS cnt", {}
        )
        neo4j_indexable = uuid_rows[0]["cnt"] if uuid_rows else 0
    except Exception:
        neo4j_indexable = None

    indexable_gap = (
        (neo4j_indexable - total_os)
        if isinstance(total_os, int) and neo4j_indexable is not None
        else None
    )

    return {
        "ok": True,
        "index": index,
        "neo4j_total_nodes": neo4j_total,
        "neo4j_indexable_nodes": neo4j_indexable,  # nodes WITH uuid — these are vectorized
        "opensearch_docs": total_os,
        "indexable_gap": indexable_gap,  # 0 means full coverage of all uuid-bearing nodes
        "note": (
            "neo4j_indexable_nodes counts only nodes with a uuid property. "
            "Nodes without uuid (external OWL/ontology imports) are not indexed by design."
        ),
        "neo4j_counts_by_label": neo4j_counts,
    }

