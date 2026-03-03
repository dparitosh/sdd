"""
Ontology Specialized Agent
Handles ingestion and querying of OWL/RDF ontology files in the knowledge graph.
Delegates RDF parsing to OntologyIngestService; queries Neo4j for ontology reference data.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from src.agents.agent_tools import Neo4jTool
from src.web.services import get_neo4j_service
from src.web.services.ontology_ingest_service import OntologyIngestConfig, OntologyIngestService


# Allowed OWL source roots (relative to repo root)
_ALLOWED_OWL_DIRS = [
    "smrlv12/data/domain_models",
    "smrlv12/data/core_model",
    "data/uploads",
    "data/raw",
]


class OntologyAgent:
    """
    Specialized agent for OWL/RDF ontology operations.

    Capabilities:
    - Ingest OWL/TTL/RDF files via OntologyIngestService → Neo4j
    - Query :ExternalOwlClass, :OWLProperty, :ExternalUnit, :ValueType, :Classification
    - Browse class hierarchies (SUBCLASS_OF / EQUIVALENT_CLASS)
    - Resolve terminology: find classes/properties by keyword
    - Cross-reference AP level tags (AP239 / AP242 / AP243)
    """

    def __init__(self):
        self.neo4j = get_neo4j_service()
        self.tool = Neo4jTool()

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def ingest_file(
        self,
        file_path: str,
        ontology_name: Optional[str] = None,
        ap_level: str = "AP243",
        rdf_format: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Ingest an OWL/RDF/Turtle file into Neo4j.

        Args:
            file_path:     Absolute or repo-relative path to .owl/.ttl/.rdf/.xml
            ontology_name: Override the displayed ontology name
            ap_level:      AP level tag applied to all ingested nodes (AP239/AP242/AP243)
            rdf_format:    Optional rdflib format hint ('xml', 'turtle', 'json-ld', …)

        Returns:
            OntologyIngestResult as a dict
        """
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"Ontology file not found: {p}")

        cfg = OntologyIngestConfig(
            ap_level=ap_level,
            ap_schema=ap_level,
            ap_standard=ap_level,
        )
        svc = OntologyIngestService(cfg)
        result = svc.ingest_file(p, ontology_name=ontology_name, rdf_format=rdf_format)
        logger.info(f"OntologyAgent.ingest_file: {p.name} -> triples={result.triples}")
        return result.__dict__

    def ingest_standard_ontologies(self) -> List[Dict[str, Any]]:
        """
        Ingest the three standard MoSSEC ontologies:
          - AP243-MoSSEC (ap243_v1.owl)
          - STEP-Core-v4  (core_v4.owl)
          - PLCS-4439     (4439_rd_v2.owl)

        Returns list of result dicts.
        """
        from pathlib import Path as _P

        repo_root = _P(__file__).resolve().parents[3]
        files = [
            (repo_root / "smrlv12/data/domain_models/mossec/ap243_v1.owl", "AP243-MoSSEC", "AP243"),
            (repo_root / "smrlv12/data/core_model/core_v4.owl", "STEP-Core-v4", "AP243"),
            (
                repo_root
                / "smrlv12/data/domain_models/product_life_cycle_support/4439_rd_v2.owl",
                "PLCS-4439",
                "AP243",
            ),
        ]
        results = []
        for path, name, ap in files:
            if not path.exists():
                logger.warning(f"OntologyAgent: standard OWL file missing: {path}")
                results.append({"name": name, "error": f"file not found: {path}"})
                continue
            try:
                stats = self.ingest_file(str(path), ontology_name=name, ap_level=ap)
                results.append({"name": name, **stats})
            except Exception as exc:
                logger.error(f"OntologyAgent: failed to ingest {name}: {exc}")
                results.append({"name": name, "error": str(exc)})
        return results

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def _run(self, cypher: str, params: Optional[Dict] = None, limit: int = 50) -> List[Dict]:
        return self.tool.search_artifacts(cypher, params=params or {}, limit=limit)

    def list_ontologies(self) -> List[Dict]:
        """Return all :Ontology nodes with class + property counts."""
        return self._run(
            "MATCH (o:Ontology) "
            "OPTIONAL MATCH (o)-[:DEFINES_REFERENCE_DATA]->(n) "
            "WITH o, count(n) AS ref_nodes "
            "RETURN coalesce(o.name, o.uri, 'Unknown') AS name, "
            "       coalesce(o.uri, '') AS uri, "
            "       coalesce(o.ap_level, o.ap_standard, '') AS ap_level, "
            "       coalesce(o.source_file, '') AS source_file, "
            "       ref_nodes "
            "ORDER BY name LIMIT $limit",
            limit=30,
        )

    def find_classes(self, keyword: str, limit: int = 20) -> List[Dict]:
        """Search :ExternalOwlClass nodes by name keyword."""
        return self._run(
            "MATCH (c:ExternalOwlClass) "
            "WHERE toLower(c.name) CONTAINS toLower($kw) "
            "   OR toLower(coalesce(c.description,'')) CONTAINS toLower($kw) "
            "RETURN c.name AS name, c.uri AS uri, "
            "       coalesce(c.ontology,'') AS ontology, "
            "       coalesce(c.ap_level,'') AS ap_level "
            "ORDER BY c.name LIMIT $limit",
            params={"kw": keyword},
            limit=limit,
        )

    def class_hierarchy(self, class_name: str, depth: int = 3) -> List[Dict]:
        """Return SUBCLASS_OF hierarchy for a named class (up to depth hops)."""
        return self._run(
            "MATCH path = (c:ExternalOwlClass)-[:SUBCLASS_OF*1..3]->(parent:ExternalOwlClass) "
            "WHERE toLower(c.name) CONTAINS toLower($kw) "
            "RETURN c.name AS child, parent.name AS parent, length(path) AS depth "
            "ORDER BY depth, child LIMIT $limit",
            params={"kw": class_name},
            limit=50,
        )

    def find_properties(self, keyword: str, limit: int = 20) -> List[Dict]:
        """Search :OWLProperty nodes (ObjectProperty + DatatypeProperty)."""
        return self._run(
            "MATCH (p:OWLProperty) "
            "WHERE toLower(p.name) CONTAINS toLower($kw) "
            "RETURN p.name AS name, p.owl_type AS owl_type, "
            "       coalesce(p.ontology,'') AS ontology, "
            "       coalesce(p.range_datatype, p.range_uri,'') AS range "
            "ORDER BY p.name LIMIT $limit",
            params={"kw": keyword},
            limit=limit,
        )

    def find_units(self, keyword: Optional[str] = None, limit: int = 30) -> List[Dict]:
        """Return :ExternalUnit nodes, optionally filtered by name keyword."""
        if keyword:
            return self._run(
                "MATCH (u:ExternalUnit) "
                "WHERE toLower(u.name) CONTAINS toLower($kw) "
                "   OR toLower(coalesce(u.symbol,'')) CONTAINS toLower($kw) "
                "RETURN u.name AS name, coalesce(u.symbol,'') AS symbol, "
                "       coalesce(u.ontology,'') AS ontology "
                "ORDER BY u.name LIMIT $limit",
                params={"kw": keyword},
                limit=limit,
            )
        return self._run(
            "MATCH (u:ExternalUnit) "
            "RETURN u.name AS name, coalesce(u.symbol,'') AS symbol, "
            "       coalesce(u.ontology,'') AS ontology "
            "ORDER BY u.name LIMIT $limit",
            limit=limit,
        )

    def find_classifications(self, keyword: Optional[str] = None, limit: int = 30) -> List[Dict]:
        """Return :Classification (SKOS concept) nodes."""
        if keyword:
            return self._run(
                "MATCH (c:Classification) "
                "WHERE toLower(c.name) CONTAINS toLower($kw) "
                "RETURN c.name AS name, coalesce(c.code,'') AS code, "
                "       coalesce(c.classification_system,'') AS system "
                "ORDER BY c.name LIMIT $limit",
                params={"kw": keyword},
                limit=limit,
            )
        return self._run(
            "MATCH (c:Classification) "
            "RETURN c.name AS name, coalesce(c.code,'') AS code, "
            "       coalesce(c.classification_system,'') AS system "
            "ORDER BY c.name LIMIT $limit",
            limit=limit,
        )

    def ap_level_distribution(self) -> List[Dict]:
        """Count all reference-data nodes per AP level."""
        return self._run(
            "MATCH (n) "
            "WHERE (n:ExternalOwlClass OR n:OWLProperty OR n:ExternalUnit "
            "       OR n:ValueType OR n:Classification) "
            "RETURN coalesce(n.ap_level,'unknown') AS ap_level, "
            "       labels(n)[0] AS label, count(*) AS cnt "
            "ORDER BY cnt DESC LIMIT 20",
            limit=20,
        )

    # ------------------------------------------------------------------
    # High-level summary (called by orchestrator node)
    # ------------------------------------------------------------------

    def summarize(self, query: str) -> str:
        """
        Produce a markdown summary relevant to the user query.
        Called from ontology_agent_node in the orchestrator workflow.
        """
        q_lower = query.lower()
        sections: List[str] = []

        # List ingested ontologies
        onts = self.list_ontologies()
        if onts:
            lines = "\n".join(
                f"- **{r.get('name','?')}**"
                + (f" [{r['ap_level']}]" if r.get("ap_level") else "")
                + (f" — {r['ref_nodes']:,} ref-data nodes" if r.get("ref_nodes") else "")
                + (f"\n  `{r['source_file']}`" if r.get("source_file") else "")
                for r in onts
            )
            sections.append(f"### Loaded Ontologies ({len(onts)})\n{lines}")
        else:
            sections.append(
                "### Ontologies\nNo ontologies ingested yet.\n"
                "Run: `python scripts/ingest_ontology_rdf.py smrlv12/data/domain_models/mossec/ap243_v1.owl`\n"
                "Or use `POST /api/ontology/ingest`."
            )

        # AP level distribution
        ap_rows = self.ap_level_distribution()
        if ap_rows:
            from itertools import groupby
            ap_map: Dict[str, int] = {}
            for r in ap_rows:
                ap = r.get("ap_level", "unknown")
                ap_map[ap] = ap_map.get(ap, 0) + r.get("cnt", 0)
            ap_lines = "  |  ".join(f"**{ap}**: {cnt:,}" for ap, cnt in sorted(ap_map.items()))
            sections.append(f"### Reference Data by AP Level\n{ap_lines}")

        # Class search
        if any(k in q_lower for k in ("class", "concept", "type", "entity")):
            kw_match = re.search(
                r"(?:class|concept|type|entity)\s+['\"]?([a-z][a-z_0-9]*)['\"]?", q_lower
            )
            kw = kw_match.group(1) if kw_match else ""
            if kw:
                classes = self.find_classes(kw, limit=15)
                if classes:
                    lines = "\n".join(
                        f"- **{r.get('name','?')}** `{r.get('uri','')[:60]}` [{r.get('ap_level','')}]"
                        for r in classes
                    )
                    sections.append(f"### Classes matching '{kw}' ({len(classes)})\n{lines}")

        # Property search
        if any(k in q_lower for k in ("property", "attribute", "relation", "predicate")):
            kw_match = re.search(
                r"(?:property|attribute|relation|predicate)\s+['\"]?([a-z][a-z_0-9]*)['\"]?", q_lower
            )
            kw = kw_match.group(1) if kw_match else ""
            if kw:
                props = self.find_properties(kw, limit=15)
                if props:
                    lines = "\n".join(
                        f"- **{r.get('name','?')}** `{r.get('owl_type','?')}` → `{r.get('range','')}`"
                        for r in props
                    )
                    sections.append(f"### Properties matching '{kw}' ({len(props)})\n{lines}")

        # Units
        if any(k in q_lower for k in ("unit", "measure", "qudt", "si ")):
            kw_match = re.search(r"unit[s]?\s+(?:for\s+)?([a-z][a-z_0-9]*)", q_lower)
            kw = kw_match.group(1) if kw_match else None
            units = self.find_units(keyword=kw, limit=20)
            if units:
                lines = "\n".join(
                    f"- **{r.get('name','?')}** `{r.get('symbol','')}` ({r.get('ontology','')})"
                    for r in units
                )
                sections.append(f"### Units ({len(units)} found)\n{lines}")

        # Classifications
        if any(k in q_lower for k in ("classif", "skos", "concept")):
            kw_match = re.search(r"classif\w*\s+['\"]?([a-z][a-z_0-9]*)['\"]?", q_lower)
            kw = kw_match.group(1) if kw_match else None
            classifs = self.find_classifications(keyword=kw, limit=20)
            if classifs:
                lines = "\n".join(
                    f"- **{r.get('name','?')}** `{r.get('code','')}` ({r.get('system','')})"
                    for r in classifs
                )
                sections.append(f"### Classifications ({len(classifs)} found)\n{lines}")

        # Class hierarchy
        if any(k in q_lower for k in ("hierarch", "subclass", "parent", "inherit")):
            kw_match = re.search(
                r"(?:hierarch|subclass|parent|inherit)\w*\s+(?:of\s+)?['\"]?([a-z][a-z_0-9\s]*?)['\"]?(?:$|\s+in)",
                q_lower,
            )
            kw = kw_match.group(1).strip() if kw_match else ""
            if kw:
                hierarchy = self.class_hierarchy(kw, depth=3)
                if hierarchy:
                    lines = "\n".join(
                        f"- `{r.get('child','?')}` → `{r.get('parent','?')}` (depth {r.get('depth')})"
                        for r in hierarchy
                    )
                    sections.append(f"### Class Hierarchy for '{kw}'\n{lines}")

        # Coverage stats
        cls_cnt = self._run("MATCH (n:ExternalOwlClass) RETURN count(n) AS cnt", limit=1)
        prop_cnt = self._run("MATCH (n:OWLProperty) RETURN count(n) AS cnt", limit=1)
        unit_cnt = self._run("MATCH (n:ExternalUnit) RETURN count(n) AS cnt", limit=1)
        cls_n = cls_cnt[0].get("cnt", 0) if cls_cnt else 0
        prop_n = prop_cnt[0].get("cnt", 0) if prop_cnt else 0
        unit_n = unit_cnt[0].get("cnt", 0) if unit_cnt else 0
        sections.append(
            f"### Reference-Data Inventory\n"
            f"- `:ExternalOwlClass` — **{cls_n:,}** nodes\n"
            f"- `:OWLProperty` (object + datatype) — **{prop_n:,}** nodes\n"
            f"- `:ExternalUnit` — **{unit_n:,}** nodes"
        )

        return "\n\n".join(sections) if sections else (
            "No ontology data found. Ingest an OWL file first via `POST /api/ontology/ingest`."
        )
