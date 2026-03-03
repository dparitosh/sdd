"""
OSLC Client Routes
Endpoints to act as an OSLC Consumer.
Allows this MBSE Graph Server to connect to, discover, and query external OSLC Providers.
"""

import ipaddress
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from typing import Optional, Dict, List
from src.web.services.oslc_client import OSLCClient
from src.web.dependencies import get_api_key

router = APIRouter(prefix="/oslc/client", tags=["OSLC Client"], dependencies=[Depends(get_api_key)])

# ---------------------------------------------------------------------------
# SSRF Protection
# ---------------------------------------------------------------------------

def _validate_oslc_url(url: str) -> str:
    """Validate that a user-supplied URL is safe for server-side requests.

    Blocks private/loopback/link-local addresses and non-HTTP schemes.
    Raises HTTPException 400 on invalid input.
    """
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported URL scheme '{parsed.scheme}'. Only http/https allowed.",
        )

    hostname = parsed.hostname or ""
    if not hostname:
        raise HTTPException(status_code=400, detail="URL must include a hostname.")

    # Block obvious private/loopback/link-local ranges
    try:
        addr = ipaddress.ip_address(hostname)
        if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
            raise HTTPException(
                status_code=400,
                detail="OSLC provider URL must not point to a private/loopback address.",
            )
    except ValueError:
        # hostname is a DNS name — block localhost explicitly
        if hostname.lower() in ("localhost", "localhost.localdomain"):
            raise HTTPException(
                status_code=400,
                detail="OSLC provider URL must not point to localhost.",
            )

    return url

class ConnectRequest(BaseModel):
    url: Optional[str] = None
    root_url: Optional[str] = None  # alias from frontend
    auth_type: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None

    @property
    def effective_url(self) -> str:
        return self.root_url or self.url or ""

class QueryRequest(BaseModel):
    query_capability_url: Optional[str] = None
    provider_url: Optional[str] = None  # alias from frontend
    resource_type: Optional[str] = None
    query: Optional[str] = None  # alias for oslc_where
    oslc_where: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None

    @property
    def effective_url(self) -> str:
        return self.query_capability_url or self.provider_url or ""

    @property
    def effective_where(self) -> str:
        return self.oslc_where or self.query or ""

@router.post("/connect")
async def connect_and_discover(request: ConnectRequest):
    """
    Connect to a remote OSLC Root Services and perform discovery.
    Returns the hierarchy of Catalogs, Service Providers, and Services found.
    """
    auth = None
    if request.username and request.password:
        auth = (request.username, request.password)
    
    client = OSLCClient(base_url=_validate_oslc_url(request.effective_url), auth=auth)
    
    try:
        discovery_result = await client.discover()
        
        # Serialize discovery details
        # (In a real app, we might persist this connection state to a session)
        return {
            "status": "connected",
            "endpoint": request.effective_url,
            "catalogs": discovery_result["catalogs"],
            "service_providers": client.service_providers,
            "services": client.services
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OSLC Discovery failed: {str(e)}")

@router.post("/query")
async def execute_query(request: QueryRequest):
    """
    Execute an OSLC Simple Query against a discovered Query Capability.
    """
    auth = None
    if request.username and request.password:
        auth = (request.username, request.password)
    
    # We instantiate a new client just for this request 
    # (assuming stateless for now, though expensive for discovery if we needed it again)
    # Ideally, we pass the Discovery result back or store it. 
    # But for a direct query, we just need the URL.
    
    # We use query_capability_url as base just to init the client, 
    # though client uses it for discovery usually.
    client = OSLCClient(base_url=_validate_oslc_url(request.effective_url), auth=auth)
    
    try:
        # We manually construct the query call since we're skipping full discovery here
        results = await client.query_resource(
            query_base=_validate_oslc_url(request.effective_url),
            oslc_where=request.effective_where
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OSLC Query failed: {str(e)}")
