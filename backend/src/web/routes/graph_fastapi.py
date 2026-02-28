"""
Graph Visualization API Routes (FastAPI)
Provides endpoints for fetching graph data in format suitable for visualization
"""

from typing import List, Optional, Union
from fastapi import APIRouter, Depends, Query, HTTPException
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
    # AP243 / Simulation (MoSSEC)
    "SimulationDossier",
    "SimulationRun",
    "SimulationModel",
    "SimulationArtifact",
    "EvidenceCategory",
    "KPI",                         # Key Performance Indicator linked to Evidence
    "DecisionLog",                 # Approval / decision audit trail (reviewer, signatureId)
    # AP239 / PLCS compliance
    "ComplianceAudit",             # AuditFinding → ComplianceAudit (Critical/Warning/Pass)
    # AP242 / CAD extras
    "CADModel",
    "Shape",
    "Position",
    "WorkOrder",
    # People & Organizations
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
    # UML Comment nodes from XMI ingestion — internal annotations, not
    # meaningful in graph visualisation.  Adding here excludes them from
    # both the node-type filter UI and the pair query WHERE clause.
    "Comment",
}

# Relationship types that are XMI-internal annotations and should be
# de-prioritised in the pair query (pushed to end via ORDER BY).
# They are NOT hard-excluded — they can still appear if no other edges exist.
_NOISE_REL_TYPES = {
    "OWNS_COMMENT",
    "HAS_COMMENT",
    "DOCUMENTED_BY",
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

        where_clause_n = " AND ".join(where_clauses) if where_clauses else "1=1"
        # Build a matching clause for the far-end node m with renamed fields
        _wc_m = (where_clause_n
                 .replace("labels(n)", "labels(m)")
                 .replace("n.ap_level", "m.ap_level"))

        # ----------------------------------------------------------------
        # Core strategy: query EDGE PAIRS (n)-[r]->(m) and extract nodes
        # from their endpoints.  This guarantees every returned node has at
        # least one visible edge — eliminating the classic "N hub nodes,
        # 0 internal edges" problem that arises when nodes are fetched
        # independently and their neighbours happen to lie outside the result.
        #
        # ORDER BY puts structural/semantic edges first so the LIMIT budget is
        # spent on meaningful pairs rather than XMI-internal annotation edges
        # (OWNS_COMMENT / HAS_COMMENT / DOCUMENTED_BY).  Those are still
        # returned if no other edges meet the limit.
        # pair_limit intentionally overshoots so that after deduplication we
        # still end up with roughly $limit unique nodes.
        # ----------------------------------------------------------------
        pair_query = f"""
        MATCH (n)-[r]->(m)
        WHERE {where_clause_n}
          AND {_wc_m}
        WITH n, r, m,
             CASE type(r)
               WHEN 'OWNS_COMMENT'       THEN 99
               WHEN 'HAS_COMMENT'        THEN 99
               WHEN 'DOCUMENTED_BY'      THEN 98
               WHEN 'REFERENCES_EXTERNAL' THEN 50
               ELSE 0
             END AS noise_rank
        ORDER BY noise_rank
        LIMIT $pair_limit
        RETURN
            coalesce(n.id, elementId(n)) AS n_id,
            labels(n)                    AS n_labels,
            coalesce(n.name, n.label)    AS n_name,
            n.description                AS n_desc,
            n.status                     AS n_status,
            n.priority                   AS n_priority,
            n.part_number                AS n_part_number,
            n.ap_level                   AS n_ap_level,
            n.ap_schema                  AS n_ap_schema,
            properties(n)                AS n_props,
            coalesce(m.id, elementId(m)) AS m_id,
            labels(m)                    AS m_labels,
            coalesce(m.name, m.label)    AS m_name,
            m.description                AS m_desc,
            m.status                     AS m_status,
            m.priority                   AS m_priority,
            m.part_number                AS m_part_number,
            m.ap_level                   AS m_ap_level,
            m.ap_schema                  AS m_ap_schema,
            properties(m)               AS m_props,
            type(r)                      AS rel_type,
            elementId(r)                 AS rel_id
        """
        pair_params = dict(params)
        pair_params["pair_limit"] = limit * 3   # overshoot then deduplicate

        pairs_result = neo4j.execute_query(pair_query, pair_params)

        # ------------------------------------------------------------------
        # Helpers
        # ------------------------------------------------------------------
        BASE_LABELS = {"XSDElement", "MBSEElement", "XSDNode", "OWLProperty"}
        OWL_PREF    = {"OWLClass", "OWLObjectProperty", "OWLDatatypeProperty"}
        TOP_KEYS     = {"id","labels","name","description","status",
                        "priority","part_number","ap_level","ap_schema","props"}
        INTERNAL_KEYS = {"uuid","xmi_uuid","xmi_id","createdAt",
                         "modifiedAt","loadSource","version"}

        def _resolve_type(labels):
            specific = [l for l in labels if l not in BASE_LABELS]
            owl = [l for l in specific if l in OWL_PREF]
            return (owl[0] if owl else
                    specific[0] if specific else
                    labels[0] if labels else "Unknown")

        def _extra_props(raw):
            return {k: str(v) for k, v in raw.items()
                    if k not in TOP_KEYS and k not in INTERNAL_KEYS
                    and v is not None and str(v).strip()}

        def _make_node_from_pair(row, prefix):
            """Build a node dict from one row of the pair query."""
            nlabels = row.get(f"{prefix}labels") or []
            nid     = row.get(f"{prefix}id")
            nname   = row.get(f"{prefix}name")
            raw     = row.get(f"{prefix}props") or {}
            return {
                "id":          nid,
                "name":        nname or row.get(f"{prefix}part_number")
                               or raw.get("label") or raw.get("local_name") or nid,
                "type":        _resolve_type(nlabels),
                "group":       _resolve_type(nlabels),
                "labels":      nlabels,
                "description": row.get(f"{prefix}desc"),
                "status":      row.get(f"{prefix}status"),
                "priority":    row.get(f"{prefix}priority"),
                "ap_level":    row.get(f"{prefix}ap_level"),
                "ap_schema":   row.get(f"{prefix}ap_schema"),
                "properties":  _extra_props(raw),
            }

        def _make_node(r):
            """Build a node dict from a single-node query row (e.g. OWL supplement)."""
            labels  = r.get("labels") or []
            raw     = r.get("props") or {}
            return {
                "id":          r["id"],
                "name":        r.get("name") or r.get("part_number")
                               or raw.get("label") or raw.get("local_name") or r["id"],
                "type":        _resolve_type(labels),
                "group":       _resolve_type(labels),
                "labels":      labels,
                "description": r.get("description"),
                "status":      r.get("status"),
                "priority":    r.get("priority"),
                "ap_level":    r.get("ap_level"),
                "ap_schema":   r.get("ap_schema"),
                "properties":  _extra_props(raw),
            }

        # ---- Process pair results -----------------------------------------
        node_ids = set()
        nodes    = []
        link_ids = set()
        links    = []

        for row in pairs_result:
            n_id = row.get("n_id")
            m_id = row.get("m_id")
            if not n_id or not m_id:
                continue
            if n_id not in node_ids and len(node_ids) < limit:
                node_ids.add(n_id)
                nodes.append(_make_node_from_pair(row, "n_"))
            if m_id not in node_ids and len(node_ids) < limit:
                node_ids.add(m_id)
                nodes.append(_make_node_from_pair(row, "m_"))
            rid = str(row.get("rel_id", ""))
            if rid and rid not in link_ids:
                link_ids.add(rid)
                links.append({
                    "source": n_id,
                    "target": m_id,
                    "type":   row.get("rel_type", ""),
                    "id":     rid,
                })

        # Fallback: if pair query returned nothing (fully isolated dataset or
        # very narrow type filter with no edges), sample any nodes so the view
        # is not empty.
        if not nodes:
            fallback_query = f"""
            MATCH (n)
            WHERE {where_clause_n}
            WITH n ORDER BY rand() LIMIT $limit
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
            """
            for r in neo4j.execute_query(fallback_query, params):
                if r and r.get("id") and r["id"] not in node_ids:
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

            # Fetch any supplemental edges introduced by OWL satellite nodes
            # (these were added after the main pair query so are not yet in links)
            supp_rel_query = """
            MATCH (source)-[r]->(target)
            WHERE coalesce(source.id, elementId(source)) IN $node_ids
              AND coalesce(target.id, elementId(target)) IN $node_ids
            RETURN coalesce(source.id, elementId(source)) AS source,
                   coalesce(target.id, elementId(target)) AS target,
                   type(r) AS type,
                   elementId(r) AS rel_id
            """
            for r in neo4j.execute_query(supp_rel_query, {"node_ids": list(node_ids)}):
                rid = str(r.get("rel_id", ""))
                if rid and rid not in link_ids:
                    link_ids.add(rid)
                    links.append({
                        "source": r["source"],
                        "target": r["target"],
                        "type":   r["type"],
                        "id":     rid,
                    })

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

        return {"relationship_types": rel_types, "total_types": len(rel_types)}

    except Exception as e:
        logger.error(f"Error fetching relationship types: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
