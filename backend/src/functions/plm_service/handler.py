"""FaaS entrypoint for plm_service."""
from fastapi import FastAPI
from .router import plm_connectors_router, plm_integration_router

app = FastAPI(title="PLM Service", version="4.0")
app.include_router(plm_connectors_router, prefix="/api/v1/plm")
app.include_router(plm_integration_router, prefix="/api")

try:
    from mangum import Mangum
    handler = Mangum(app)
except ImportError:
    handler = None
