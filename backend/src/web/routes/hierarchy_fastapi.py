"""
Hierarchy Navigation REST API Routes (FastAPI)
Endpoints for cross-level traceability and navigation across AP239/AP242/AP243
"""

from typing import List, Optional, Dict, Any
from enum import Enum
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from loguru import logger

from src.web.services import get_neo4j_service
from src.web.dependencies import get_api_key
from src.web.app_fastapi import Neo4jJSONResponse

router = APIRouter()


# Enums
class DirectionEnum(str, Enum):
    upstream = "upstream"
    downstream = "downstream"
    both = "both"


# Pydantic models
class RequirementInfo(BaseModel):
    id: str
    name: str
    type: Optional[str] = None
    status: Optional[str] = None


class TraceabilityLink(BaseModel):
    part_id: Optional[str] = None
    part_name: Optional[str] = None
    ontology_name: Optional[str] = None


class TraceabilityItem(BaseModel):
    requirement: RequirementInfo
    traceability: List[TraceabilityLink]


class TraceabilityMatrixResponse(BaseModel):
    count: int
    matrix: List[TraceabilityItem]


class SourceNode(BaseModel):
    type: str
    id: str


class NavigationTarget(BaseModel):
    type: str
    id: str
    name: Optional[str] = None
    level: Optional[int] = None


class NavigationResponse(BaseModel):
    source: SourceNode
    upstream: Optional[List[NavigationTarget]] = []
    downstream: Optional[List[NavigationTarget]] = []


class SearchResultNode(BaseModel):
    type: str
    id: str
    name: Optional[str] = None
    description: Optional[str] = None
    schema: Optional[str] = None


class SearchResults(BaseModel):
    ap239: List[SearchResultNode]
    ap242: List[SearchResultNode]
    ap243: List[SearchResultNode]


class CrossLevelSearchResponse(BaseModel):
    query: str
    levels_searched: List[int]
    results: SearchResults
    count: int
    total: int


class ImpactNode(BaseModel):
    type: str
    id: str
    name: Optional[str] = None
    level: Optional[int] = None
    distance: int


class ImpactAnalysisResponse(BaseModel):
    source: SourceNode
    affected_nodes: List[ImpactNode]


