"""FaaS entrypoint for auth_service."""
from fastapi import FastAPI
from .router import auth_router, sessions_router

app = FastAPI(title="Auth Service", version="4.0")
app.include_router(auth_router, prefix="/api")
app.include_router(sessions_router, prefix="/api")

try:
    from mangum import Mangum
    handler = Mangum(app)
except ImportError:
    handler = None
