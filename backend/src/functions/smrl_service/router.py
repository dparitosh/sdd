"""
ISO 10303-4443 Generic CRUD router.

Re-exports the existing router from web/routes/ during migration.
Original: backend/src/web/routes/smrl_v1_fastapi (17 endpoints)
Mounted at: /api/v1
"""
from src.web.routes.smrl_v1_fastapi import router  # noqa: F401
