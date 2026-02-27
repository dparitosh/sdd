"""
AP239 Requirements Management router.

Re-exports the existing router from web/routes/ during migration.
Original: backend/src/web/routes/ap239_fastapi.py (8 endpoints)
Mounted at: /api/ap239
"""
from src.web.routes.ap239_fastapi import router  # noqa: F401
