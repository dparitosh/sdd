"""
AP239 service layer.

Business logic for AP239 Requirements Management.
Currently delegates to the web service layer.
"""
from src.web.services.neo4j_service import get_neo4j_service  # noqa: F401
