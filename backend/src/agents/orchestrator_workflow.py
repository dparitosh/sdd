"""
Multi-Agent Orchestration Workflow using LangGraph
Coordinates specialized agents (MBSE, PLM, Simulation, Compliance) for complex engineering tasks

Now also supports Azure AI Baseline Orchestrator pattern (vendor-neutral).
"""

import asyncio
import operator
import re
from typing import Annotated, Literal, Sequence, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.graph import END, StateGraph
from loguru import logger

from ..agentic import (
    BaselineOrchestrator,
    KeywordPlanner,
    SimpleReflector,
    SingleToolAgent,
)
from ..agentic.adapters import MBSEToolsAdapter
from .agent_tools import Neo4jTool
from .langgraph_agent import MBSETools
from .ontology_agent import OntologyAgent
from .plm_agent import PLMAgent
from .semantic_agent import SemanticAgent
from .simulation_agent import SimulationAgent
from .step_agent import StepAgent


# ============================================================================
# MBSE AI SYSTEM PROMPT  — authoritative persona embedded in all agent replies
# ============================================================================

MBSE_SYSTEM_PROMPT = (
    "You are an ISO 10303 MBSE Knowledge Graph AI for MoSSEC (Model-Based SSE for "
    "Space & Complex Systems). Your scope:\n"
    "  AP239 PLCS  — programme activities, work orders, product instances\n"
    "  AP242 MMB3D — parts, assemblies, BOM, materials, CAD geometry, product definitions\n"
    "  AP243 SDD   — simulation dossiers, runs, artifacts, evidence categories, KPIs, "
    "workflow methods\n"
    "  Digital Thread — Requirement → Part → SimulationDossier → SimulationRun → "
    "EvidenceCategory\n"
    "  Requirement Traceability — SATISFIES/VERIFIED_BY/TRACED_TO/ALLOCATED_TO chains\n"
    "  OSLC lifecycle links — cross-tool integration\n"
    "Answer style: identify node labels, show relationship chains, cite UIDs/statuses, "
    "flag missing links, cross-reference AP standards."
)


# ============================================================================
# STATE DEFINITION
# ============================================================================


class EngineeringState(TypedDict):
    """
    Shared state across all specialized agents
    Enables coordination and information flow between agents
    """

    # Input
    user_query: str
    task_type: Literal[
        "traceability", "impact_analysis", "requirement_check", "bom_sync",
        "knowledge_query",
        "step_ingest", "step_query",
        "ontology_ingest", "ontology_query",
        "plm_ingest", "plm_query",
        "shacl_validate", "shacl_report",
        "semantic_search", "semantic_insight",
        "ont_classify",
        "export_rdf", "export_csv",
        "kg_expand",
        # ── Workflow / AP243 orchestration ─────────────────────────────────
        "workflow_execute",    # Execute a named WorkflowMethod (AP243 action_method)
        "workflow_validate",   # Validate parameters against AP243 constraints
        "workflow_query",      # List/search WorkflowMethod nodes
        # ── Digital Thread ─────────────────────────────────────────────────
        "digital_thread_trace",  # AP239 Activity → AP242 BOM → AP243 SDD chain
        "oslc_query",            # OSLC lifecycle resource query & linking
        "ap_standard_query",     # Direct AP239/AP242/AP243 node query
        "mossec_overview",       # Full MoSSEC knowledge graph summary
    ]

    # MBSE Agent outputs
    requirement_id: str | None
    artifact_details: dict | None
    traceability_data: dict | None

    # PLM Agent outputs
    affected_parts: list[dict]
    bom_data: dict | None
    change_impact: dict | None

    # Simulation Agent outputs
    simulation_parameters: dict | None
    validation_results: dict | None
    simulation_summary: dict | None

    # Compliance Agent outputs
    compliance_status: dict | None
    violations: list[dict]
    recommendations: list[str]

    # ── New: Workflow / Digital Thread Agent outputs ────────────────────────
    workflow_data: dict | None      # WorkflowMethod + steps + resources
    digital_thread: dict | None     # AP239→AP242→AP243 thread trace
    ap_standard_data: dict | None   # AP standard level query results

    # Shared
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next_action: str
    error: str | None


# ============================================================================
# AGENT NODE FUNCTIONS
# ============================================================================


