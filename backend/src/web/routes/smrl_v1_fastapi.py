"""
ISO SMRL v1 REST API Routes (FastAPI)
=====================================
ISO 10303-4443 compliant SMRL (Systems Modeling Resource Library) API

Generic CRUD operations for any resource type with full SMRL compliance.
"""

from typing import Any, Dict, List, Optional
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Body
from pydantic import BaseModel, Field
from loguru import logger

from src.web.services import get_neo4j_service
from src.web.dependencies import get_api_key
from src.web.utils.responses import Neo4jJSONResponse
from src.web.services.smrl_adapter import SMRLAdapter, neo4j_list_to_smrl, neo4j_to_smrl
from src.web.utils.runtime_config import get_public_base_url

# Optional import for OSLC TRS (requires rdflib)
try:
    from src.web.services.oslc_trs_service import OSLCTRSService
    HAS_OSLC_TRS = True
except ImportError:
    OSLCTRSService = None
    HAS_OSLC_TRS = False

router = APIRouter()


def _resolve_smrl_label(resource_type: str) -> str:
    """Map an SMRL resource type to a Neo4j label, raising 400 for unknown types."""
    reverse_mapping = {v: k for k, v in SMRLAdapter.SMRL_TYPE_MAPPING.items()}
    node_label = reverse_mapping.get(resource_type)
    if not node_label:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown SMRL resource type: {resource_type}. "
                   f"Valid types: {', '.join(sorted(reverse_mapping.keys()))}",
        )
    return node_label

# Import sub-routers to include under /api/v1 for test compatibility
try:
    from src.web.routes.hierarchy_fastapi import router as hierarchy_router
    from src.web.routes.plm_fastapi import router as plm_router
    from src.web.routes.simulation_fastapi import router as simulation_router
    from src.web.routes.export_fastapi import router as export_router
    from src.web.routes.version_fastapi import router as version_router

    # Include sub-routers (they have their own prefixes like /simulation, /export, etc.)
    router.include_router(hierarchy_router, tags=["SMRL v1 - Hierarchy"])
    router.include_router(plm_router, tags=["SMRL v1 - PLM"])
    router.include_router(simulation_router, tags=["SMRL v1 - Simulation"])
    router.include_router(export_router, tags=["SMRL v1 - Export"])
    router.include_router(version_router, tags=["SMRL v1 - Version Control"])
    logger.info("✓ Included sub-routers in SMRL v1 for /api/v1 compatibility")
except Exception as e:
    logger.warning(f"Could not include all sub-routers in SMRL v1: {e}")


# ============================================================================
# PYDANTIC MODELS
# ============================================================================


class SMRLResource(BaseModel):
    """Generic SMRL resource model"""

    uid: Optional[str] = None
    href: Optional[str] = None
    smrl_type: Optional[str] = None
    name: Optional[str] = None
    created_by: Optional[str] = "api_user"
    modified_by: Optional[str] = "api_user"

    class Config:
        extra = "allow"  # Allow additional fields


class SMRLMatchRequest(BaseModel):
    """Request model for SMRL match endpoint"""

    resource_type: str = Field(..., description="SMRL resource type to query")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Filter criteria")
    limit: int = Field(
        default=100, ge=1, le=1000, description="Maximum results to return"
    )


class SMRLErrorResponse(BaseModel):
    """SMRL standard error response"""

    status: int
    message: str
    details: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""

    status: str
    version: str
    smrl_compliance: str
    api_version: str


