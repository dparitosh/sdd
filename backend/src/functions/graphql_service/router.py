"""Router re-export for graphql_service.

Strawberry's GraphQLRouter provides both GET (GraphiQL UI) and POST (query execution).
Mounted at /api/graphql in the unified app.
"""
from src.web.routes.graphql_fastapi import graphql_router, schema

__all__ = ["graphql_router", "schema"]
