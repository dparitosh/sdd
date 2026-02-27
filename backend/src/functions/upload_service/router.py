"""
File upload + STEP ingestion combined router.

Re-exports routers from web/routes/ during migration.
Sources:
  - upload_fastapi.py (5 endpoints, /api/upload/*)
  - step_ingest_fastapi.py (1 endpoint, /api/step/*)
"""
from src.web.routes.upload_fastapi import router as upload_router  # noqa: F401
from src.web.routes.step_ingest_fastapi import router as step_ingest_router  # noqa: F401
