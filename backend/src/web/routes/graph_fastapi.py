"""
Graph Visualization API Routes (FastAPI)
Provides endpoints for fetching graph data in format suitable for visualization
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from loguru import logger

from src.web.services import get_neo4j_service
from src.web.dependencies import get_api_key
from src.web.app_fastapi import Neo4jJSONResponse

router = APIRouter()

# Whitelist of allowed node types to prevent Cypher injection
ALLOWED_NODE_TYPES = {
    "Requirement", "Part", "Class", "Package", "Property", "Association", "Port",
    "InstanceSpecification", "Constraint", "Material", "Assembly", "Document",
    "Person", "ExternalUnit", "Analysis", "AnalysisModel", "Approval",
    "Classification", "ExternalOwlClass", "GeometricModel", "MaterialProperty",
    "PartVersion", "RequirementVersion", "ShapeRepresentation", "ValueType",
    "Activity", "Breakdown", "Component", "ComponentPlacement", "Event",
    "ExternalPropertyDefinition", "Interface", "Parameter", "System", "Slot", "Comment",
}


# Pydantic models
class GraphNode(BaseModel):
    id: str
    name: str
    type: str
    group: str
    labels: List[str]
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    ap_level: Optional[int] = None
    ap_schema: Optional[str] = None


class GraphLink(BaseModel):
    source: str
    target: str
    type: str
    id: str


class GraphMetadata(BaseModel):
    node_count: int
    link_count: int
    node_types: List[str]
    relationship_types: List[str]
    filters_applied: dict


class GraphData(BaseModel):
    nodes: List[GraphNode]
    links: List[GraphLink]
    metadata: GraphMetadata


class NodeType(BaseModel):
    type: str
    count: int


class NodeTypesResponse(BaseModel):
    node_types: List[NodeType]
    total_types: int


class RelationshipType(BaseModel):
    type: str
    count: int


class RelationshipTypesResponse(BaseModel):
    relationship_types: List[RelationshipType]
    total_types: int


@router.get("/data", response_model=GraphData, response_class=Neo4jJSONResponse)
async def get_graph_data(
    node_types: Optional[str] = Query(None, description="Comma-separated node types"),
    limit: int = Query(500, ge=1, le=1000, description="Maximum nodes to return"),
    depth: int = Query(1, ge=1, le=3, description="Relationship traversal depth"),
    ap_level: Optional[int] = Query(None, description="Filter by AP level (1=AP239, 2=AP242, 3=AP243)"),
    api_key: str = Depends(get_api_key)
):
    """
    Get graph data for visualization (nodes and edges)
    
    Args:
        node_types: Comma-separated list of node types (e.g., 'Requirement,Part,Class')
        limit: Maximum number of nodes (default: 500, max: 1000)
        depth: Relationship traversal depth (default: 1, max: 3)
        ap_level: Filter by AP level (1, 2, or 3)
        
    Returns:
        Graph data with nodes and links arrays for force-graph visualization
    
    Performance:
        Reduced max limit from 2000 to 1000 to prevent browser performance issues
    """
    try:
        neo4j = get_neo4j_service()

        # Parse and sanitize node types
        requested_types = []
        if node_types:
            requested_types = [nt.strip() for nt in node_types.split(",") if nt.strip()]
        
        # Filter against whitelist to prevent injection
        validated_types = [nt for nt in requested_types if nt in ALLOWED_NODE_TYPES]

        # Build query
        where_clauses = []
        params = {"limit": limit}

        if validated_types:
            type_conditions = " OR ".join([f"'{nt}' IN labels(n)" for nt in validated_types])
            where_clauses.append(f"({type_conditions})")

        if ap_level is not None:
            where_clauses.append("n.ap_level = $ap_level")
            params["ap_level"] = ap_level

        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Fetch nodes
        node_query = f"""
        MATCH (n)
        WHERE {where_clause}
         RETURN coalesce(n.id, toString(id(n))) AS id,
               labels(n) AS labels,
               n.name AS name,
               n.description AS description,
               n.status AS status,
               n.priority AS priority,
               n.part_number AS part_number,
               n.ap_level AS ap_level,
               n.ap_schema AS ap_schema
        LIMIT $limit
        """

        nodes_result = neo4j.execute_query(node_query, params)

        # Format nodes
        node_ids = set()
        nodes = []

        for r in nodes_result:
            if not r or not r.get("id"):
                continue

            node_id = r["id"]
            node_ids.add(node_id)

            labels = r.get("labels") or []
            node_type = labels[0] if labels else "Unknown"

            node = {
                "id": node_id,
                "name": r.get("name") or r.get("part_number") or node_id,
                "type": node_type,
                "group": node_type,
                "labels": labels,
                "description": r.get("description"),
                "status": r.get("status"),
                "priority": r.get("priority"),
                "ap_level": r.get("ap_level"),
                "ap_schema": r.get("ap_schema"),
            }
            nodes.append(node)

        # Fetch relationships
        links = []
        if node_ids:
            rel_query = """
            MATCH (source)-[r]->(target)
             WHERE coalesce(source.id, toString(id(source))) IN $node_ids
            AND coalesce(target.id, toString(id(target))) IN $node_ids
             RETURN coalesce(source.id, toString(id(source))) AS source,
                 coalesce(target.id, toString(id(target))) AS target,
                   type(r) AS type,
                   id(r) AS rel_id
            """

            rels_result = neo4j.execute_query(rel_query, {"node_ids": list(node_ids)})

            for r in rels_result:
                link = {
                    "source": r["source"],
                    "target": r["target"],
                    "type": r["type"],
                    "id": str(r["rel_id"]),
                }
                links.append(link)

        # Build metadata
        metadata = {
            "node_count": len(nodes),
            "link_count": len(links),
            "node_types": list(set(n["type"] for n in nodes)),
            "relationship_types": list(set(l["type"] for l in links)),
            "filters_applied": {
                "node_types": validated_types or "all",
                "ap_level": ap_level or "all",
                "limit": limit,
                "depth": depth,
            },
        }

        return {
            "nodes": nodes,
            "links": links,
            "metadata": metadata,
        }

    except Exception as e:
        logger.error(f"Error fetching graph data: {e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/node-types", response_model=NodeTypesResponse, response_class=Neo4jJSONResponse)
async def get_node_types(api_key: str = Depends(get_api_key)):
    """
    Get list of all node types (labels) in the graph with counts
    
    Returns:
        Array of node types with their counts
    """
    try:
        neo4j = get_neo4j_service()

        query = """
        CALL db.labels() YIELD label
        CALL {
            WITH label
            MATCH (n)
            WHERE label IN labels(n)
            RETURN count(n) AS count
        }
        RETURN label AS type, count
        ORDER BY count DESC, type
        """

        results = neo4j.execute_query(query)

        node_types = [{"type": r["type"], "count": r["count"]} for r in results]

        return {
            "node_types": node_types,
            "total_types": len(node_types)
        }

    except Exception as e:
        logger.error(f"Error fetching node types: {e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/relationship-types", response_model=RelationshipTypesResponse, response_class=Neo4jJSONResponse)
async def get_relationship_types(api_key: str = Depends(get_api_key)):
    """
    Get list of all relationship types in the graph with counts
    
    Returns:
        Array of relationship types with their counts
    """
    try:
        neo4j = get_neo4j_service()

        query = """
        CALL db.relationshipTypes() YIELD relationshipType
        CALL {
            WITH relationshipType
            MATCH ()-[r]->()
            WHERE type(r) = relationshipType
            RETURN count(r) AS count
        }
        RETURN relationshipType AS type, count
        ORDER BY count DESC, type
        """

        results = neo4j.execute_query(query)

        rel_types = [{"type": r["type"], "count": r["count"]} for r in results]

        return {
            "relationship_types": rel_types,
            "total_types": len(rel_types)
        }

    except Exception as e:
        logger.error(f"Error fetching relationship types: {e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))
