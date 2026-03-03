"""
AP239 REST API Routes (FastAPI) - Product Life Cycle Support
============================================================
Endpoints for Requirements, Analysis, Approvals, and Documents

ISO 10303 AP239 provides PLCS (Product Life Cycle Support) capabilities
including requirements management, design approvals, and engineering analysis.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, Path
from pydantic import BaseModel, Field
from loguru import logger

from src.web.services import get_neo4j_service
from src.web.dependencies import get_api_key
from src.web.utils.responses import Neo4jJSONResponse

router = APIRouter()


# Pydantic models
class Requirement(BaseModel):
    uid: Optional[str] = None
    id: Optional[str] = None
    name: Optional[str] = "Unknown"
    description: Optional[str] = None
    type: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[str] = None
    versions: List[str] = []
    satisfied_by_parts: List[str] = []


class RequirementsResponse(BaseModel):
    count: int
    requirements: List[Requirement]


class RequirementVersion(BaseModel):
    version: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[str] = None


class AnalysisInfo(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None


class ApprovalInfo(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    date: Optional[str] = None


class DocumentInfo(BaseModel):
    name: Optional[str] = None
    id: Optional[str] = None
    version: Optional[str] = None


class PartInfo(BaseModel):
    id: str
    name: Optional[str] = None


class UnitInfo(BaseModel):
    name: Optional[str] = None
    symbol: Optional[str] = None


class RequirementDetail(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    type: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[str] = None
    ap_level: Optional[int] = None
    ap_schema: Optional[str] = None
    versions: List[RequirementVersion] = []
    analyses: List[AnalysisInfo] = []
    approvals: List[ApprovalInfo] = []
    documents: List[DocumentInfo] = []
    satisfied_by_parts: List[PartInfo] = []
    units: List[UnitInfo] = []


class TraceabilityLink(BaseModel):
    part_id: Optional[str] = None
    part_name: Optional[str] = None
    materials: List[str] = []
    ontologies: List[str] = []
    ontology_id: Optional[str] = None
    ontology_name: Optional[str] = None
    ontology_type: Optional[str] = None
    sa_id: Optional[str] = None
    sa_name: Optional[str] = None


class TraceabilityResponse(BaseModel):
    requirement: str
    traceability: List[TraceabilityLink]


class Analysis(BaseModel):
    name: str
    type: Optional[str] = None
    method: Optional[str] = None
    status: Optional[str] = None
    models: List[str] = []
    verifies_requirements: List[str] = []
    geometry_models: List[str] = []


class AnalysesResponse(BaseModel):
    count: int
    analyses: List[Analysis]


class Approval(BaseModel):
    name: str
    status: Optional[str] = None
    approved_by: Optional[str] = None
    approval_date: Optional[str] = None
    approves_requirements: List[str] = []
    approved_part_versions: List[str] = []


class ApprovalsResponse(BaseModel):
    count: int
    approvals: List[Approval]


class Document(BaseModel):
    name: str
    document_id: Optional[str] = None
    version: Optional[str] = None
    type: Optional[str] = None
    documents_requirements: List[str] = []


class DocumentsResponse(BaseModel):
    count: int
    documents: List[Document]


class StatusBreakdown(BaseModel):
    total: int
    by_status: Dict[str, int] = {}


class StatisticsResponse(BaseModel):
    ap_level: str
    ap_schema: str
    statistics: Dict[str, StatusBreakdown]


# ============================================================================
# REQUIREMENTS ENDPOINTS
# ============================================================================


@router.get(
    "/requirements",
    response_model=RequirementsResponse,
    response_class=Neo4jJSONResponse,
)
async def get_requirements(
    type: Optional[str] = Query(None, description="Filter by requirement type"),
    priority: Optional[str] = Query(
        None, description="Filter by priority (High, Medium, Low)"
    ),
    status: Optional[str] = Query(
        None, description="Filter by status (Draft, Approved, Obsolete)"
    ),
    search: Optional[str] = Query(None, description="Search in name and description"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    api_key: str = Depends(get_api_key),
):
    """
    Get all requirements with optional filtering and pagination

    Args:
        type: Filter by requirement type (Performance, Functional, etc.)
        priority: Filter by priority (High, Medium, Low)
        status: Filter by status (Draft, Approved, Obsolete)
        search: Text search in name and description
        limit: Maximum number of results (default: 100, max: 500)
        offset: Number of results to skip for pagination

    Returns:
        Array of requirement objects with pagination
    """
    try:
        neo4j = get_neo4j_service()

        # Build dynamic query
        filters = []
        params = {}

        if type:
            filters.append("req.type = $type")
            params["type"] = type

        if priority:
            filters.append("req.priority = $priority")
            params["priority"] = priority

        if status:
            filters.append("req.status = $status")
            params["status"] = status

        if search:
            filters.append("(req.name =~ $search OR req.description =~ $search)")
            params["search"] = f"(?i).*{search}.*"

        where_clause = " AND ".join(filters) if filters else "1=1"

        # Add pagination parameters
        params["limit"] = limit
        params["offset"] = offset

        query = f"""
        MATCH (req:Requirement)
        WHERE req.ap_level = 'AP239' AND {where_clause}
        OPTIONAL MATCH (req)-[:HAS_VERSION]->(v:RequirementVersion)
        OPTIONAL MATCH (req)-[:SATISFIED_BY_PART]->(part:Part)
        RETURN req.uid AS uid,
               req.id AS id,
               req.name AS name,
               req.description AS description,
               req.type AS type,
               req.priority AS priority,
               req.status AS status,
               req.created_at AS created_at,
               COLLECT(DISTINCT v.version) AS versions,
               COLLECT(DISTINCT part.name) AS satisfied_by_parts
        ORDER BY req.priority DESC, req.created_at DESC
        SKIP $offset
        LIMIT $limit
        """

        results = neo4j.execute_query(query, params)

        requirements = [
            {
                "uid": r.get("uid"),
                "id": r["id"],
                "name": r["name"] or "Unknown",
                "description": r["description"],
                "type": r["type"],
                "priority": r["priority"],
                "status": r["status"],
                "created_at": str(r["created_at"]) if r["created_at"] else None,
                "versions": [v for v in r["versions"] if v],
                "satisfied_by_parts": [p for p in r["satisfied_by_parts"] if p],
            }
            for r in results
        ]

        return {"count": len(requirements), "requirements": requirements}

    except Exception as e:
        logger.error(f"Error fetching requirements: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/requirements/{req_id}",
    response_model=RequirementDetail,
    response_class=Neo4jJSONResponse,
)
async def get_requirement_detail(
    req_id: str = Path(..., description="Requirement ID"),
    api_key: str = Depends(get_api_key),
):
    """
    Get detailed information about a specific requirement

    Args:
        req_id: Unique requirement identifier

    Returns:
        Requirement with all relationships (versions, analyses, approvals, etc.)
    """
    try:
        neo4j = get_neo4j_service()

        query = """
        MATCH (req:Requirement {id: $req_id})
        OPTIONAL MATCH (req)-[:HAS_VERSION]->(v:RequirementVersion)
        OPTIONAL MATCH (req)-[:VERIFIES]->(ana:Analysis)
        OPTIONAL MATCH (req)-[:APPROVES]->(appr:Approval)
        OPTIONAL MATCH (doc:Document)-[:DOCUMENTS]->(req)
        OPTIONAL MATCH (req)-[:SATISFIED_BY_PART]->(part:Part)
        OPTIONAL MATCH (req)-[:REQUIREMENT_VALUE_TYPE]->(unit:ExternalUnit)
        RETURN req,
               COLLECT(DISTINCT {version: v.version, name: v.name, status: v.status}) AS versions,
               COLLECT(DISTINCT {name: ana.name, type: ana.type, status: ana.status}) AS analyses,
               COLLECT(DISTINCT {name: appr.name, status: appr.status, date: toString(appr.approval_date)}) AS approvals,
               COLLECT(DISTINCT {name: doc.name, id: doc.document_id, version: doc.version}) AS documents,
               COLLECT(DISTINCT {id: part.id, name: part.name}) AS parts,
               COLLECT(DISTINCT {name: unit.name, symbol: unit.symbol}) AS units
        """

        results = neo4j.execute_query(query, {"req_id": req_id})

        if not results:
            raise HTTPException(status_code=404, detail="Requirement not found")

        r = results[0]
        req = r["req"]

        requirement = {
            "id": req.get("id"),
            "name": req.get("name", "Unknown"),
            "description": req.get("description"),
            "type": req.get("type"),
            "priority": req.get("priority"),
            "status": req.get("status"),
            "created_at": str(req.get("created_at")) if req.get("created_at") else None,
            "ap_level": req.get("ap_level"),
            "ap_schema": req.get("ap_schema"),
            "versions": [
                {
                    "version": v.get("version"),
                    "description": v.get("description"),
                    "status": v.get("status"),
                    "created_at": (
                        str(v.get("created_at")) if v.get("created_at") else None
                    ),
                }
                for v in r["versions"]
                if v.get("version")
            ],
            "analyses": [a for a in r["analyses"] if a.get("name")],
            "approvals": [a for a in r["approvals"] if a.get("name")],
            "documents": [d for d in r["documents"] if d.get("name")],
            "satisfied_by_parts": [p for p in r["parts"] if p.get("id")],
            "units": [u for u in r["units"] if u.get("name")],
        }

        return requirement

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching requirement {req_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/requirements/{req_id}/traceability",
    response_model=TraceabilityResponse,
    response_class=Neo4jJSONResponse,
)
async def get_requirement_traceability(
    req_id: str = Path(..., description="Requirement ID"),
    api_key: str = Depends(get_api_key),
):
    """
    Get full traceability chain for a requirement (AP239 → AP242 → AP243)

    Args:
        req_id: Unique requirement identifier

    Returns:
        Tree structure showing how requirement flows through parts to ontologies
    """
    try:
        neo4j = get_neo4j_service()

        query = """
        MATCH (req:Requirement {id: $req_id})

        // Part traceability (AP242)
        OPTIONAL MATCH (req)-[:SATISFIED_BY_PART]->(part:Part)
        OPTIONAL MATCH (part)-[:USES_MATERIAL]->(mat:Material)
        OPTIONAL MATCH (mat)-[:MATERIAL_CLASSIFIED_AS]->(owl:ExternalOwlClass)

        // Direct ontology links (AP243 via OSLC)
        OPTIONAL MATCH (req)-[:MAPS_TO_OSLC|TYPED_BY]->(direct_owl)
        WHERE 'OntologyClass' IN labels(direct_owl) OR 'ExternalOwlClass' IN labels(direct_owl) OR 'Class' IN labels(direct_owl)

        // Simulation artifact links (SDD/prototype)
        OPTIONAL MATCH (req)-[:VERIFIED_BY|SATISFIED_BY|LINKED_TO_REQUIREMENT]-(sa:SimulationArtifact)

        WITH req, part, direct_owl, sa,
             COLLECT(DISTINCT mat.name) AS materials,
             COLLECT(DISTINCT owl.name) AS ontologies
        RETURN req.name AS requirement,
               COLLECT(DISTINCT {
                   part_id: part.id,
                   part_name: part.name,
                   materials: materials,
                   ontologies: ontologies,
                   ontology_id: COALESCE(direct_owl.id, direct_owl.uri),
                   ontology_name: COALESCE(direct_owl.name, direct_owl.label),
                   ontology_type: labels(direct_owl)[0],
                   sa_id: sa.id,
                   sa_name: sa.name
               }) AS traceability_chain
        """

        results = neo4j.execute_query(query, {"req_id": req_id})

        if not results:
            raise HTTPException(status_code=404, detail="Requirement not found")

        raw_chain = results[0]["traceability_chain"]
        filtered_chain = [
            link for link in raw_chain
            if link.get("part_id") or link.get("ontology_id") or link.get("sa_id")
        ]
        return {
            "requirement": results[0]["requirement"],
            "traceability": filtered_chain,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching traceability for {req_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class BulkTraceabilityRequest(BaseModel):
    requirement_ids: List[str] = Field(..., min_items=1, max_items=100)


class BulkTraceabilityItem(BaseModel):
    requirement_id: str
    requirement_name: Optional[str] = None
    traceability: List[TraceabilityLink]


class BulkTraceabilityResponse(BaseModel):
    count: int
    results: List[BulkTraceabilityItem]


@router.post(
    "/requirements/traceability/bulk",
    response_model=BulkTraceabilityResponse,
    response_class=Neo4jJSONResponse,
)
async def get_bulk_requirement_traceability(
    request: BulkTraceabilityRequest, api_key: str = Depends(get_api_key)
):
    """
    Get traceability chains for multiple requirements in a single query (fixes N+1 problem)

    Args:
        request: Object with requirement_ids array (max 100 IDs)
        api_key: API key for authentication

    Returns:
        Array of traceability results for each requirement

    Performance:
        This endpoint resolves the N+1 query problem by fetching all traceability
        data in a single database query instead of one query per requirement.
    """
    try:
        neo4j = get_neo4j_service()

        # Bulk query fetches all requirements and their traceability in one go
        query = """
        UNWIND $req_ids AS req_id
        MATCH (req:Requirement {id: req_id})
        
        // Get part traceability
        OPTIONAL MATCH (req)-[:SATISFIED_BY_PART]->(part:Part)
        OPTIONAL MATCH (part)-[:USES_MATERIAL]->(mat:Material)
        OPTIONAL MATCH (mat)-[:MATERIAL_CLASSIFIED_AS]->(owl:ExternalOwlClass)
        
        // Get direct ontology traceability
        OPTIONAL MATCH (req)-[:MAPS_TO_OSLC|TYPED_BY]->(direct_owl)
        WHERE 'OntologyClass' IN labels(direct_owl) OR 'ExternalOwlClass' IN labels(direct_owl) OR 'Class' IN labels(direct_owl)
        
        // Get simulation artifact traceability
        OPTIONAL MATCH (req)-[:VERIFIED_BY|SATISFIED_BY|LINKED_TO_REQUIREMENT]-(sa:SimulationArtifact)
        
        WITH req, part, direct_owl, sa,
             COLLECT(DISTINCT mat.name) AS materials,
             COLLECT(DISTINCT owl.name) AS ontologies
             
        RETURN req.id AS requirement_id,
               req.name AS requirement_name,
               COLLECT(DISTINCT {
                   part_id: part.id,
                   part_name: part.name,
                   materials: materials,
                   ontologies: ontologies,
                   ontology_id: COALESCE(direct_owl.id, direct_owl.uri),
                   ontology_name: COALESCE(direct_owl.name, direct_owl.label),
                   ontology_type: labels(direct_owl)[0],
                   sa_id: sa.id,
                   sa_name: sa.name
               }) AS traceability_chain
        """

        results = neo4j.execute_query(query, {"req_ids": request.requirement_ids})

        # Format response
        bulk_results = [
            {
                "requirement_id": r["requirement_id"],
                "requirement_name": r["requirement_name"],
                "traceability": [
                    link
                    for link in r["traceability_chain"]
                    if link.get("part_id") or link.get("ontology_id") or link.get("sa_id")  # Filter out empty links
                ],
            }
            for r in results
        ]

        return {"count": len(bulk_results), "results": bulk_results}

    except Exception as e:
        logger.error(f"Error fetching bulk traceability: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ANALYSIS ENDPOINTS
# ============================================================================


@router.get(
    "/analyses", response_model=AnalysesResponse, response_class=Neo4jJSONResponse
)
async def get_analyses(
    type: Optional[str] = Query(None, description="Filter by analysis type"),
    status: Optional[str] = Query(
        None, description="Filter by status (Planned, Running, Completed)"
    ),
    api_key: str = Depends(get_api_key),
):
    """
    Get all engineering analyses

    Args:
        type: Filter by analysis type (ThermalSimulation, StressAnalysis, etc.)
        status: Filter by status (Planned, Running, Completed)

    Returns:
        Array of analysis objects
    """
    try:
        neo4j = get_neo4j_service()

        filters = []
        params = {}

        if type:
            filters.append("ana.type = $type")
            params["type"] = type

        if status:
            filters.append("ana.status = $status")
            params["status"] = status

        where_clause = " AND ".join(filters) if filters else "1=1"

        query = f"""
        MATCH (ana:Analysis)
        WHERE ana.ap_level = 'AP239' AND {where_clause}
        OPTIONAL MATCH (ana)-[:USES_MODEL]->(model:AnalysisModel)
        OPTIONAL MATCH (req:Requirement)-[:VERIFIES]->(ana)
        OPTIONAL MATCH (ana)-[:ANALYZED_BY_MODEL]->(geo:GeometricModel)
        RETURN ana.name AS name,
               ana.type AS type,
               ana.method AS method,
               ana.status AS status,
               COLLECT(DISTINCT model.name) AS models,
               COLLECT(DISTINCT req.name) AS verifies_requirements,
               COLLECT(DISTINCT geo.name) AS geometry_models
        ORDER BY ana.status, ana.name
        """

        results = neo4j.execute_query(query, params)

        analyses = [
            {
                "name": r["name"],
                "type": r["type"],
                "method": r["method"],
                "status": r["status"],
                "models": [m for m in r["models"] if m],
                "verifies_requirements": [
                    req for req in r["verifies_requirements"] if req
                ],
                "geometry_models": [g for g in r["geometry_models"] if g],
            }
            for r in results
        ]

        return {"count": len(analyses), "analyses": analyses}

    except Exception as e:
        logger.error(f"Error fetching analyses: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# APPROVAL ENDPOINTS
# ============================================================================


@router.get(
    "/approvals", response_model=ApprovalsResponse, response_class=Neo4jJSONResponse
)
async def get_approvals(
    status: Optional[str] = Query(
        None, description="Filter by approval status (Pending, Approved, Rejected)"
    ),
    api_key: str = Depends(get_api_key),
):
    """
    Get all design approvals

    Args:
        status: Filter by approval status (Pending, Approved, Rejected)

    Returns:
        Array of approval objects
    """
    try:
        neo4j = get_neo4j_service()

        where_clause = "appr.status = $status" if status else "1=1"
        params = {"status": status} if status else {}

        query = f"""
        MATCH (appr:Approval)
        WHERE appr.ap_level = 'AP239' AND {where_clause}
        OPTIONAL MATCH (req:Requirement)-[:APPROVES]->(appr)
        OPTIONAL MATCH (appr)-[:APPROVED_FOR_VERSION]->(pv:PartVersion)
        RETURN appr.name AS name,
               appr.status AS status,
               appr.approved_by AS approved_by,
               appr.approval_date AS approval_date,
               COLLECT(DISTINCT req.name) AS approves_requirements,
               COLLECT(DISTINCT pv.name) AS approved_part_versions
        ORDER BY appr.approval_date DESC
        """

        results = neo4j.execute_query(query, params)

        approvals = [
            {
                "name": r["name"],
                "status": r["status"],
                "approved_by": r["approved_by"],
                "approval_date": (
                    str(r["approval_date"]) if r["approval_date"] else None
                ),
                "approves_requirements": [
                    req for req in r["approves_requirements"] if req
                ],
                "approved_part_versions": [
                    pv for pv in r["approved_part_versions"] if pv
                ],
            }
            for r in results
        ]

        return {"count": len(approvals), "approvals": approvals}

    except Exception as e:
        logger.error(f"Error fetching approvals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DOCUMENT ENDPOINTS
# ============================================================================


@router.get(
    "/documents", response_model=DocumentsResponse, response_class=Neo4jJSONResponse
)
async def get_documents(
    type: Optional[str] = Query(
        None, description="Filter by document type (Specification, Report, Drawing)"
    ),
    api_key: str = Depends(get_api_key),
):
    """
    Get all engineering documents

    Args:
        type: Filter by document type (Specification, Report, Drawing)

    Returns:
        Array of document objects
    """
    try:
        neo4j = get_neo4j_service()

        where_clause = "doc.type = $type" if type else "1=1"
        params = {"type": type} if type else {}

        query = f"""
        MATCH (doc:Document)
        WHERE doc.ap_level = 'AP239'
              AND doc.document_id IS NOT NULL
              AND {where_clause}
        OPTIONAL MATCH (doc)-[:DOCUMENTS]->(req:Requirement)
        RETURN doc.name AS name,
               doc.document_id AS document_id,
               toString(doc.version) AS version,
               doc.type AS type,
               COLLECT(DISTINCT req.name) AS documents_requirements
        ORDER BY doc.name
        """

        results = neo4j.execute_query(query, params)

        documents = [
            {
                "name": r["name"],
                "document_id": r["document_id"],
                "version": r["version"],
                "type": r["type"],
                "documents_requirements": [
                    req for req in r["documents_requirements"] if req
                ],
            }
            for r in results
        ]

        return {"count": len(documents), "documents": documents}

    except Exception as e:
        logger.error(f"Error fetching documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# STATISTICS ENDPOINT
# ============================================================================


@router.get(
    "/statistics", response_model=StatisticsResponse, response_class=Neo4jJSONResponse
)
async def get_ap239_statistics(api_key: str = Depends(get_api_key)):
    """
    Get summary statistics for AP239 data

    Returns:
        Counts and status breakdown for all AP239 entities
    """
    try:
        neo4j = get_neo4j_service()

        query = """
        MATCH (n)
        WHERE n.ap_level = 'AP239' AND n.ap_schema = 'AP239'
        WITH labels(n)[0] AS node_type, n.status AS status
        RETURN node_type, status, count(*) AS count
        ORDER BY node_type, status
        """

        results = neo4j.execute_query(query)

        # Group by node type
        stats = {}
        for r in results:
            node_type = r["node_type"]
            if node_type not in stats:
                stats[node_type] = {"total": 0, "by_status": {}}
            stats[node_type]["total"] += r["count"]
            if r["status"]:
                stats[node_type]["by_status"][r["status"]] = r["count"]

        return {"ap_level": "AP239", "ap_schema": "AP239", "statistics": stats}

    except Exception as e:
        logger.error(f"Error fetching AP239 statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
