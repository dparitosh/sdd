"""
AI Agent Orchestrator router.

Re-exports the existing router from web/routes/ during migration.
Original: backend/src/web/routes/agents_fastapi (1 endpoint)
Mounted at: /api/agents
"""
from src.web.routes.agents_fastapi import router  # noqa: F401