@router.get(
    "/traceability-matrix",
    response_model=TraceabilityMatrixResponse,
    response_class=Neo4jJSONResponse,
)
async def get_traceability_matrix(api_key: str = Depends(get_api_key)):
    """
    Get complete traceability matrix showing relationships across all AP levels

    Returns:
        Matrix of requirements → parts → ontologies with relationship chains
    """
    try:
        neo4j = get_neo4j_service()

        query = """
        MATCH (req:Requirement)
        WHERE req.ap_level = 1
        OPTIONAL MATCH (req)-[*1..3]->(part:Part)
        WHERE part.ap_level = 2
        OPTIONAL MATCH (part)-[*1..3]->(owl:ExternalOwlClass)
        WHERE owl.ap_level = 3
        WITH req, part, owl
        RETURN req.id AS requirement_id,
               req.name AS requirement_name,
               req.type AS requirement_type,
               req.status AS requirement_status,
               COLLECT(DISTINCT {
                   part_id: part.id,
                   part_name: part.name,
                   ontology_name: owl.name
               }) AS traceability
        ORDER BY req.name
        """

        results = neo4j.execute_query(query)

        matrix = [
            {
                "requirement": {
                    "id": r["requirement_id"],
                    "name": r["requirement_name"],
                    "type": r["requirement_type"],
                    "status": r["requirement_status"],
                },
                "traceability": [t for t in r["traceability"] if t.get("part_id")],
            }
            for r in results
        ]

        return {"count": len(matrix), "matrix": matrix}

    except Exception as e:
        logger.error(f"Error fetching traceability matrix: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/navigate/{node_type}/{node_id}",
    response_model=NavigationResponse,
    response_class=Neo4jJSONResponse,
)
async def navigate_hierarchy(
    node_type: str,
    node_id: str,
    direction: DirectionEnum = Query(
        DirectionEnum.both, description="Navigation direction"
    ),
    depth: int = Query(2, ge=1, le=5, description="Maximum traversal depth"),
    api_key: str = Depends(get_api_key),
):
    """
    Navigate from any node to see upstream and downstream connections

    Args:
        node_type: Type of node (Requirement, Part, Material, etc.)
        node_id: ID or name of the node
        direction: 'upstream' (to higher levels), 'downstream' (to lower levels), or 'both'
        depth: Maximum depth to traverse (1-5, default: 2)

    Returns:
        Navigation tree showing related nodes at other levels
    """
    try:
        neo4j = get_neo4j_service()

        # Validate node_type
        VALID_NODE_TYPES = {
            "Requirement",
            "Part",
            "Material",
            "Assembly",
            "ExternalOwlClass",
            "Class",
            "Package",
        }
        if node_type not in VALID_NODE_TYPES:
            raise HTTPException(
                status_code=400, detail=f"Invalid node type: {node_type}"
            )

        # Determine property to match
        id_prop = "id" if node_type in ["Requirement", "Part"] else "name"

        # Build queries based on direction
        if direction == DirectionEnum.both:
            query_up = f"""
            MATCH (node:{node_type} {{{id_prop}: $node_id}})
            MATCH path = (node)<-[*1..{depth}]-(target)
            WHERE target.ap_level < node.ap_level
            RETURN DISTINCT target, labels(target)[0] AS target_type, 
                   target.ap_level AS level, 'upstream' AS direction
            """

            query_down = f"""
            MATCH (node:{node_type} {{{id_prop}: $node_id}})
            MATCH path = (node)-[*1..{depth}]->(target)
            WHERE target.ap_level > node.ap_level
            RETURN DISTINCT target, labels(target)[0] AS target_type,
                   target.ap_level AS level, 'downstream' AS direction
            """

            results_up = neo4j.execute_query(query_up, {"node_id": node_id})
            results_down = neo4j.execute_query(query_down, {"node_id": node_id})
            results = results_up + results_down

            navigation = {
                "source": {"type": node_type, "id": node_id},
                "upstream": [],
                "downstream": [],
            }

            for r in results:
                target = r["target"]
                target_info = {
                    "type": r["target_type"],
                    "id": target.get("id", target.get("name")),
                    "name": target.get("name"),
                    "level": r["level"],
                }

                if r["direction"] == "upstream":
                    navigation["upstream"].append(target_info)
                else:
                    navigation["downstream"].append(target_info)

            return navigation

        else:
            # Single direction
            if direction == DirectionEnum.upstream:
                path_pattern = f"(node)<-[*1..{depth}]-(target)"
                where_clause = "target.ap_level < node.ap_level"
            else:  # downstream
                path_pattern = f"(node)-[*1..{depth}]->(target)"
                where_clause = "target.ap_level > node.ap_level"

            query = f"""
            MATCH (node:{node_type} {{{id_prop}: $node_id}})
            MATCH path = {path_pattern}
            WHERE {where_clause}
            RETURN DISTINCT target, labels(target)[0] AS target_type, target.ap_level AS level
            """

            results = neo4j.execute_query(query, {"node_id": node_id})

            navigation = {
                "source": {"type": node_type, "id": node_id},
                direction.value: [
                    {
                        "type": r["target_type"],
                        "id": r["target"].get("id", r["target"].get("name")),
                        "name": r["target"].get("name"),
                        "level": r["level"],
                    }
                    for r in results
                ],
            }

            return navigation

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error navigating hierarchy from {node_type}:{node_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/search", response_model=CrossLevelSearchResponse, response_class=Neo4jJSONResponse
)
async def cross_level_search(
    q: str = Query(..., min_length=1, description="Search query"),
    levels: str = Query("1,2,3", description="Comma-separated AP levels to search"),
    api_key: str = Depends(get_api_key),
):
    """
    Search across all AP levels simultaneously

    Args:
        q: Search query (searches name and description fields)
        levels: Comma-separated AP levels to search (default: "1,2,3")

    Returns:
        Search results grouped by AP level
    """
    try:
        neo4j = get_neo4j_service()

        # Parse levels
        level_list = [int(l.strip()) for l in levels.split(",") if l.strip().isdigit()]
        if not level_list:
            level_list = [1, 2, 3]

        query = """
        MATCH (n)
        WHERE n.ap_level IN $levels
          AND (n.name =~ $search OR n.description =~ $search)
        RETURN n, labels(n)[0] AS node_type, n.ap_level AS level, n.ap_schema AS schema
        ORDER BY n.ap_level, node_type, n.name
        LIMIT 100
        """

        results = neo4j.execute_query(
            query, {"levels": level_list, "search": f"(?i).*{q}.*"}
        )

        # Group by level
        by_level = {1: [], 2: [], 3: []}

        for r in results:
            node = r["n"]
            result_info = {
                "type": r["node_type"],
                "id": node.get("id", node.get("name")),
                "name": node.get("name"),
                "description": node.get("description"),
                "schema": r["schema"],
            }
            by_level[r["level"]].append(result_info)

        total_count = sum(len(v) for v in by_level.values())

        return {
            "query": q,
            "levels_searched": level_list,
            "results": {
                "ap239": by_level[1],
                "ap242": by_level[2],
                "ap243": by_level[3],
            },
            "count": total_count,
            "total": total_count,
        }

    except Exception as e:
        logger.error(f"Error in cross-level search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", response_class=Neo4jJSONResponse)
