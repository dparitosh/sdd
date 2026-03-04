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


# ─── Simulation Insights ────────────────────────────────────────────────────


def simulation_run_status() -> Dict[str, Any]:
    """Breakdown of SimulationRun nodes by status and sim_type."""
    total_row = _run("MATCH (sr:SimulationRun) RETURN count(sr) AS cnt")
    total = total_row[0]["cnt"] if total_row else 0

    by_status = _run(
        "MATCH (sr:SimulationRun) "
        "RETURN coalesce(sr.status, 'Unknown') AS status, count(*) AS cnt "
        "ORDER BY cnt DESC"
    )
    by_type = _run(
        "MATCH (sr:SimulationRun) "
        "RETURN coalesce(sr.sim_type, 'Unclassified') AS sim_type, count(*) AS cnt "
        "ORDER BY cnt DESC"
    )
    recent = _run(
        "MATCH (sr:SimulationRun) "
        "RETURN sr.id AS id, coalesce(sr.status,'?') AS status, "
        "       coalesce(sr.sim_type,'?') AS sim_type, "
        "       coalesce(sr.timestamp, sr.start_time, '') AS ts "
        "ORDER BY ts DESC LIMIT 5"
    )
    completed = next((r["cnt"] for r in by_status if r["status"] == "Completed"), 0)
    failed = next((r["cnt"] for r in by_status if r["status"] in ("Failed", "Error")), 0)
    running = next((r["cnt"] for r in by_status if r["status"] == "Running"), 0)
    return {
        "total_runs": total,
        "completed": completed,
        "failed": failed,
        "running": running,
        "success_rate_pct": round(completed / max(total, 1) * 100, 1),
        "by_status": by_status,
        "by_sim_type": by_type,
        "recent_runs": recent,
    }


def simulation_workflow_coverage() -> Dict[str, Any]:
    """WorkflowMethod coverage — steps, linked runs, orphan runs."""
    wf_rows = _run(
        "MATCH (wm:WorkflowMethod) "
        "OPTIONAL MATCH (wm)-[:HAS_STEP]->(te:TaskElement) "
        "WITH wm, count(te) AS steps "
        "OPTIONAL MATCH (sr:SimulationRun)-[:CHOSEN_METHOD]->(wm) "
        "RETURN wm.id AS id, wm.name AS name, wm.sim_type AS sim_type, "
        "       wm.status AS status, steps, count(sr) AS linked_runs "
        "ORDER BY wm.id"
    )
    orphan_row = _run(
        "MATCH (sr:SimulationRun) "
        "WHERE NOT EXISTS { (sr)-[:CHOSEN_METHOD]->(:WorkflowMethod) } "
        "RETURN count(sr) AS cnt"
    )
    orphan_runs = orphan_row[0]["cnt"] if orphan_row else 0
    total_runs_row = _run("MATCH (sr:SimulationRun) RETURN count(sr) AS cnt")
    total_runs = total_runs_row[0]["cnt"] if total_runs_row else 0
    total_steps = sum(r.get("steps", 0) for r in wf_rows)
    return {
        "workflow_count": len(wf_rows),
        "total_task_elements": total_steps,
        "total_runs": total_runs,
        "runs_linked_to_workflow": total_runs - orphan_runs,
        "orphan_runs": orphan_runs,
        "coverage_pct": round((total_runs - orphan_runs) / max(total_runs, 1) * 100, 1),
        "workflows": wf_rows,
    }


def simulation_parameter_health() -> Dict[str, Any]:
    """SimulationParameter constraint coverage and data-type distribution."""
    total_row = _run("MATCH (p:SimulationParameter) RETURN count(p) AS cnt")
    total = total_row[0]["cnt"] if total_row else 0

    with_constraints = _run(
        "MATCH (p:SimulationParameter) "
        "WHERE EXISTS { (p)-[:HAS_CONSTRAINT]->() } "
        "RETURN count(p) AS cnt"
    )
    constrained = with_constraints[0]["cnt"] if with_constraints else 0

    by_type = _run(
        "MATCH (p:SimulationParameter) "
        "RETURN coalesce(p.data_type, 'unknown') AS data_type, count(*) AS cnt "
        "ORDER BY cnt DESC LIMIT 10"
    )
    # Violations: parameters with out-of-range default values (if any validation recorded)
    violation_rows = _run(
        "MATCH (p:SimulationParameter)-[:VIOLATES_CONSTRAINT]->(c) "
        "RETURN p.id AS id, p.name AS name, c.message AS msg LIMIT 20"
    )
    return {
        "total_parameters": total,
        "with_constraints": constrained,
        "without_constraints": total - constrained,
        "constraint_coverage_pct": round(constrained / max(total, 1) * 100, 1),
        "by_data_type": by_type,
        "constraint_violations": violation_rows,
    }


