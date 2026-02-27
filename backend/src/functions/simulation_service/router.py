"""
Simulation service router.

Re-exports the existing simulation router from web/routes/ during migration.
This currently includes both simulation AND dossier endpoints.
The dossier endpoints will be split to sdd_service in Phase 1c.

Original: backend/src/web/routes/simulation_fastapi.py (16 endpoints)
Mounted at: /api/simulation
"""
from src.web.routes.simulation_fastapi import router  # noqa: F401
