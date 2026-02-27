"""
Ontology ingestion + SHACL validation combined router.

Re-exports routers from web/routes/ during migration.
Sources:
  - ontology_ingest_fastapi.py (1 endpoint, /api/ontology/*)
  - shacl_fastapi.py (2 endpoints, /api/validate/*)
"""
from src.web.routes.ontology_ingest_fastapi import router as ontology_router  # noqa: F401
from src.web.routes.shacl_fastapi import router as shacl_router  # noqa: F401