def simulation_dossier_health() -> Dict[str, Any]:
    """SimulationDossier completeness — artifacts, KPIs, evidence categories."""
    total_row = _run("MATCH (sd:SimulationDossier) RETURN count(sd) AS cnt")
    total = total_row[0]["cnt"] if total_row else 0

    dossiers = _run(
        "MATCH (sd:SimulationDossier) "
        "OPTIONAL MATCH (sd)-[:CONTAINS]->(a:SimulationArtifact) "
        "WITH sd, count(a) AS artifact_count "
        "OPTIONAL MATCH (sd)-[:HAS_KPI]->(k) "
        "WITH sd, artifact_count, count(k) AS kpi_count "
        "OPTIONAL MATCH (sd)-[:HAS_EVIDENCE_CATEGORY]->(ec) "
        "RETURN sd.name AS name, coalesce(sd.status,'?') AS status, "
        "       artifact_count, kpi_count, count(ec) AS evidence_categories "
        "ORDER BY sd.name"
    )
    complete = sum(
        1 for d in dossiers
        if d.get("artifact_count", 0) > 0 and d.get("kpi_count", 0) > 0
    )
    artifact_total = sum(d.get("artifact_count", 0) for d in dossiers)
    return {
        "total_dossiers": total,
        "complete_dossiers": complete,
        "incomplete_dossiers": total - complete,
        "completeness_pct": round(complete / max(total, 1) * 100, 1),
        "total_artifacts": artifact_total,
        "dossiers": dossiers,
    }


def simulation_digital_thread() -> Dict[str, Any]:
    """Digital thread traceability: SimulationRun → WorkflowMethod → Requirement."""
    runs_row = _run("MATCH (sr:SimulationRun) RETURN count(sr) AS cnt")
    total_runs = runs_row[0]["cnt"] if runs_row else 0

    with_method_row = _run(
        "MATCH (sr:SimulationRun)-[:CHOSEN_METHOD]->(:WorkflowMethod) "
        "RETURN count(DISTINCT sr) AS cnt"
    )
    with_method = with_method_row[0]["cnt"] if with_method_row else 0

    with_req_row = _run(
        "MATCH (sr:SimulationRun)-[:VALIDATES|VERIFIES|SATISFIES]->(r:Requirement) "
        "RETURN count(DISTINCT sr) AS cnt"
    )
    with_req = with_req_row[0]["cnt"] if with_req_row else 0

    with_dossier_row = _run(
        "MATCH (sd:SimulationDossier)-[:CONTAINS]->(sr:SimulationRun) "
        "RETURN count(DISTINCT sr) AS cnt"
    )
    with_dossier = with_dossier_row[0]["cnt"] if with_dossier_row else 0

    ap_cross_row = _run(
        "MATCH (a)-[r]->(b) "
        "WHERE (a.ap_level IS NOT NULL OR b.ap_level IS NOT NULL) "
        "  AND ANY(l IN labels(a) WHERE l IN ['SimulationRun','SimulationDossier','WorkflowMethod']) "
        "RETURN count(r) AS cnt"
    )
    ap_cross = ap_cross_row[0]["cnt"] if ap_cross_row else 0

    oslc_row = _run(
        "MATCH (n) WHERE n.source = 'oslc' OR ANY(l IN labels(n) WHERE l STARTS WITH 'Oslc') "
        "RETURN count(n) AS cnt"
    )
    oslc_nodes = oslc_row[0]["cnt"] if oslc_row else 0

    thread_score = round(
        (
            (with_method / max(total_runs, 1)) * 0.4
            + (with_dossier / max(total_runs, 1)) * 0.3
            + (with_req / max(total_runs, 1)) * 0.3
        ) * 100,
        1,
    )
    return {
        "total_runs": total_runs,
        "with_workflow_method": with_method,
        "with_requirement_link": with_req,
        "within_dossier": with_dossier,
        "ap_cross_standard_edges": ap_cross,
        "oslc_nodes": oslc_nodes,
        "thread_completeness_pct": thread_score,
    }


