"""FaaS entrypoint for graphql_service."""
from fastapi import FastAPI
from .router import graphql_router

app = FastAPI(title="GraphQL Service", version="4.0")
app.include_router(graphql_router, prefix="/api/graphql")

try:
    from mangum import Mangum
    handler = Mangum(app)
except ImportError:
    handler = None
