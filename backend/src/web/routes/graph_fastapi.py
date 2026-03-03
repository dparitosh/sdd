"""
Graph Visualization API Routes (FastAPI)
Provides endpoints for fetching graph data in format suitable for visualization
"""

from typing import List, Optional, Union
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from loguru import logger

from src.web.dependencies import get_api_key
from src.web.utils.responses import Neo4jJSONResponse
from src.web.container import Services

router = APIRouter()

# Whitelist of allowed node types to prevent Cypher injection
ALLOWED_NODE_TYPES = {
    "Requirement",
    "Part",
    "Class",
    "Package",
    "Property",
    "Association",
    "Port",
    "InstanceSpecification",
    "Constraint",
    "Material",
    "Assembly",
    "Document",
    "Person",
    "ExternalUnit",
    "Analysis",
    "AnalysisModel",
    "Approval",
    "Classification",
    "ExternalOwlClass",
    "GeometricModel",
    "MaterialProperty",
    "PartVersion",
    "RequirementVersion",
    "ShapeRepresentation",
    "ValueType",
    "Activity",
    "Breakdown",
    # MoSSEC Types
    "ModelInstance",
    "Study",
    "ActualActivity",
    "AssociativeModelNetwork",
    "ModelType",
    "Method",
    "Result",
    "Verification",
    "Context",
    "MethodActivity",
    "Component",
    "ComponentPlacement",
    "Event",
    "ExternalPropertyDefinition",
    "Interface",
    "Parameter",
    "System",
    "Slot",
    "Comment",
    # XMI/MBSE Element Types
    "MBSEElement",
    "Connector",
    "Generalization",
    # XSD Schema Types
    "XSDSchema",
    "XSDElement",
    "XSDComplexType",
    "XSDSimpleType",
    "XSDAttribute",
    "XSDGroup",
    "XSDAttributeGroup",
    # OWL Ontology Layer Types
    "OWLClass",
    "OWLObjectProperty",
    "OWLDatatypeProperty",
    "OWLProperty",
    # Ontology / OSLC Types
    "Ontology",
    "OntologyClass",
    "OntologyProperty",
    # Semantic Layer Types (metadata)
    "Documentation",
    "DomainConcept",
    "ExternalModel",
    # AP243 / Simulation
    "SimulationDossier",
    "SimulationRun",
    "SimulationModel",
    "SimulationArtifact",
    "EvidenceCategory",
    # AP242 / CAD extras
    "CADModel",
    "Shape",
    "Position",
    "WorkOrder",
    # People & Organizations
    "Person",
    "Organization",
    # OSLC integration
    "ServiceProvider",
    "Service",
    "Catalog",
    "CreationFactory",
    "QueryCapability",
    "Link",
}

# Metadata node types - excluded from default visualization
# These are derived/semantic nodes, not core domain data
# ExternalModel is intentionally NOT here — it is a core OSLC integration node
METADATA_NODE_TYPES = {
    "Documentation",
    "DomainConcept",
}


# Pydantic models
class GraphNode(BaseModel):
    id: str
    name: Optional[str] = None
    type: str
    group: str
    labels: List[str]
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    ap_level: Optional[Union[str, int]] = None
    ap_schema: Optional[str] = None
    properties: Optional[dict] = None


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
    is_metadata: bool = False  # True for semantic layer nodes


class NodeTypesResponse(BaseModel):
    node_types: List[NodeType]
    total_types: int


class RelationshipType(BaseModel):
    type: str
    count: int


class RelationshipTypesResponse(BaseModel):
    relationship_types: List[RelationshipType]
    total_types: int


# ── Pydantic models for path-finding, RAG, communities, expansion ───────────

class PathNode(BaseModel):
    id: str
    name: Optional[str] = None
    type: str
    labels: List[str]


class PathLink(BaseModel):
    source: str
    target: str
    type: str


class ShortestPathResponse(BaseModel):
    found: bool
    path_length: int = 0
    nodes: List[PathNode] = []
    links: List[PathLink] = []


class RAGQueryRequest(BaseModel):
    question: str
    top_k: int = 5


class RAGQueryResponse(BaseModel):
    answer: str
    sources: List[dict] = []
    nodes: List[dict] = []
    links: List[dict] = []


class CommunityNode(BaseModel):
    id: str
    community: int


class CommunityResponse(BaseModel):
    communities: List[CommunityNode]
    cluster_count: int


class ExpandResponse(BaseModel):
    nodes: List[dict]
    links: List[dict]


# ── Pydantic models for search & authoring ──────────────────────────────────

