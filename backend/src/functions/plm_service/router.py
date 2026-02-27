"""
PLM connectors + integration combined router.

Re-exports routers from web/routes/ during migration.
Sources:
  - plm_connectors_fastapi.py (3 endpoints, /api/v1/plm/*)
  - plm_fastapi.py (5 endpoints, /api/plm/*)
"""
from src.web.routes.plm_connectors_fastapi import router as plm_connectors_router  # noqa: F401
from src.web.routes.plm_fastapi import router as plm_integration_router  # noqa: F401