async def mbse_agent_node(state: EngineeringState) -> dict:
    """
    MBSE Agent: Query requirements, artifacts, and traceability.

    1. Detect intent from the natural-language query.
    2. Run targeted Cypher queries against Neo4j (no HTTP loopback).
    3. Synthesize a markdown reply via the configured LLM (Ollama / OpenAI).
    """
    logger.info("🔍 MBSE Agent: Analysing query intent and searching knowledge graph")

    user_query = state["user_query"]
    q_lower = user_query.lower()

    # ── Early-exit: specialized task types bypass MBSE KG logic entirely ──────
    _task = state.get("task_type", "knowledge_query")
    if _task in ("step_ingest", "step_query"):
        logger.info("MBSE Agent: delegating STEP task → step_agent")
        return {"next_action": "step_agent"}
    if _task in ("ontology_ingest", "ontology_query"):
        logger.info("MBSE Agent: delegating ontology task → ontology_agent")
        return {"next_action": "ontology_agent"}
    if _task in ("plm_ingest", "plm_query", "bom_sync"):
        logger.info("MBSE Agent: delegating PLM task → plm_agent")
        return {"next_action": "plm_agent"}
    if _task in ("semantic_search", "semantic_insight"):
        logger.info("MBSE Agent: delegating semantic task → semantic_agent")
        return {"next_action": "semantic_agent"}
    if _task in ("shacl_validate", "shacl_report"):
        logger.info("MBSE Agent: delegating SHACL task → shacl_agent")
        return {"next_action": "shacl_agent"}
    if _task == "ont_classify":
        logger.info("MBSE Agent: delegating classification → ontology_agent")
        return {"next_action": "ontology_agent"}
    if _task in ("export_rdf", "export_csv"):
        logger.info("MBSE Agent: delegating export task → export_handler")
        return {"next_action": "export_handler"}
    if _task == "kg_expand":
        logger.info("MBSE Agent: delegating KG expansion → semantic_agent")
        return {"next_action": "semantic_agent"}
    if _task in ("workflow_execute", "workflow_validate", "workflow_query"):
        logger.info("MBSE Agent: delegating workflow task → workflow_agent")
        return {"next_action": "workflow_agent"}
    if _task in ("digital_thread_trace", "oslc_query", "ap_standard_query", "mossec_overview"):
        logger.info("MBSE Agent: delegating digital thread / AP standard task → digital_thread_agent")
        return {"next_action": "digital_thread_agent"}
    # ─────────────────────────────────────────────────────────────────────────

    try:
        neo4j = Neo4jTool()

        # ------------------------------------------------------------------
        # 0. Extract page context injected by the frontend chatbot
        #    Format: "[Context: ...]\n[Page: <PageLabel>]\n<actual query>"
        # ------------------------------------------------------------------
        import re as _re

        # Strip [Context: ...] prefix lines and capture [Page: ...]
        page_label = ""
        actual_query = user_query
        _ctx_match = _re.search(r"\[Context:[^\]]*\]", user_query)
        _page_match = _re.search(r"\[Page:\s*([^\]]+)\]", user_query)
        if _page_match:
            page_label = _page_match.group(1).strip()
        # Remove all [Context:...] and [Page:...] prefix blocks from the actual query
        actual_query = _re.sub(r"\[Context:[^\]]*\]\s*", "", actual_query)
        actual_query = _re.sub(r"\[Page:[^\]]*\]\s*", "", actual_query).strip()
        q_lower_clean = actual_query.lower()

        # Page→keyword boost map: ensures relevant sections always run for page context
        _PAGE_BOOST: dict[str, list[str]] = {
            "Requirements":        ["requirement"],
            "AP239 Requirements":  ["requirement", "oslc", "ap239"],
            "Traceability Matrix": ["requirement", "traceability", "trace"],
            "Parts (AP242)":       ["part", "ap242", "bom", "product model", "ap242"],
            "Graph Explorer":      ["graph overview", "mossec", "knowledge graph"],
            "MoSSEC Dashboard":    ["mossec", "simulation", "ap243"],
            "Simulation Models":   ["simulation", "ap243", "analysis model", "model instance"],
            "Simulation Runs":     ["simulation", "run"],
            "Simulation Results":  ["simulation", "result"],
            "Dossier Detail":      ["simulation", "dossier", "evidence"],
            "PLM Integration":     ["plm", "part"],
            "Ontology Manager":    ["ontolog", "owl"],
            "OSLC Browser":        ["oslc"],
            "SHACL Validator":     ["shacl"],
            "Data Import":         ["import"],
            "Product Specs":       ["product", "spec"],
            "Quality Portal":      ["quality"],
            # Graph Explorer sub-views surfaced via chatbot hints
            "Digital Thread":      ["digital thread", "thread", "ap239", "chain", "dossier", "evidence"],
            "AP242 Product":       ["ap242", "part", "bom", "product model", "assembly"],
            "AP243 Simulation":    ["ap243", "simulation", "dossier", "mossec"],
        }
        # Build an augmented query string that merges page boosts
        _boost_terms = _PAGE_BOOST.get(page_label, [])
        q_lower = q_lower_clean
        # Boost: if none of the boost terms appear in the query, inject them so
        # the intent routing sections below fire without requiring exact keywords.
        for _t in _boost_terms:
            if _t not in q_lower:
                q_lower = q_lower + " " + _t

        logger.info(f"MBSE Agent: page='{page_label}' | effective_q='{q_lower[:120]}'")

        # ------------------------------------------------------------------
        # 1. Intent-based Cypher routing
        # ------------------------------------------------------------------
        data_sections: list[str] = []      # collects formatted result blocks
        traceability_data = None

        def _run(cypher: str, params: dict | None = None, limit: int = 50) -> list[dict]:
            return neo4j.search_artifacts(cypher, params=params or {}, limit=limit)

        # Requirements
        if any(k in q_lower for k in ("requirement", " req ")):
            rows = _run(
                "MATCH (n:Requirement) "
                "WHERE n.id IS NOT NULL AND NOT n.id STARTS WITH '_' "
                "RETURN coalesce(n.id, n.uid, 'N/A') AS uid, n.name AS name, "
                "       coalesce(n.status,'?') AS status, "
                "       coalesce(n.priority,'?') AS priority "
                "ORDER BY uid LIMIT $limit",
                limit=50,
            )
            if rows:
                lines = "\n".join(
                    f"- **{r.get('uid','?')}** — {r.get('name','?')}  "
                    f"(status: {r.get('status','?')}, priority: {r.get('priority','?')})"
                    for r in rows
                )
                data_sections.append(f"### Requirements ({len(rows)} found)\n{lines}")
            # Traceability links for real requirements only
            trace_rows = _run(
                "MATCH (r:Requirement)-[rel]->(t) "
                "WHERE r.id IS NOT NULL AND NOT r.id STARTS WITH '_' "
                "RETURN coalesce(r.id, r.uid) AS req_uid, r.name AS req_name, "
                "       type(rel) AS rel_type, "
                "       coalesce(t.id, t.uid, t.name) AS target_uid, "
                "       coalesce(t.name, t.title) AS target_name, "
                "       labels(t)[0] AS target_label "
                "LIMIT $limit",
                limit=100,
            )
            if trace_rows:
                traceability_data = {"rows": trace_rows}
                data_sections.append(
                    f"### Traceability links ({len(trace_rows)} found)\n"
                    + "\n".join(
                        f"- {r.get('req_uid')} -> [{r.get('rel_type')}] -> "
                        f"{r.get('target_name','?')} ({r.get('target_label','?')})"
                        for r in trace_rows[:20]
                    )
                    + ("\n*(showing first 20)*" if len(trace_rows) > 20 else "")
                )

        # Ontologies
        if any(k in q_lower for k in ("ontolog", "owl")):
            rows = _run(
                "MATCH (n:Ontology) "
                "RETURN coalesce(n.name, n.title, split(n.uri,'#')[0], 'Unknown') AS name, "
                "       coalesce(n.uri, n.url, n.source_url, '') AS url, "
                "       coalesce(n.ap_standard, n.ap_level, '') AS standard "
                "ORDER BY name LIMIT $limit",
                limit=30,
            )
            if rows:
                lines = "\n".join(
                    f"- **{r.get('name','?')}**"
                    + (f" ({r['standard']})" if r.get("standard") else "")
                    + (f"  [{r['url']}]({r['url']})" if r.get("url") else "")
                    for r in rows
                )
                data_sections.append(f"### Loaded Ontologies ({len(rows)} found)\n{lines}")
            # Also count OntologyClass / OntologyProperty
            cls_rows = _run(
                "MATCH (n) WHERE 'OntologyClass' IN labels(n) OR 'ExternalOwlClass' IN labels(n) "
                "RETURN labels(n)[0] AS label, count(*) AS cnt",
            )
            if cls_rows:
                summary = ", ".join(f"{r.get('label')}: {r.get('cnt')}" for r in cls_rows)
                data_sections.append(f"### Ontology class counts\n{summary}")

        # OSLC
        if "oslc" in q_lower:
            rows = _run(
                "MATCH (n) "
                "WHERE n.source = 'oslc' OR 'OslcRequirement' IN labels(n) "
                "   OR n.oslc_domain IS NOT NULL "
                "RETURN labels(n)[0] AS label, n.uid AS uid, n.name AS name "
                "LIMIT $limit",
                limit=30,
            )
            if not rows:
                # fallback: requirements that have MAPS_TO_OSLC edges
                rows = _run(
                    "MATCH (r:Requirement)-[:MAPS_TO_OSLC]->(t) "
                    "WHERE r.id IS NOT NULL AND NOT r.id STARTS WITH '_' "
                    "RETURN coalesce(r.id, r.uid) AS uid, r.name AS name, t.name AS oslc_target "
                    "LIMIT $limit",
                    limit=30,
                )
            if rows:
                lines = "\n".join(
                    f"- **{r.get('uid','?')}** — {r.get('name','?')}"
                    for r in rows
                )
                data_sections.append(f"### OSLC Resources ({len(rows)} found)\n{lines}")
            else:
                data_sections.append(
                    "### OSLC Resources\nNo OSLC-tagged nodes found. "
                    "Use the OSLC ingestion endpoint to import lifecycle data."
                )

        # ── Simulation Dossiers, Runs, Artifacts — full AP243 SDD breakdown ────────
        if any(k in q_lower for k in ("simulation", "dossier", "run", "analysis model", "ap243", "mossec")):
            dossier_rows = _run(
                "MATCH (d:SimulationDossier) "
                "OPTIONAL MATCH (d)-[:HAS_SIMULATION_RUN]->(r:SimulationRun) "
                "OPTIONAL MATCH (r)-[:CONTAINS_ARTIFACT]->(a:SimulationArtifact) "
                "RETURN coalesce(d.uid, d.id,'?') AS uid, coalesce(d.name,'?') AS name, "
                "       coalesce(d.status,'?') AS status, "
                "       count(DISTINCT r) AS run_count, count(DISTINCT a) AS artifact_count "
                "ORDER BY d.uid LIMIT $limit",
                limit=25,
            )
            if dossier_rows:
                dlines = "\n".join(
                    f"- **{r.get('name','?')}** `{r.get('uid','?')}` "
                    f"| status: {r.get('status','?')} "
                    f"| runs: {r.get('run_count',0)} | artifacts: {r.get('artifact_count',0)}"
                    for r in dossier_rows
                )
                data_sections.append(f"### Simulation Dossiers (AP243 SDD) — {len(dossier_rows)} found\n{dlines}")
            # AP243 Model & Workflow nodes
            ap243_model_rows = _run(
                "MATCH (n) WHERE ANY(l IN labels(n) WHERE "
                "  l IN ['ModelInstance','ModelType','WorkflowMethod','TaskElement',"
                "         'ParameterStudy','AnalysisModel','KPI','ValidationRecord']) "
                "RETURN labels(n)[0] AS label, coalesce(n.uid, n.id,'') AS uid, "
                "       coalesce(n.name,'?') AS name "
                "ORDER BY label, uid LIMIT $limit",
                limit=30,
            )
            if ap243_model_rows:
                by_lbl: dict[str, list] = {}
                for r in ap243_model_rows:
                    by_lbl.setdefault(r.get("label", "?"), []).append(r)
                model_sections = []
                for lbl, items in by_lbl.items():
                    model_sections.append(
                        f"**:{lbl}** ({len(items)}): "
                        + ", ".join(f"`{r.get('name','?')}`" for r in items[:5])
                        + (" …" if len(items) > 5 else "")
                    )
                data_sections.append(
                    f"### AP243 Model & Workflow Nodes ({len(ap243_model_rows)} found)\n"
                    + "\n".join(model_sections)
                )

        # ── Digital Thread — end-to-end engineering lifecycle chain ────────────
        if any(k in q_lower for k in ("digital thread", "thread trace", "end-to-end", "lifecycle chain", "thread chain")):
            thread_rows = _run(
                "MATCH (req:Requirement)-[:SATISFIED_BY_PART|ALLOCATED_TO|TRACED_TO]->(p) "
                "MATCH (d:SimulationDossier)-[:HAS_SIMULATION_RUN]->(run:SimulationRun) "
                "OPTIONAL MATCH (run)-[:CONTAINS_ARTIFACT]->(art:SimulationArtifact) "
                "OPTIONAL MATCH (art)-[:EVIDENCE_FOR]->(ev:EvidenceCategory) "
                "WHERE req.id IS NOT NULL AND NOT req.id STARTS WITH '_' "
                "RETURN coalesce(req.id, req.uid,'?') AS req_uid, req.name AS req_name, "
                "       coalesce(p.id, p.name,'?') AS part_uid, p.name AS part_name, "
                "       coalesce(d.uid,'?') AS dossier_uid, d.name AS dossier_name, "
                "       coalesce(run.uid,'?') AS run_uid, "
                "       coalesce(ev.name,'') AS evidence_name "
                "LIMIT $limit",
                limit=30,
            )
            if thread_rows:
                t_lines = "\n".join(
                    f"- REQ `{r.get('req_uid','?')}` ({r.get('req_name','?')}) "
                    f"→ Part `{r.get('part_uid','?')}` "
                    f"→ Dossier `{r.get('dossier_uid','?')}` "
                    f"→ Run `{r.get('run_uid','?')}`"
                    + (f" → Evidence: {r.get('evidence_name')!r}" if r.get("evidence_name") else "")
                    for r in thread_rows
                )
                data_sections.append(f"### Digital Thread — Req→Part→Dossier→Run ({len(thread_rows)} chains)\n{t_lines}")
            else:
                alt_rows = _run(
                    "MATCH (a)-[r:IMPLEMENTS|VALIDATES_USING|DERIVED_FROM|SATISFIES|ALLOCATED_TO|HAS_SIMULATION_RUN]->(b) "
                    "RETURN labels(a)[0] AS from_lbl, coalesce(a.name,a.uid,'?') AS from_name, "
                    "       type(r) AS rel, labels(b)[0] AS to_lbl, coalesce(b.name,b.uid,'?') AS to_name "
                    "ORDER BY rel LIMIT $limit",
                    limit=30,
                )
                if alt_rows:
                    t_lines = "\n".join(
                        f"- [{r.get('from_lbl')}] **{r.get('from_name','?')}** "
                        f"—[{r.get('rel')}]→ [{r.get('to_lbl')}] **{r.get('to_name','?')}**"
                        for r in alt_rows
                    )
                    data_sections.append(f"### Digital Thread Relationships ({len(alt_rows)} edges)\n{t_lines}")
                else:
                    data_sections.append(
                        "### Digital Thread\n"
                        "No end-to-end chains found yet. Run `link_ap_hierarchy.py` and "
                        "`run_migration_v4.py` to build the digital thread.\n\n"
                        "Expected chain: `Requirement -[:SATISFIED_BY_PART]→ Part "
                        "-[:VALIDATES_USING]→ SimulationDossier "
                        "-[:HAS_SIMULATION_RUN]→ SimulationRun "
                        "-[:CONTAINS_ARTIFACT]→ SimulationArtifact "
                        "-[:EVIDENCE_FOR]→ EvidenceCategory`"
                    )

        # ── Traceability with Dossier — req → design element → simulation → evidence ─
        if any(k in q_lower for k in ("traceability", "traceabl", "trace to dossier", "requirement trace", "verif")):
            trace_rows = _run(
                "MATCH (req:Requirement) "
                "WHERE req.id IS NOT NULL AND NOT req.id STARTS WITH '_' "
                "OPTIONAL MATCH (req)-[:SATISFIED_BY_PART|ALLOCATED_TO]->(p) "
                "OPTIONAL MATCH (p)-[:VALIDATES_USING|VERIFIED_BY]->(d:SimulationDossier) "
                "OPTIONAL MATCH (d)-[:HAS_SIMULATION_RUN]->(run:SimulationRun) "
                "OPTIONAL MATCH (run)-[:CONTAINS_ARTIFACT]->(art:SimulationArtifact) "
                "OPTIONAL MATCH (art)-[:EVIDENCE_FOR]->(ev:EvidenceCategory) "
                "RETURN coalesce(req.id, req.uid,'?') AS req_uid, req.name AS req_name, "
                "       coalesce(req.status,'?') AS req_status, "
                "       coalesce(p.name, p.id,'') AS design_element, "
                "       coalesce(d.uid,'') AS dossier_uid, d.name AS dossier_name, "
                "       coalesce(run.uid,'') AS run_uid, "
                "       coalesce(ev.name,'') AS evidence_name, "
                "       CASE WHEN d IS NOT NULL THEN 'verified' ELSE 'unverified' END AS trace_status "
                "ORDER BY trace_status, req.id LIMIT $limit",
                limit=40,
            )
            if trace_rows:
                verified   = [r for r in trace_rows if r.get("trace_status") == "verified"]
                unverified = [r for r in trace_rows if r.get("trace_status") != "verified"]
                if verified:
                    v_lines = "\n".join(
                        f"- ✅ `{r.get('req_uid','?')}` {r.get('req_name','?')}"
                        + (f" → {r.get('design_element')}" if r.get("design_element") else "")
                        + (f" → Dossier `{r.get('dossier_uid')}`" if r.get("dossier_uid") else "")
                        + (f" → Evidence: {r.get('evidence_name')!r}" if r.get("evidence_name") else "")
                        for r in verified[:20]
                    )
                    data_sections.append(f"### Requirements Traced via Dossier ({len(verified)} verified)\n{v_lines}")
                if unverified:
                    u_lines = "\n".join(
                        f"- ❌ `{r.get('req_uid','?')}` {r.get('req_name','?')} *(no dossier link)*"
                        for r in unverified[:15]
                    )
                    data_sections.append(f"### Untraced Requirements ({len(unverified)} without dossier)\n{u_lines}")

        # ── Evidence Categories — EvidenceCategory nodes linked to simulation chain ─
        if any(k in q_lower for k in ("evidence", "evidencecategory", "evidence category")):
            ev_rows = _run(
                "MATCH (ev:EvidenceCategory) "
                "OPTIONAL MATCH (a:SimulationArtifact)-[:EVIDENCE_FOR]->(ev) "
                "OPTIONAL MATCH (a)<-[:CONTAINS_ARTIFACT]-(run:SimulationRun) "
                "OPTIONAL MATCH (run)<-[:HAS_SIMULATION_RUN]-(d:SimulationDossier) "
                "RETURN coalesce(ev.uid, ev.id,'?') AS uid, coalesce(ev.name,'?') AS name, "
                "       coalesce(ev.category_type,'?') AS category_type, "
                "       count(DISTINCT a) AS artifact_count, "
                "       collect(DISTINCT coalesce(d.name, d.uid,'?'))[0..3] AS dossiers "
                "ORDER BY ev.name LIMIT $limit",
                limit=20,
            )
            if ev_rows:
                e_lines = "\n".join(
                    f"- **{r.get('name','?')}** `{r.get('uid','?')}` "
                    f"(type: {r.get('category_type','?')}, artifacts: {r.get('artifact_count',0)})"
                    + (
                        " | dossiers: "
                        + ", ".join(str(d) for d in (r.get("dossiers") or []) if d and d != "?")[:60]
                        if r.get("dossiers")
                        else ""
                    )
                    for r in ev_rows
                )
                data_sections.append(f"### Evidence Categories ({len(ev_rows)} found)\n{e_lines}")
            else:
                data_sections.append(
                    "### Evidence Categories\n"
                    "No EvidenceCategory nodes found. Run `ingest_sdd_data.py` to create "
                    "SimulationDossier, SimulationArtifact, and EvidenceCategory nodes."
                )

        # ── AP242 Product Model — complete product graph (BOM, materials, node counts) ─
        if any(k in q_lower for k in ("ap242", "product model", "bom hierarchy", "bill of material", "product graph", "assembly tree")):
            bom_rows = _run(
                "MATCH (asm:Assembly)-[:ASSEMBLES_WITH]->(p) "
                "WHERE 'Part' IN labels(p) OR 'AP242Product' IN labels(p) "
                "RETURN asm.name AS assembly, coalesce(p.name,'?') AS part_name, "
                "       coalesce(p.part_number, p.id,'') AS pn "
                "ORDER BY asm.name, p.name LIMIT $limit",
                limit=40,
            )
            if bom_rows:
                bom_by_asm: dict[str, list] = {}
                for r in bom_rows:
                    bom_by_asm.setdefault(r.get("assembly", "?"), []).append(r)
                bom_lines = []
                for asm, children in bom_by_asm.items():
                    child_list = ", ".join(
                        f"`{r.get('part_name','?')}`" + (f" ({r.get('pn')})" if r.get("pn") else "")
                        for r in children[:6]
                    ) + (" …" if len(children) > 6 else "")
                    bom_lines.append(f"- **{asm}** → {child_list}")
                data_sections.append(
                    f"### AP242 BOM Hierarchy ({len(bom_rows)} part-links)\n" + "\n".join(bom_lines)
                )
            mat_rows = _run(
                "MATCH (p)-[:USES_MATERIAL]->(m:Material) "
                "WHERE 'Part' IN labels(p) OR 'AP242Product' IN labels(p) "
                "RETURN p.name AS part_name, m.name AS material, "
                "       coalesce(m.material_type,'?') AS mat_type "
                "ORDER BY p.name LIMIT $limit",
                limit=20,
            )
            if mat_rows:
                m_lines = "\n".join(
                    f"- **{r.get('part_name','?')}** uses {r.get('material','?')} ({r.get('mat_type','?')})"
                    for r in mat_rows
                )
                data_sections.append(f"### AP242 Material Assignments ({len(mat_rows)} links)\n{m_lines}")
            ap242_stats = _run(
                "MATCH (n) WHERE 'Part' IN labels(n) OR 'Assembly' IN labels(n) "
                "   OR 'Material' IN labels(n) OR 'AP242Product' IN labels(n) "
                "   OR 'PartVersion' IN labels(n) OR 'GeometricModel' IN labels(n) "
                "RETURN labels(n)[0] AS label, count(n) AS cnt ORDER BY cnt DESC LIMIT 10",
                limit=10,
            )
            if ap242_stats:
                stat_lines = "  |  ".join(
                    f"**:{r.get('label','?')}**: {r.get('cnt'):,}" for r in ap242_stats
                )
                data_sections.append(f"### AP242 Product Model Node Counts\n{stat_lines}")

        # PLM / connectors
        if any(k in q_lower for k in ("plm", "connector", "teamcenter", "windchill", "part")):
            rows = _run(
                "MATCH (n) WHERE 'Part' IN labels(n) OR n.plm_system IS NOT NULL "
                "RETURN coalesce(n.id, n.uid, n.part_number, 'N/A') AS id, "
                "       n.name AS name, coalesce(n.part_number,'') AS part_number, "
                "       coalesce(n.status,'?') AS status, "
                "       coalesce(n.description,'') AS description, "
                "       coalesce(n.ap_level,'') AS ap_level "
                "LIMIT $limit",
                limit=20,
            )
            if rows:
                lines = "\n".join(
                    f"- **{r.get('name','?')}** `{r.get('id','?')}`"
                    + (f" | PN: {r['part_number']}" if r.get('part_number') else "")
                    + (f" | {r['status']}" if r.get('status') and r['status'] != '?' else "")
                    + (f" | {r['ap_level']}" if r.get('ap_level') else "")
                    + (f"\n  _{r['description']}_" if r.get('description') else "")
                    for r in rows
                )
                # Fetch related nodes for each part (version, material, assembly, geometry)
                if rows:
                    part_id = rows[0].get('id')
                    rel_rows = _run(
                        "MATCH (n)-[r]-(m) WHERE coalesce(n.id, n.uid, n.part_number) = $pid "
                        "RETURN type(r) AS rel, labels(m)[0] AS target_label, "
                        "       m.name AS target_name, "
                        "       coalesce(m.version, m.status, m.specification, m.code, '') AS detail, "
                        "       startNode(r) = n AS outgoing "
                        "LIMIT 20",
                        params={"pid": part_id},
                    )
                    if rel_rows:
                        rel_lines = "\n".join(
                            f"  {'-->' if r.get('outgoing') else '<--'} [{r.get('rel')}] "
                            f"{r.get('target_name','?')} ({r.get('target_label','?')})"
                            + (f" — {r['detail']}" if r.get('detail') else "")
                            for r in rel_rows
                        )
                        lines += f"\n\n**Relationships:**\n{rel_lines}"
                data_sections.append(f"### PLM Parts / Connectors ({len(rows)} found)\n{lines}")
            else:
                data_sections.append(
                    "### PLM Connectors\nNo PLM parts found in the graph. "
                    "Configure Teamcenter or Windchill connectors via `/api/plm`."
                )

        # Impact analysis — named entity search
        if any(k in q_lower for k in ("impact", "change", "affect", "propagat")):
            # Extract the subject — words after "impact of" / "change to" / "affect"
            subject_match = re.search(
                r'(?:impact of|change(?:d)? (?:to|in)|affect(?:ing)?|propagat\w*)\s+["\']?(.+?)["\']?$',
                q_lower,
            )
            subject = subject_match.group(1).strip() if subject_match else user_query
            rows = _run(
                "MATCH (n)-[r]-(m) "
                "WHERE toLower(n.name) CONTAINS toLower($q) "
                "   OR toLower(coalesce(n.uid,'')) CONTAINS toLower($q) "
                "WITH n.name AS src_name, labels(n)[0] AS src_label, "
                "     type(r) AS rel, m.name AS tgt_name, labels(m)[0] AS tgt_label, "
                "     count(*) AS edge_copies "
                "RETURN src_name, src_label, rel, tgt_name, tgt_label, edge_copies "
                "ORDER BY edge_copies DESC, rel "
                "LIMIT $limit",
                params={"q": subject},
                limit=30,
            )
            if rows:
                lines = "\n".join(
                    f"- **{r.get('src_name','?')}** `{r.get('rel')}` → "
                    f"**{r.get('tgt_name','?')}** ({r.get('tgt_label','?')})"
                    + (f" ×{r['edge_copies']}" if r.get("edge_copies", 1) > 1 else "")
                    for r in rows
                )
                data_sections.append(f"### Impact graph for '{subject}' ({len(rows)} edges)\n{lines}")

        # Unlinked / missing traceability
        if any(k in q_lower for k in ("unlink", "missing", "no trace", "without trace", "no link")):
            rows = _run(
                "MATCH (r:Requirement) "
                "WHERE NOT (r)-[]->() AND r.id IS NOT NULL AND NOT r.id STARTS WITH '_' "
                "RETURN coalesce(r.id, r.uid) AS uid, r.name AS name LIMIT $limit",
                limit=50,
            )
            data_sections.append(
                f"### Unlinked Requirements ({len(rows)} found)\n"
                + ("\n".join(f"- **{r.get('uid')}** — {r.get('name')}" for r in rows) or "None — all requirements have at least one outgoing link.")
            )

        # Export info
        if "export" in q_lower:
            data_sections.append(
                "### Export Options\n"
                "- **RDF/Turtle**: `GET /api/export/rdf?format=turtle`\n"
                "- **GraphML**: `GET /api/export/graphml`\n"
                "- **CSV**: `GET /api/export/csv`\n"
                "- **JSON-LD**: `GET /api/export/rdf?format=json-ld`\n"
                "All exports require an `X-API-Key` header when `API_KEY` is configured."
            )

        # MoSSEC / Knowledge Graph model overview
        if any(k in q_lower for k in (
            "mossec", "ap243", "model overview", "knowledge graph",
            "graph overview", "graph model", "what is in the graph",
            "explain the model", "describe the model", "explain model",
        )):
            # Node type distribution
            node_rows = _run(
                "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS cnt "
                "ORDER BY cnt DESC LIMIT 15",
                limit=15,
            )
            if node_rows:
                node_lines = "\n".join(
                    f"- **{r.get('label','?')}**: {r.get('cnt')}" for r in node_rows
                )
                total = sum(r.get("cnt", 0) for r in node_rows)
                data_sections.append(
                    f"### MoSSEC Knowledge Graph — Node Distribution ({total:,} shown)\n{node_lines}"
                )

            # AP standard coverage
            ap_rows = _run(
                "MATCH (n) WHERE n.ap_level IS NOT NULL OR n.ap_standard IS NOT NULL "
                "RETURN coalesce(n.ap_level, n.ap_standard) AS ap, count(*) AS cnt "
                "ORDER BY cnt DESC LIMIT 5",
                limit=5,
            )
            if ap_rows:
                ap_lines = "  |  ".join(
                    f"**{r.get('ap','?')}**: {r.get('cnt')}" for r in ap_rows
                )
                data_sections.append(f"### AP Standard Coverage\n{ap_lines}")

            # Ontologies
            ont_rows = _run(
                "MATCH (n:Ontology) "
                "RETURN coalesce(n.name, n.title, split(n.uri,'#')[0], 'Unknown') AS name, "
                "       coalesce(n.uri, n.url, n.source_url, '') AS url, "
                "       coalesce(n.ap_standard, n.ap_level, '') AS standard "
                "ORDER BY name LIMIT 10",
                limit=10,
            )
            if ont_rows:
                ont_lines = "\n".join(
                    f"- **{r.get('name','?')}**"
                    + (f" ({r['standard']})" if r.get("standard") else "")
                    + (f"  <{r['url']}>" if r.get("url") else "")
                    for r in ont_rows
                )
                data_sections.append(f"### Loaded Ontologies ({len(ont_rows)})\n{ont_lines}")

            # Simulation dossiers
            dossier_rows = _run(
                "MATCH (n:SimulationDossier) "
                "RETURN n.name AS name, coalesce(n.status,'?') AS status ORDER BY n.name LIMIT 10",
                limit=10,
            )
            if dossier_rows:
                dos_lines = "\n".join(
                    f"- **{r.get('name','?')}** — {r.get('status','?')}"
                    for r in dossier_rows
                )
                data_sections.append(f"### Simulation Dossiers ({len(dossier_rows)})\n{dos_lines}")

            # Simulation artifacts summary
            art_rows = _run(
                "MATCH (n:SimulationArtifact) "
                "RETURN n.name AS name, coalesce(n.status,'?') AS status ORDER BY n.name LIMIT 15",
                limit=15,
            )
            if art_rows:
                art_lines = "\n".join(
                    f"- **{r.get('name','?')}** ({r.get('status','?')})" for r in art_rows
                )
                data_sections.append(f"### Simulation Artifacts ({len(art_rows)})\n{art_lines}")

            # Top relationship types
            rel_rows = _run(
                "MATCH ()-[r]->() RETURN type(r) AS rel, count(*) AS cnt "
                "ORDER BY cnt DESC LIMIT 12",
                limit=12,
            )
            if rel_rows:
                rel_lines = "\n".join(
                    f"- `{r.get('rel','?')}`: {r.get('cnt')}" for r in rel_rows
                )
                data_sections.append(f"### Top Relationship Types\n{rel_lines}")

            # MBSEElement class names from AP243 domain XMI
            # NOTE: `:MBSEElement` is a shared label on ALL ~3,249 XMI nodes.
            # Use DISTINCT to collapse the many-copies-per-name into concept names.
            mbse_rows = _run(
                "MATCH (n:MBSEElement) WHERE n.name IS NOT NULL AND n.name <> '' "
                "RETURN DISTINCT n.name AS name ORDER BY n.name LIMIT 40",
                limit=40,
            )
            if mbse_rows:
                mbse_names = ", ".join(f"`{r.get('name','?')}`" for r in mbse_rows)
                data_sections.append(
                    f"### MBSEElement Concept Names — AP243 Domain Model ({len(mbse_rows)} distinct shown)\n{mbse_names}"
                )

            # Requirements quick count
            req_rows = _run(
                "MATCH (n:Requirement) WHERE n.id IS NOT NULL AND NOT n.id STARTS WITH '_' "
                "RETURN count(n) AS cnt",
                limit=1,
            )
            if req_rows:
                req_cnt = req_rows[0].get("cnt", 0)
                data_sections.append(
                    f"### Requirements\n{req_cnt} requirements ingested. "
                    "Ask *'show requirements'* for the full list."
                )

        # Ingestion / pipeline status
        if any(k in q_lower for k in (
            "ingest", "pipeline", "data load", "reload", "loaded data",
            "what data", "pipeline status", "ingestion status", "load status",
            "data status", "what is loaded", "what's loaded",
        )):
            # Overall counts
            count_rows = _run("MATCH (n) RETURN count(n) AS nodes", limit=1)
            rel_count_rows = _run("MATCH ()-[r]->() RETURN count(r) AS rels", limit=1)
            nodes_total = count_rows[0].get("nodes", "?") if count_rows else "?"
            rels_total = rel_count_rows[0].get("rels", "?") if rel_count_rows else "?"

            label_rows = _run(
                "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS cnt "
                "ORDER BY cnt DESC LIMIT 20",
                limit=20,
            )
            if label_rows:
                label_lines = "\n".join(
                    f"- **{r.get('label','?')}**: {r.get('cnt'):,}" for r in label_rows
                )
                data_sections.append(
                    f"### Graph Node Inventory ({nodes_total:,} total nodes,"
                    f" {rels_total:,} relationships)\n{label_lines}"
                )

            xmi_rows = _run(
                "MATCH (n:MBSEElement) "
                "RETURN count(n) AS total, count(DISTINCT n.name) AS distinct_names, "
                "       collect(DISTINCT coalesce(n.source_file,'Domain_model.xmi'))[0] AS source_file",
                limit=1,
            )
            if xmi_rows and xmi_rows[0].get("total"):
                x = xmi_rows[0]
                data_sections.append(
                    f"### XMI Source\n"
                    f"- File: `{x.get('source_file','Domain_model.xmi')}`\n"
                    f"- **{x.get('total'):,}** `:MBSEElement` nodes\n"
                    f"- **{x.get('distinct_names'):,}** distinct concept names\n"
                    f"- Loaded via `SemanticXMILoader` → `apoc.merge.node` (batch 500)"
                )

            ont_rows = _run(
                "MATCH (o:Ontology) "
                "OPTIONAL MATCH (o)-[:DEFINES_REFERENCE_DATA]->(n) "
                "RETURN coalesce(o.name, o.uri, 'Unknown') AS name, "
                "       coalesce(o.ap_level, o.ap_standard, '') AS ap, "
                "       count(n) AS ref_data_nodes "
                "ORDER BY name LIMIT 15",
                limit=15,
            )
            owl_cls_rows = _run("MATCH (n:ExternalOwlClass) RETURN count(n) AS cnt", limit=1)
            owl_prop_rows = _run("MATCH (n:OWLProperty) RETURN count(n) AS cnt", limit=1)
            owl_cls_cnt = owl_cls_rows[0].get("cnt", 0) if owl_cls_rows else 0
            owl_prop_cnt = owl_prop_rows[0].get("cnt", 0) if owl_prop_rows else 0
            ont_section = f"### Ingested Ontologies\n"
            if ont_rows:
                ont_section += "\n".join(
                    f"- **{r.get('name','?')}**"
                    + (f" [{r['ap']}]" if r.get("ap") else "")
                    + (f" — {r['ref_data_nodes']:,} ref-data nodes" if r.get("ref_data_nodes") else "")
                    for r in ont_rows
                )
            else:
                ont_section += "No ontology nodes found."
            ont_section += (
                f"\n- `:ExternalOwlClass` nodes: **{owl_cls_cnt:,}**"
                f"\n- `:OWLProperty` nodes: **{owl_prop_cnt:,}**"
            )
            data_sections.append(ont_section)

            step_rows = _run(
                "MATCH (n:StepFile) "
                "RETURN n.source_file AS file, coalesce(n.label, n.source_file) AS label, "
                "       coalesce(n.instance_count, 0) AS instances "
                "ORDER BY label LIMIT 10",
                limit=10,
            )
            step_inst_rows = _run(
                "MATCH (n:StepInstance) RETURN count(n) AS cnt",
                limit=1,
            )
            step_inst_cnt = step_inst_rows[0].get("cnt", 0) if step_inst_rows else 0
            if step_rows:
                step_lines = "\n".join(
                    f"- **{r.get('label','?')}**: {r.get('instances'):,} instances"
                    for r in step_rows
                )
                data_sections.append(
                    f"### STEP Files ({len(step_rows)} ingested,"
                    f" {step_inst_cnt:,} `:StepInstance` nodes)\n{step_lines}"
                )
            else:
                data_sections.append(
                    f"### STEP Files\n"
                    f"No STEP files ingested yet ({step_inst_cnt:,} `:StepInstance` nodes total).\n"
                    "Use `POST /api/step/ingest` or `python scripts/ingest_step_file.py <file.stp>`."
                )

            data_sections.append(
                "### Full Ingestion Pipeline (`scripts/load_all_data.py`)\n"
                "| Step | Script | Purpose |\n"
                "|---|---|---|\n"
                "| 1 | `reload_database.py` | Clear DB → load `Domain_model.xmi` via `SemanticXMILoader` |\n"
                "| 2 | `run_sdd_schema_migration.py` | Constraints, indexes, stub REQ nodes |\n"
                "| 3 | `run_migration.py` | AP hierarchy Cypher metadata |\n"
                "| 4 | `002_ap_hierarchy_sample_data.py` | AP239/AP242/AP243 sample nodes |\n"
                "| 5 | `ingest_sdd_data.py` | SimulationDossier, Artifact, EvidenceCategory, KPI |\n"
                "| 6 | `create_sample_data.py` | Requirements, traceability, DataTypes |\n"
                "| 7 | `link_ap_hierarchy.py` | AP239 ↔ AP242 ↔ AP243 cross-level links |\n"
                "| 8 | `run_migration_v4.py` | Digital thread v4 (11 relationship types) |\n"
                "| 9 | `ingest_ontology_rdf.py ×3` | AP243-MoSSEC + STEP-Core-v4 + PLCS-4439 OWL |\n"
                "| 10 | `load_oslc_seed.py` | OSLC Core/RM/AP242/AP243 vocabulary nodes |"
            )

        # Schema / label browser
        if any(k in q_lower for k in (
            "schema", "label", "node type", "node label", "label type",
            "what labels", "all labels", "relationship type", "rel type",
        )):
            lbl_rows = _run(
                "MATCH (n) UNWIND labels(n) AS lbl "
                "RETURN lbl AS label, count(n) AS cnt "
                "ORDER BY cnt DESC LIMIT 30",
                limit=30,
            )
            if lbl_rows:
                lines = "\n".join(
                    f"- `:{r.get('label','?')}` — {r.get('cnt'):,}" for r in lbl_rows
                )
                data_sections.append(f"### All Node Labels ({len(lbl_rows)} distinct)\n{lines}")

            schema_rel_rows = _run(
                "MATCH ()-[r]->() RETURN type(r) AS rel, count(*) AS cnt "
                "ORDER BY cnt DESC LIMIT 25",
                limit=25,
            )
            if schema_rel_rows:
                lines = "\n".join(
                    f"- `{r.get('rel','?')}` → {r.get('cnt'):,}" for r in schema_rel_rows
                )
                data_sections.append(
                    f"### All Relationship Types ({len(schema_rel_rows)} distinct)\n{lines}"
                )

        # Generic semantic / name search (fallback or when query has a specific subject)
        if not data_sections:
            # Extract meaningful keywords (skip stop words)
            stop = {"show", "list", "find", "all", "the", "a", "an", "in", "on",
                    "to", "of", "is", "are", "get", "give", "me", "my", "our", "graph"}
            keywords = [w for w in re.sub(r"[^a-z0-9 ]", "", q_lower).split() if w not in stop]
            search_term = " ".join(keywords[:4]) if keywords else user_query
            rows = _run(
                "MATCH (n) "
                "WHERE toLower(coalesce(n.name,'')) CONTAINS toLower($q) "
                "   OR toLower(coalesce(n.uid,'')) CONTAINS toLower($q) "
                "   OR toLower(coalesce(n.description,'')) CONTAINS toLower($q) "
                "WITH labels(n)[0] AS label, n.name AS name, "
                "     count(*) AS copies, "
                "     collect(coalesce(n.uid, n.id, ''))[0] AS uid "
                "RETURN label, uid, name, copies "
                "ORDER BY copies DESC, name "
                "LIMIT $limit",
                params={"q": search_term},
                limit=20,
            )
            if rows:
                lines = "\n".join(
                    f"- [{r.get('label','?')}] **{r.get('name','?')}** `{r.get('uid','?')}`"
                    + (f" ×{r['copies']}" if r.get("copies", 1) > 1 else "")
                    for r in rows
                )
                data_sections.append(f"### Search results for '{search_term}' ({len(rows)} found)\n{lines}")
            else:
                data_sections.append(
                    f"No nodes found matching '{search_term}'. "
                    "Try a more specific term, or ask about requirements, ontologies, simulations, or OSLC."
                )

        # ------------------------------------------------------------------
        # 2. KG statistics for context
        # ------------------------------------------------------------------
        try:
            stats = neo4j.svc.get_statistics()
        except Exception:
            stats = {}

        # ------------------------------------------------------------------
        # 3. Format reply directly from graph data (fast path)
        #    LLM synthesis skipped — Ollama latency is prohibitive for
        #    synchronous HTTP. The graph data is already markdown-structured.
        # ------------------------------------------------------------------
        if data_sections:
            intro = (
                f"*MoSSEC MBSE Knowledge Graph AI* — AP239 · AP242 · AP243 · Digital Thread\n"
                f"Graph: **{stats.get('total_nodes', '?')}** nodes · "
                f"**{stats.get('total_relationships', '?')}** relationships\n\n"
            )
            reply_text = intro + "\n\n".join(data_sections)
        else:
            reply_text = (
                f"No matching data found for: **{actual_query}**\n\n"
                f"The graph contains {stats.get('total_nodes', '?')} nodes. "
                f"Try asking about: requirements, ontologies, simulations, OSLC, traceability, impact, parts, or export."
            )

        logger.info(f"MBSE Agent: built reply ({len(reply_text)} chars) from {len(data_sections)} data section(s)")

        # ------------------------------------------------------------------
        # 4. Build response
        # ------------------------------------------------------------------
        task = state.get("task_type", "knowledge_query")
        next_step = END
        if task in ("impact_analysis", "bom_sync", "plm_ingest", "plm_query"):
            next_step = "plm_agent"
        elif task == "requirement_check":
            next_step = "simulation_agent"
        elif task in ("step_ingest", "step_query"):
            next_step = "step_agent"
        elif task in ("ontology_ingest", "ontology_query"):
            next_step = "ontology_agent"
        # Keyword-based PLM routing for generic knowledge_query
        elif any(k in q_lower for k in ("plmxml", "plm xml", "teamcenter", "bom for", "bill of material", "part number", "item revision")):
            next_step = "plm_agent"

        return {
            "artifact_details": {"kg_stats": stats},
            "traceability_data": traceability_data,
            "messages": [AIMessage(content=reply_text)],
            "next_action": next_step,
        }

    except Exception as e:
        logger.exception(f"MBSE Agent error: {e}")
        return {
            "error": f"MBSE Agent failed: {str(e)}",
            "messages": [AIMessage(content=f"MBSE Agent encountered error: {str(e)}")],
            "next_action": END,
        }


