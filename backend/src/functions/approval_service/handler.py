"""FaaS entrypoint for approval_service."""
from fastapi import FastAPI
from .router import router

app = FastAPI(title="Approval Service", version="4.0")
app.include_router(router, prefix="/api/v1/approvals")

try:
    from mangum import Mangum
    handler = Mangum(app)
except ImportError:
    handler = None
