"""
Metrics + KPI Analytics service layer.

Business logic for telemetry_service.
Currently delegates to the web service layer.
"""
from src.web.services.neo4j_service import get_neo4j_service  # noqa: F401