async def plm_agent_node(state: EngineeringState) -> dict:
    """PLM Agent: Teamcenter PLMXML ingestion, BOM queries, live REST (when configured)."""
    logger.info("⚙️ PLM Agent: Handling PLM / PLMXML request")

    user_query = state.get("user_query", "")
    task = state.get("task_type", "knowledge_query")
    agent = PLMAgent(system_type="teamcenter")

    try:
        # PLMXML ingest / query path (file-based, no live TC connection required)
        if task in ("plm_ingest", "plm_query") or any(
            k in user_query.lower()
            for k in ("plmxml", "plm xml", ".xml", ".plmxml", "ingest", "bom", "item", "part")
        ):
            msg = agent.summarize(user_query)
            return {
                "messages": [AIMessage(content=msg)],
                "next_action": END,
            }

        # Live Teamcenter REST path (impact_analysis / bom_sync)
        part_ids = ["000123", "000456"]
        availability = await agent.check_part_availability(part_ids)
        return {
            "affected_parts": [{"id": pid, "status": "Released"} for pid in part_ids],
            "messages": [AIMessage(
                content=f"PLM Agent: Checked {len(availability)} parts in Teamcenter."
            )],
            "next_action": END,
        }
    except Exception as exc:
        logger.exception(f"PLM Agent error: {exc}")
        return {
            "error": str(exc),
            "messages": [AIMessage(content=f"PLM Agent error: {exc}")],
            "next_action": END,
        }


