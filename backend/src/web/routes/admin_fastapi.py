"""Admin maintenance routes.

These endpoints are intended for local/dev maintenance actions such as clearing
Neo4j during development or test runs.

Safety:
- Requires API key dependency (dev bypass applies if API_KEY is unset)
- Requires an explicit confirmation flag in the request body
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.web.dependencies import get_api_key
from src.web.utils.responses import Neo4jJSONResponse
from src.web.services import get_neo4j_service


router = APIRouter(prefix="/api/admin", tags=["Admin"])


class ClearDbRequest(BaseModel):
    confirm: bool = Field(
        False,
        description="Must be true to confirm you want to delete ALL nodes and relationships.",
    )
    batch_size: int = Field(
        5000,
        ge=1,
        le=50000,
        description="Batch size for iterative deletion.",
    )


@router.post("/clear-db", response_class=Neo4jJSONResponse)
async def clear_db(req: ClearDbRequest, _api_key: str = Depends(get_api_key)):
    """Delete ALL nodes and relationships from the configured Neo4j database."""

    if not req.confirm:
        raise HTTPException(
            status_code=400,
            detail="Refusing to clear database without confirm=true in request body.",
        )

    neo4j = get_neo4j_service()

    deleted_total = 0
    while True:
        result = neo4j.execute_query(
            "MATCH (n) WITH n LIMIT $limit DETACH DELETE n RETURN count(n) as deleted",
            {"limit": int(req.batch_size)},
            use_cache=False,
        )
        deleted = int(result[0]["deleted"]) if result else 0
        deleted_total += deleted
        if deleted == 0:
            break

    remaining = neo4j.execute_query(
        "MATCH (n) RETURN count(n) as count",
        use_cache=False,
    )
    remaining_nodes = int(remaining[0]["count"]) if remaining else -1

    return {
        "success": True,
        "deleted_total": deleted_total,
        "remaining_nodes": remaining_nodes,
    }
