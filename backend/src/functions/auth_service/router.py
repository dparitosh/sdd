"""
Authentication + Session management combined router.

Re-exports routers from web/routes/ during migration.
Sources:
  - auth_fastapi.py (5 endpoints, /api/auth/*)
  - sessions_fastapi.py (7 endpoints, /api/sessions/*)
"""
from src.web.routes.auth_fastapi import router as auth_router  # noqa: F401
from src.web.routes.sessions_fastapi import router as sessions_router  # noqa: F401