async def simulation_agent_node(state: EngineeringState) -> dict:
    """Simulation Agent: Run analysis"""
    logger.info("🧪 Simulation Agent: Validating requirements")
    
    agent = SimulationAgent()
    params = agent.get_simulation_parameters("Model-X")
    
    # Run simulation (Fea)
    result = await agent.run_simulation("fea", params)
    
    return {
        "simulation_parameters": params,
        "simulation_summary": result,
        "messages": [AIMessage(content=f"Simulation Agent: Simulation complete. Status: {result.get('status')}")],
        "next_action": END
    }


async def step_agent_node(state: EngineeringState) -> dict:
    """STEP Agent: Ingest and query ISO 10303 STEP files."""
    logger.info("📐 STEP Agent: Processing STEP file query")

    user_query = state.get("user_query", "")
    q_lower = user_query.lower()
    agent = StepAgent()

    try:
        # Ingest intent — accept a file path from the query
        if any(k in q_lower for k in ("ingest", "load", "import")):
            import re
            path_match = re.search(
                r"(?:ingest|load|import)\s+['\"]?([^'\" ]+\.st(?:p|px?|ep))['\"]?",
                user_query,
                re.IGNORECASE,
            )
            if path_match:
                file_path = path_match.group(1)
                stats = agent.ingest_file(file_path)
                msg = (
                    f"STEP ingestion complete for `{file_path}`.\n\n"
                    + "\n".join(f"- **{k}**: {v}" for k, v in stats.items())
                )
            else:
                msg = (
                    "Please provide a STEP file path in the query, e.g.:\n"
                    "`ingest data/raw/assembly.stp`\n\n"
                    "Or use `POST /api/step/ingest` with `{\"path\": \"...\"}`."
                )
        else:
            msg = agent.summarize(user_query)

        return {
            "messages": [AIMessage(content=msg)],
            "next_action": END,
        }
    except Exception as e:
        logger.exception(f"STEP Agent error: {e}")
        return {
            "error": f"STEP Agent failed: {e}",
            "messages": [AIMessage(content=f"STEP Agent error: {e}")],
            "next_action": END,
        }


