"""
PLM Integration Routes (FastAPI)
Endpoints for Product Lifecycle Management operations:
- Requirements traceability
- Composition/BOM hierarchy
- Change impact analysis
- Parameter extraction
- Constraint validation
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from pydantic import BaseModel, Field

from src.web.utils.responses import Neo4jJSONResponse
from src.web.services import get_neo4j_service
from src.web.dependencies import get_api_key

# ============================================================================
# ROUTER CONFIGURATION
# ============================================================================

router = APIRouter(prefix="/plm", tags=["PLM Integration"], dependencies=[Depends(get_api_key)])


# ============================================================================
# PYDANTIC MODELS
# ============================================================================


class TraceNode(BaseModel):
    id: str
    name: str
    type: str


class TraceLink(BaseModel):
    source: TraceNode
    relationship_chain: List[str]
    target: TraceNode
    path_length: int


class TraceabilityResponse(BaseModel):
    total: int
    filters: dict
    traceability: List[TraceLink]


class PathNode(BaseModel):
    id: str
    name: str
    type: str
    visibility: Optional[str] = None
    aggregation: Optional[str] = None


class CompositionPath(BaseModel):
    path: List[PathNode]
    depth: int


class CompositionRoot(BaseModel):
    id: str
    name: str
    type: str


class CompositionResponse(BaseModel):
    root: CompositionRoot
    children: List[CompositionPath]
    total_children: int


class ImpactNode(BaseModel):
    id: str
    name: str
    type: str
    relationship_chain: List[str]
    distance: int


class ImpactDetail(BaseModel):
    count: int
    affected_nodes: Optional[List[ImpactNode]] = None
    dependencies: Optional[List[ImpactNode]] = None


class ImpactAnalysisResponse(BaseModel):
    node: TraceNode
    upstream_impact: ImpactDetail
    downstream_impact: ImpactDetail
    total_impact: int


class Multiplicity(BaseModel):
    lower: Optional[str] = None
    upper: Optional[str] = None


class ParameterOwner(BaseModel):
    name: str
    type: str


class Parameter(BaseModel):
    id: str
    name: str
    owner: Optional[ParameterOwner] = None
    type: Optional[str] = None
    multiplicity: Multiplicity
    visibility: Optional[str] = None
    aggregation: Optional[str] = None
    default_value: Optional[str] = None
    is_derived: Optional[bool] = None
    is_read_only: Optional[bool] = None


class ParametersResponse(BaseModel):
    total: int
    filters: dict
    parameters: List[Parameter]


class ConstraintOwner(BaseModel):
    id: str
    name: str
    type: str


class Constraint(BaseModel):
    id: str
    name: str
    body: Optional[str] = None
    language: Optional[str] = None
    owner: Optional[ConstraintOwner] = None


class ConstraintsResponse(BaseModel):
    total: int
    filters: dict
    constraints: List[Constraint]


# ============================================================================
# TRACEABILITY ENDPOINT
# ============================================================================


@router.get(
    "/traceability",
    response_model=TraceabilityResponse,
    response_class=Neo4jJSONResponse,
)
async def get_traceability(
    source_type: Optional[str] = Query(None, description="Filter by source node type"),
    target_type: Optional[str] = Query(None, description="Filter by target node type"),
    relationship_type: Optional[str] = Query(
        None, description="Filter by relationship type"
    ),
    depth: int = Query(2, ge=1, le=10, description="Maximum path depth to traverse"),
):
    """
    Get traceability matrix showing relationships between elements

    Trace connections between different types of nodes (Requirements, Classes, etc.)
    across multiple relationship hops.

    Args:
        source_type: Filter by source node type (e.g., "Requirement", "Class")
        target_type: Filter by target node type
        relationship_type: Filter by specific relationship type
        depth: Maximum traversal depth (1-10)

    Returns:
        Traceability links with source, target, and relationship chains
    """
    try:
        neo4j = get_neo4j_service()

        # Build dynamic query
        query_parts = []
        params = {}

        # Source node filter - validate against whitelist to prevent Cypher injection
        ALLOWED_NODE_TYPES = {
            "Class", "Package", "Requirement", "Part", "PartVersion", "Material",
            "Assembly", "Connector", "Property", "Port", "Association",
            "Generalization", "Constraint", "Comment", "InstanceSpecification",
            "MBSEElement", "XSDElement", "StepFile", "StepInstance",
            "DomainConcept", "OntologyClass", None,
        }
        ALLOWED_REL_TYPES = {
            "OWNS", "DEFINES", "ASSOCIATES_WITH", "HAS_ATTRIBUTE", "TYPED_BY",
            "GENERALIZES_TO", "HAS_PORT", "CONTAINS", "INSTANCE_OF", "STEP_REF",
            "ALIGNS_TO", "SATISFIES", "TRACES_TO", "DERIVES_FROM",
            "IMPLEMENTS", "VERIFIES", "REFINES", None,
        }
        if source_type and source_type not in ALLOWED_NODE_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid source_type: {source_type}")
        if target_type and target_type not in ALLOWED_NODE_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid target_type: {target_type}")
        if relationship_type and relationship_type not in ALLOWED_REL_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid relationship_type: {relationship_type}")

        if source_type:
            query_parts.append(f"MATCH (source:{source_type})")
            params["source_type"] = source_type
        else:
            query_parts.append("MATCH (source)")

        # Relationship filter with depth
        if relationship_type:
            query_parts.append(f"-[rels:{relationship_type}*1..{depth}]->")
        else:
            query_parts.append(f"-[rels*1..{depth}]->")

        # Target node filter
        if target_type:
            query_parts.append(f"(target:{target_type})")
        else:
            query_parts.append("(target)")

        query = (
            " ".join(query_parts)
            + """
        RETURN source.id as source_id,
               source.name as source_name,
               labels(source)[0] as source_type,
               [rel in rels | type(rel)] as relationship_chain,
               target.id as target_id,
               target.name as target_name,
               labels(target)[0] as target_type,
               size(rels) as path_length
        ORDER BY path_length, source_name, target_name
        LIMIT 1000
        """
        )

        result = neo4j.execute_query(query, params)

        traces = [
            {
                "source": {
                    "id": r["source_id"],
                    "name": r["source_name"],
                    "type": r["source_type"],
                },
                "relationship_chain": r["relationship_chain"],
                "target": {
                    "id": r["target_id"],
                    "name": r["target_name"],
                    "type": r["target_type"],
                },
                "path_length": r["path_length"],
            }
            for r in result
        ]

        return {
            "total": len(traces),
            "filters": {
                "source_type": source_type,
                "target_type": target_type,
                "relationship_type": relationship_type,
                "depth": depth,
            },
            "traceability": traces,
        }

    except Exception as e:
        logger.error(f"Traceability query error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve traceability data: {str(e)}",
        )


# ============================================================================
# COMPOSITION/BOM ENDPOINT
# ============================================================================


@router.get(
    "/composition/{node_id}",
    response_model=CompositionResponse,
    response_class=Neo4jJSONResponse,
)
async def get_composition(
    node_id: str,
    depth: int = Query(10, ge=1, le=20, description="Maximum composition depth"),
):
    """
    Get Bill of Materials (BOM) composition hierarchy for a node

    Shows complete containment tree with all children at all levels.

    Args:
        node_id: ID of the root node
        depth: Maximum depth to traverse (1-20)

    Returns:
        Hierarchical composition structure with all child nodes

    Raises:
        HTTPException 404: Node not found or has no composition
    """
    try:
        neo4j = get_neo4j_service()

        query = f"""
        MATCH path = (root {{id: $node_id}})-[:CONTAINS*1..{depth}]->(child)
        RETURN root.id as root_id,
               root.name as root_name,
               labels(root)[0] as root_type,
               [node in nodes(path) | {{
                   id: node.id,
                   name: node.name,
                   type: labels(node)[0],
                   visibility: node.visibility,
                   aggregation: node.aggregation
               }}] as path_nodes,
               length(path) as depth
        ORDER BY depth, child.name
        LIMIT 1000
        """

        result = neo4j.execute_query(query, {"node_id": node_id})

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Node with ID '{node_id}' not found or has no composition",
            )

        # Build hierarchical tree structure
        composition = {
            "root": {
                "id": result[0]["root_id"],
                "name": result[0]["root_name"],
                "type": result[0]["root_type"],
            },
            "children": [
                {"path": r["path_nodes"], "depth": r["depth"]} for r in result
            ],
            "total_children": len(result),
        }

        return composition

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Composition query error for {node_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve composition data: {str(e)}",
        )


# ============================================================================
# IMPACT ANALYSIS ENDPOINT
# ============================================================================


@router.get(
    "/impact/{node_id}",
    response_model=ImpactAnalysisResponse,
    response_class=Neo4jJSONResponse,
)
async def get_impact_analysis(
    node_id: str,
    depth: int = Query(3, ge=1, le=10, description="Maximum analysis depth"),
):
    """
    Analyze change impact for a node

    Finds all nodes that would be affected by changes to this node,
    showing both upstream (dependent on this) and downstream (this depends on) dependencies.

    Args:
        node_id: ID of the node to analyze
        depth: Maximum depth to analyze (1-10)

    Returns:
        Upstream and downstream impact analysis with affected nodes

    Raises:
        HTTPException 404: Node not found
    """
    try:
        neo4j = get_neo4j_service()

        # Get node info first
        node_query = """
        MATCH (n {id: $node_id})
        RETURN n.id as id, n.name as name, labels(n)[0] as type
        """
        node_info = neo4j.execute_query(node_query, {"node_id": node_id})

        if not node_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Node with ID '{node_id}' not found",
            )

        # Find upstream impact (who references/depends on this node)
        upstream_query = f"""
        MATCH path = (dependent)-[r*1..{depth}]->(node {{id: $node_id}})
        WHERE type(r[0]) IN ['TYPED_BY', 'GENERALIZES', 'DEPENDS_ON', 'USES', 'ASSOCIATES_WITH']
        RETURN DISTINCT
               dependent.id as dependent_id,
               dependent.name as dependent_name,
               labels(dependent)[0] as dependent_type,
               [rel in relationships(path) | type(rel)] as relationship_chain,
               length(path) as distance
        ORDER BY distance, dependent_name
        LIMIT 500
        """

        upstream_result = neo4j.execute_query(upstream_query, {"node_id": node_id})

        # Find downstream impact (what this node references/depends on)
        downstream_query = f"""
        MATCH path = (node {{id: $node_id}})-[r*1..{depth}]->(dependency)
        WHERE type(r[0]) IN ['TYPED_BY', 'GENERALIZES', 'DEPENDS_ON', 'USES', 'ASSOCIATES_WITH']
        RETURN DISTINCT
               dependency.id as dependency_id,
               dependency.name as dependency_name,
               labels(dependency)[0] as dependency_type,
               [rel in relationships(path) | type(rel)] as relationship_chain,
               length(path) as distance
        ORDER BY distance, dependency_name
        LIMIT 500
        """

        downstream_result = neo4j.execute_query(downstream_query, {"node_id": node_id})

        return {
            "node": {
                "id": node_info[0]["id"],
                "name": node_info[0]["name"],
                "type": node_info[0]["type"],
            },
            "upstream_impact": {
                "count": len(upstream_result),
                "affected_nodes": [
                    {
                        "id": r["dependent_id"],
                        "name": r["dependent_name"],
                        "type": r["dependent_type"],
                        "relationship_chain": r["relationship_chain"],
                        "distance": r["distance"],
                    }
                    for r in upstream_result
                ],
            },
            "downstream_impact": {
                "count": len(downstream_result),
                "dependencies": [
                    {
                        "id": r["dependency_id"],
                        "name": r["dependency_name"],
                        "type": r["dependency_type"],
                        "relationship_chain": r["relationship_chain"],
                        "distance": r["distance"],
                    }
                    for r in downstream_result
                ],
            },
            "total_impact": len(upstream_result) + len(downstream_result),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Impact analysis error for {node_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze impact: {str(e)}",
        )


# ============================================================================
# PARAMETERS ENDPOINT
# ============================================================================


@router.get(
    "/parameters", response_model=ParametersResponse, response_class=Neo4jJSONResponse
)
async def get_parameters(
    class_name: Optional[str] = Query(
        None, alias="class", description="Filter by class name"
    ),
    limit: int = Query(1000, ge=1, le=5000, description="Maximum number of results"),
):
    """
    Get system parameters from Properties

    Retrieve properties with their types, multiplicity, and constraints.
    Useful for design/simulation integration.

    Args:
        class_name: Filter by owning class name
        limit: Maximum results (1-5000)

    Returns:
        List of parameters with type and multiplicity information
    """
    try:
        neo4j = get_neo4j_service()

        query_parts = ["MATCH (p:Property)"]
        params = {"limit": limit}

        if class_name:
            query_parts.append(
                "MATCH (c:Class {name: $class_name})-[:HAS_ATTRIBUTE]->(p)"
            )
            params["class_name"] = class_name

        query_parts.append(
            f"""
        OPTIONAL MATCH (p)-[:TYPED_BY]->(type)
        OPTIONAL MATCH (p)<-[:HAS_ATTRIBUTE]-(owner)
        RETURN p.id as id,
               p.name as name,
               p.visibility as visibility,
               p.lower as lower,
               p.upper as upper,
               p.aggregation as aggregation,
               p.defaultValue as default_value,
               p.isDerived as is_derived,
               p.isReadOnly as is_read_only,
               type.name as type_name,
               owner.name as owner_name,
               labels(owner)[0] as owner_type
        ORDER BY owner_name, p.name
        LIMIT $limit
        """
        )

        query = " ".join(query_parts)
        result = neo4j.execute_query(query, params)

        parameters = [
            {
                "id": r["id"],
                "name": r["name"],
                "owner": (
                    {"name": r["owner_name"], "type": r["owner_type"]}
                    if r.get("owner_name")
                    else None
                ),
                "type": r["type_name"],
                "multiplicity": {"lower": r["lower"], "upper": r["upper"]},
                "visibility": r["visibility"],
                "aggregation": r["aggregation"],
                "default_value": r["default_value"],
                "is_derived": r["is_derived"],
                "is_read_only": r["is_read_only"],
            }
            for r in result
        ]

        return {
            "total": len(parameters),
            "filters": {"class": class_name, "limit": limit},
            "parameters": parameters,
        }

    except Exception as e:
        logger.error(f"Parameters query error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve parameters: {str(e)}",
        )


# ============================================================================
# CONSTRAINTS ENDPOINT
# ============================================================================


@router.get(
    "/constraints", response_model=ConstraintsResponse, response_class=Neo4jJSONResponse
)
async def get_constraints(
    element_id: Optional[str] = Query(None, description="Filter by element ID"),
    limit: int = Query(1000, ge=1, le=5000, description="Maximum number of results"),
):
    """
    Get validation constraints

    Retrieve OCL or other constraint specifications for design/simulation validation.

    Args:
        element_id: Filter by owning element ID
        limit: Maximum results (1-5000)

    Returns:
        List of constraints with bodies and owners
    """
    try:
        neo4j = get_neo4j_service()

        query_parts = ["MATCH (c:Constraint)"]
        params = {"limit": limit}

        if element_id:
            query_parts.append("MATCH (e {id: $element_id})-[:HAS_RULE]->(c)")
            params["element_id"] = element_id

        query_parts.append(
            f"""
        OPTIONAL MATCH (owner)-[:HAS_RULE]->(c)
        RETURN c.id as id,
               c.name as name,
               c.body as body,
               c.language as language,
               owner.id as owner_id,
               owner.name as owner_name,
               labels(owner)[0] as owner_type
        ORDER BY owner_name, c.name
        LIMIT $limit
        """
        )

        query = " ".join(query_parts)
        result = neo4j.execute_query(query, params)

        constraints = [
            {
                "id": r["id"],
                "name": r["name"],
                "body": r["body"],
                "language": r["language"],
                "owner": (
                    {
                        "id": r["owner_id"],
                        "name": r["owner_name"],
                        "type": r["owner_type"],
                    }
                    if r.get("owner_id")
                    else None
                ),
            }
            for r in result
        ]

        return {
            "total": len(constraints),
            "filters": {"element_id": element_id, "limit": limit},
            "constraints": constraints,
        }

    except Exception as e:
        logger.error(f"Constraints query error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve constraints: {str(e)}",
        )
