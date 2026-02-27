"""
Graph service layer.

Business logic for graph data access and hierarchy traversal.
Currently delegates to the web service layer.
"""
from src.web.services.neo4j_service import get_neo4j_service  # noqa: F401