async def ontology_agent_node(state: EngineeringState) -> dict:
    """Ontology Agent: Ingest and query OWL/RDF ontology files."""
    logger.info("🧠 Ontology Agent: Processing ontology query")

    user_query = state.get("user_query", "")
    q_lower = user_query.lower()
    agent = OntologyAgent()

    try:
        # Ingest standard MoSSEC ontologies
        if any(k in q_lower for k in ("ingest standard", "load standard", "reload ontolog")):
            results = agent.ingest_standard_ontologies()
            lines = "\n".join(
                f"- **{r.get('name','?')}**: "
                + (f"triples={r.get('triples',0)}, classes={r.get('classes_upserted',0)}" if 'triples' in r else f"ERROR: {r.get('error','?')}")
                for r in results
            )
            msg = f"Standard ontology ingestion complete:\n\n{lines}"

        # Ingest a specific OWL file from query
        elif any(k in q_lower for k in ("ingest", "load", "import")):
            import re
            path_match = re.search(
                r"(?:ingest|load|import)\s+['\"]?([^'\" ]+\.(?:owl|ttl|rdf|xml|jsonld))['\"]?",
                user_query,
                re.IGNORECASE,
            )
            if path_match:
                file_path = path_match.group(1)
                stats = agent.ingest_file(file_path)
                msg = (
                    f"Ontology ingestion complete for `{file_path}`.\n\n"
                    + "\n".join(f"- **{k}**: {v}" for k, v in stats.items() if k != '__class__')
                )
            else:
                msg = (
                    "Please provide an OWL/RDF file path in the query, e.g.:\n"
                    "`ingest smrlv12/data/domain_models/mossec/ap243_v1.owl`\n\n"
                    "Or use `POST /api/ontology/ingest` with `{\"path\": \"...\"}`."
                )
        else:
            msg = agent.summarize(user_query)

        return {
            "messages": [AIMessage(content=msg)],
            "next_action": END,
        }
    except Exception as e:
        logger.exception(f"Ontology Agent error: {e}")
        return {
            "error": f"Ontology Agent failed: {e}",
            "messages": [AIMessage(content=f"Ontology Agent error: {e}")],
            "next_action": END,
        }


async def semantic_agent_node(state: EngineeringState) -> dict:
    """Semantic Agent: RAG search and insight generation over the knowledge graph."""
    logger.info("🔮 Semantic Agent: Processing semantic query")

    user_query = state.get("user_query", "")
    _task = state.get("task_type", "semantic_search")
    agent = SemanticAgent()

    try:
        if _task == "semantic_insight":
            result = agent.semantic_insight(user_query)
            msg = result.get("answer", "No insight generated.")
            sources = result.get("sources", [])
            if sources:
                msg += "\n\n**Sources:**\n" + "\n".join(
                    f"- {s.get('uid', '?')}: {s.get('name', '')}" for s in sources[:10]
                )
        else:
            # semantic_search or kg_expand
            expand = _task == "kg_expand"
            result = agent.semantic_search(user_query, expand=expand)
            hits = result.get("hits", [])
            if hits:
                lines = []
                for h in hits[:20]:
                    lines.append(f"- **{h.get('uid', '?')}** {h.get('name', '')} (score={h.get('score', 0):.3f})")
                msg = f"Found {len(hits)} semantic matches:\n\n" + "\n".join(lines)
            else:
                msg = "No semantic matches found."

        return {
            "messages": [AIMessage(content=msg)],
            "next_action": END,
        }
    except Exception as e:
        logger.exception(f"Semantic Agent error: {e}")
        return {
            "error": f"Semantic Agent failed: {e}",
            "messages": [AIMessage(content=f"Semantic Agent error: {e}")],
            "next_action": END,
        }