# ─── AI Narrative (LLM-powered health summary) ───────────────────────────────

def ai_narrative(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call Ollama to generate a natural-language health summary of all insight metrics.

    Returns a dict with keys:
      overall_score  — 0-100 aggregate health
      headline       — one-sentence LLM verdict
      summary        — 2-3 sentence narrative
      priority_issues — list[{severity, title, detail, metric_key}]
      recommendations — list[{action, impact, effort}]
      confidence     — "high" | "medium" | "low"
      generated_at   — Unix timestamp
    """
    import json as _json
    import os as _os
    import time as _time

    import requests as _requests

    ollama_url = _os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    chat_model = _os.getenv("OLLAMA_CHAT_MODEL", "llama3:latest")

    # ── Compute scalar health score from key percentage metrics ──
    scores: list[float] = []
    _pct_keys = [
        ("bom-completeness",            "completeness_pct"),
        ("traceability-gaps",           "coverage_pct"),
        ("classification-coverage",     "coverage_pct"),
        ("simulation-run-status",       "success_rate_pct"),
        ("simulation-workflow-coverage","coverage_pct"),
        ("simulation-parameter-health", "constraint_coverage_pct"),
        ("simulation-dossier-health",   "completeness_pct"),
        ("simulation-digital-thread",   "thread_completeness_pct"),
    ]
    for mkey, vkey in _pct_keys:
        val = snapshot.get(mkey, {}).get(vkey)
        if val is not None:
            scores.append(float(val))
    # SHACL: invert violations (0 = 100 %, each violation drops 5 pts)
    shacl_viol = snapshot.get("shacl-compliance", {}).get("total_violations")
    if shacl_viol is not None:
        scores.append(max(0.0, 100.0 - float(shacl_viol) * 5))

    overall_score = int(sum(scores) / len(scores)) if scores else 0

    # ── Build compact digest for LLM (strip large arrays) ──
    digest: Dict[str, Any] = {}
    for k, v in snapshot.items():
        if isinstance(v, dict):
            digest[k] = {kk: vv for kk, vv in v.items() if not isinstance(vv, (list, dict))}

    prompt = (
        "You are an AI engineering analyst for an MBSE / Simulation Data Dossier (SDD) "
        "knowledge graph system. Analyze these live metrics and produce a structured JSON "
        "assessment for engineers.\n\n"
        f"METRICS SNAPSHOT:\n{_json.dumps(digest, indent=2)}\n\n"
        "Respond ONLY with valid JSON (no markdown code fences, no extra text) "
        "using exactly this schema:\n"
        "{\n"
        '  "headline": "<one verdict sentence, max 12 words>",\n'
        '  "summary": "<2-3 sentence engineering narrative>",\n'
        '  "priority_issues": [\n'
        '    {"severity": "critical|warning|healthy", "title": "...", '
        '"detail": "...", "metric_key": "..."}\n'
        "  ],\n"
        '  "recommendations": [\n'
        '    {"action": "...", "impact": "high|medium|low", "effort": "high|medium|low"}\n'
        "  ],\n"
        '  "confidence": "high|medium|low"\n'
        "}"
    )

    _fallback = {
        "headline": "AI analysis offline — raw metrics displayed",
        "summary": (
            "Ollama is not responding. "
            "All metrics below are sourced directly from the knowledge graph without LLM synthesis. "
            "Start Ollama and click Re-analyze for AI-powered insights."
        ),
        "priority_issues": [],
        "recommendations": [],
        "confidence": "low",
    }

    try:
        resp = _requests.post(
            f"{ollama_url.rstrip('/')}/api/chat",
            json={
                "model": chat_model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "keep_alive": "10m",
            },
            timeout=120,
        )
        resp.raise_for_status()
        content = resp.json().get("message", {}).get("content", "").strip()
        # Strip markdown fences if the model wraps in ```json ... ```
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:]).rstrip("`").strip()
        parsed: Dict[str, Any] = _json.loads(content)
    except _json.JSONDecodeError as exc:
        logger.warning(f"AI narrative: Ollama returned non-JSON — {exc}")
        parsed = {**_fallback, "confidence": "low",
                  "headline": "AI returned unexpected format — check Ollama logs"}
    except Exception as exc:
        logger.warning(f"AI narrative: Ollama unavailable — {exc}")
        parsed = _fallback.copy()

    parsed["overall_score"] = overall_score
    parsed["generated_at"] = _time.time()
    return parsed


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
