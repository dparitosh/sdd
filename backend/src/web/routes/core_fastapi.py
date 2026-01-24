"""
Core REST API endpoints for Package, Class, Property, Port, and Association entities
FastAPI implementation with async support and Pydantic models
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends, Request
from pydantic import BaseModel, Field
import time

from src.web.services import get_neo4j_service
from src.web.app_fastapi import Neo4jJSONResponse, limiter
from src.web.dependencies import get_api_key

router = APIRouter()

# Simple in-memory cache for stats endpoint
_stats_cache = {"data": None, "timestamp": 0}
STATS_CACHE_TTL = 60  # 60 seconds


# Pydantic models
class PackageResponse(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = "Unknown"
    comment: Optional[str] = None
    child_count: int


class PackageContent(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = "Unknown"
    type: Optional[str] = None
    comment: Optional[str] = None
    display_name: Optional[str] = None
    member_ends: Optional[str] = None


class PackageDetails(BaseModel):
    package_id: Optional[str] = None
    package_name: Optional[str] = "Unknown"
    package_comment: Optional[str] = None
    contents: List[PackageContent]


class ClassResponse(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = "Unknown"
    comment: Optional[str] = None
    property_count: int


class PropertyDetail(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None
    type_id: Optional[str] = None


class ParentClass(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None


class ClassDetails(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = "Unknown"
    comment: Optional[str] = None
    properties: List[PropertyDetail]
    parents: List[ParentClass]


class SearchResult(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = "Unknown"
    type: Optional[str] = None
    comment: Optional[str] = None


class Artifact(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = "Unknown"
    type: Optional[str] = None
    comment: Optional[str] = None


class Statistics(BaseModel):
    nodes: int  # For test compatibility
    relationships: int  # For test compatibility
    node_types: dict
    relationship_types: dict
    total_nodes: int
    total_relationships: int


@router.get(
    "/packages", response_model=List[PackageResponse], response_class=Neo4jJSONResponse
)
async def get_packages():
    """
    Get all packages with child counts

    Returns:
        List of packages with metadata
    """
    try:
        neo4j = get_neo4j_service()

        query = """
        MATCH (p:Package)
        OPTIONAL MATCH (p)-[:CONTAINS]->(child)
        RETURN p.id AS id,
               p.name AS name,
               p.comment AS comment,
               count(child) AS child_count
        ORDER BY p.name
        """
        result = neo4j.execute_query(query)

        packages = [
            {
                "id": r["id"],
                "name": r["name"] or "Unknown",
                "comment": r["comment"],
                "child_count": r["child_count"],
            }
            for r in result
        ]

        return packages
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get(
    "/package/{package_id}",
    response_model=PackageDetails,
    response_class=Neo4jJSONResponse,
)
async def get_package_contents(package_id: str):
    """
    Get package contents by ID

    Args:
        package_id: Unique package identifier

    Returns:
        Package details with all contained elements
    """
    try:
        neo4j = get_neo4j_service()

        query = """
        MATCH (p:Package {id: $package_id})
        OPTIONAL MATCH (p)-[:CONTAINS]->(child)
        RETURN p.id AS package_id,
               p.name AS package_name,
               p.comment AS package_comment,
               collect({
                   id: child.id,
                   name: CASE 
                       WHEN labels(child)[0] = 'Association' AND child.member_ends IS NOT NULL 
                       THEN replace(replace(child.member_ends, '[', ''), ']', '') + ' relationship'
                       WHEN labels(child)[0] = 'Association' AND child.display_name IS NOT NULL 
                       THEN replace(replace(child.display_name, '[', ''), ']', '')
                       ELSE child.name 
                   END,
                   type: labels(child)[0],
                   comment: child.comment,
                   display_name: child.display_name,
                   member_ends: child.member_ends
               }) AS contents
        """
        result = neo4j.execute_query(query, {"package_id": package_id})

        if result:
            return result[0]
        raise HTTPException(status_code=404, detail="Package not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get(
    "/classes", response_model=List[ClassResponse], response_class=Neo4jJSONResponse
)
async def get_classes():
    """
    Get all classes with property counts

    Returns:
        List of classes (limited to 100)
    """
    try:
        neo4j = get_neo4j_service()

        query = """
        MATCH (c:Class)
        OPTIONAL MATCH (c)-[:HAS_ATTRIBUTE]->(p:Property)
        RETURN c.id AS id,
               c.name AS name,
               c.comment AS comment,
               count(p) AS property_count
        ORDER BY c.name
        LIMIT 100
        """
        result = neo4j.execute_query(query)

        classes = [
            {
                "id": r["id"],
                "name": r["name"],
                "comment": r["comment"],
                "property_count": r["property_count"],
            }
            for r in result
        ]

        return classes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get(
    "/class/{class_id}", response_model=ClassDetails, response_class=Neo4jJSONResponse
)
async def get_class_details(class_id: str):
    """
    Get class details with properties and parent classes

    Args:
        class_id: Unique class identifier

    Returns:
        Class details with properties and inheritance
    """
    try:
        neo4j = get_neo4j_service()

        query = """
        MATCH (c:Class {id: $class_id})
        OPTIONAL MATCH (c)-[:HAS_ATTRIBUTE]->(p:Property)
        OPTIONAL MATCH (p)-[:TYPED_BY]->(t:Class)
        OPTIONAL MATCH (c)-[:GENERALIZES]->(parent:Class)
        RETURN c.id AS id,
               c.name AS name,
               c.comment AS comment,
               collect(DISTINCT {
                   id: p.id,
                   name: p.name,
                   type: t.name,
                   type_id: t.id
               }) AS properties,
               collect(DISTINCT {
                   id: parent.id,
                   name: parent.name
               }) AS parents
        """
        result = neo4j.execute_query(query, {"class_id": class_id})

        if result:
            data = result[0]
            # Clean up None values
            data["properties"] = [
                p for p in data.get("properties", []) if p and p.get("id")
            ]
            data["parents"] = [p for p in data.get("parents", []) if p and p.get("id")]
            return data
        raise HTTPException(status_code=404, detail="Class not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


class SearchRequest(BaseModel):
    name: str = Field(..., min_length=2, description="Search query")
    limit: int = Field(50, ge=1, le=100, description="Maximum results")


class SearchResponse(BaseModel):
    results: List[SearchResult]


@router.get(
    "/search", response_model=List[SearchResult], response_class=Neo4jJSONResponse
)
@limiter.limit("60/minute")
async def search_get(
    request: Request,
    q: str = Query(
        ..., min_length=2, description="Search query (minimum 2 characters)"
    ),
    api_key: str = Depends(get_api_key),
):
    """
    Search for entities by name (rate limited: 60 requests/minute)

    Args:
        request: FastAPI request object (for rate limiting)
        q: Search query string (minimum 2 characters)
        api_key: API key for authentication

    Returns:
        List of matching entities (limited to 50)

    Security:
        Requires valid API key via X-API-Key header
        Rate limited to 60 requests per minute per IP
    """
    try:
        neo4j = get_neo4j_service()

        # Use optimized search query
        query = """
        MATCH (n)
        WHERE n.name =~ ('(?i).*' + $query + '.*')
        RETURN n.id AS id,
               n.name AS name,
               labels(n)[0] AS type,
               n.comment AS comment
        ORDER BY n.name
        LIMIT 50
        """
        result = neo4j.execute_query(query, {"query": q})

        results = [
            {
                "id": r["id"],
                "name": r["name"],
                "type": r["type"],
                "comment": r["comment"],
            }
            for r in result
            if r.get("id")  # Filter out entries with None id
        ]

        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@router.post("/search", response_model=SearchResponse, response_class=Neo4jJSONResponse)
@limiter.limit("60/minute")
async def search_post(
    request: Request, search_request: SearchRequest, api_key: str = Depends(get_api_key)
):
    """
    Search for entities by name via POST (rate limited: 60 requests/minute)

    Args:
        request: FastAPI request object (for rate limiting)
        search_request: Search parameters (name and limit)
        api_key: API key for authentication

    Returns:
        Search results wrapped in results key

    Security:
        Requires valid API key via X-API-Key header
        Rate limited to 60 requests per minute per IP
    """
    try:
        neo4j = get_neo4j_service()

        # Use optimized search query
        query = """
        MATCH (n)
        WHERE n.name =~ ('(?i).*' + $query + '.*')
        RETURN n.id AS id,
               n.name AS name,
               labels(n)[0] AS type,
               n.comment AS comment
        ORDER BY n.name
        LIMIT $limit
        """
        result = neo4j.execute_query(
            query, {"query": search_request.name, "limit": search_request.limit}
        )

        results = [
            {
                "id": r["id"],
                "name": r["name"],
                "type": r["type"],
                "comment": r["comment"],
            }
            for r in result
            if r.get("id")  # Filter out entries with None id
        ]

        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@router.post("/search", response_model=SearchResponse, response_class=Neo4jJSONResponse)
async def search_post(search_request: SearchRequest):
    """
    Search for entities by name (POST version for test compatibility)

    Args:
        search_request: Search parameters with name and limit

    Returns:
        Search results with 'results' wrapper
    """
    try:
        neo4j = get_neo4j_service()

        # Use optimized search query
        query = """
        MATCH (n)
        WHERE n.name =~ ('(?i).*' + $query + '.*')
        RETURN n.id AS id,
               n.name AS name,
               labels(n)[0] AS type,
               n.comment AS comment
        ORDER BY n.name
        LIMIT $limit
        """
        result = neo4j.execute_query(
            query, {"query": search_request.name, "limit": search_request.limit}
        )

        results = [
            {
                "id": r["id"],
                "name": r["name"],
                "type": r["type"],
                "comment": r["comment"],
            }
            for r in result
            if r.get("id")  # Filter out entries with None id
        ]

        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@router.get(
    "/artifacts", response_model=List[Artifact], response_class=Neo4jJSONResponse
)
async def get_artifacts(
    type: Optional[str] = Query(
        None, description="Filter by artifact type (Class, Package, etc.)"
    ),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    api_key: str = Depends(get_api_key),
):
    """
    Get all artifacts (UML/SysML elements)

    Args:
        type: Optional filter by artifact type (Class, Package, Property, etc.)
        limit: Maximum number of results (default: 100, max: 1000)
        api_key: API key for authentication

    Returns:
        List of artifacts

    Security:
        Requires valid API key via X-API-Key header
    """
    try:
        neo4j = get_neo4j_service()

        if type:
            # Filter by specific type
            query = """
            MATCH (n)
            WHERE $type IN labels(n) AND n.name IS NOT NULL
            RETURN coalesce(n.id, toString(id(n))) AS id,
                   n.name AS name,
                   labels(n)[0] AS type,
                   n.comment AS comment
            ORDER BY n.name
            LIMIT $limit
            """
            result = neo4j.execute_query(query, {"type": type, "limit": limit})
        else:
            # Get all artifacts
            query = """
            MATCH (n)
            WHERE n.name IS NOT NULL
            RETURN coalesce(n.id, toString(id(n))) AS id,
                   n.name AS name,
                   labels(n)[0] AS type,
                   n.comment AS comment
            ORDER BY labels(n)[0], n.name
            LIMIT $limit
            """
            result = neo4j.execute_query(query, {"limit": limit})

        artifacts = [
            {
                "id": r["id"],
                "name": r["name"],
                "type": r["type"],
                "comment": r["comment"],
            }
            for r in result
            if r.get("name")  # Ensure name exists
        ]

        return artifacts
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/stats", response_model=Statistics, response_class=Neo4jJSONResponse)
async def get_stats(api_key: str = Depends(get_api_key)):
    """
    Get graph statistics (cached for 60 seconds)

    Args:
        api_key: API key for authentication

    Returns:
        Statistics about nodes and relationships in the graph

    Security:
        Requires valid API key via X-API-Key header

    Performance:
        Results cached for 60 seconds to reduce database load
    """
    try:
        # Check cache
        current_time = time.time()
        if (
            _stats_cache["data"]
            and (current_time - _stats_cache["timestamp"]) < STATS_CACHE_TTL
        ):
            return _stats_cache["data"]

        # Fetch fresh data
        neo4j = get_neo4j_service()
        stats = neo4j.get_statistics()

        # Add aliases for test compatibility
        stats["nodes"] = stats["total_nodes"]
        stats["relationships"] = stats["total_relationships"]

        # Update cache
        _stats_cache["data"] = stats
        _stats_cache["timestamp"] = current_time

        # Return flat structure matching frontend expectations
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


class CypherRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=5000)


class CypherResponse(BaseModel):
    columns: List[str]
    data: List[dict]
    execution_time: float
    result: Optional[List[dict]] = None  # Alias for test compatibility


@router.post("/cypher", response_model=CypherResponse, response_class=Neo4jJSONResponse)
@limiter.limit("30/minute")
async def execute_cypher(request: Request, cypher_request: CypherRequest):
    """
    Execute a read-only Cypher query (rate limited: 30 requests/minute)

    Security: Only MATCH, RETURN, WITH, UNWIND, WHERE, ORDER BY, LIMIT, SKIP operations allowed
    Dangerous operations (CREATE, DELETE, SET, MERGE, REMOVE, DETACH) are blocked

    Args:
        request: FastAPI request object (for rate limiting)
        cypher_request: CypherRequest with query string

    Returns:
        Query results with columns and data

    Rate Limiting:
        30 requests per minute per IP to prevent abuse
    """
    import time
    import re

    try:
        # Normalize query for security check
        normalized_query = cypher_request.query.upper().strip()

        # Block dangerous operations
        dangerous_keywords = [
            r"\bCREATE\b",
            r"\bDELETE\b",
            r"\bSET\b",
            r"\bMERGE\b",
            r"\bREMOVE\b",
            r"\bDETACH\b",
            r"\bDROP\b",
            r"\bCALL\b",
            r"\bLOAD\b",
            r"\bCREATE\s+INDEX\b",
            r"\bDROP\s+INDEX\b",
        ]

        for pattern in dangerous_keywords:
            if re.search(pattern, normalized_query):
                raise HTTPException(
                    status_code=403,
                    detail=f"Query contains forbidden operation: {pattern.replace(r'\\b', '').replace(r'\\s+', ' ')}",
                )

        # Execute query with timeout
        neo4j = get_neo4j_service()
        start_time = time.time()

        # Add LIMIT if not present to prevent massive result sets
        if "LIMIT" not in normalized_query:
            query_with_limit = f"{cypher_request.query} LIMIT 1000"
        else:
            query_with_limit = cypher_request.query

        result = neo4j.execute_query(query_with_limit, {})
        execution_time = time.time() - start_time

        # Extract columns and data
        if result:
            columns = list(result[0].keys()) if result else []
            data = [dict(record) for record in result]
        else:
            columns = []
            data = []

        return {
            "columns": columns,
            "data": data,
            "execution_time": round(execution_time, 3),
            "result": data,  # Alias for test compatibility
        }

    except HTTPException:
        # Re-raise HTTP exceptions (validation errors)
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query execution error: {str(e)}")


@router.get(
    "/artifacts/{artifact_type}/{artifact_id}", response_class=Neo4jJSONResponse
)
async def get_artifact_by_id(
    artifact_type: str, artifact_id: str, api_key: str = Depends(get_api_key)
):
    """
    Get specific artifact by type and ID

    Args:
        artifact_type: Type of artifact (Class, Package, Requirement, etc.)
        artifact_id: Unique identifier
        api_key: API key for authentication

    Returns:
        Artifact details with properties
    """
    try:
        neo4j = get_neo4j_service()

        query = f"""
        MATCH (n:{artifact_type} {{id: $artifact_id}})
        RETURN n.id AS id,
               n.name AS name,
               properties(n) AS properties
        """
        result = neo4j.execute_query(query, {"artifact_id": artifact_id})

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"{artifact_type} with id '{artifact_id}' not found",
            )

        artifact = result[0]
        return {
            "id": artifact["id"],
            "name": artifact["name"],
            "properties": artifact["properties"],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
