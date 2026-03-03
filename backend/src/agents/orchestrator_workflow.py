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
    # ─────────────────────────────────────────────────────────────────────────

    try:
        neo4j = Neo4jTool()

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

        # Simulation
        if any(k in q_lower for k in ("simulation", "dossier", "run", "analysis model")):
            rows = _run(
                "MATCH (n) WHERE 'SimulationArtifact' IN labels(n) "
                "   OR 'SimulationDossier' IN labels(n) OR 'SimulationRun' IN labels(n) "
                "RETURN labels(n)[0] AS label, n.uid AS uid, n.name AS name, "
                "       coalesce(n.status,'?') AS status "
                "ORDER BY n.uid LIMIT $limit",
                limit=30,
            )
            if rows:
                lines = "\n".join(
                    f"- [{r.get('label')}] **{r.get('name','?')}** `{r.get('uid','?')}` ({r.get('status')})"
                    for r in rows
                )
                data_sections.append(f"### Simulation Artifacts ({len(rows)} found)\n{lines}")

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
            intro = f"Here is what I found in the knowledge graph ({stats.get('total_nodes', '?')} nodes total):\n\n"
            reply_text = intro + "\n\n".join(data_sections)
        else:
            reply_text = (
                f"No matching data found for: **{user_query}**\n\n"
                f"The graph contains {stats.get('total_nodes', '?')} nodes. "
                f"Try asking about: requirements, ontologies, simulations, OSLC, traceability, impact, or export."
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
# GRAPH CONSTRUCTION
# ============================================================================

def create_engineering_workflow():
    """Create the multi-agent workflow graph"""
    workflow = StateGraph(EngineeringState)

    # Add nodes
    workflow.add_node("mbse_agent", mbse_agent_node)
    workflow.add_node("plm_agent", plm_agent_node)
    workflow.add_node("simulation_agent", simulation_agent_node)
    workflow.add_node("step_agent", step_agent_node)
    workflow.add_node("ontology_agent", ontology_agent_node)
    workflow.add_node("semantic_agent", semantic_agent_node)
    workflow.add_node("shacl_agent", shacl_agent_node)
    workflow.add_node("export_handler", export_handler_node)

    # set entry point
    workflow.set_entry_point("mbse_agent")

    # Add conditional edges based on next_action
    def router(state):
        return state["next_action"]

    workflow.add_conditional_edges(
        "mbse_agent",
        router,
        {
            "plm_agent": "plm_agent",
            "simulation_agent": "simulation_agent",
            "step_agent": "step_agent",
            "ontology_agent": "ontology_agent",
            "semantic_agent": "semantic_agent",
            "shacl_agent": "shacl_agent",
            "export_handler": "export_handler",
            END: END
        }
    )

    workflow.add_edge("plm_agent", END)
    workflow.add_edge("simulation_agent", END)
    workflow.add_edge("step_agent", END)
    workflow.add_edge("ontology_agent", END)
    workflow.add_edge("semantic_agent", END)
    workflow.add_edge("shacl_agent", END)
    workflow.add_edge("export_handler", END)

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
        # Original LangGraph multi-agent workflow
        result = execute_engineering_workflow(
            user_query="What happens if I change the brake caliper material to titanium?",
            task_type="impact_analysis",
        )

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
