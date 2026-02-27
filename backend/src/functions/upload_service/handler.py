"""FaaS entrypoint for upload_service."""
from fastapi import FastAPI
from .router import upload_router, step_ingest_router

app = FastAPI(title="Upload Service", version="4.0")
app.include_router(upload_router)
app.include_router(step_ingest_router)

try:
    from mangum import Mangum
    handler = Mangum(app)
except ImportError:
    handler = None
