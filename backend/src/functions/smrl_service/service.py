"""
ISO 10303-4443 Generic CRUD service layer.

Business logic for smrl_service.
Currently delegates to the web service layer.
"""
from src.web.services.neo4j_service import get_neo4j_service  # noqa: F401
