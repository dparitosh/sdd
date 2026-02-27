"""
AP242 CAD Integration router.

Re-exports the existing router from web/routes/ during migration.
Original: backend/src/web/routes/ap242_fastapi (8 endpoints)
Mounted at: /api/ap242
"""
from src.web.routes.ap242_fastapi import router  # noqa: F401
