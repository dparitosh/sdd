"""Schema re-export for graphql_service.

Re-exports the Strawberry schema and Query type from the canonical
graphql_fastapi module. Phase 1c may extend this with Mutation types.
"""
from src.web.routes.graphql_fastapi import schema, Query

__all__ = ["schema", "Query"]
