"""
Version control + Admin + Cache management combined router.

Re-exports routers from web/routes/ during migration.
Sources:
  - version_fastapi.py (4 endpoints, /api/version/*)
  - admin_fastapi.py (1 endpoint, /api/admin/*)
  - cache_fastapi.py (6 endpoints, /api/cache/*)
"""
from src.web.routes.version_fastapi import router as version_router  # noqa: F401
from src.web.routes.admin_fastapi import router as admin_router  # noqa: F401
from src.web.routes.cache_fastapi import router as cache_router  # noqa: F401