class SearchResult(BaseModel):
    id: str
    name: str
    type: str
    labels: List[str]
    description: Optional[str] = None
    ap_level: Optional[str] = None


class SearchResponse(BaseModel):
    results: List[SearchResult]
    total: int


class CreateRelationshipInput(BaseModel):
    source_id: str
    target_id: str
    relationship_type: str
    properties: Optional[dict] = None


class CreateRelationshipResponse(BaseModel):
    success: bool
    source_id: str
    target_id: str
    relationship_type: str
    message: str


# ── Search endpoint ─────────────────────────────────────────────────────────

@router.get("/search", response_model=SearchResponse, response_class=Neo4jJSONResponse)
async def search_nodes(
    q: str = Query(..., min_length=1, description="Search query"),
    node_type: Optional[str] = Query(None, description="Filter by node type"),
    limit: int = Query(25, ge=1, le=200, description="Maximum results"),
    neo4j=Depends(Services.neo4j),
    _api_key: str = Depends(get_api_key),
):
    """
    Full-text search across nodes by name or description.
    Used by the authoring mode for node selection.
    """
    try:
        where_parts = ["(toLower(coalesce(n.name,'')) CONTAINS toLower($q) OR toLower(coalesce(n.label,'')) CONTAINS toLower($q) OR toLower(coalesce(n.description,'')) CONTAINS toLower($q))"]
        params: dict = {"q": q, "limit": limit}

        if node_type and node_type in ALLOWED_NODE_TYPES:
            where_parts.append(f"'{node_type}' IN labels(n)")

        where_clause = " AND ".join(where_parts)

        query = f"""
        MATCH (n)
        WHERE {where_clause}
        RETURN coalesce(n.id, elementId(n)) AS id,
               coalesce(n.name, n.label) AS name,
               labels(n) AS labels,
               n.description AS description,
               n.ap_level AS ap_level
        ORDER BY CASE WHEN toLower(coalesce(n.name, n.label, '')) STARTS WITH toLower($q) THEN 0 ELSE 1 END, coalesce(n.name, n.label)
        LIMIT $limit
        """

        results = neo4j.execute_query(query, params)

        items = []
        for r in results:
            labels = r.get("labels") or []
            node_t = labels[0] if labels else "Unknown"
            items.append({
                "id": r["id"],
                "name": r.get("name") or r["id"],
                "type": node_t,
                "labels": labels,
                "description": r.get("description"),
                "ap_level": r.get("ap_level"),
            })

        return {"results": items, "total": len(items)}

    except Exception as e:
        logger.error(f"Error searching nodes: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ── Create relationship endpoint ────────────────────────────────────────────

@router.post("/relationships", response_model=CreateRelationshipResponse, response_class=Neo4jJSONResponse)
async def create_relationship(
    body: CreateRelationshipInput,
    neo4j=Depends(Services.neo4j),
    _api_key: str = Depends(get_api_key),
):
    """
    Create a relationship between two existing nodes.
    Used by authoring mode for manual graph construction.
    """
    # Sanitize relationship type (alphanumeric + underscore only)
    import re
    rel_type = body.relationship_type.upper().replace(" ", "_")
    if not re.match(r'^[A-Z_][A-Z0-9_]*$', rel_type):
        raise HTTPException(status_code=400, detail="Invalid relationship type. Use UPPER_SNAKE_CASE.")

    try:
        # Verify both nodes exist
        check_query = """
        OPTIONAL MATCH (s) WHERE coalesce(s.id, elementId(s)) = $source_id
        OPTIONAL MATCH (t) WHERE coalesce(t.id, elementId(t)) = $target_id
        RETURN s IS NOT NULL AS source_exists, t IS NOT NULL AS target_exists
        """
        check = neo4j.execute_query(check_query, {
            "source_id": body.source_id,
            "target_id": body.target_id,
        })

        if not check or not check[0].get("source_exists"):
            raise HTTPException(status_code=404, detail=f"Source node '{body.source_id}' not found")
        if not check[0].get("target_exists"):
            raise HTTPException(status_code=404, detail=f"Target node '{body.target_id}' not found")

        # Create the relationship (using APOC if available, else plain Cypher)
        props = body.properties or {}
        create_query = f"""
        MATCH (s) WHERE coalesce(s.id, elementId(s)) = $source_id
        MATCH (t) WHERE coalesce(t.id, elementId(t)) = $target_id
        CREATE (s)-[r:`{rel_type}`]->(t)
        SET r += $props
        RETURN type(r) AS type
        """
        neo4j.execute_query(create_query, {
            "source_id": body.source_id,
            "target_id": body.target_id,
            "props": props,
        })

        return {
            "success": True,
            "source_id": body.source_id,
            "target_id": body.target_id,
            "relationship_type": rel_type,
            "message": f"Relationship {rel_type} created successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating relationship: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/data", response_model=GraphData, response_class=Neo4jJSONResponse)
async def get_graph_data(
    response: Response,
    node_types: Optional[str] = Query(None, description="Comma-separated node types"),
    limit: int = Query(500, ge=1, le=100000, description="Maximum nodes to return"),
    depth: int = Query(1, ge=1, le=3, description="Relationship traversal depth"),
    ap_level: Optional[str] = Query(
        None, description="Filter by AP level (e.g. AP239, AP242, AP243, Core)"
    ),
    include_metadata: bool = Query(
        False, description="Include metadata nodes (Documentation, DomainConcept, ExternalModel)"
    ),
    neo4j=Depends(Services.neo4j),
    _api_key: str = Depends(get_api_key),
):
    """
    Get graph data for visualization (nodes and edges)

    Args:
        node_types: Comma-separated list of node types (e.g., 'Requirement,Part,Class')
        limit: Maximum number of nodes (default: 500, max: 100000)
        depth: Relationship traversal depth (default: 1, max: 3)
        ap_level: Filter by AP level string (AP239, AP242, AP243, Core)

    Returns:
        Graph data with nodes and links arrays for force-graph visualization
    """
    try:
        # Parse and sanitize node types
        requested_types = []
        if node_types:
            requested_types = [nt.strip() for nt in node_types.split(",") if nt.strip()]

        # Filter against whitelist to prevent injection
        validated_types = [nt for nt in requested_types if nt in ALLOWED_NODE_TYPES]

        # Instruct clients / CDNs to cache graph data for 60s (private)
        response.headers["Cache-Control"] = "private, max-age=60"

        # Exclude metadata types unless explicitly requested
        if not include_metadata:
            validated_types = [nt for nt in validated_types if nt not in METADATA_NODE_TYPES]

        # Build query
        where_clauses = []
        params: dict[str, Union[int, str]] = {"limit": limit}

        # OWL property nodes (OWLObjectProperty, OWLDatatypeProperty) are
        # intermediate satellites that only make sense when connected to their
        # host OWLClass.  Exclude them from the primary flat query and fetch
        # them later as connected neighbours of any OWLClass nodes returned.
        OWL_SATELLITE_LABELS = {"OWLObjectProperty", "OWLDatatypeProperty"}

        if validated_types:
            # If user explicitly requested an OWL satellite type, allow it
            primary_types = [nt for nt in validated_types if nt not in OWL_SATELLITE_LABELS]
            satellite_requested = [nt for nt in validated_types if nt in OWL_SATELLITE_LABELS]
            if primary_types or not satellite_requested:
                type_conditions = " OR ".join(
                    [f"'{nt}' IN labels(n)" for nt in (primary_types or validated_types)]
                )
                where_clauses.append(f"({type_conditions})")
            else:
                # Only satellite types requested — allow them through
                type_conditions = " OR ".join(
                    [f"'{nt}' IN labels(n)" for nt in validated_types]
                )
                where_clauses.append(f"({type_conditions})")
        else:
            # No specific types: exclude metadata AND OWL satellite nodes
            exclude_labels = METADATA_NODE_TYPES | OWL_SATELLITE_LABELS if not include_metadata else OWL_SATELLITE_LABELS
            exclude_conditions = " AND ".join(
                [f"NOT '{lbl}' IN labels(n)" for lbl in exclude_labels]
            )
            where_clauses.append(f"({exclude_conditions})")

        if ap_level is not None:
            where_clauses.append("n.ap_level = $ap_level")
            # params is dict[str, Any] but defined by limit which is int
            params["ap_level"] = ap_level

        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Fetch primary nodes (excludes OWL satellite property nodes)
        node_query = f"""
        MATCH (n)
        WHERE {where_clause}
         RETURN coalesce(n.id, elementId(n)) AS id,
               labels(n) AS labels,
               coalesce(n.name, n.label) AS name,
               n.description AS description,
               n.status AS status,
               n.priority AS priority,
               n.part_number AS part_number,
               n.ap_level AS ap_level,
               n.ap_schema AS ap_schema,
               properties(n) AS props
        LIMIT $limit
        """

        nodes_result = neo4j.execute_query(node_query, params)

        # Helper: build a node dict from a query record
        def _make_node(r):
            labels = r.get("labels") or []
            BASE_LABELS = {"XSDElement", "MBSEElement", "XSDNode", "OWLProperty"}
            specific = [l for l in labels if l not in BASE_LABELS]
            OWL_PREF = {"OWLClass", "OWLObjectProperty", "OWLDatatypeProperty"}
            owl = [l for l in specific if l in OWL_PREF]
            node_type = owl[0] if owl else (specific[0] if specific else (labels[0] if labels else "Unknown"))
            # Collect extra properties not already in top-level fields
            _TOP_KEYS = {"id", "labels", "name", "description", "status",
                         "priority", "part_number", "ap_level", "ap_schema", "props"}
            # Internal/metadata keys to exclude from the tooltip properties
            _INTERNAL_KEYS = {"uuid", "xmi_uuid", "xmi_id", "createdAt",
                              "modifiedAt", "loadSource", "version"}
            raw_props = r.get("props") or {}
            extra_props = {
                k: str(v) for k, v in raw_props.items()
                if k not in _TOP_KEYS
                and k not in _INTERNAL_KEYS
                and v is not None
                and str(v).strip()
            }
            return {
                "id": r["id"],
                "name": r.get("name") or r.get("part_number") or raw_props.get("label") or raw_props.get("local_name") or r["id"],
                "type": node_type,
                "group": node_type,
                "labels": labels,
                "description": r.get("description"),
                "status": r.get("status"),
                "priority": r.get("priority"),
                "ap_level": r.get("ap_level"),
                "ap_schema": r.get("ap_schema"),
                "properties": extra_props,
            }

        # Format primary nodes
        node_ids = set()
        nodes = []

        for r in nodes_result:
            if not r or not r.get("id"):
                continue
            node_ids.add(r["id"])
            nodes.append(_make_node(r))

        # ------------------------------------------------------------------
        # Fetch OWL satellite nodes connected to OWLClass nodes in the result
        # ------------------------------------------------------------------
        owl_class_ids = [
            n["id"] for n in nodes
            if "OWLClass" in (n.get("labels") or [])
        ]
        if owl_class_ids:
            owl_sat_query = """
            MATCH (cls:OWLClass)-[:HAS_OBJECT_PROPERTY|HAS_DATATYPE_PROPERTY]->(prop)
            WHERE coalesce(cls.id, elementId(cls)) IN $class_ids
            RETURN DISTINCT coalesce(prop.id, elementId(prop)) AS id,
                   labels(prop) AS labels,
                   coalesce(prop.name, prop.label) AS name,
                   prop.description AS description,
                   prop.status AS status,
                   prop.priority AS priority,
                   prop.ap_level AS ap_level,
                   prop.ap_schema AS ap_schema,
                   properties(prop) AS props
            """
            sat_result = neo4j.execute_query(owl_sat_query, {"class_ids": owl_class_ids})
            for r in sat_result:
                if r and r.get("id") and r["id"] not in node_ids:
                    node_ids.add(r["id"])
                    nodes.append(_make_node(r))

            # Also fetch RANGE_CLASS target OWLClass nodes that may not be in
            # the primary result set (e.g. cross-schema range classes)
            range_query = """
            MATCH (cls:OWLClass)-[:HAS_OBJECT_PROPERTY]->(op)-[:RANGE_CLASS]->(rng:OWLClass)
            WHERE cls.id IN $class_ids
              AND NOT coalesce(rng.id, elementId(rng)) IN $existing_ids
            RETURN DISTINCT coalesce(rng.id, elementId(rng)) AS id,
                   labels(rng) AS labels,
                   rng.name AS name,
                   rng.description AS description,
                   rng.status AS status,
                   rng.priority AS priority,
                   rng.ap_level AS ap_level,
                   rng.ap_schema AS ap_schema,
                   properties(rng) AS props
            """
            range_result = neo4j.execute_query(
                range_query, {"class_ids": owl_class_ids, "existing_ids": list(node_ids)}
            )
            for r in range_result:
                if r and r.get("id") and r["id"] not in node_ids:
                    node_ids.add(r["id"])
                    nodes.append(_make_node(r))

        # Fetch relationships
        # Split node_ids into property-based IDs and elementId-based fallbacks
        # so each branch can use an efficient index lookup.
        prop_ids = [nid for nid in node_ids if not nid.startswith("4:") and ":" not in nid]
        elem_ids = [nid for nid in node_ids if nid not in prop_ids]

        links = []
        if node_ids:
            rel_query = """
            MATCH (source)-[r]->(target)
            WHERE source.id IN $prop_ids
              AND target.id IN $prop_ids
            RETURN source.id AS source,
                   target.id AS target,
                   type(r) AS type,
                   elementId(r) AS rel_id
            LIMIT 10000
            """
            rels_result = neo4j.execute_query(
                rel_query,
                {"prop_ids": prop_ids if prop_ids else list(node_ids)},
                use_cache=False,
            )

            # If we have element-ID-based nodes, pick up their edges too
            if elem_ids:
                elem_rel_query = """
                MATCH (source)-[r]->(target)
                WHERE elementId(source) IN $elem_ids
                  AND elementId(target) IN $elem_ids
                RETURN coalesce(source.id, elementId(source)) AS source,
                       coalesce(target.id, elementId(target)) AS target,
                       type(r) AS type,
                       elementId(r) AS rel_id
                LIMIT 5000
                """
                elem_rels = neo4j.execute_query(
                    elem_rel_query,
                    {"elem_ids": elem_ids},
                    use_cache=False,
                )
                rels_result = rels_result + elem_rels

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
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/node-types", response_model=NodeTypesResponse, response_class=Neo4jJSONResponse
)
async def get_node_types(
    response: Response,
    include_metadata: bool = Query(
        False, description="Include metadata node types in results"
    ),
    neo4j=Depends(Services.neo4j),
    _api_key: str = Depends(get_api_key),
):
    """
    Get list of all node types (labels) in the graph with counts

    Args:
        include_metadata: Include metadata types like Documentation, DomainConcept

    Returns:
        Array of node types with their counts and metadata flag
    """
    try:
        query = """
        CALL db.labels() YIELD label
        CALL (label) {
            MATCH (n)
            WHERE label IN labels(n)
            RETURN count(n) AS count
        }
        RETURN label AS type, count
        ORDER BY count DESC, type
        """

        results = neo4j.execute_query(query)

        # Node-type list rarely changes — cache for 5 min
        response.headers["Cache-Control"] = "public, max-age=300"

        node_types = []
        for r in results:
            node_type = r["type"]
            is_meta = node_type in METADATA_NODE_TYPES
            # Skip metadata unless requested
            if is_meta and not include_metadata:
                continue
            node_types.append({
                "type": node_type,
                "count": r["count"],
                "is_metadata": is_meta
            })

        return {"node_types": node_types, "total_types": len(node_types)}

    except Exception as e:
        logger.error(f"Error fetching node types: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/relationship-types",
    response_model=RelationshipTypesResponse,
    response_class=Neo4jJSONResponse,
)
async def get_relationship_types(
    response: Response,
    neo4j=Depends(Services.neo4j),
):
    """
    Get list of all relationship types in the graph with counts

    Returns:
        Array of relationship types with their counts
    """
    try:
        query = """
        CALL db.relationshipTypes() YIELD relationshipType
        CALL (relationshipType) {
            MATCH ()-[r]->()
            WHERE type(r) = relationshipType
            RETURN count(r) AS count
        }
        RETURN relationshipType AS type, count
        ORDER BY count DESC, type
        """

        results = neo4j.execute_query(query)

        # Relationship types rarely change — cache for 5 min
        response.headers["Cache-Control"] = "public, max-age=300"

        rel_types = [{"type": r["type"], "count": r["count"]} for r in results]

        return {"relationship_types": rel_types, "total_types": len(rel_types)}

    except Exception as e:
        logger.error(f"Error fetching relationship types: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ── Shortest-path endpoint (E2) ─────────────────────────────────────────────

@router.get("/shortest-path", response_model=ShortestPathResponse, response_class=Neo4jJSONResponse)
async def shortest_path(
    source: str = Query(..., description="Source node ID"),
    target: str = Query(..., description="Target node ID"),
    max_depth: int = Query(15, ge=1, le=30, description="Max traversal depth"),
    neo4j=Depends(Services.neo4j),
    _api_key: str = Depends(get_api_key),
):
    """Find the shortest path between two nodes in the knowledge graph."""
    try:
        # Match by property id, element-id, OR node name (case-insensitive)
        query = """
        MATCH (a)
        WHERE coalesce(a.id, elementId(a)) = $source
           OR toLower(coalesce(a.name, a.label, '')) = toLower($source)
        WITH a LIMIT 1
        MATCH (b)
        WHERE coalesce(b.id, elementId(b)) = $target
           OR toLower(coalesce(b.name, b.label, '')) = toLower($target)
        WITH a, b LIMIT 1
        MATCH p = shortestPath((a)-[*..%d]-(b))
        RETURN nodes(p) AS nodes, relationships(p) AS rels
        """ % max_depth

        results = neo4j.execute_query(query, {"source": source, "target": target})
        if not results:
            return {"found": False, "path_length": 0, "nodes": [], "links": []}

        row = results[0]
        raw_nodes = row.get("nodes", [])
        raw_rels = row.get("rels", [])

        path_nodes = []
        for n in raw_nodes:
            props = dict(n) if hasattr(n, '__iter__') else {}
            nid = props.get("id") or str(n.element_id) if hasattr(n, 'element_id') else str(n)
            labels = list(n.labels) if hasattr(n, 'labels') else []
            name = props.get("name") or props.get("label") or nid
            node_type = labels[0] if labels else "Unknown"
            path_nodes.append({"id": nid, "name": name, "type": node_type, "labels": labels})

        path_links = []
        for r in raw_rels:
            src = str(r.start_node.element_id) if hasattr(r, 'start_node') else ""
            tgt = str(r.end_node.element_id) if hasattr(r, 'end_node') else ""
            # Map element_id back to the node id we returned
            src_id = next((pn["id"] for pn in path_nodes if pn["id"] == src or str(src) == str(pn["id"])), src)
            tgt_id = next((pn["id"] for pn in path_nodes if pn["id"] == tgt or str(tgt) == str(pn["id"])), tgt)
            # Use node property ids if available
            if hasattr(r, 'start_node'):
                sn_props = dict(r.start_node)
                src_id = sn_props.get("id", src_id)
            if hasattr(r, 'end_node'):
                en_props = dict(r.end_node)
                tgt_id = en_props.get("id", tgt_id)
            path_links.append({
                "source": src_id,
                "target": tgt_id,
                "type": r.type if hasattr(r, 'type') else str(type(r)),
            })

        return {
            "found": True,
            "path_length": len(path_links),
            "nodes": path_nodes,
            "links": path_links,
        }

    except Exception as e:
        logger.error(f"Shortest-path query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ── GraphRAG endpoint (E3) ──────────────────────────────────────────────────

@router.post("/rag-query", response_model=RAGQueryResponse, response_class=Neo4jJSONResponse)
async def rag_query(
    body: RAGQueryRequest,
    _api_key: str = Depends(get_api_key),
    neo4j=Depends(Services.neo4j),
):
    """Natural-language query over the knowledge graph using RAG pipeline."""
    try:
        from src.agents.semantic_agent import SemanticAgent
        agent = SemanticAgent()
        result = agent.semantic_insight(body.question, top_k=body.top_k)

        raw_answer = result.get("answer", "")
        is_fallback = result.get("fallback", False)

        # Build subgraph from the source hits + their 2-hop expanded neighbours
        raw_hits = result.get("hits", [])
        expanded = result.get("expanded", {})
        graph_nodes = []
        graph_links = []
        seen_ids = set()

        # ── Enrich hit names from Neo4j ─────────────────────────────────────
        # OpenSearch metadata only stores item_type; resolve real node names.
        uid_to_name: dict = {}
        hit_uids = [h.get("uid") for h in raw_hits if h.get("uid")]
        if hit_uids:
            try:
                name_rows = neo4j.execute_query(
                    "UNWIND $uids AS uid "
                    "MATCH (n {uid: uid}) "
                    "RETURN uid, COALESCE(n.name, n.product_id, n.label, uid) AS name, "
                    "       labels(n) AS labels",
                    {"uids": hit_uids},
                )
                uid_to_name = {r["uid"]: {"name": r["name"], "labels": list(r["labels"])} for r in name_rows}
            except Exception as exc:
                logger.warning(f"GraphRAG: Neo4j name enrichment failed — {exc}")

        def _resolve_name(uid: str, fallback: str) -> str:
            """Return Neo4j name if available, else fall back to metadata value."""
            neo4j_name = uid_to_name.get(uid, {}).get("name")
            # Only use the Neo4j name if it differs from the uid (i.e. a real name exists)
            if neo4j_name and neo4j_name != uid:
                return neo4j_name
            return fallback if (fallback and fallback != uid) else uid

        # If no LLM answer (search-only fallback), synthesise a simple answer from hits
        if not raw_answer and raw_hits:
            hit_names = ", ".join(_resolve_name(h.get("uid", "?"), h.get("name", "")) for h in raw_hits[:5])
            raw_answer = (
                f"**Search results for:** _{body.question}_\n\n"
                f"Top matches: {hit_names}\n\n"
                "*(Vector search index unavailable — showing full-text keyword matches only.)*"
            )
        elif not raw_answer:
            raw_answer = "No results found for this query in the knowledge graph."

        if is_fallback:
            raw_answer = raw_answer.rstrip() + "\n\n---\n*Semantic search index offline — using Neo4j keyword fallback.*"

        for hit in raw_hits:
            uid = hit.get("uid")
            if uid and uid not in seen_ids:
                seen_ids.add(uid)
                resolved_name = _resolve_name(uid, hit.get("name", uid))
                resolved_labels = uid_to_name.get(uid, {}).get("labels", [])
                graph_nodes.append({
                    "id": uid,
                    "name": resolved_name,
                    "type": resolved_labels[0] if resolved_labels else "RAGHit",
                    "labels": resolved_labels,
                    "score": hit.get("score", 0),
                })
            # Add expanded neighbours
            for nb in expanded.get(uid or "", []):
                nb_id = nb.get("neighbor_uid")
                if nb_id and nb_id not in seen_ids:
                    seen_ids.add(nb_id)
                    graph_nodes.append({
                        "id": nb_id,
                        "name": nb.get("neighbor_name", nb_id),
                        "type": (nb.get("neighbor_labels") or ["Unknown"])[0],
                        "labels": nb.get("neighbor_labels", []),
                    })
                if uid and nb_id:
                    rels = nb.get("rel_types", [])
                    graph_links.append({
                        "source": uid,
                        "target": nb_id,
                        "type": " → ".join(rels) if rels else "RELATED",
                    })

        # Build enriched sources list
        raw_sources = result.get("sources", [])
        sources = [
            {
                "uid": s.get("uid"),
                "name": _resolve_name(s.get("uid", ""), s.get("name", "")),
                "score": s.get("score"),
            }
            for s in raw_sources
        ]

        return {
            "answer": raw_answer,
            "sources": sources,
            "nodes": graph_nodes,
            "links": graph_links,
        }

    except Exception as e:
        logger.error(f"GraphRAG query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ── Node expansion endpoint (E1 context-menu expand) ────────────────────────

@router.get("/expand/{node_id}", response_model=ExpandResponse, response_class=Neo4jJSONResponse)
async def expand_node(
    node_id: str,
    depth: int = Query(2, ge=1, le=3, description="Hop depth"),
    neo4j=Depends(Services.neo4j),
    _api_key: str = Depends(get_api_key),
):
    """Expand a node by 1-3 hops, returning the subgraph around it."""
    try:
        query = """
        MATCH (center)-[r*1..%d]-(neighbor)
        WHERE coalesce(center.id, elementId(center)) = $node_id
          AND neighbor <> center
        RETURN DISTINCT
            coalesce(center.id, elementId(center)) AS center_id,
            labels(center) AS center_labels,
            coalesce(center.name, center.label) AS center_name,
            coalesce(neighbor.id, elementId(neighbor)) AS neighbor_id,
            labels(neighbor) AS neighbor_labels,
            coalesce(neighbor.name, neighbor.label) AS neighbor_name,
            [rel IN r | type(rel)] AS rel_types,
            properties(neighbor) AS neighbor_props
        LIMIT 200
        """ % depth

        results = neo4j.execute_query(query, {"node_id": node_id})

        nodes_map = {}
        links = []
        for row in results:
            cid = row["center_id"]
            if cid not in nodes_map:
                nodes_map[cid] = {
                    "id": cid,
                    "name": row.get("center_name") or cid,
                    "type": (row.get("center_labels") or ["Unknown"])[0],
                    "labels": row.get("center_labels", []),
                }
            nid = row["neighbor_id"]
            if nid not in nodes_map:
                raw_props = row.get("neighbor_props") or {}
                extra = {k: str(v) for k, v in raw_props.items()
                         if k not in {"id", "name", "label", "uuid", "xmi_uuid"} and v is not None}
                nodes_map[nid] = {
                    "id": nid,
                    "name": row.get("neighbor_name") or nid,
                    "type": (row.get("neighbor_labels") or ["Unknown"])[0],
                    "labels": row.get("neighbor_labels", []),
                    "properties": extra,
                }
            rel_types = row.get("rel_types", [])
            rel_label = rel_types[0] if len(rel_types) == 1 else " → ".join(rel_types)
            links.append({"source": cid, "target": nid, "type": rel_label})

        return {"nodes": list(nodes_map.values()), "links": links}

    except Exception as e:
        logger.error(f"Node expansion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ── Community detection endpoint (E14) ──────────────────────────────────────

@router.get("/communities", response_model=CommunityResponse, response_class=Neo4jJSONResponse)
async def detect_communities(
    neo4j=Depends(Services.neo4j),
    _api_key: str = Depends(get_api_key),
):
    """
    Lightweight community detection using label propagation.
    Falls back to connected-component grouping if GDS is unavailable.
    """
    try:
        # Try Neo4j GDS label propagation first
        try:
            gds_query = """
            CALL gds.labelPropagation.stream({
                nodeProjection: '*',
                relationshipProjection: { ALL: { type: '*', orientation: 'UNDIRECTED' } }
            }) YIELD nodeId, communityId
            RETURN gds.util.asNode(nodeId).id AS id, communityId AS community
            ORDER BY community
            """
            results = neo4j.execute_query(gds_query)
            if results:
                items = [{"id": r["id"], "community": r["community"]} for r in results]
                clusters = len(set(r["community"] for r in results))
                return {"communities": items, "cluster_count": clusters}
        except Exception:
            logger.info("GDS not available, using connected-component fallback")

        # Fallback: BFS-based connected components via Cypher
        cc_query = """
        MATCH (n)
        WHERE n.id IS NOT NULL
        WITH collect(n) AS allNodes
        UNWIND allNodes AS n
        OPTIONAL MATCH (n)-[r]-(m)
        WHERE m.id IS NOT NULL
        WITH n.id AS nid, collect(DISTINCT m.id) AS neighbors
        RETURN nid AS id, neighbors
        """
        rows = neo4j.execute_query(cc_query)
        # Build adjacency and run BFS
        adj = {}
        for row in rows:
            nid = row["id"]
            adj[nid] = row.get("neighbors", [])

        visited = set()
        community_map = {}
        comm_id = 0
        for nid in adj:
            if nid in visited:
                continue
            queue = [nid]
            visited.add(nid)
            while queue:
                current = queue.pop(0)
                community_map[current] = comm_id
                for nb in adj.get(current, []):
                    if nb not in visited:
                        visited.add(nb)
                        queue.append(nb)
            comm_id += 1

        items = [{"id": k, "community": v} for k, v in community_map.items()]
        return {"communities": items, "cluster_count": comm_id}

    except Exception as e:
        logger.error(f"Community detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ── Graph diff endpoint (E20) ───────────────────────────────────────────────

class GraphDiffRequest(BaseModel):
    """Compare two sets of node types to find added/removed nodes & links"""
    node_types_a: List[str] = []
    node_types_b: List[str] = []
    limit: int = 500


class DiffResult(BaseModel):
    added_nodes: list = []
    removed_nodes: list = []
    added_links: list = []
    removed_links: list = []
    summary: dict = {}


@router.post("/diff", response_model=DiffResult, response_class=Neo4jJSONResponse)
async def graph_diff(
    req: GraphDiffRequest,
    neo4j=Depends(Services.neo4j),
    _api_key: str = Depends(get_api_key),
):
    """
    Compare two graph snapshots defined by different node-type selections.
    Returns added/removed nodes and links between snapshot A and B.
    """
    try:
        def fetch_snapshot(node_types, lim):
            if node_types:
                safe = [t for t in node_types if t in ALLOWED_NODE_TYPES]
                if not safe:
                    return set(), set()
                labels = "|".join(f"`{t}`" for t in safe)
                q = f"MATCH (n) WHERE n:{labels} WITH n LIMIT {lim} " \
                    f"OPTIONAL MATCH (n)-[r]->(m) WHERE m:{labels} " \
                    f"RETURN n.id AS nid, type(r) AS rtype, m.id AS mid"
            else:
                q = f"MATCH (n) WITH n LIMIT {lim} " \
                    f"OPTIONAL MATCH (n)-[r]->(m) " \
                    f"RETURN n.id AS nid, type(r) AS rtype, m.id AS mid"
            rows = neo4j.execute_query(q)
            nodes = set()
            links = set()
            for row in rows:
                if row.get("nid"):
                    nodes.add(str(row["nid"]))
                if row.get("nid") and row.get("mid") and row.get("rtype"):
                    links.add((str(row["nid"]), str(row["rtype"]), str(row["mid"])))
            return nodes, links

        nodes_a, links_a = fetch_snapshot(req.node_types_a, req.limit)
        nodes_b, links_b = fetch_snapshot(req.node_types_b, req.limit)

        added_n = list(nodes_b - nodes_a)
        removed_n = list(nodes_a - nodes_b)
        added_l = [{"source": s, "type": t, "target": tgt} for s, t, tgt in (links_b - links_a)]
        removed_l = [{"source": s, "type": t, "target": tgt} for s, t, tgt in (links_a - links_b)]

        return {
            "added_nodes": added_n,
            "removed_nodes": removed_n,
            "added_links": added_l,
            "removed_links": removed_l,
            "summary": {
                "added_nodes_count": len(added_n),
                "removed_nodes_count": len(removed_n),
                "added_links_count": len(added_l),
                "removed_links_count": len(removed_l),
                "snapshot_a_nodes": len(nodes_a),
                "snapshot_b_nodes": len(nodes_b),
            }
        }
    except Exception as e:
        logger.error(f"Graph diff failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
