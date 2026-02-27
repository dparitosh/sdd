"""
EXPRESS Schema Parser & Analyzer router.

Re-exports the existing router from web/routes/ during migration.
Original: backend/src/web/routes/express_parser_fastapi (18 endpoints)
Mounted at: /api/express
"""
from src.web.routes.express_parser_fastapi import router  # noqa: F401