async def shacl_agent_node(state: EngineeringState) -> dict:
    """SHACL Agent: Validate nodes or generate compliance reports."""
    logger.info("✅ SHACL Agent: Processing validation request")

    from ..web.services.shacl_validation_service import SHACLValidationService

    user_query = state.get("user_query", "")
    _task = state.get("task_type", "shacl_validate")
    svc = SHACLValidationService()

    try:
        if _task == "shacl_report":
            report = svc.get_report()
            if report:
                lines = [f"| {r['shape_name']} | {r['severity']} | {r['count']} |" for r in report]
                msg = (
                    "**SHACL Compliance Report**\n\n"
                    "| Shape | Severity | Count |\n| --- | --- | --- |\n"
                    + "\n".join(lines)
                )
            else:
                msg = "No SHACL violations found — all nodes are compliant."
        else:
            # Determine label from query
            import re as _re
            label_match = _re.search(
                r"validate\s+(?:all\s+)?(\w+)", user_query, _re.IGNORECASE
            )
            label = label_match.group(1) if label_match else "PLMXMLItem"
            result = svc.validate_batch(label)
            msg = (
                f"Validated **{result.total_checked}** `{label}` nodes:\n"
                f"- Violations: **{result.violations_found}**\n"
                f"- Compliant: **{result.total_checked - result.violations_found}**"
            )

        return {
            "messages": [AIMessage(content=msg)],
            "next_action": END,
        }
    except Exception as e:
        logger.exception(f"SHACL Agent error: {e}")
        return {
            "error": f"SHACL Agent failed: {e}",
            "messages": [AIMessage(content=f"SHACL Agent error: {e}")],
            "next_action": END,
        }


