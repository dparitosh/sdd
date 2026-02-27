"""FaaS entrypoint for ap243_service."""
from fastapi import FastAPI
from .router import router

app = FastAPI(title="AP243 Service", version="4.0")
app.include_router(router)

try:
    from mangum import Mangum
    handler = Mangum(app)
except ImportError:
    handler = None
