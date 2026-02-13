"""
OSLC TRS Routes
Endpoints for Tracked Resource Set (Smart Linking).
"""

from fastapi import APIRouter, Depends, Header, Response, Request
from src.web.services.oslc_trs_service import OSLCTRSService

router = APIRouter(prefix="/oslc/trs", tags=["OSLC TRS"])


def get_trs_service() -> OSLCTRSService:
    """Lazy initialization to avoid crash if Neo4j is not yet connected at import time."""
    return OSLCTRSService()


@router.get("")
async def get_tracked_resource_set(
    accept: str = Header("text/turtle", alias="Accept"),
    trs_service: OSLCTRSService = Depends(get_trs_service),
):
    """
    Get the Tracked Resource Set (TRS) description.
    """
    graph = await trs_service.get_tracked_resource_set()
    
    if "application/json" in accept or "application/ld+json" in accept:
        content = graph.serialize(format="json-ld")
        media_type = "application/ld+json"
    else:
        content = graph.serialize(format="turtle")
        media_type = "text/turtle"
        
    return Response(content=content, media_type=media_type)

@router.get("/base")
async def get_base(
    page: int = 1,
    accept: str = Header("text/turtle", alias="Accept"),
    trs_service: OSLCTRSService = Depends(get_trs_service),
):
    """
    Get the Base (Initial Load) of the TRS.
    Paged collection of all resources.
    """
    graph = await trs_service.get_base_page(page)
    
    if "application/json" in accept or "application/ld+json" in accept:
        content = graph.serialize(format="json-ld")
        media_type = "application/ld+json"
    else:
        content = graph.serialize(format="turtle")
        media_type = "text/turtle"
        
    return Response(content=content, media_type=media_type)

@router.get("/changelog")
async def get_changelog(
    accept: str = Header("text/turtle", alias="Accept"),
    trs_service: OSLCTRSService = Depends(get_trs_service),
):
    """
    Get the Change Log (Recent Events).
    """
    graph = await trs_service.get_changelog()
    
    if "application/json" in accept or "application/ld+json" in accept:
        content = graph.serialize(format="json-ld")
        media_type = "application/ld+json"
    else:
        content = graph.serialize(format="turtle")
        media_type = "text/turtle"
        
    return Response(content=content, media_type=media_type)