async def get_hierarchy_statistics(api_key: str = Depends(get_api_key)):
    """
    Get statistics about the entire hierarchy structure

    Returns:
        Node counts by level, relationship counts, and connectivity metrics
    """
    try:
        neo4j = get_neo4j_service()

        # Node counts by level
        node_query = """
        MATCH (n)
        WHERE n.ap_level IS NOT NULL
        RETURN n.ap_level AS level, n.ap_schema AS schema, 
               labels(n)[0] AS node_type, count(*) AS count
        ORDER BY level, node_type
        """

        # Cross-level relationship counts
        rel_query = """
        MATCH (n1)-[r]->(n2)
        WHERE n1.ap_level IS NOT NULL AND n2.ap_level IS NOT NULL
          AND n1.ap_level <> n2.ap_level
        RETURN n1.ap_level AS from_level, n2.ap_level AS to_level,
               type(r) AS relationship_type, count(*) AS count
        ORDER BY from_level, to_level
        """

        node_results = neo4j.execute_query(node_query)
        rel_results = neo4j.execute_query(rel_query)

        # Organize results
        by_level = {}
        for r in node_results:
            level_key = f"Level {r['level']} ({r['schema']})"
            if level_key not in by_level:
                by_level[level_key] = {}
            by_level[level_key][r["node_type"]] = r["count"]

        cross_level_rels = [
            {
                "from": f"AP{r['from_level']}",
                "to": f"AP{r['to_level']}",
                "relationship": r["relationship_type"],
                "count": r["count"],
            }
            for r in rel_results
        ]

        return {
            "nodes_by_level": by_level,
            "cross_level_relationships": cross_level_rels,
            "total_cross_level_links": sum(r["count"] for r in cross_level_rels),
        }

    except Exception as e:
        logger.error(f"Error fetching hierarchy statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/impact/{node_type}/{node_id}",
    response_model=ImpactAnalysisResponse,
    response_class=Neo4jJSONResponse,
)
async def analyze_impact(
    node_type: str, node_id: str, api_key: str = Depends(get_api_key)
):
    """
    Analyze the impact of changes to a specific node across all levels

    Args:
        node_type: Type of the source node
        node_id: ID of the source node

    Returns:
        All nodes that would be affected by changes to the specified node
    """
    try:
        neo4j = get_neo4j_service()

        id_prop = "id" if node_type in ["Requirement", "Part"] else "name"

        query = f"""
        MATCH (source:{node_type} {{{id_prop}: $node_id}})
        MATCH path = (source)-[*1..4]->(affected)
        WHERE affected.ap_level IS NOT NULL
        RETURN DISTINCT affected, labels(affected)[0] AS affected_type,
               affected.ap_level AS level, length(path) AS distance
        ORDER BY distance, level, affected_type
        """

        results = neo4j.execute_query(query, {"node_id": node_id})

        impact = {
            "source": {"type": node_type, "id": node_id},
            "affected_nodes": [
                {
                    "type": r["affected_type"],
                    "id": r["affected"].get("id", r["affected"].get("name")),
                    "name": r["affected"].get("name"),
                    "level": r["level"],
                    "distance": r["distance"],
                }
                for r in results
            ],
        }

        return impact

    except Exception as e:
        logger.error(f"Error analyzing impact for {node_type}:{node_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
