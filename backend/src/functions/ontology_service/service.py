"""
Ontology service layer.

Combines ontology ingestion and SHACL validation services.
Currently delegates to the web service layer.
"""
from src.web.services.ontology_ingest_service import OntologyIngestService  # noqa: F401
