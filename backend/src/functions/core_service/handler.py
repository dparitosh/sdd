"""FaaS entrypoint for core_service."""
from fastapi import FastAPI
from .router import router

app = FastAPI(title="Core Service", version="4.0")
app.include_router(router)

try:
    from mangum import Mangum
    handler = Mangum(app)
except ImportError:
    handler = None