async def export_handler_node(state: EngineeringState) -> dict:
    """Export Handler: Generate RDF or CSV exports of graph data."""
    logger.info("📤 Export Handler: Processing export request")

    from ..web.services.graph_query_registry import execute_named_query

    user_query = state.get("user_query", "")
    _task = state.get("task_type", "export_rdf")

    try:
        # Run a broad query to gather export data
        result = execute_named_query("classification_web", limit=500)
        rows = result.get("rows", [])

        if _task == "export_csv":
            if rows:
                import csv
                import io
                buf = io.StringIO()
                writer = csv.DictWriter(buf, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
                msg = f"CSV export generated ({len(rows)} rows).\n\n```csv\n{buf.getvalue()[:2000]}\n```"
            else:
                msg = "No data found for CSV export."
        else:
            # export_rdf — return a summary
            msg = (
                f"RDF export: {len(rows)} classification triples available.\n"
                "Use `GET /api/export/rdf` for the full Turtle file."
            )

        return {
            "messages": [AIMessage(content=msg)],
            "next_action": END,
        }
    except Exception as e:
        logger.exception(f"Export Handler error: {e}")
        return {
            "error": f"Export Handler failed: {e}",
            "messages": [AIMessage(content=f"Export Handler error: {e}")],
            "next_action": END,
        }


# ============================================================================
# WORKFLOW AGENT  (AP243 WorkflowMethod / TaskElement / ActionResource)
# ============================================================================


async def workflow_agent_node(state: EngineeringState) -> dict:
    """
    Workflow Agent — AP243-aligned orchestration node.

    Handles:
      * workflow_query   — list/search :WorkflowMethod nodes with step chains
      * workflow_execute — validate parameters, record execution intent in KG
      * workflow_validate — validate parameter values against AP243 constraints

    Maps to STEP schema:
      :WorkflowMethod  ← action_method (Part 41 / AP243)
      :TaskElement     ← sequential_method step (Part 49)
      :ActionResource  ← action_resource (Part 41)
      [:HAS_STEP]      ← method_relationship
      [:CHOSEN_METHOD] ← directed_action ← executed_action reference
    """
    logger.info("⚙️  Workflow Agent: Processing AP243 workflow request")

    user_query = state.get("user_query", "")
    q_lower    = user_query.lower()
    _task      = state.get("task_type", "workflow_query")

    try:
        from .agent_tools import Neo4jTool
        neo4j = Neo4jTool()

        def _run(cypher: str, params: dict | None = None, limit: int = 50) -> list[dict]:
            return neo4j.search_artifacts(cypher, params=params or {}, limit=limit)

        sections: list[str] = []
        workflow_data: dict = {}

        # ── 1. List / search WorkflowMethod nodes ───────────────────────────
        if _task in ("workflow_query", "workflow_execute") or any(
            k in q_lower for k in ("workflow", "method", "step", "task element", "action method")
        ):
            # Extract optional workflow id / name filter from query
            id_match = re.search(r"\b(WF-[\w\-]+)\b", user_query, re.IGNORECASE)
            filter_val = id_match.group(1).upper() if id_match else None

            if filter_val:
                rows = _run(
                    "MATCH (wf:WorkflowMethod) "
                    "WHERE wf.id = $fv OR toUpper(wf.name) CONTAINS toUpper($fv) "
                    "OPTIONAL MATCH (wf)-[:HAS_STEP]->(te:TaskElement) "
                    "WITH wf, collect(te) AS steps "
                    "RETURN wf.id AS id, wf.name AS name, wf.sim_type AS sim_type, "
                    "       wf.status AS status, wf.version AS version, "
                    "       wf.purpose AS purpose, size(steps) AS step_count "
                    "ORDER BY wf.id LIMIT $limit",
                    params={"fv": filter_val},
                    limit=5,
                )
            else:
                rows = _run(
                    "MATCH (wf:WorkflowMethod) "
                    "OPTIONAL MATCH (wf)-[:HAS_STEP]->(te:TaskElement) "
                    "WITH wf, collect(te) AS steps "
                    "RETURN wf.id AS id, wf.name AS name, wf.sim_type AS sim_type, "
                    "       wf.status AS status, wf.version AS version, "
                    "       wf.purpose AS purpose, size(steps) AS step_count "
                    "ORDER BY wf.id LIMIT $limit",
                    limit=20,
                )

            if rows:
                lines = "\n".join(
                    f"- **{r['id']}** — {r.get('name','?')}  "
                    f"| sim_type: `{r.get('sim_type','?')}`  "
                    f"| status: `{r.get('status','?')}`  "
                    f"| steps: {r.get('step_count',0)}"
                    + (f"\n  *{r['purpose']}*" if r.get("purpose") else "")
                    for r in rows
                )
                sections.append(f"### WorkflowMethod nodes ({len(rows)} found)\n{lines}")
                workflow_data["workflows"] = rows

                # Fetch step chains for the first (or matched) workflow
                first_id = rows[0]["id"]
                steps = _run(
                    "MATCH (wf:WorkflowMethod {id: $wid})-[:HAS_STEP]->(te:TaskElement) "
                    "RETURN te.uid AS uid, te.name AS name, te.type AS type, "
                    "       te.sequence_position AS seq, te.description AS desc "
                    "ORDER BY te.sequence_position",
                    params={"wid": first_id},
                    limit=50,
                )
                if steps:
                    step_lines = "\n".join(
                        f"  {s.get('seq','?')}. [{s.get('type','?')}] **{s.get('name','?')}**"
                        + (f" — {s['desc']}" if s.get("desc") else "")
                        for s in steps
                    )
                    sections.append(f"### Step Chain for `{first_id}` ({len(steps)} steps)\n{step_lines}")
                    workflow_data["steps"] = steps

                # Resources
                resources = _run(
                    "MATCH (wf:WorkflowMethod {id: $wid})-[:USES_RESOURCE]->(r:ActionResource) "
                    "RETURN r.id AS id, r.name AS name, r.type AS type",
                    params={"wid": first_id},
                    limit=20,
                )
                if resources:
                    res_lines = "\n".join(
                        f"- **{r.get('name','?')}** (`{r.get('type','?')}`)"
                        for r in resources
                    )
                    sections.append(f"### Action Resources for `{first_id}`\n{res_lines}")
                    workflow_data["resources"] = resources

                # Linked SimulationRuns via [:CHOSEN_METHOD]
                runs = _run(
                    "MATCH (sr:SimulationRun)-[:CHOSEN_METHOD]->(wf:WorkflowMethod {id: $wid}) "
                    "RETURN sr.id AS id, coalesce(sr.status,'?') AS status, sr.sim_type AS sim_type "
                    "ORDER BY sr.id LIMIT 20",
                    params={"wid": first_id},
                    limit=20,
                )
                if runs:
                    run_lines = "\n".join(
                        f"- `{r.get('id','?')}` — {r.get('status','?')}"
                        + (f" | {r['sim_type']}" if r.get("sim_type") else "")
                        for r in runs
                    )
                    sections.append(f"### Linked Simulation Runs\n{run_lines}")
                    workflow_data["runs"] = runs
            else:
                sections.append(
                    "### WorkflowMethod nodes\nNo WorkflowMethod nodes found in the graph.\n"
                    "Seed them with: `python backend/scripts/seed_workflows.py`"
                )

        # ── 2. Parameter validation context for workflow_execute ─────────────
        if _task == "workflow_execute":
            param_rows = _run(
                "MATCH (p:SimulationParameter) "
                "OPTIONAL MATCH (p)-[:HAS_CONSTRAINT]->(c) "
                "RETURN p.id AS id, p.name AS name, "
                "       coalesce(p.data_type,'any') AS data_type, "
                "       count(c) AS constraint_count "
                "ORDER BY p.name LIMIT $limit",
                limit=30,
            )
            if param_rows:
                p_lines = "\n".join(
                    f"- **{r.get('name','?')}** (`{r.get('data_type','?')}`)"
                    + (f" — {r['constraint_count']} constraint(s)" if r.get("constraint_count") else "")
                    for r in param_rows
                )
                sections.append(f"### Available Simulation Parameters ({len(param_rows)})\n{p_lines}")
                workflow_data["parameters"] = param_rows

        # ── 3. Workflow validation ────────────────────────────────────────────
        if _task == "workflow_validate":
            # Check for WorkflowMethod nodes with missing required properties
            issues = _run(
                "MATCH (wf:WorkflowMethod) "
                "WHERE wf.purpose IS NULL OR wf.sim_type IS NULL OR wf.status IS NULL "
                "RETURN wf.id AS id, wf.name AS name, "
                "       wf.purpose IS NULL AS missing_purpose, "
                "       wf.sim_type IS NULL AS missing_sim_type, "
                "       wf.status IS NULL AS missing_status "
                "LIMIT $limit",
                limit=20,
            )
            # Check for TaskElement nodes with missing sequence_position
            orphan_steps = _run(
                "MATCH (te:TaskElement) "
                "WHERE NOT EXISTS { MATCH ()-[:HAS_STEP]->(te) } "
                "RETURN te.uid AS uid, te.name AS name LIMIT 20",
                limit=20,
            )
            if issues:
                issue_lines = "\n".join(
                    f"- `{r.get('id','?')}`: "
                    + ", ".join(
                        f"missing `{k.replace('missing_','')}`"
                        for k in ("missing_purpose", "missing_sim_type", "missing_status")
                        if r.get(k)
                    )
                    for r in issues
                )
                sections.append(f"### WorkflowMethod Validation Issues ({len(issues)})\n{issue_lines}")
            else:
                sections.append("### WorkflowMethod Validation\n✅ All WorkflowMethod nodes have required properties.")
            if orphan_steps:
                sections.append(
                    f"### Orphan TaskElement nodes ({len(orphan_steps)})\n"
                    + "\n".join(f"- `{r.get('uid','?')}` — {r.get('name','?')}" for r in orphan_steps)
                )
            workflow_data["validation"] = {"issues": issues, "orphan_steps": orphan_steps}

        # ── Build reply ───────────────────────────────────────────────────────
        if sections:
            reply = "## Workflow Orchestration (AP243 WorkflowMethod)\n\n" + "\n\n".join(sections)
        else:
            reply = (
                "No workflow data found for the current query.\n"
                "Try: 'list workflows', 'show workflow WF-EM-001 steps', or 'validate workflows'."
            )

        return {
            "workflow_data": workflow_data,
            "messages": [AIMessage(content=reply)],
            "next_action": END,
        }

    except Exception as e:
        logger.exception(f"Workflow Agent error: {e}")
        return {
            "error": f"Workflow Agent failed: {e}",
            "messages": [AIMessage(content=f"Workflow Agent error: {e}")],
            "next_action": END,
        }


# ============================================================================
# DIGITAL THREAD AGENT  (AP239 ↔ AP242 ↔ AP243 + OSLC lifecycle)
# ============================================================================


async def digital_thread_agent_node(state: EngineeringState) -> dict:
    """
    Digital Thread Agent — traces the full engineering lifecycle chain.

    AP239 (programme / activity recording)
        → AP242 (product data management / BOM / configuration)
            → AP243 (simulation-based design / SDD dossiers)
                → OSLC lifecycle resources (requirements, change requests, test plans)

    Handles task types:
      digital_thread_trace — full AP239→AP242→AP243 chain with OSLC links
      oslc_query           — OSLC resource query + linked STEP artefacts
      ap_standard_query    — targeted AP239/AP242/AP243 node browse
      mossec_overview      — comprehensive MoSSEC knowledge graph summary
    """
    logger.info("🧵 Digital Thread Agent: Tracing AP239 ↔ AP242 ↔ AP243 + OSLC lifecycle")

    user_query  = state.get("user_query", "")
    q_lower     = user_query.lower()
    _task       = state.get("task_type", "digital_thread_trace")

    try:
        from .agent_tools import Neo4jTool
        neo4j = Neo4jTool()

        def _run(cypher: str, params: dict | None = None, limit: int = 50) -> list[dict]:
            return neo4j.search_artifacts(cypher, params=params or {}, limit=limit)

        sections: list[str] = []
        thread_data: dict   = {}
        ap_data: dict       = {}

        # ── AP239: Activity Recording ────────────────────────────────────────
        if _task in ("digital_thread_trace", "ap_standard_query") or "ap239" in q_lower or "activit" in q_lower:
            ap239_nodes = _run(
                "MATCH (n) WHERE n.ap_level = 'AP239' OR n.ap_standard = 'AP239' "
                "   OR ANY(l IN labels(n) WHERE l CONTAINS 'Ap239') "
                "RETURN labels(n)[0] AS label, "
                "       coalesce(n.id, n.uid, n.name, '') AS uid, n.name AS name, "
                "       coalesce(n.status,'?') AS status "
                "ORDER BY label, uid LIMIT $limit",
                limit=30,
            )
            if ap239_nodes:
                lines = "\n".join(
                    f"- [{r.get('label','?')}] **{r.get('name','?')}** `{r.get('uid','?')}` — {r.get('status','?')}"
                    for r in ap239_nodes
                )
                sections.append(f"### AP239 — Programme / Activity Recording ({len(ap239_nodes)} nodes)\n{lines}")
                ap_data["ap239"] = ap239_nodes
            else:
                # Fallback: look for Activity-labelled nodes from STEP ingestion
                act_rows = _run(
                    "MATCH (n) WHERE ANY(l IN labels(n) WHERE l CONTAINS 'Activity') "
                    "RETURN labels(n)[0] AS label, n.name AS name, "
                    "       coalesce(n.uid, n.id,'') AS uid LIMIT $limit",
                    limit=20,
                )
                if act_rows:
                    lines = "\n".join(f"- [{r.get('label')}] **{r.get('name','?')}** `{r.get('uid','?')}`" for r in act_rows)
                    sections.append(f"### AP239 — Activity nodes ({len(act_rows)} found)\n{lines}")
                    ap_data["ap239"] = act_rows
                else:
                    sections.append(
                        "### AP239 — Activity Recording\n"
                        "No AP239 nodes found. Run `002_ap_hierarchy_sample_data.py` to seed AP-level data."
                    )

        # ── AP242: Product Data Management ───────────────────────────────────
        if _task in ("digital_thread_trace", "ap_standard_query") or "ap242" in q_lower or any(k in q_lower for k in ("product", "bom", "part", "configuration")):
            ap242_nodes = _run(
                "MATCH (n) WHERE n.ap_level = 'AP242' OR n.ap_standard = 'AP242' "
                "   OR ANY(l IN labels(n) WHERE l CONTAINS 'Ap242') "
                "RETURN labels(n)[0] AS label, "
                "       coalesce(n.id, n.uid, n.name, '') AS uid, n.name AS name, "
                "       coalesce(n.status,'?') AS status "
                "ORDER BY label, uid LIMIT $limit",
                limit=30,
            )
            if ap242_nodes:
                lines = "\n".join(
                    f"- [{r.get('label','?')}] **{r.get('name','?')}** `{r.get('uid','?')}` — {r.get('status','?')}"
                    for r in ap242_nodes
                )
                sections.append(f"### AP242 — Product Data Management ({len(ap242_nodes)} nodes)\n{lines}")
                ap_data["ap242"] = ap242_nodes
            else:
                # Fallback: Part / PLM nodes
                part_rows = _run(
                    "MATCH (n:Part) RETURN n.id AS uid, n.name AS name, "
                    "       coalesce(n.part_number,'') AS pn, coalesce(n.status,'?') AS status "
                    "ORDER BY n.name LIMIT $limit",
                    limit=20,
                )
                if part_rows:
                    lines = "\n".join(f"- **{r.get('name','?')}** PN:`{r.get('pn','')}` — {r.get('status','?')}" for r in part_rows)
                    sections.append(f"### AP242 — Parts / BOM ({len(part_rows)} nodes)\n{lines}")
                    ap_data["ap242"] = part_rows
                else:
                    sections.append(
                        "### AP242 — Product Data Management\n"
                        "No AP242 nodes found. Seed with `002_ap_hierarchy_sample_data.py` or import PLMXML."
                    )

        # ── AP243: Simulation-based Design (MoSSEC) ───────────────────────────
        if _task in ("digital_thread_trace", "ap_standard_query", "mossec_overview") or "ap243" in q_lower or any(
            k in q_lower for k in ("simulation dossier", "mossec", "sdd", "simulation run", "sim artifact")
        ):
            ap243_nodes = _run(
                "MATCH (n) WHERE n.ap_level = 'AP243' OR n.ap_standard = 'AP243' "
                "   OR ANY(l IN labels(n) WHERE l IN ['SimulationDossier','SimulationRun','SimulationArtifact','WorkflowMethod','TaskElement']) "
                "RETURN labels(n)[0] AS label, "
                "       coalesce(n.id, n.uid, n.name, '') AS uid, n.name AS name, "
                "       coalesce(n.status,'?') AS status "
                "ORDER BY label, uid LIMIT $limit",
                limit=40,
            )
            if ap243_nodes:
                from itertools import groupby
                by_label: dict[str, list] = {}
                for r in ap243_nodes:
                    by_label.setdefault(r.get("label","?"), []).append(r)
                label_sections = []
                for lbl, items in by_label.items():
                    item_lines = "\n".join(
                        f"  - **{r.get('name','?')}** `{r.get('uid','?')}` — {r.get('status','?')}"
                        for r in items[:10]
                    )
                    label_sections.append(f"**:{lbl}** ({len(items)})\n{item_lines}")
                sections.append(
                    f"### AP243 — Simulation-based Design / MoSSEC ({len(ap243_nodes)} nodes)\n"
                    + "\n\n".join(label_sections)
                )
                ap_data["ap243"] = ap243_nodes
            else:
                sections.append(
                    "### AP243 — Simulation-based Design\n"
                    "No AP243/SDD nodes found. Run the full ingestion pipeline."
                )

        # ── Cross-level thread links ──────────────────────────────────────────
        if _task == "digital_thread_trace":
            cross_rows = _run(
                "MATCH (a)-[r]->(b) "
                "WHERE (a.ap_level IS NOT NULL OR b.ap_level IS NOT NULL) "
                "  AND a.ap_level <> coalesce(b.ap_level,'') "
                "RETURN a.ap_level AS from_ap, labels(a)[0] AS from_label, a.name AS from_name, "
                "       type(r) AS rel, "
                "       b.ap_level AS to_ap, labels(b)[0] AS to_label, b.name AS to_name "
                "ORDER BY from_ap, to_ap LIMIT $limit",
                limit=40,
            )
            if cross_rows:
                lines = "\n".join(
                    f"- **{r.get('from_ap','?')}**:{r.get('from_name','?')} "
                    f"—[{r.get('rel','?')}]→ "
                    f"**{r.get('to_ap','?')}**:{r.get('to_name','?')}"
                    for r in cross_rows
                )
                sections.append(f"### Cross-Standard Digital Thread Links ({len(cross_rows)} edges)\n{lines}")
                thread_data["cross_links"] = cross_rows
            else:
                # Try generic cross-links via common relationship types
                alt_rows = _run(
                    "MATCH (a)-[r:IMPLEMENTS|VALIDATES_USING|DERIVED_FROM|SATISFIES|ALLOCATED_TO]->(b) "
                    "RETURN labels(a)[0] AS from_label, a.name AS from_name, "
                    "       type(r) AS rel, labels(b)[0] AS to_label, b.name AS to_name "
                    "ORDER BY rel LIMIT 40",
                    limit=40,
                )
                if alt_rows:
                    lines = "\n".join(
                        f"- [{r.get('from_label')}] {r.get('from_name','?')} "
                        f"—[{r.get('rel')}]→ [{r.get('to_label')}] {r.get('to_name','?')}"
                        for r in alt_rows
                    )
                    sections.append(f"### Digital Thread Relationships ({len(alt_rows)} edges)\n{lines}")
                    thread_data["cross_links"] = alt_rows
                else:
                    sections.append(
                        "### Digital Thread Links\n"
                        "No cross-standard links found yet. Run `link_ap_hierarchy.py` and "
                        "`run_migration_v4.py` to build the digital thread."
                    )

        # ── OSLC lifecycle resources ──────────────────────────────────────────
        if _task in ("oslc_query", "digital_thread_trace") or "oslc" in q_lower:
            oslc_rows = _run(
                "MATCH (n) "
                "WHERE n.source = 'oslc' OR ANY(l IN labels(n) WHERE l STARTS WITH 'Oslc') "
                "   OR n.oslc_domain IS NOT NULL OR n.oslc_type IS NOT NULL "
                "RETURN labels(n)[0] AS label, "
                "       coalesce(n.uid, n.id, '') AS uid, "
                "       coalesce(n.title, n.name, '') AS name, "
                "       coalesce(n.oslc_domain,'') AS domain "
                "ORDER BY label, uid LIMIT $limit",
                limit=30,
            )
            if oslc_rows:
                lines = "\n".join(
                    f"- [{r.get('label','?')}] **{r.get('name','?')}**"
                    + (f" | domain: `{r['domain']}`" if r.get("domain") else "")
                    for r in oslc_rows
                )
                sections.append(f"### OSLC Lifecycle Resources ({len(oslc_rows)} nodes)\n{lines}")

                # OSLC → STEP traceability
                oslc_links = _run(
                    "MATCH (o)-[r:MAPS_TO_OSLC|OSLC_TRACES|SATISFIES|IMPLEMENTS]->(s) "
                    "RETURN labels(o)[0] AS oslc_label, o.name AS oslc_name, "
                    "       type(r) AS rel, labels(s)[0] AS step_label, s.name AS step_name "
                    "LIMIT 30",
                    limit=30,
                )
                if oslc_links:
                    link_lines = "\n".join(
                        f"- **{r.get('oslc_name','?')}** —[{r.get('rel')}]→ {r.get('step_name','?')} ({r.get('step_label','?')})"
                        for r in oslc_links
                    )
                    sections.append(f"### OSLC ↔ STEP Traceability ({len(oslc_links)} links)\n{link_lines}")
                thread_data["oslc"] = oslc_rows
            else:
                sections.append(
                    "### OSLC Lifecycle Resources\n"
                    "No OSLC nodes found. Run `load_oslc_seed.py` to import OSLC Core/RM/AP242/AP243 vocabulary nodes."
                )

        # ── MoSSEC overview ───────────────────────────────────────────────────
        if _task == "mossec_overview" or any(k in q_lower for k in ("mossec", "overview", "knowledge graph")):
            node_dist = _run(
                "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS cnt "
                "ORDER BY cnt DESC LIMIT 20",
                limit=20,
            )
            rel_dist = _run(
                "MATCH ()-[r]->() RETURN type(r) AS rel, count(*) AS cnt "
                "ORDER BY cnt DESC LIMIT 15",
                limit=15,
            )
            ap_dist = _run(
                "MATCH (n) WHERE n.ap_level IS NOT NULL "
                "RETURN n.ap_level AS ap, count(*) AS cnt ORDER BY ap",
                limit=10,
            )
            if node_dist:
                total_nodes = sum(r.get("cnt", 0) for r in node_dist)
                node_lines = "\n".join(f"- `:{r.get('label','?')}`: {r.get('cnt'):,}" for r in node_dist)
                sections.append(f"### MoSSEC Node Distribution ({total_nodes:,} total)\n{node_lines}")
            if rel_dist:
                total_rels = sum(r.get("cnt", 0) for r in rel_dist)
                rel_lines = "\n".join(f"- `{r.get('rel','?')}`: {r.get('cnt'):,}" for r in rel_dist)
                sections.append(f"### Relationship Types ({total_rels:,} total)\n{rel_lines}")
            if ap_dist:
                ap_lines = "  |  ".join(f"**{r.get('ap','?')}**: {r.get('cnt'):,}" for r in ap_dist)
                sections.append(f"### AP Standard Coverage\n{ap_lines}")

        # ── Fallback ──────────────────────────────────────────────────────────
        if not sections:
            sections.append(
                "No digital thread data found for the current query.\n\n"
                "Try:\n"
                "- `trace digital thread for FEA-MAXWELL-2D`\n"
                "- `show AP239 activities`\n"
                "- `query AP242 BOM`\n"
                "- `list OSLC resources`\n"
                "- `mossec overview`"
            )

        reply = "## Digital Thread — AP239 ↔ AP242 ↔ AP243 + OSLC\n\n" + "\n\n".join(sections)

        return {
            "digital_thread": thread_data,
            "ap_standard_data": ap_data,
            "messages": [AIMessage(content=reply)],
            "next_action": END,
        }

    except Exception as e:
        logger.exception(f"Digital Thread Agent error: {e}")
        return {
            "error": f"Digital Thread Agent failed: {e}",
            "messages": [AIMessage(content=f"Digital Thread Agent error: {e}")],
            "next_action": END,
        }


# ============================================================================
# GRAPH CONSTRUCTION
# ============================================================================

def create_engineering_workflow():
    """Create the multi-agent workflow graph"""
    workflow = StateGraph(EngineeringState)

    # Add nodes
    workflow.add_node("mbse_agent",           mbse_agent_node)
    workflow.add_node("plm_agent",            plm_agent_node)
    workflow.add_node("simulation_agent",     simulation_agent_node)
    workflow.add_node("step_agent",           step_agent_node)
    workflow.add_node("ontology_agent",       ontology_agent_node)
    workflow.add_node("semantic_agent",       semantic_agent_node)
    workflow.add_node("shacl_agent",          shacl_agent_node)
    workflow.add_node("export_handler",       export_handler_node)
    workflow.add_node("workflow_agent",       workflow_agent_node)       # AP243 WorkflowMethod
    workflow.add_node("digital_thread_agent", digital_thread_agent_node) # AP239↔AP242↔AP243 + OSLC

    # set entry point
    workflow.set_entry_point("mbse_agent")

    # Add conditional edges based on next_action
    def router(state):
        return state["next_action"]

    workflow.add_conditional_edges(
        "mbse_agent",
        router,
        {
            "plm_agent":            "plm_agent",
            "simulation_agent":     "simulation_agent",
            "step_agent":           "step_agent",
            "ontology_agent":       "ontology_agent",
            "semantic_agent":       "semantic_agent",
            "shacl_agent":          "shacl_agent",
            "export_handler":       "export_handler",
            "workflow_agent":       "workflow_agent",
            "digital_thread_agent": "digital_thread_agent",
            END: END,
        },
    )

    workflow.add_edge("plm_agent",            END)
    workflow.add_edge("simulation_agent",     END)
    workflow.add_edge("step_agent",           END)
    workflow.add_edge("ontology_agent",       END)
    workflow.add_edge("semantic_agent",       END)
    workflow.add_edge("shacl_agent",          END)
    workflow.add_edge("export_handler",       END)
    workflow.add_edge("workflow_agent",       END)
    workflow.add_edge("digital_thread_agent", END)

    return workflow.compile()


async def execute_engineering_workflow(user_query: str, task_type: str = "impact_analysis") -> dict:
    """Execute the multi-agent workflow"""
    # create_engineering_workflow now returns a compiled graph (CompiledStateGraph)
    # due to 'return workflow.compile()' at line 203
    app = create_engineering_workflow()
    
    initial_state = {
        "user_query": user_query,
        "task_type": task_type,
        "messages": [HumanMessage(content=user_query)],
        "next_action": "mbse_agent",
        
        # Initialize other fields to None/Empty
        "requirement_id": None, "artifact_details": None, "traceability_data": None,
        "affected_parts": [], "bom_data": None, "change_impact": None,
        "simulation_parameters": None, "validation_results": None, "simulation_summary": None,
        "compliance_status": None, "violations": [], "recommendations": [],
        # New: workflow + digital thread
        "workflow_data": None, "digital_thread": None, "ap_standard_data": None,
        "error": None
    }
    
    # app is already compiled, so we call ainvoke directly
    result = await app.ainvoke(initial_state)
    return result


# ============================================================================
# BASELINE ORCHESTRATOR (AZURE AI PATTERN)
# ============================================================================

def create_baseline_orchestrator() -> BaselineOrchestrator:
    """Create a baseline orchestrator aligned with Azure AI agentic patterns."""
    tools = MBSETools()
    tool_registry = MBSEToolsAdapter(tools_api=tools)
    planner = KeywordPlanner()
    reflector = SimpleReflector()

    mbse_agent = SingleToolAgent(name="mbse_worker", planner=planner)

    orchestrator = BaselineOrchestrator(
        tool_registry=tool_registry,
        planner=planner,
        reflector=reflector,
        agents=[mbse_agent],
        max_retries=1,
    )
    return orchestrator


def execute_baseline_workflow(user_query: str) -> str:
    """Execute a goal using the baseline orchestrator."""
    logger.info(f"🚀 Executing baseline orchestrator workflow for: {user_query}")
    orchestrator = create_baseline_orchestrator()

    try:
        response = orchestrator.run(user_query)
        logger.info("✓ Baseline workflow completed successfully")
        return response
    except Exception as e:
        logger.error(f"Baseline workflow failed: {e}")
        return f"Error: {e}"


# ============================================================================
# EXAMPLE USAGE
# ============================================================================


if __name__ == "__main__":
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else "baseline"

    if mode == "langgraph":
        # LangGraph multi-agent workflow (async — must be run with asyncio)
        async def _run_langgraph():
            return await execute_engineering_workflow(
                user_query="What happens if I change the brake caliper material to titanium?",
                task_type="impact_analysis",
            )

        result = asyncio.run(_run_langgraph())

        print("\n" + "=" * 80)
        print("LANGGRAPH WORKFLOW EXECUTION RESULTS")
        print("=" * 80)
        print(f"\nQuery: {result['user_query']}")
        print(f"Task Type: {result['task_type']}")
        print(f"\n--- MBSE Agent Results ---")
        print(f"Artifacts Found: {result.get('artifact_details', 'None')}")
        print(f"\n--- PLM Agent Results ---")
        print(f"Affected Parts: {len(result.get('affected_parts', []))}")
        print(f"Change Impact: {result.get('change_impact', 'None')}")
        print(f"\n--- Simulation Agent Results ---")
        print(f"Validation: {result.get('validation_results', 'None')}")
        print(f"\n--- Compliance Agent Results ---")
        print(f"Compliance Status: {result.get('compliance_status', 'None')}")
        print(f"Recommendations: {result.get('recommendations', [])}")
        print(f"\nWorkflow Data: {result.get('workflow_data', 'None')}")
        print(f"Digital Thread: {result.get('digital_thread', 'None')}")
        print(f"\nError: {result.get('error', 'None')}")
        print("=" * 80)

    else:
        # Baseline orchestrator (Azure AI pattern, vendor-neutral)
        query = "Show me traceability from requirements to design elements"
        response = execute_baseline_workflow(query)

        print("\n" + "=" * 80)
        print("BASELINE ORCHESTRATOR RESULTS (Azure AI Pattern)")
        print("=" * 80)
        print(f"\nQuery: {query}")
        print(f"\nResponse:\n{response}")
        print("\n" + "=" * 80)
