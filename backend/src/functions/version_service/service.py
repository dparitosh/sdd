"""
Version service layer.

Business logic for version control, admin operations, and cache management.
Currently delegates to the web service layer.
"""
from src.web.services.neo4j_service import get_neo4j_service  # noqa: F401
