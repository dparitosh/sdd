"""
backend.src.functions — FaaS-ready function domains.

Each sub-package is an independently deployable function containing:
  - handler.py  — Mangum/Azure FaaS entrypoint
  - router.py   — FastAPI APIRouter with domain endpoints
  - service.py  — Business logic (imports from core/)

For local development, all routers are mounted in ``main.py``.
"""
