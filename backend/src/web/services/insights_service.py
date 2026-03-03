"""
AI Insights Service — pre-computed analytics over the knowledge graph.

Provides 5 standard insight queries and a per-node SmartAnalysis pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from loguru import logger

from src.web.container import Services


def _neo4j():
    """Lazy accessor for Neo4j service."""
    svc = Services.neo4j()
    return svc


def _run(cypher: str, params: dict | None = None) -> list[dict]:
    """Execute a read-only Cypher query and return dicts."""
    neo4j = _neo4j()
    with neo4j.driver.session(database=neo4j.database) as session:
        result = session.run(cypher, **(params or {}))
        return [dict(r) for r in result]


# ─── Insight queries ─────────────────────────────────────────────────────────

# Labels that represent "items" in the knowledge graph.
# Adapts across PLM XML and AP/MBSE ontology schemas.
_ITEM_LABELS = [
    "PLMXMLItem", "Part", "AP242Product", "SimulationArtifact", "SimulationDossier",
    "SimulationRun", "ValidationCase", "Assembly", "Document",
    "MBSEElement",
]

# Labels used for SHACL compliance node totals.
_COMPLIANCE_LABELS = [
    "PLMXMLItem", "PLMXMLRevision", "PLMXMLBOMLine", "PLMXMLDataSet",
    "StepFile", "Part", "AP242Product", "AP242ProductDefinition",
    "AP242AssemblyOccurrence", "SimulationArtifact", "SimulationDossier",
    "SimulationRun", "ValidationCase", "Assembly", "Document",
    "MBSEElement",
]


def _detect_item_label() -> str:
    """Return the best available label for 'item' nodes in the current DB."""
    for label in _ITEM_LABELS:
        rows = _run(f"MATCH (n:`{label}`) RETURN count(n) AS cnt LIMIT 1")
        if rows and rows[0]["cnt"] > 0:
            return label
    return "MBSEElement"  # ultimate fallback


def bom_completeness() -> Dict[str, Any]:
    """Count unclassified items and items missing revisions."""
    label = _detect_item_label()
    total = _run(f"MATCH (n:`{label}`) RETURN count(n) AS cnt")[0]["cnt"]
    unclassified = _run(
        f"MATCH (n:`{label}`) WHERE n.classification_status = 'unclassified' "
        "OR NOT EXISTS { (n)-[:CLASSIFIED_AS]->() } "
        "RETURN count(n) AS cnt"
    )[0]["cnt"]
    no_revision = _run(
        f"MATCH (n:`{label}`) WHERE NOT EXISTS {{ (n)-[:HAS_REVISION]->() }} "
        "RETURN count(n) AS cnt"
    )[0]["cnt"]
    return {
        "total_items": total,
        "item_label": label,
        "unclassified": unclassified,
        "missing_revision": no_revision,
        "completeness_pct": round((total - unclassified) / max(total, 1) * 100, 1),
    }


def traceability_gaps() -> Dict[str, Any]:
    """Requirements without any TRACES_TO / SATISFIES relationship."""
    total = _run("MATCH (r:Requirement) RETURN count(r) AS cnt")[0]["cnt"]
    orphan_rows = _run(
        "MATCH (r:Requirement) "
        "WHERE NOT EXISTS { (r)-[:TRACES_TO|SATISFIES|VERIFIES]->() } "
        "RETURN coalesce(r.uid, r.id) AS uid, "
        "coalesce(r.title, r.name) AS title LIMIT 200"
    )
    return {
        "total_requirements": total,
        "orphaned": len(orphan_rows),
        "coverage_pct": round((total - len(orphan_rows)) / max(total, 1) * 100, 1),
        "orphan_list": orphan_rows[:50],
    }


def classification_coverage() -> Dict[str, Any]:
    """Percentage of item nodes with a CLASSIFIED_AS edge."""
    label = _detect_item_label()
    total = _run(f"MATCH (n:`{label}`) RETURN count(n) AS cnt")[0]["cnt"]
    classified = _run(
        f"MATCH (n:`{label}`)-[:CLASSIFIED_AS]->() RETURN count(DISTINCT n) AS cnt"
    )[0]["cnt"]
    return {
        "total_items": total,
        "item_label": label,
        "classified": classified,
        "unclassified": total - classified,
        "coverage_pct": round(classified / max(total, 1) * 100, 1),
    }


def part_similarity() -> Dict[str, Any]:
    """Detect parts/products that share the same name/product_id but come from
    different source files — i.e. revision or version variants.

    This catches STEP file revisions imported from different uploads that
    represent the same physical part (e.g. Rotor Shaft Key rev A vs rev B).
    """
    rows = _run(
        "MATCH (p) WHERE p:Part OR p:AP242Product "
        "WITH coalesce(p.product_id, p.name) AS groupKey, "
        "     collect({uid: coalesce(p.uid, p.product_id, p.name), "
        "              name: p.name, "
        "              source_file: p.source_file, "
        "              ap_level: p.ap_level, "
        "              labels: labels(p)}) AS variants "
        "WHERE size(variants) > 1 "
        "RETURN groupKey, variants "
        "ORDER BY size(variants) DESC"
    )
    groups = []
    for r in rows:
        groups.append({
            "group_key": r["groupKey"],
            "variant_count": len(r["variants"]),
            "variants": r["variants"],
        })
    return {
        "similar_groups": groups,
        "total_groups": len(groups),
        "total_variants": sum(g["variant_count"] for g in groups),
    }


def semantic_duplicates(threshold: float = 0.95, limit: int = 20) -> Dict[str, Any]:
    """
    Find near-duplicate nodes via OpenSearch more-like-this self-query.

    Uses concurrent requests to stay within reasonable response times.
    """
    import httpx
    import os as _os
    from concurrent.futures import ThreadPoolExecutor, as_completed

    os_url = _os.getenv("VECTORSTORE_HOST", "http://localhost:9200").rstrip("/")
    pairs: list[dict] = []

    def _mlt_query(hit):
        """Run a single MLT query for one hit. Returns list of pair dicts."""
        uid = hit["_source"].get("uid", hit["_id"])
        mlt_body = {
            "size": 3,
            "_source": ["uid", "name"],
            "query": {
                "more_like_this": {
                    "fields": ["text"],
                    "like": [{"_index": "embeddings", "_id": hit["_id"]}],
                    "min_term_freq": 1,
                    "min_doc_freq": 1,
                }
            },
        }
        local_pairs = []
        try:
            r = httpx.post(f"{os_url}/embeddings/_search", json=mlt_body, timeout=8)
            if r.is_success:
                for m in r.json().get("hits", {}).get("hits", []):
                    score = m.get("_score", 0)
                    if m["_id"] != hit["_id"] and score >= threshold:
                        local_pairs.append({
                            "uid_a": uid,
                            "uid_b": m["_source"].get("uid", m["_id"]),
                            "name_a": hit["_source"].get("name", ""),
                            "name_b": m["_source"].get("name", ""),
                            "score": round(score, 4),
                        })
        except Exception:
            pass
        return local_pairs

    try:
        # Grab a sample of embeddings from OpenSearch
        body = {
            "size": min(limit, 100),
            "_source": ["uid", "name", "metadata.item_type"],
            "query": {"match_all": {}},
        }
        resp = httpx.post(f"{os_url}/embeddings/_search", json=body, timeout=10)
        resp.raise_for_status()
        hits = resp.json().get("hits", {}).get("hits", [])

        # Run MLT queries in parallel (up to 10 concurrent workers)
        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = {pool.submit(_mlt_query, h): h for h in hits[:limit]}
            for fut in as_completed(futures):
                pairs.extend(fut.result())
    except Exception as exc:
        logger.warning(f"OpenSearch unavailable for duplicate detection: {exc}")

    # De-duplicate symmetric pairs
    seen = set()
    unique: list[dict] = []
    for p in pairs:
        key = tuple(sorted([p["uid_a"], p["uid_b"]]))
        if key not in seen:
            seen.add(key)
            unique.append(p)

    return {"duplicate_pairs": unique, "count": len(unique)}


def shacl_compliance() -> Dict[str, Any]:
    """Violations grouped by label vs total nodes."""
    violations = _run(
        "MATCH (v:SHACLViolation)-[:VIOLATES]->(n) "
        "WITH labels(n) AS lbls, count(v) AS vcount "
        "UNWIND lbls AS lbl "
        "RETURN lbl AS label, sum(vcount) AS violations "
        "ORDER BY violations DESC"
    )
    # Build adaptive WHERE clause from compliance labels
    where_parts = " OR ".join(f"n:`{lbl}`" for lbl in _COMPLIANCE_LABELS)
    totals = _run(
        f"MATCH (n) WHERE {where_parts} "
        "WITH labels(n) AS lbls, count(n) AS cnt "
        "UNWIND lbls AS lbl "
        "RETURN lbl AS label, sum(cnt) AS total "
        "ORDER BY total DESC"
    )
    total_map = {r["label"]: r["total"] for r in totals}
    rows = []
    for v in violations:
        lbl = v["label"]
        t = total_map.get(lbl, 0)
        rows.append({
            "label": lbl,
            "violations": v["violations"],
            "total_nodes": t,
            "compliance_pct": round((t - v["violations"]) / max(t, 1) * 100, 1),
        })
    return {"by_label": rows, "total_violations": sum(v["violations"] for v in violations)}


# ─── SmartAnalysis per-node pipeline ─────────────────────────────────────────

@dataclass
class SmartAnalysisResult:
    uid: str
    overview: Dict[str, Any] = field(default_factory=dict)
    ontology: Dict[str, Any] = field(default_factory=dict)
    similar: List[Dict[str, Any]] = field(default_factory=list)
    violations: List[Dict[str, Any]] = field(default_factory=list)
    graph: Dict[str, Any] = field(default_factory=dict)


def smart_analysis(uid: str) -> SmartAnalysisResult:
    """
    5-step deep analysis of a single node:
    1. Overview — node properties + labels
    2. Ontology — CLASSIFIED_AS targets
    3. Similar — semantic neighbours (OpenSearch kNN)
    4. Violations — SHACL violations for this node
    5. Graph — 2-hop neighbourhood
    """
    res = SmartAnalysisResult(uid=uid)

    # Step 1 — Overview
    rows = _run(
        "MATCH (n {uid: $uid}) RETURN properties(n) AS props, labels(n) AS labels",
        {"uid": uid},
    )
    if rows:
        res.overview = {"properties": rows[0]["props"], "labels": rows[0]["labels"]}
    else:
        res.overview = {"error": f"Node {uid} not found"}
        return res

    # Step 2 — Ontology classification
    ont_rows = _run(
        "MATCH (n {uid: $uid})-[:CLASSIFIED_AS]->(c) "
        "RETURN c.uri AS uri, c.name AS name, c.ap_level AS ap_level",
        {"uid": uid},
    )
    res.ontology = {"classifications": ont_rows}

    # Step 3 — Similar nodes (2-hop semantic neighbours)
    sim_rows = _run(
        "MATCH (n {uid: $uid})-[r1]-(m)-[r2]-(o) "
        "WHERE o <> n AND o.uid IS NOT NULL "
        "RETURN DISTINCT o.uid AS uid, o.name AS name, "
        "labels(o) AS labels, type(r1) AS rel1, type(r2) AS rel2 "
        "LIMIT 20",
        {"uid": uid},
    )
    res.similar = sim_rows

    # Step 4 — SHACL violations
    viol_rows = _run(
        "MATCH (v:SHACLViolation)-[:VIOLATES]->(n {uid: $uid}) "
        "RETURN v.shape_name AS shape, v.message AS message, v.severity AS severity",
        {"uid": uid},
    )
    res.violations = viol_rows

    # Step 5 — Graph neighbourhood
    graph_rows = _run(
        "MATCH (n {uid: $uid})-[r]-(m) "
        "RETURN n.uid AS source, type(r) AS rel, m.uid AS target, "
        "labels(m) AS target_labels, m.name AS target_name "
        "LIMIT 100",
        {"uid": uid},
    )
    nodes_set = {uid}
    edges = []
    for g in graph_rows:
        t = g.get("target")
        if t:
            nodes_set.add(t)
            edges.append({
                "source": g["source"],
                "target": t,
                "relationship": g["rel"],
            })
    res.graph = {"node_count": len(nodes_set), "edge_count": len(edges), "edges": edges}

    return res
