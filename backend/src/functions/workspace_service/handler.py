"""FaaS entrypoint for workspace_service."""
from fastapi import FastAPI
from .router import router

app = FastAPI(title="Workspace Service", version="4.0")
app.include_router(router, prefix="/api/v1/workspace")

try:
    from mangum import Mangum
    handler = Mangum(app)
except ImportError:
    handler = None
