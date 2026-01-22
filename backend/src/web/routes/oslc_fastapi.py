"""
OSLC Routes (FastAPI)
Endpoints for Open Services for Lifecycle Collaboration compliance.
Acts as an OSLC Server for RM (Requirements), AM (Architecture), and QM (Quality).
"""

from fastapi import APIRouter, Depends, Header, Request, Response
from loguru import logger
from src.web.services.oslc_service import OSLCService

router = APIRouter(prefix="/oslc", tags=["OSLC Semantic Web"])

def get_oslc_service(request: Request) -> OSLCService:
    # Dynamically determine base URL from request
    base_url = str(request.base_url).rstrip("/")
    return OSLCService(base_url=base_url)

@router.get("/rootservices")
async def get_rootservices(
    request: Request,
    accept: str = Header("application/rdf+xml"),
    oslc_service: OSLCService = Depends(get_oslc_service)
):
    """
    OSLC Entry Point (Root Services).
    Auto-discoverable by tools like IBM DOORS Next or Cameo.
    """
    logger.info(f"OSLC Discovery: RootServices [Accept: {accept}]")
    graph = oslc_service.generate_rootservices()
    result = oslc_service.serialize_response(graph, accept)
    return Response(content=result["content"], media_type=result["media_type"])

@router.get("/catalog")
async def get_service_provider_catalog(
    request: Request,
    accept: str = Header("application/rdf+xml"),
    oslc_service: OSLCService = Depends(get_oslc_service)
):
    """
    OSLC Service Provider Catalog.
    Lists available projects/providers.
    """
    logger.info(f"OSLC Discovery: Catalog [Accept: {accept}]")
    graph = oslc_service.generate_service_provider_catalog()
    result = oslc_service.serialize_response(graph, accept)
    return Response(content=result["content"], media_type=result["media_type"])

@router.get("/sp/{project_id}")
async def get_service_provider(
    project_id: str,
    request: Request,
    accept: str = Header("application/rdf+xml"),
    oslc_service: OSLCService = Depends(get_oslc_service)
):
    """
    OSLC Service Provider Details.
    Lists capabilities (Selection, Creation, Query) for a specific project.
    """
    logger.info(f"OSLC Discovery: ServiceProvider {project_id} [Accept: {accept}]")
    graph = oslc_service.generate_service_provider(project_id)
    result = oslc_service.serialize_response(graph, accept)
    return Response(content=result["content"], media_type=result["media_type"])