# ============================================================================
# HEALTH CHECK
# ============================================================================


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """API health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "smrl_compliance": "ISO 10303-4443",
        "api_version": "v1",
    }


# ============================================================================
# COMPATIBILITY ROUTES (for test expectations)
# ============================================================================


# Forward /traceability to PLM router
@router.get("/traceability", response_class=Neo4jJSONResponse)
async def get_traceability_compat(
    source_type: Optional[str] = Query(None),
    target_type: Optional[str] = Query(None),
    relationship_type: Optional[str] = Query(None),
    depth: int = Query(2, ge=1, le=10),
):
    """Compatibility endpoint for /api/v1/traceability"""
    from src.web.routes.plm_fastapi import get_traceability

    return await get_traceability(source_type, target_type, relationship_type, depth)


# Forward /parameters to PLM router
@router.get("/parameters", response_class=Neo4jJSONResponse)
async def get_parameters_compat(
    class_name: Optional[str] = Query(None),
    property_name: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
):
    """Compatibility endpoint for /api/v1/parameters"""
    from src.web.routes.plm_fastapi import get_parameters

    return await get_parameters(class_name=class_name, limit=limit)


# Forward /constraints to PLM router
@router.get("/constraints", response_class=Neo4jJSONResponse)
async def get_constraints_compat(
    owner_type: Optional[str] = Query(None),
    constraint_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
):
    """Compatibility endpoint for /api/v1/constraints"""
    from src.web.routes.plm_fastapi import get_constraints

    # PLM router expects element_id, not owner_type
    return await get_constraints(element_id=None, limit=limit)


# Forward /composition to PLM router
@router.get("/composition/{node_id}", response_class=Neo4jJSONResponse)
async def get_composition_compat(node_id: str, depth: int = Query(5, ge=1, le=10)):
    """Compatibility endpoint for /api/v1/composition"""
    from src.web.routes.plm_fastapi import get_composition

    return await get_composition(node_id, depth)


# Forward /impact to PLM router
@router.get("/impact/{node_id}", response_class=Neo4jJSONResponse)
async def get_impact_compat(
    node_id: str,
    depth: int = Query(3, ge=1, le=10),
    include_details: bool = Query(False),
):
    """Compatibility endpoint for /api/v1/impact"""
    from src.web.routes.plm_fastapi import get_impact_analysis

    return await get_impact_analysis(node_id, depth)


# Forward /versions to version router
@router.get("/versions/{node_id}", response_class=Neo4jJSONResponse)
async def get_versions_compat(node_id: str):
    """Compatibility endpoint for /api/v1/versions"""
    from src.web.routes.version_fastapi import get_node_versions

    return await get_node_versions(node_id)


# Forward /diff to version router
@router.post("/diff", response_class=Neo4jJSONResponse)
async def post_diff_compat(compare_request: dict = Body(...)):
    """Compatibility endpoint for /api/v1/diff"""
    from src.web.routes.version_fastapi import compare_versions, CompareRequest

    req = CompareRequest(**compare_request)
    return await compare_versions(req)


# Forward /history to version router
@router.get("/history/{node_id}", response_class=Neo4jJSONResponse)
async def get_history_compat(node_id: str):
    """Compatibility endpoint for /api/v1/history"""
    from src.web.routes.version_fastapi import get_node_history

    return await get_node_history(node_id)


# Forward /checkpoint to version router
@router.post("/checkpoint", response_class=Neo4jJSONResponse, status_code=201)
async def create_checkpoint_compat(checkpoint_request: dict = Body(...)):
    """Compatibility endpoint for /api/v1/checkpoint"""
    from src.web.routes.version_fastapi import create_checkpoint, CheckpointRequest

    req = CheckpointRequest(**checkpoint_request)
    return await create_checkpoint(req)


# ============================================================================
# GENERIC SMRL RESOURCE ENDPOINTS
# ============================================================================


@router.get("/{resource_type}", response_class=Neo4jJSONResponse)
async def get_resources(
    resource_type: str = Path(..., description="SMRL resource type"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    skip: int = Query(0, ge=0, description="Number of results to skip"),
    api_key: str = Depends(get_api_key),
):
    """
    Get all resources of a specific type

    Args:
        resource_type: SMRL resource type (e.g., AccessibleModelTypeConstituent)
        limit: Maximum number of results to return
        skip: Number of results to skip (pagination)

    Returns:
        Array of SMRL-formatted resources
    """
    try:
        neo4j = get_neo4j_service()

        # Map SMRL type to Neo4j label (validated)
        node_label = _resolve_smrl_label(resource_type)

        query = f"""
        MATCH (n:{node_label})
        RETURN n
        ORDER BY n.name
        SKIP $skip
        LIMIT $limit
        """

        result = neo4j.execute_query(query, {"skip": skip, "limit": limit})

        # Convert to SMRL format
        nodes = [(dict(r["n"]), list(r["n"].labels)) for r in result]
        response = neo4j_list_to_smrl(nodes)

        return response

    except Exception as e:
        logger.error(f"Error fetching resources {resource_type}: {e}")
        error = SMRLAdapter.create_smrl_error_response(
            500, "Internal server error", str(e)
        )
        raise HTTPException(status_code=500, detail=error)


@router.get("/{resource_type}/{uid}", response_class=Neo4jJSONResponse)
async def get_resource(
    resource_type: str = Path(..., description="SMRL resource type"),
    uid: str = Path(..., description="Resource unique identifier"),
    api_key: str = Depends(get_api_key),
):
    """
    Get a specific resource by UID

    Args:
        resource_type: SMRL resource type
        uid: Unique identifier (uid, id, or xmi_id)

    Returns:
        SMRL-formatted resource
    """
    try:
        neo4j = get_neo4j_service()

        # Map SMRL type to Neo4j label (validated)
        node_label = _resolve_smrl_label(resource_type)

        query = f"""
        MATCH (n:{node_label})
        WHERE n.uid = $uid OR n.id = $uid OR n.xmi_id = $uid
        RETURN n
        LIMIT 1
        """

        result = neo4j.execute_query(query, {"uid": uid})

        if not result:
            error = SMRLAdapter.create_smrl_error_response(
                404, f"Resource not found: {resource_type}/{uid}"
            )
            raise HTTPException(status_code=404, detail=error)

        # Convert to SMRL format
        node_data = dict(result[0]["n"])
        node_labels = list(result[0]["n"].labels)
        resource = neo4j_to_smrl(node_data, node_labels)

        return resource

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching resource {resource_type}/{uid}: {e}")
        error = SMRLAdapter.create_smrl_error_response(
            500, "Internal server error", str(e)
        )
        raise HTTPException(status_code=500, detail=error)


@router.post("/{resource_type}", response_class=Neo4jJSONResponse, status_code=201)
async def create_resource(
    resource_type: str = Path(..., description="SMRL resource type"),
    data: Dict[str, Any] = Body(..., description="Resource data"),
    api_key: str = Depends(get_api_key),
):
    """
    Create a new resource

    Args:
        resource_type: SMRL resource type
        data: Resource properties and data

    Returns:
        Created resource in SMRL format
    """
    try:
        neo4j = get_neo4j_service()

        # Map SMRL type to Neo4j label (validated)
        node_label = _resolve_smrl_label(resource_type)

        # Generate UID if not provided
        uid = data.get("uid", f"{resource_type}-{uuid4()}")
        href = f"/api/v1/{resource_type}/{uid}"

        # Build node properties
        properties = {
            "uid": uid,
            "href": href,
            "smrl_type": resource_type,
            "name": data.get("name", ""),
            "created_by": data.get("created_by", "api_user"),
            "modified_by": data.get("modified_by", "api_user"),
        }

        # Add custom properties
        for key, value in data.items():
            if key not in ["uid", "href", "smrl_type"] and not key.startswith("_"):
                properties[key] = value

        # Create node with datetime()
        query = f"""
        CREATE (n:{node_label})
        SET n = $properties
        SET n.created_on = datetime()
        SET n.last_modified = datetime()
        RETURN n
        """

        result = neo4j.execute_query(query, {"properties": properties})

        # Convert to SMRL format
        node_data = dict(result[0]["n"])
        node_labels = list(result[0]["n"].labels)
        resource = neo4j_to_smrl(node_data, node_labels)

        # OSLC TRS Notification
        if HAS_OSLC_TRS:
            try:
                trs = OSLCTRSService()
                base_url = get_public_base_url()
                res_uri = f"{base_url}{href}"
                await trs.publish_event(res_uri, "create")
            except Exception as e:
                logger.warning(f"Failed to publish TRS event: {e}")

        return resource

    except Exception as e:
        logger.error(f"Error creating resource {resource_type}: {e}")
        error = SMRLAdapter.create_smrl_error_response(
            500, "Internal server error", str(e)
        )
        raise HTTPException(status_code=500, detail=error)


@router.put("/{resource_type}/{uid}", response_class=Neo4jJSONResponse)
async def replace_resource(
    resource_type: str = Path(..., description="SMRL resource type"),
    uid: str = Path(..., description="Resource unique identifier"),
    data: Dict[str, Any] = Body(..., description="Complete resource data"),
    api_key: str = Depends(get_api_key),
):
    """
    Replace an existing resource (full update)

    Args:
        resource_type: SMRL resource type
        uid: Unique identifier
        data: Complete resource data

    Returns:
        Updated resource in SMRL format
    """
    try:
        neo4j = get_neo4j_service()

        # Map SMRL type to Neo4j label (validated)
        node_label = _resolve_smrl_label(resource_type)

        # Check if resource exists
        check_query = f"""
        MATCH (n:{node_label})
        WHERE n.uid = $uid
        RETURN count(n) as exists
        """
        result = neo4j.execute_query(check_query, {"uid": uid})

        if result[0]["exists"] == 0:
            error = SMRLAdapter.create_smrl_error_response(
                404, f"Resource not found: {resource_type}/{uid}"
            )
            raise HTTPException(status_code=404, detail=error)

        # Replace all properties (except uid)
        properties = {"modified_by": data.get("modified_by", "api_user")}
        for key, value in data.items():
            if key != "uid" and not key.startswith("_"):
                properties[key] = value

        # Update node
        query = f"""
        MATCH (n:{node_label})
        WHERE n.uid = $uid
        SET n = $properties
        SET n.uid = $uid
        SET n.last_modified = datetime()
        RETURN n
        """

        result = neo4j.execute_query(query, {"uid": uid, "properties": properties})

        # Convert to SMRL format
        node_data = dict(result[0]["n"])
        node_labels = list(result[0]["n"].labels)
        resource = neo4j_to_smrl(node_data, node_labels)

        # OSLC TRS Notification
        if HAS_OSLC_TRS:
            try:
                trs = OSLCTRSService()
                base_url = get_public_base_url()
                res_uri = f"{base_url}/api/v1/{resource_type}/{uid}"
                await trs.publish_event(res_uri, "update")
            except Exception as e:
                logger.warning(f"Failed to publish TRS event: {e}")

        return resource

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error replacing resource {resource_type}/{uid}: {e}")
        error = SMRLAdapter.create_smrl_error_response(
            500, "Internal server error", str(e)
        )
        raise HTTPException(status_code=500, detail=error)


@router.patch("/{resource_type}/{uid}", response_class=Neo4jJSONResponse)
async def update_resource(
    resource_type: str = Path(..., description="SMRL resource type"),
    uid: str = Path(..., description="Resource unique identifier"),
    data: Dict[str, Any] = Body(..., description="Partial resource data"),
    api_key: str = Depends(get_api_key),
):
    """
    Update specific fields of a resource (partial update)

    Args:
        resource_type: SMRL resource type
        uid: Unique identifier
        data: Fields to update

    Returns:
        Updated resource in SMRL format
    """
    try:
        neo4j = get_neo4j_service()

        # Map SMRL type to Neo4j label (validated)
        node_label = _resolve_smrl_label(resource_type)

        # Build SET clause for partial update
        set_clauses = ["n.last_modified = datetime()"]
        params = {"uid": uid}

        for key, value in data.items():
            if key != "uid" and not key.startswith("_"):
                param_key = f"param_{key.replace('.', '_')}"
                set_clauses.append(f"n.`{key}` = ${param_key}")
                params[param_key] = value

        query = f"""
        MATCH (n:{node_label})
        WHERE n.uid = $uid
        SET {', '.join(set_clauses)}
        RETURN n
        """

        result = neo4j.execute_query(query, params)

        if not result:
            error = SMRLAdapter.create_smrl_error_response(
                404, f"Resource not found: {resource_type}/{uid}"
            )
            raise HTTPException(status_code=404, detail=error)

        # Convert to SMRL format
        node_data = dict(result[0]["n"])
        node_labels = list(result[0]["n"].labels)
        resource = neo4j_to_smrl(node_data, node_labels)

        # OSLC TRS Notification
        if HAS_OSLC_TRS:
            try:
                trs = OSLCTRSService()
                base_url = get_public_base_url()
                res_uri = f"{base_url}/api/v1/{resource_type}/{uid}"
                await trs.publish_event(res_uri, "update")
            except Exception as e:
                logger.warning(f"Failed to publish TRS event: {e}")

        return resource

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating resource {resource_type}/{uid}: {e}")
        error = SMRLAdapter.create_smrl_error_response(
            500, "Internal server error", str(e)
        )
        raise HTTPException(status_code=500, detail=error)


@router.delete("/{resource_type}/{uid}")
async def delete_resource(
    resource_type: str = Path(..., description="SMRL resource type"),
    uid: str = Path(..., description="Resource unique identifier"),
    api_key: str = Depends(get_api_key),
):
    """
    Delete a resource

    Args:
        resource_type: SMRL resource type
        uid: Unique identifier

    Returns:
        Confirmation message
    """
    try:
        neo4j = get_neo4j_service()

        # Map SMRL type to Neo4j label (validated)
        node_label = _resolve_smrl_label(resource_type)

        query = f"""
        MATCH (n:{node_label})
        WHERE n.uid = $uid
        DETACH DELETE n
        RETURN count(n) as deleted
        """

        result = neo4j.execute_query(query, {"uid": uid})

        if result[0]["deleted"] == 0:
            error = SMRLAdapter.create_smrl_error_response(
                404, f"Resource not found: {resource_type}/{uid}"
            )
            raise HTTPException(status_code=404, detail=error)

        return {"message": f"Resource deleted: {resource_type}/{uid}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting resource {resource_type}/{uid}: {e}")
        error = SMRLAdapter.create_smrl_error_response(
            500, "Internal server error", str(e)
        )
        raise HTTPException(status_code=500, detail=error)


# ============================================================================
# SMRL MATCH ENDPOINT (Advanced Query)
# ============================================================================


@router.post("/match", response_class=Neo4jJSONResponse)
async def smrl_match(
    request: SMRLMatchRequest = Body(..., description="Match query parameters"),
    api_key: str = Depends(get_api_key),
):
    """
    Advanced query endpoint matching SMRL standard

    Args:
        request: Match request with resource_type, filters, and limit

    Returns:
        Array of matching resources in SMRL format

    Example:
        {
            "resource_type": "AccessibleModelTypeConstituent",
            "filters": {"name": "Vehicle", "visibility": "public"},
            "limit": 100
        }
    """
    try:
        neo4j = get_neo4j_service()

        # Map SMRL type to Neo4j label (validated)
        node_label = _resolve_smrl_label(request.resource_type)

        # Build WHERE clause
        where_clauses = []
        params = {"limit": request.limit}

        for key, value in request.filters.items():
            param_key = f"filter_{key.replace('.', '_')}"
            where_clauses.append(f"n.`{key}` = ${param_key}")
            params[param_key] = value

        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

        query = f"""
        MATCH (n:{node_label})
        WHERE {where_clause}
        RETURN n
        LIMIT $limit
        """

        result = neo4j.execute_query(query, params)

        # Convert to SMRL format
        nodes = [(dict(r["n"]), list(r["n"].labels)) for r in result]
        response = neo4j_list_to_smrl(nodes)

        return response

    except Exception as e:
        logger.error(f"Error in SMRL match: {e}")
        error = SMRLAdapter.create_smrl_error_response(
            500, "Internal server error", str(e)
        )
        raise HTTPException(status_code=500, detail=error)
