"""
Metrics + KPI Analytics router.

Re-exports the existing router from web/routes/ during migration.
Original: backend/src/web/routes/metrics_fastapi (3 endpoints)
Mounted at: /api/metrics
"""
from src.web.routes.metrics_fastapi import router  # noqa: F401
