"""
STEP Specialized Agent
Handles ingestion and querying of ISO 10303 STEP (Part-21/STPX) files in the knowledge graph.
Delegates file parsing to StepIngestService; queries Neo4j for STEP instance data.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from src.agents.agent_tools import Neo4jTool
from src.web.services import get_neo4j_service
from src.web.services.step_ingest_service import StepIngestConfig, StepIngestService


class StepAgent:
    """
    Specialized agent for STEP file operations.

    Capabilities:
    - Ingest STEP Part-21 (.stp/.step) and STEP-XML (.stpx) files
    - Query :StepFile / :StepInstance nodes in Neo4j
    - Browse entity types, count instances, trace STEP_REF relationships
    - Map STEP entity types to AP242/AP243 semantic labels
    """

    def __init__(self, batch_size: int = 500):
        self.neo4j = get_neo4j_service()
        self.tool = Neo4jTool()
        self.batch_size = batch_size

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def ingest_file(
        self,
        file_path: str,
        label: Optional[str] = None,
        batch_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Ingest a STEP file into Neo4j.

        Args:
            file_path: Absolute or repo-relative path to .stp/.step/.stpx
            label:     Optional human-readable name for the :StepFile node
            batch_size: UNWIND batch size (default 500)

        Returns:
            Stats dict from StepIngestService
        """
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"STEP file not found: {p}")

        cfg = StepIngestConfig(
            batch_size=batch_size or self.batch_size,
        )
        svc = StepIngestService(cfg)
        stats = svc.ingest_file(p, file_label=label or p.stem)
        logger.info(f"StepAgent.ingest_file: {p.name} -> {stats}")
        return stats

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def _run(self, cypher: str, params: Optional[Dict] = None, limit: int = 50) -> List[Dict]:
        return self.tool.search_artifacts(cypher, params=params or {}, limit=limit)

    def list_step_files(self, limit: int = 30) -> List[Dict]:
        """Return all :StepFile nodes with instance counts."""
        return self._run(
            "MATCH (f:StepFile) "
            "OPTIONAL MATCH (f)-[:CONTAINS_INSTANCE]->(i:StepInstance) "
            "RETURN f.source_file AS file, coalesce(f.label, f.source_file) AS label, "
            "       f.createdAt AS loaded_on, count(i) AS instance_count "
            "ORDER BY label LIMIT $limit",
            limit=limit,
        )

    def entity_type_summary(self, step_file_label: Optional[str] = None, limit: int = 30) -> List[Dict]:
        """Count :StepInstance nodes grouped by entity_type."""
        if step_file_label:
            return self._run(
                "MATCH (f:StepFile)-[:CONTAINS_INSTANCE]->(n:StepInstance) "
                "WHERE coalesce(f.label, f.source_file) = $lbl "
                "RETURN n.entity_type AS entity_type, count(*) AS cnt "
                "ORDER BY cnt DESC LIMIT $limit",
                params={"lbl": step_file_label},
                limit=limit,
            )
        return self._run(
            "MATCH (n:StepInstance) "
            "RETURN n.entity_type AS entity_type, count(*) AS cnt "
            "ORDER BY cnt DESC LIMIT $limit",
            limit=limit,
        )

    def instances_of_type(self, entity_type: str, limit: int = 20) -> List[Dict]:
        """Return :StepInstance nodes of a given entity type."""
        return self._run(
            "MATCH (n:StepInstance {entity_type: $et}) "
            "RETURN n.instance_id AS id, n.entity_type AS type, n.params AS params "
            "LIMIT $limit",
            params={"et": entity_type.upper()},
            limit=limit,
        )

    def trace_references(self, instance_id: str, depth: int = 2) -> List[Dict]:
        """Follow STEP_REF relationships up to `depth` hops from an instance."""
        return self._run(
            "MATCH path = (start:StepInstance {instance_id: $iid})"
            "-[:STEP_REF*1..2]->(ref:StepInstance) "
            "RETURN start.instance_id AS start_id, "
            "       ref.entity_type AS ref_type, "
            "       ref.instance_id AS ref_id "
            "LIMIT $limit",
            params={"iid": instance_id},
            limit=50,
        )

    def ap_mapping_summary(self) -> List[Dict]:
        """
        Show which STEP entity types could map to AP242/AP243 semantic labels.
        Looks for :StepInstance nodes that already have a semantic_label property.
        """
        return self._run(
            "MATCH (n:StepInstance) WHERE n.semantic_label IS NOT NULL "
            "RETURN n.entity_type AS step_type, n.semantic_label AS semantic_label, "
            "       count(*) AS cnt "
            "ORDER BY cnt DESC LIMIT 30",
            limit=30,
        )

    # ------------------------------------------------------------------
    # High-level summary (called by orchestrator node)
    # ------------------------------------------------------------------

    def summarize(self, query: str) -> str:
        """
        Produce a markdown summary relevant to the user query.
        Called from step_agent_node in the orchestrator workflow.
        """
        q_lower = query.lower()
        sections: List[str] = []

        # File inventory
        files = self.list_step_files(limit=20)
        if files:
            lines = "\n".join(
                f"- **{r.get('label','?')}** — {r.get('instance_count', 0):,} instances"
                + (f" (loaded: {r.get('loaded_on','')})" if r.get("loaded_on") else "")
                for r in files
            )
            sections.append(f"### STEP Files Loaded ({len(files)})\n{lines}")
        else:
            sections.append(
                "### STEP Files\nNo STEP files ingested yet.\n"
                "Use `POST /api/step/ingest` or:\n"
                "```\npython scripts/ingest_step_file.py <path/to/file.stp>\n```"
            )

        # Entity type breakdown
        entity_filter = None
        type_match = re.search(r"\bentity\s+type[s]?\s+(?:for\s+)?([a-z_0-9]+)", q_lower)
        file_match = re.search(r"(?:in|for|file)\s+['\"]?([a-z0-9_\-\.]+\.st(?:p|px?))['\"]?", q_lower)
        if file_match:
            entity_filter = file_match.group(1)

        types = self.entity_type_summary(step_file_label=entity_filter, limit=25)
        if types:
            lines = "\n".join(
                f"- `{r.get('entity_type','?')}`: {r.get('cnt', 0):,}" for r in types
            )
            file_note = f" in `{entity_filter}`" if entity_filter else " (all files)"
            sections.append(f"### Entity Type Distribution{file_note}\n{lines}")

        # Specific entity type lookup
        if type_match or any(k in q_lower for k in ("instance", "instances of")):
            et_match = re.search(
                r"instances?\s+of\s+['\"]?([A-Z_a-z0-9]+)['\"]?", query, re.IGNORECASE
            )
            if et_match:
                et = et_match.group(1).upper()
                rows = self.instances_of_type(et, limit=15)
                if rows:
                    lines = "\n".join(
                        f"- `#{r.get('id','?')}` {r.get('params','')[:80]}" for r in rows
                    )
                    sections.append(f"### Instances of `{et}` ({len(rows)} shown)\n{lines}")

        # AP242 semantic mapping
        if any(k in q_lower for k in ("ap242", "semantic", "mapping", "map")):
            mapped = self.ap_mapping_summary()
            if mapped:
                lines = "\n".join(
                    f"- `{r.get('step_type','?')}` → `{r.get('semantic_label','?')}`: {r.get('cnt',0)}"
                    for r in mapped
                )
                sections.append(f"### AP242 Semantic Mappings ({len(mapped)})\n{lines}")
            else:
                sections.append(
                    "### AP242 Semantic Mappings\n"
                    "No semantic labels assigned yet. "
                    "Run `scripts/ingest_semantic_layer.py` to apply AP242 mappings."
                )

        return "\n\n".join(sections) if sections else (
            "No STEP data found. Ingest a STEP file first via `POST /api/step/ingest`."
        )
