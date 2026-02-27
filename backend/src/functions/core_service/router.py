"""
Core API (packages, classes, search, stats, cypher) router.

Re-exports the existing router from web/routes/ during migration.
Original: backend/src/web/routes/core_fastapi (10 endpoints)
Mounted at: /api
"""
from src.web.routes.core_fastapi import router  # noqa: F401
