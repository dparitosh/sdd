"""Graph Query Registry — named Cypher queries for the frontend.

Provides a curated set of parameterised Cypher queries that can be
executed by name via ``GET /api/graph/query/{name}?params…``.

Each query returns node / edge rows suitable for the graph renderer.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from loguru import logger

from src.web.services import get_neo4j_service

# ---------------------------------------------------------------------------
# Registry: name → { cypher, description, params }
# ---------------------------------------------------------------------------

QUERY_REGISTRY: Dict[str, Dict[str, Any]] = {
    "bom_tree": {
        "description": "BOM explosion tree rooted at a PLMXMLItem uid.",
        "params": ["uid"],
        "cypher": """
            MATCH path = (root:PLMXMLItem {uid: $uid})
                  -[:HAS_REVISION]->(:PLMXMLRevision)
                  -[:HAS_BOM_LINE]->(:PLMXMLBOMLine)
                  -[:REFERENCES]->(child:PLMXMLItem)
            RETURN [n IN nodes(path) | {
                uid: n.uid,
                labels: labels(n),
                name: COALESCE(n.name, n.item_id, n.uid),
                properties: properties(n)
            }] AS nodes,
            [r IN relationships(path) | {
                type: type(r),
                start: startNode(r).uid,
                end: endNode(r).uid
            }] AS edges
        """,
    },
    "ontology_hierarchy": {
        "description": "Full OWL class hierarchy (SUBCLASS_OF edges).",
        "params": [],
        "cypher": """
            MATCH (child:ExternalOwlClass)-[r:SUBCLASS_OF]->(parent:ExternalOwlClass)
            RETURN child.uri   AS source_id,
                   child.name  AS source_name,
                   parent.uri  AS target_id,
                   parent.name AS target_name,
                   type(r)     AS rel_type
            ORDER BY parent.name, child.name
        """,
    },
    "classification_web": {
        "description": "All CLASSIFIED_AS edges between items and OWL classes.",
        "params": [],
        "cypher": """
            MATCH (item:PLMXMLItem)-[r:CLASSIFIED_AS]->(cls:ExternalOwlClass)
            RETURN item.uid       AS source_id,
                   item.name      AS source_name,
                   cls.uri        AS target_id,
                   cls.name       AS target_name,
                   r.confidence   AS confidence,
                   r.ap_level     AS ap_level,
                   type(r)        AS rel_type
            ORDER BY cls.name
        """,
    },
    "traceability_chain": {
        "description": "Requirement → traces-to chain (AP239 requirements).",
        "params": [],
        "cypher": """
            MATCH (req)-[r:TRACES_TO|SATISFIES|VERIFIES]->(target)
            RETURN req.uid    AS source_id,
                   COALESCE(req.title, req.name, req.uid) AS source_name,
                   target.uid AS target_id,
                   COALESCE(target.name, target.uid) AS target_name,
                   type(r)    AS rel_type
        """,
    },
    "shacl_violations": {
        "description": "All SHACL violations with the offending node.",
        "params": [],
        "cypher": """
            MATCH (n)-[:HAS_VIOLATION]->(v:SHACLViolation)
            RETURN n.uid          AS node_uid,
                   COALESCE(n.name, n.uid) AS node_name,
                   labels(n)      AS node_labels,
                   v.uid          AS violation_uid,
                   v.shape_name   AS shape_name,
                   v.property     AS property,
                   v.severity     AS severity,
                   v.message      AS message
            ORDER BY v.severity, v.shape_name
        """,
    },
    "semantic_neighbors": {
        "description": "2-hop graph neighbourhood of a node (by uid).",
        "params": ["uid"],
        "cypher": """
            MATCH path = (center {uid: $uid})-[*1..2]-(neighbor)
            UNWIND nodes(path) AS n
            UNWIND relationships(path) AS r
            WITH COLLECT(DISTINCT {
                uid: n.uid,
                labels: labels(n),
                name: COALESCE(n.name, n.item_id, n.uid)
            }) AS nodeList,
            COLLECT(DISTINCT {
                type: type(r),
                start: startNode(r).uid,
                end: endNode(r).uid
            }) AS edgeList
            RETURN nodeList AS nodes, edgeList AS edges
        """,
    },
    "step_geometry": {
        "description": "STEP files linked from PLMXMLDataSets.",
        "params": [],
        "cypher": """
            MATCH (ds:PLMXMLDataSet)-[:LINKED_STEP_FILE]->(sf:StepFile)
            RETURN ds.uid    AS dataset_uid,
                   ds.name   AS dataset_name,
                   sf.uid    AS step_uid,
                   sf.name   AS step_name,
                   sf.file_schema AS file_schema
            ORDER BY ds.name
        """,
    },
    "oslc_req_links": {
        "description": "OSLC requirement links (AP239 ↔ OSLC-RM).",
        "params": [],
        "cypher": """
            MATCH (req)-[r:CLASSIFIED_AS|SATISFIES|TRACES_TO]->(target)
            WHERE any(l IN labels(req) WHERE l IN ['Requirement', 'ExternalOwlClass'])
               OR any(l IN labels(target) WHERE l IN ['Requirement', 'ExternalOwlClass'])
            RETURN req.uid     AS source_id,
                   COALESCE(req.name, req.title, req.uid) AS source_name,
                   target.uid  AS target_id,
                   COALESCE(target.name, target.uid) AS target_name,
                   type(r)     AS rel_type
        """,
    },
}


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------

def execute_named_query(
    name: str,
    params: Optional[Dict[str, Any]] = None,
    limit: int = 500,
) -> Dict[str, Any]:
    """Run a registered named query and return rows.

    Returns ``{"name": ..., "rows": [...], "count": int}``.
    Raises ``KeyError`` if the query name is not in the registry.
    """
    entry = QUERY_REGISTRY.get(name)
    if entry is None:
        raise KeyError(f"Unknown query name: '{name}'. Available: {list(QUERY_REGISTRY)}")

    cypher = entry["cypher"]
    if limit and "LIMIT" not in cypher.upper():
        cypher = cypher.rstrip().rstrip(";") + f"\nLIMIT {limit}"

    neo4j = get_neo4j_service()
    with neo4j.driver.session(database=neo4j.database) as session:
        result = session.run(cypher, **(params or {}))
        rows = [dict(r) for r in result]

    logger.info(f"GraphQueryRegistry: '{name}' returned {len(rows)} rows")
    return {"name": name, "rows": rows, "count": len(rows)}


def list_queries() -> List[Dict[str, Any]]:
    """Return metadata for all registered queries (no Cypher exposed)."""
    return [
        {
            "name": name,
            "description": entry["description"],
            "params": entry["params"],
        }
        for name, entry in QUERY_REGISTRY.items()
    ]
