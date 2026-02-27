"""
Multi-Format Export router.

Re-exports the existing router from web/routes/ during migration.
Original: backend/src/web/routes/export_fastapi (8 endpoints)
Mounted at: /api/export
"""
from src.web.routes.export_fastapi import router  # noqa: F401
