"""
AP243 Product Structure & Ontologies router.

Re-exports the existing router from web/routes/ during migration.
Original: backend/src/web/routes/ap243_fastapi (12 endpoints)
Mounted at: /api/ap243
"""
from src.web.routes.ap243_fastapi import router  # noqa: F401
