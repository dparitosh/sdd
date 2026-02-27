"""FaaS entrypoint for audit_service."""
from fastapi import FastAPI
from .router import router

app = FastAPI(title="Audit Service", version="4.0")
app.include_router(router, prefix="/api/v1/audit")

try:
    from mangum import Mangum
    handler = Mangum(app)
except ImportError:
    handler = None
