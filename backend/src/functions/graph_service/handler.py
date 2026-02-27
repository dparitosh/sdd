"""FaaS entrypoint for graph_service."""
from fastapi import FastAPI
from .router import graph_router, hierarchy_router

app = FastAPI(title="Graph Service", version="4.0")
app.include_router(graph_router, prefix="/api/graph")
app.include_router(hierarchy_router, prefix="/api/hierarchy")

try:
    from mangum import Mangum
    handler = Mangum(app)
except ImportError:
    handler = None
