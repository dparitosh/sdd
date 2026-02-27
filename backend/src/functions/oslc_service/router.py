"""
OSLC Provider + Client + TRS combined router.

Re-exports routers from web/routes/ during migration.
Sources:
  - oslc_fastapi.py (6 endpoints, /oslc/*)
  - oslc_client_fastapi.py (2 endpoints, /oslc/client/*)
  - trs_fastapi.py (3 endpoints, /oslc/trs/*)
"""
from src.web.routes.oslc_fastapi import router as oslc_router  # noqa: F401
from src.web.routes.oslc_client_fastapi import router as oslc_client_router  # noqa: F401
from src.web.routes.trs_fastapi import router as trs_router  # noqa: F401
