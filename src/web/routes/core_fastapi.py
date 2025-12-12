"""
Core REST API endpoints for Package, Class, Property, Port, and Association entities
FastAPI implementation with async support and Pydantic models
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.web.services import get_neo4j_service
from src.web.app_fastapi import Neo4jJSONResponse

router = APIRouter()


# Pydantic models
class PackageResponse(BaseModel):
    id: str
    name: str
    comment: Optional[str] = None
    child_count: int


class PackageContent(BaseModel):
    id: str
    name: str
    type: str
    comment: Optional[str] = None
    display_name: Optional[str] = None
    member_ends: Optional[str] = None


class PackageDetails(BaseModel):
    package_id: str
    package_name: str
    package_comment: Optional[str] = None
    contents: List[PackageContent]


class ClassResponse(BaseModel):
    id: str
    name: str
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
    id: str
    name: str
    comment: Optional[str] = None
    properties: List[PropertyDetail]
    parents: List[ParentClass]


class SearchResult(BaseModel):
    id: Optional[str] = None
    name: str
    type: str
    comment: Optional[str] = None


class Artifact(BaseModel):
    id: Optional[str] = None
    name: str
    type: str
    comment: Optional[str] = None


class Statistics(BaseModel):
    node_types: dict
    relationship_types: dict
    total_nodes: int
    total_relationships: int


@router.get("/packages", response_model=List[PackageResponse], response_class=Neo4jJSONResponse)
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
                "name": r["name"],
                "comment": r["comment"],
                "child_count": r["child_count"],
            }
            for r in result
        ]

        return packages
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/package/{package_id}", response_model=PackageDetails, response_class=Neo4jJSONResponse)
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


@router.get("/classes", response_model=List[ClassResponse], response_class=Neo4jJSONResponse)
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


@router.get("/class/{class_id}", response_model=ClassDetails, response_class=Neo4jJSONResponse)
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
            data["properties"] = [p for p in data.get("properties", []) if p and p.get("id")]
            data["parents"] = [p for p in data.get("parents", []) if p and p.get("id")]
            return data
        raise HTTPException(status_code=404, detail="Class not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/search", response_model=List[SearchResult], response_class=Neo4jJSONResponse)
async def search(q: str = Query(..., min_length=2, description="Search query (minimum 2 characters)")):
    """
    Search for entities by name
    
    Args:
        q: Search query string
        
    Returns:
        List of matching entities (limited to 50)
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
            {"id": r["id"], "name": r["name"], "type": r["type"], "comment": r["comment"]}
            for r in result
            if r.get("id")  # Filter out entries with None id
        ]

        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@router.get("/artifacts", response_model=List[Artifact], response_class=Neo4jJSONResponse)
async def get_artifacts(
    type: Optional[str] = Query(None, description="Filter by artifact type (Class, Package, etc.)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results")
):
    """
    Get all artifacts (UML/SysML elements)
    
    Args:
        type: Optional filter by artifact type (Class, Package, Property, etc.)
        limit: Maximum number of results (default: 100, max: 1000)
        
    Returns:
        List of artifacts
    """
    try:
        neo4j = get_neo4j_service()

        if type:
            # Filter by specific type
            query = """
            MATCH (n)
            WHERE $type IN labels(n)
            RETURN n.id AS id,
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
            RETURN n.id AS id,
                   n.name AS name,
                   labels(n)[0] AS type,
                   n.comment AS comment
            ORDER BY labels(n)[0], n.name
            LIMIT $limit
            """
            result = neo4j.execute_query(query, {"limit": limit})

        artifacts = [
            {"id": r["id"], "name": r["name"], "type": r["type"], "comment": r["comment"]}
            for r in result
            if r.get("name")  # Ensure name exists
        ]

        return artifacts
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/stats", response_model=Statistics, response_class=Neo4jJSONResponse)
async def get_stats():
    """
    Get graph statistics
    
    Returns:
        Statistics about nodes and relationships in the graph
    """
    try:
        neo4j = get_neo4j_service()
        stats = neo4j.get_statistics()

        # Return flat structure matching frontend expectations
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
