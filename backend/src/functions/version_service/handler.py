"""FaaS entrypoint for version_service."""
from fastapi import FastAPI
from .router import version_router, admin_router, cache_router

app = FastAPI(title="Version Service", version="4.0")
app.include_router(version_router, prefix="/api")
app.include_router(admin_router)
app.include_router(cache_router, prefix="/api")

try:
    from mangum import Mangum
    handler = Mangum(app)
except ImportError:
    handler = None
