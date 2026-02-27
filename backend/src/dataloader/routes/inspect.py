"""
Dataloader — Graph inspection/audit router.

Read-only endpoints for inspecting the knowledge graph state:
  - Label / relationship type counts
  - AP level distribution
  - Node property coverage
  - Schema audit
"""

from __future__ import annotations

from fastapi import APIRouter
from loguru import logger

from src.dataloader.dependencies import get_neo4j_connection

router = APIRouter(prefix="/inspect", tags=["Graph Inspection"])


@router.get("/labels", summary="List all node labels with counts")
async def get_labels():
    conn = get_neo4j_connection()
    try:
        result = conn.execute_query("""
            CALL db.labels() YIELD label
            CALL apoc.cypher.run('MATCH (n:`' + label + '`) RETURN count(n) as cnt', {})
            YIELD value
            RETURN label, value.cnt AS count
            ORDER BY value.cnt DESC
        """)
        return {"labels": result}
    except Exception:
        # Fallback without APOC
        result = conn.execute_query("""
            MATCH (n)
            WITH labels(n) AS lbls
            UNWIND lbls AS label
            RETURN label, count(*) AS count
            ORDER BY count DESC
        """)
        return {"labels": result}
    finally:
        conn.close()


@router.get("/relationships", summary="List all relationship types with counts")
async def get_relationships():
    conn = get_neo4j_connection()
    try:
        result = conn.execute_query("""
            MATCH ()-[r]->()
            RETURN type(r) AS type, count(r) AS count
            ORDER BY count DESC
        """)
        return {"relationship_types": result}
    finally:
        conn.close()


@router.get("/ap-distribution", summary="AP level node distribution")
async def get_ap_distribution():
    """Show node counts grouped by ap_level and ap_schema."""
    conn = get_neo4j_connection()
    try:
        result = conn.execute_query("""
            MATCH (n)
            WHERE n.ap_level IS NOT NULL
            RETURN n.ap_level AS ap_level,
                   n.ap_schema AS ap_schema,
                   labels(n)[0] AS primary_label,
                   count(n) AS count
            ORDER BY n.ap_level, count DESC
        """)
        return {"ap_distribution": result}
    finally:
        conn.close()


@router.get("/constraints", summary="List all database constraints")
async def get_constraints():
    conn = get_neo4j_connection()
    try:
        result = conn.execute_query("SHOW CONSTRAINTS")
        return {"constraints": result}
    except Exception:
        try:
            result = conn.execute_query("CALL db.constraints() YIELD name, description RETURN name, description")
            return {"constraints": result}
        except Exception as e:
            return {"error": str(e)}
    finally:
        conn.close()


@router.get("/indexes", summary="List all database indexes")
async def get_indexes():
    conn = get_neo4j_connection()
    try:
        result = conn.execute_query("SHOW INDEXES")
        return {"indexes": result}
    except Exception:
        try:
            result = conn.execute_query("CALL db.indexes() YIELD name, labelsOrTypes, properties RETURN name, labelsOrTypes, properties")
            return {"indexes": result}
        except Exception as e:
            return {"error": str(e)}
    finally:
        conn.close()


@router.get("/summary", summary="Full graph summary statistics")
async def graph_summary():
    """Comprehensive graph statistics."""
    conn = get_neo4j_connection()
    try:
        nodes = conn.execute_query("MATCH (n) RETURN count(n) AS count")
        rels = conn.execute_query("MATCH ()-[r]->() RETURN count(r) AS count")

        label_counts = conn.execute_query("""
            MATCH (n) UNWIND labels(n) AS label
            RETURN label, count(*) AS count ORDER BY count DESC LIMIT 20
        """)

        rel_counts = conn.execute_query("""
            MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS count
            ORDER BY count DESC LIMIT 20
        """)

        ap_counts = conn.execute_query("""
            MATCH (n) WHERE n.ap_level IS NOT NULL
            RETURN n.ap_level AS level, count(n) AS count
            ORDER BY level
        """)

        return {
            "total_nodes": nodes[0]["count"] if nodes else 0,
            "total_relationships": rels[0]["count"] if rels else 0,
            "top_labels": label_counts,
            "top_relationship_types": rel_counts,
            "ap_level_distribution": ap_counts,
        }
    finally:
        conn.close()
