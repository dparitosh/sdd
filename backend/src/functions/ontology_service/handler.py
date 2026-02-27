"""FaaS entrypoint for ontology_service."""
from fastapi import FastAPI
from .router import ontology_router, shacl_router

app = FastAPI(title="Ontology Service", version="4.0")
app.include_router(ontology_router)
app.include_router(shacl_router)

try:
    from mangum import Mangum
    handler = Mangum(app)
except ImportError:
    handler = None
