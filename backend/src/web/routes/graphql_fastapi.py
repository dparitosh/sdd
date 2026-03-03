"""GraphQL API (read-only) for the MBSE Knowledge Graph.

This provides a minimal schema intended for UI simplification (single endpoint) while
preserving the existing REST API.
"""

from __future__ import annotations

import re
from typing import Any, Optional

import strawberry
from fastapi import Depends
from loguru import logger
from strawberry.fastapi import GraphQLRouter
from strawberry.scalars import JSON

from src.web.dependencies import get_api_key
from src.web.services import get_neo4j_service


_DISALLOWED_CYPHER_RE = re.compile(
    r"\b("
    r"CREATE|MERGE|SET|DELETE|DETACH|REMOVE|DROP|CALL\s+dbms|CALL\s+apoc|LOAD\s+CSV|"
    r"ADMIN|GRANT|DENY|REVOKE|ALTER|PASSWORD|USER|ROLE"
    r")\b",
    re.IGNORECASE,
)


def _assert_read_only_cypher(query: str) -> None:
    if _DISALLOWED_CYPHER_RE.search(query or ""):
        raise ValueError("Only read-only Cypher is allowed")


@strawberry.type
class Query:
    @strawberry.field
    def statistics(self) -> JSON:
        """Return graph statistics in the same shape as the REST `/api/stats` endpoint."""
        try:
            neo4j = get_neo4j_service()
            return neo4j.get_statistics()
        except Exception as exc:
            logger.error(f"GraphQL statistics resolver error: {exc}")
            raise Exception(f"Failed to query Neo4j statistics: {exc}") from exc

    @strawberry.field
    def cypher_read(
        self, query: str, params: Optional[JSON] = None, limit: int = 200
    ) -> list[JSON]:
        """Execute a read-only Cypher query and return rows as JSON objects.

        Notes:
        - This is intentionally read-only and blocks unsafe clauses.
        - For complex needs, prefer the REST endpoints that expose curated queries.
        """
        _assert_read_only_cypher(query)

        bound_params: dict[str, Any] = dict(params or {})
        bound_params.setdefault("limit", limit)

        # If the query doesn't contain an explicit LIMIT, we append one defensively.
        normalized = query.strip().rstrip(";")
        if re.search(r"\bLIMIT\b", normalized, re.IGNORECASE) is None:
            normalized = f"{normalized}\nLIMIT $limit"

        try:
            neo4j = get_neo4j_service()
            rows = neo4j.execute_query(normalized, bound_params)
            return [dict(row) for row in rows]
        except Exception as exc:
            logger.error(f"GraphQL cypher_read resolver error: {exc}")
            raise Exception(f"Failed to execute Cypher query: {exc}") from exc


schema = strawberry.Schema(query=Query)

# Secure by default: respect the existing API key dependency.
graphql_router = GraphQLRouter(schema, dependencies=[Depends(get_api_key)])
