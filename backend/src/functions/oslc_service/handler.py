"""FaaS entrypoint for oslc_service."""
from fastapi import FastAPI
from .router import oslc_router, oslc_client_router, trs_router

app = FastAPI(title="OSLC Service", version="4.0")
app.include_router(oslc_router)
app.include_router(oslc_client_router, prefix="/api")
app.include_router(trs_router, prefix="/api")

try:
    from mangum import Mangum
    handler = Mangum(app)
except ImportError:
    handler = None
