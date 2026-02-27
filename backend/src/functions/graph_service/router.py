"""
Graph data + Hierarchy combined router.

Re-exports routers from web/routes/ during migration.
Sources:
  - graph_fastapi.py (3 endpoints, /api/graph/*)
  - hierarchy_fastapi.py (5 endpoints, /api/hierarchy/*)
"""
from src.web.routes.graph_fastapi import router as graph_router  # noqa: F401
from src.web.routes.hierarchy_fastapi import router as hierarchy_router  # noqa: F401
