"""Semantic Agent — RAG pipeline over the knowledge graph.

Provides two high-level operations:

1. ``semantic_search(query, top_k, expand, threshold)``
      Embed → kNN → Neo4j expansion → assemble context.

2. ``semantic_insight(question, top_k)``
      semantic_search → build prompt → LLM synthesis → markdown answer + sources.

Falls back to Neo4j full-text search when OpenSearch is unreachable.
"""

from __future__ import annotations

import os
import re
import time as _time
from typing import Any, Dict, Generator, List, Optional

import requests
from loguru import logger

from src.web.services import get_neo4j_service

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL") or os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")
CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL") or os.getenv("OLLAMA_MODEL") or "llama3:latest"
# Accept all env var naming conventions for OpenSearch
OPENSEARCH_HOST = (
    os.getenv("VECTORSTORE_HOST")
    or os.getenv("OPENSEARCH_URL")
    or os.getenv("OPENSEARCH_HOST")
    or "http://localhost:9200"
)
# Accept both index name styles
OPENSEARCH_INDEX = os.getenv("OPENSEARCH_INDEX") or os.getenv("VECTORSTORE_INDEX") or "embeddings"

# ---------------------------------------------------------------------------
# Cypher helpers
# ---------------------------------------------------------------------------

_EXPAND_2HOP = """
MATCH (center {uid: $uid})-[r*1..2]-(neighbor)
RETURN center.uid                              AS center_uid,
       COALESCE(center.name, center.uid)       AS center_name,
       [rel IN r | type(rel)]                  AS rel_types,
       neighbor.uid                            AS neighbor_uid,
       COALESCE(neighbor.name, neighbor.uid)   AS neighbor_name,
       labels(neighbor)                        AS neighbor_labels
LIMIT 50
"""

_FULLTEXT_FALLBACK = """
CALL db.index.fulltext.queryNodes('plmxml_fulltext', $query)
YIELD node, score
RETURN COALESCE(node.id, node.uid, elementId(node)) AS uid,
       COALESCE(node.name, node.label, node.uid)      AS name,
       labels(node)                                    AS labels,
       score
ORDER BY score DESC
LIMIT $top_k
"""

_GENERIC_SEARCH_FALLBACK = """
MATCH (node)
WHERE toLower(COALESCE(node.name, node.label, '')) CONTAINS toLower($query)
   OR toLower(COALESCE(node.description, '')) CONTAINS toLower($query)
   OR toLower(COALESCE(node.uid, '')) CONTAINS toLower($query)
   OR toLower(COALESCE(node.product_id, '')) CONTAINS toLower($query)
RETURN COALESCE(node.id, node.uid, elementId(node))        AS uid,
       COALESCE(node.name, node.label, node.uid)            AS name,
       labels(node)                                         AS labels,
       COALESCE(node.description, node.definition, '')      AS description,
       1.0                                                  AS score
ORDER BY CASE WHEN toLower(COALESCE(node.name, node.uid, '')) STARTS WITH toLower($query) THEN 0 ELSE 1 END
LIMIT $top_k
"""

# Exact lookup by any ID field — used when the query contains a recognisable ID token.
# Searches uid, product_id, item_id, name, and id in one pass and returns full properties.
_EXACT_ID_LOOKUP = """
MATCH (node)
WHERE node.uid          = $token
   OR node.product_id   = $token
   OR node.item_id      = $token
   OR node.id           = $token
   OR node.name         = $token
   OR toLower(node.uid)        CONTAINS toLower($token)
   OR toLower(node.product_id) CONTAINS toLower($token)
RETURN COALESCE(node.uid, node.product_id, node.id, elementId(node))  AS uid,
       COALESCE(node.name, node.uid, node.product_id)                  AS name,
       labels(node)                                                     AS labels,
       COALESCE(node.description, node.definition, '')                  AS description,
       properties(node)                                                  AS props,
       1.0                                                              AS score
ORDER BY CASE WHEN node.uid = $token OR node.product_id = $token THEN 0 ELSE 1 END
LIMIT $top_k
"""

# Optimised: caller resolves exact label(s) from schema cache, then queries only those
_LABEL_SEARCH_FALLBACK = """
MATCH (node)
WHERE any(lbl IN labels(node) WHERE lbl IN $labels)
  AND (
    toLower(COALESCE(node.name, node.item_id, node.label, '')) CONTAINS toLower($query)
    OR toLower(COALESCE(node.description, node.definition, '')) CONTAINS toLower($query)
    OR TRUE  -- include all nodes of this type for listing queries
  )
RETURN COALESCE(node.id, node.uid, elementId(node))        AS uid,
       COALESCE(node.name, node.item_id, node.label, node.uid) AS name,
       labels(node)                                         AS labels,
       COALESCE(node.description, node.definition, '')      AS description,
       0.5                                                  AS score
ORDER BY name
LIMIT $top_k
"""

# Matches nodes whose *label* (type name) contains the keyword.
# Used when the user asks a list/inventory question like "list of dossiers".
# NOTE: _TYPE_MATCH_FALLBACK is only used when _label_match_from_schema() returns nothing.
_TYPE_MATCH_FALLBACK = """
MATCH (node)
WHERE any(lbl IN labels(node)
          WHERE toLower(lbl) CONTAINS toLower($keyword)
             OR toLower($keyword) CONTAINS toLower(lbl))
RETURN COALESCE(node.id, node.uid, elementId(node))        AS uid,
       COALESCE(node.name, node.item_id, node.label, node.uid) AS name,
       labels(node)                                         AS labels,
       COALESCE(node.description, node.definition, '')      AS description,
       0.3                                                  AS score
ORDER BY name
LIMIT $top_k
"""

# Fast schema-level overview using the built-in metadata procedure.
# db.schema.visualization() is O(1) — reads the schema meta-graph, never scans data edges.
_SCHEMA_VIZ_QUERY = "CALL db.schema.visualization() YIELD nodes, relationships RETURN nodes, relationships"

# Ontology-specific query: returns OWL class hierarchy + object-property domain/range
_ONTOLOGY_OVERVIEW_QUERY = """
MATCH (c)
WHERE any(l IN labels(c) WHERE l IN ['OWLClass','OntologyClass','OWLObjectProperty','OWLDatatypeProperty','Ontology'])
OPTIONAL MATCH (c)-[r]->(t)
RETURN COALESCE(c.name, c.label, c.uid, elementId(c)) AS name,
       labels(c)                                        AS nodeLabels,
       type(r)                                          AS relType,
       COALESCE(t.name, t.label, t.uid)                 AS targetName,
       labels(t)                                        AS targetLabels
ORDER BY name
LIMIT 80
"""

# ---------------------------------------------------------------------------
# Schema & index metadata cache (module-level, shared across all agent instances)
# ---------------------------------------------------------------------------

_SCHEMA_CACHE: Dict[str, Any] = {"labels": None, "ts": 0.0}
_INDEX_CACHE:  Dict[str, Any] = {"has_plmxml_fulltext": None, "ts": 0.0}
_SCHEMA_TTL = 3600   # 1 hour — label set doesn't change unless DB is reloaded
_INDEX_TTL  = 3600


def _cached_labels(neo4j) -> set:
    """Return the set of existing node labels from a 1-hour metadata cache."""
    now = _time.time()
    if _SCHEMA_CACHE["labels"] is not None and now - _SCHEMA_CACHE["ts"] < _SCHEMA_TTL:
        return _SCHEMA_CACHE["labels"]
    try:
        with neo4j.driver.session(database=neo4j.database) as s:
            rows = list(s.run("CALL db.labels() YIELD label RETURN label"))
        labels = {r["label"] for r in rows}
    except Exception as exc:
        logger.debug(f"_cached_labels failed: {exc}")
        labels = set()
    _SCHEMA_CACHE.update({"labels": labels, "ts": now})
    logger.debug(f"[schema cache] {len(labels)} labels loaded")
    return labels


def _cached_fulltext_index_exists(neo4j) -> bool:
    """Return True if the plmxml_fulltext index exists (cached 1 hour)."""
    now = _time.time()
    if _INDEX_CACHE["has_plmxml_fulltext"] is not None and now - _INDEX_CACHE["ts"] < _INDEX_TTL:
        return _INDEX_CACHE["has_plmxml_fulltext"]
    try:
        with neo4j.driver.session(database=neo4j.database) as s:
            rows = list(s.run(
                "CALL db.indexes() YIELD name RETURN name"
            ))
        exists = any("plmxml_fulltext" in r["name"] for r in rows)
    except Exception as exc:
        logger.debug(f"_cached_fulltext_index_exists failed: {exc}")
        exists = False
    _INDEX_CACHE.update({"has_plmxml_fulltext": exists, "ts": now})
    logger.debug(f"[index cache] plmxml_fulltext exists={exists}")
    return exists


def _label_match_from_schema(keyword: str, existing_labels: set) -> list:
    """Return labels from the schema that match *keyword* (case-insensitive contains).

    Checks both plural and singular form so 'dossiers' matches 'SimulationDossier'.
    Returns a list of matching label strings, or [] if none match.
    """
    kw = keyword.lower()
    kw_singular = kw[:-1] if kw.endswith("s") and len(kw) > 3 else kw
    matched = [
        lbl for lbl in existing_labels
        if kw in lbl.lower() or kw_singular in lbl.lower()
    ]
    return matched


# ---------------------------------------------------------------------------
# Structural / topology query helpers
# ---------------------------------------------------------------------------

# Patterns that indicate the user is asking about graph STRUCTURE or CONNECTIVITY,
# not looking up a specific named entity.
_STRUCTURAL_RE = re.compile(
    r"""(?:
        traceab|
        connect(?:ed(?!\s+to\s+\w)|ion|ivity)|
        how\s+(?:are|is)\s+(?:\w+\s+)?(?:nodes?|things?|items?|elements?)\s+(?:linked|connected|related|structured)|
        graph\s+(?:struct|overview|topolog|layout|map)|
        node\s+type|
        what\s+(?:type|kind|label|relation(?:ship)?)\s+|
        topolog|
        linkage|
        assoc(?:iation|iated)|
        dependenc|
        hierarchy|
        (?:parent|child)\s+(?:node|type|relation)|
        upstream|downstream|
        overview\s+of|
        network\s+(?:of|struct)|
        provide\s+(?:an?\s+)?(?:overview|summar|traceab)|
        what\s+nodes?\s+exist|
        what\s+(?:are\s+)?(?:the\s+)?(?:node|label|type|relation)|
        how\s+(?:are|is)\s+(?:\w+\s+)?(?:graph|data|information)\s+(?:organiz|structur|laid\s+out)
    )""",
    re.VERBOSE | re.IGNORECASE,
)


def _is_structural_query(query: str) -> bool:
    """Return True when the query is about graph topology / connectivity rather than entity lookup."""
    return bool(_STRUCTURAL_RE.search(query))


# Matches ID-like tokens inside any query string regardless of surrounding words.
# Examples: DOS-2024-003, REQ-001, SIM-RUN-003, AP-239, DOSSIER-2024-001
_ID_TOKEN_RE = re.compile(
    r'\b([A-Z][A-Z0-9]{1,9}(?:-[A-Z0-9]{1,10}){1,4})\b'
)


def _extract_id_token(query: str) -> Optional[str]:
    """Return the first ID-pattern token found in *query*, else None.

    ID tokens look like ``DOS-2024-003``, ``REQ-001``, ``SIM-RUN-003``.
    Only matches tokens that contain at least one digit segment so that
    plain abbreviations like "AP" (no dash) are ignored.
    """
    for m in _ID_TOKEN_RE.finditer(query.upper()):
        token = m.group(1)
        # Must have at least one purely-numeric segment (rules out e.g. "AP-CAD")
        if any(part.isdigit() for part in token.split('-')):
            return token
    return None


def _structural_context_fallback(
    neo4j,
    query: str,
    existing_labels: set,
    top_k: int,
    focus_area: Optional[str] = None,
    node_types: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Synthesise pseudo-hits describing graph schema/connectivity for structural queries.

    Uses ``db.schema.visualization()`` (O(1) metadata proc) for all cases.
    When *focus_area* is ``'ONTOLOGY'``, queries OWL/ontology nodes directly.
    When *node_types* is provided, filters the schema viz result client-side.
    """
    hits: List[Dict[str, Any]] = []
    rel_grouped: Dict[str, List[str]] = {}

    with neo4j.driver.session(database=neo4j.database) as session:

        # ── Ontology focus: query OWL class / property nodes directly ────────
        if focus_area == "ONTOLOGY":
            try:
                rows = list(session.run(_ONTOLOGY_OVERVIEW_QUERY))
                # Collect class names
                class_names: List[str] = []
                prop_grouped: Dict[str, List[str]] = {}
                for r in rows:
                    lbl_list = list(r.get("nodeLabels") or [])
                    if any(l in lbl_list for l in ("OWLClass", "OntologyClass","Ontology")):
                        n = r.get("name")
                        if n and n not in class_names:
                            class_names.append(n)
                    rel = r.get("relType")
                    target = r.get("targetName")
                    if rel and target:
                        prop_grouped.setdefault(rel, []).append(
                            f"{r.get('name','?')} → {target}"
                        )
                if class_names:
                    hits.append({
                        "uid": "__structural_labels__",
                        "name": "Ontology Classes",
                        "labels": ["_SchemaInfo"],
                        "description": ", ".join(class_names[:60]),
                        "score": 1.0,
                        "structural": True,
                    })
                if prop_grouped:
                    # Consolidate all property/rel types into ONE hit (same as general path)
                    # to keep the LLM prompt compact and fast
                    hits.append({
                        "uid": "__structural_rel_types__",
                        "name": "Ontology Properties & Relationships",
                        "labels": ["_SchemaInfo"],
                        "description": ", ".join(list(prop_grouped.keys())[:60]),
                        "score": 0.9,
                        "structural": True,
                    })
                logger.info(f"SemanticAgent: ONTOLOGY structural context — {len(hits)} schema hits")
                return {"hits": hits, "expanded": {}, "fallback": True, "structural": True}
            except Exception as exc:
                logger.debug(f"_structural_context_fallback ONTOLOGY query failed: {exc}")

        # ── All cases: use O(1) metadata procedures — never scan data edges ────
        # db.relationshipTypes() lists all rel type names in < 5 ms (metadata call).
        # The LLM can reason about their meaning without needing (from→to) mappings.
        if not rel_grouped:
            try:
                rel_rows = list(session.run(
                    "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType"
                ))
                rel_types = [r["relationshipType"] for r in rel_rows]
                # Group all rel types into one pseudo-entry so the LLM gets a clean list
                # Use rel_grouped[type] = [type] so the build-hits loop below works unchanged
                for rt in rel_types:
                    rel_grouped[rt] = [rt]
                logger.info(
                    f"SemanticAgent: db.relationshipTypes() returned {len(rel_grouped)} types"
                )
            except Exception as exc:
                logger.debug(f"_structural_context_fallback rel-types failed: {exc}")

    # ── Build pseudo-hits ─────────────────────────────────────────────────────
    # Filter labels to those relevant to the active node_types list (if given)
    if node_types:
        display_labels = sorted(lbl for lbl in node_types if not lbl.startswith("_"))
    else:
        display_labels = sorted(lbl for lbl in existing_labels if not lbl.startswith("_"))

    if display_labels:
        hits.append({
            "uid": "__structural_labels__",
            "name": "Node Types in Graph",
            "labels": ["_SchemaInfo"],
            "description": ", ".join(display_labels[:60]),
            "score": 1.0,
            "structural": True,
        })

    if rel_grouped:
        # Consolidate all rel types into one readable pseudo-hit
        hits.append({
            "uid": "__structural_rel_types__",
            "name": "Relationship Types",
            "labels": ["_SchemaInfo"],
            "description": ", ".join(list(rel_grouped.keys())[:60]),
            "score": 0.9,
            "structural": True,
        })

    logger.info(
        f"SemanticAgent: structural fallback — {len(hits)} pseudo-hits "
        f"(focus={focus_area}, node_types={node_types})"
    )
    return {
        "hits": hits,
        "expanded": {},
        "fallback": True,
        "structural": True,
    }


# Regex to strip common list/intent prefixes before keyword matching.
_INTENT_RE = re.compile(
    r"""^(?:
        list\s+(?:of\s+)?(?:all\s+)?|
        show\s+(?:me\s+)?(?:all\s+)?(?:the\s+)?|
        find\s+(?:all\s+)?(?:the\s+)?|
        get\s+(?:all\s+)?(?:the\s+)?|
        give\s+me\s+(?:all\s+)?(?:the\s+)?|
        what\s+are\s+(?:all\s+)?(?:the\s+)?|
        what\s+is\s+(?:a\s+)?|
        tell\s+me\s+about\s+|
        display\s+(?:all\s+)?(?:the\s+)?|
        describe\s+(?:all\s+)?(?:the\s+)?|
        enumerate\s+(?:all\s+)?(?:the\s+)?|
        count\s+(?:all\s+)?(?:the\s+)?|
        how\s+many\s+
    )""",
    re.VERBOSE | re.IGNORECASE,
)


def _strip_intent(query: str) -> str:
    """Strip leading intent phrases and return the core keyword(s).

    Applied recursively so compound prefixes like "Show me list of X"
    are fully unwrapped in two passes: "list of X" → "X".

    Examples::

        "list of dossiers"          -> "dossiers"
        "show me list of dossiers"  -> "dossiers"
        "show all Parts"            -> "Parts"
        "find the requirements"     -> "requirements"
        "what are simulations"      -> "simulations"
    """
    stripped = _INTENT_RE.sub("", query.strip()).strip().rstrip("?.,!")
    # Recurse until stable (handles "show me list of X" → "list of X" → "X")
    while True:
        next_pass = _INTENT_RE.sub("", stripped).strip().rstrip("?.,!")
        if next_pass == stripped or not next_pass:
            break
        stripped = next_pass
    # Return first three words at most so the label matching stays tight
    words = stripped.split()[:3]
    return " ".join(words) if words else query


# ---------------------------------------------------------------------------
# SemanticAgent
# ---------------------------------------------------------------------------

class SemanticAgent:
    """RAG-style semantic agent over PLM knowledge graph."""

    def __init__(self):
        self.neo4j = get_neo4j_service()

    # -- public API ----------------------------------------------------------

    def semantic_search(
        self,
        query: str,
        top_k: int = 10,
        expand: bool = True,
        threshold: float = 0.5,
        focus_area: Optional[str] = None,
        node_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Embed *query*, run kNN, optionally expand hits in graph.

        Returns ``{"hits": [...], "expanded": {...}}``.
        """
        # Step 0: structural/topology queries go straight to schema fallback — no embedding needed
        if _is_structural_query(query):
            logger.info("SemanticAgent.semantic_search: structural query — bypassing embedding")
            return self._fulltext_fallback(
                query, top_k, focus_area=focus_area, node_types=node_types
            )

        # Step 0b: exact ID-token lookup (e.g. "DOS-2024-003") — bypass kNN entirely
        id_token = _extract_id_token(query)
        if id_token:
            logger.info(f"SemanticAgent.semantic_search: ID token detected — exact lookup for '{id_token}'")
            id_result = self._exact_id_lookup(id_token, top_k, expand=expand)
            if id_result.get("hits"):
                return id_result
            logger.info(f"SemanticAgent: exact ID lookup found nothing for '{id_token}', continuing to kNN")

        # Step 0c: MBSE direct Cypher intent — detect known MBSE phrases and query Neo4j directly,
        # bypassing OpenSearch entirely (which doesn't index these abstract query terms).
        try:
            cypher_result = self._cypher_intent_query(query, top_k, focus_area=focus_area)
            if cypher_result and cypher_result.get("hits"):
                logger.info("SemanticAgent: Cypher intent match — returning direct Neo4j results")
                return cypher_result
        except Exception as _cypher_exc:
            logger.warning(f"SemanticAgent._cypher_intent_query error (will fall through): {_cypher_exc}")

        # Step 1: embed
        embedding = self._embed(query)
        if embedding is None:
            logger.warning("SemanticAgent: embedding failed, falling back to full-text")
            return self._fulltext_fallback(query, top_k, focus_area=focus_area, node_types=node_types)

        # Step 2: kNN search
        hits = self._knn_search(embedding, top_k, threshold)
        if hits is None:
            logger.warning("SemanticAgent: OpenSearch unreachable, falling back to full-text")
            return self._fulltext_fallback(query, top_k, focus_area=focus_area, node_types=node_types)
        if not hits:
            logger.info("SemanticAgent: kNN returned 0 hits (threshold too high or no embeddings found), falling back to Neo4j search")
            return self._fulltext_fallback(query, top_k, focus_area=focus_area, node_types=node_types)

        # Step 2b: keyword relevance check — if the user asked an intent/list query
        # (e.g. "list of dossiers") and NONE of the kNN hits contain the keyword in
        # their uid or labels, the kNN results are off-topic; fall through to Neo4j.
        keyword = _strip_intent(query)
        if keyword.lower() != query.strip().lower():
            # Intent was stripped — user is asking for a category/type
            # Also check singular form (e.g. "dossiers" → "dossier")
            kw_singular = keyword[:-1] if keyword.endswith("s") and len(keyword) > 3 else keyword

            def _hit_matches(hit: Dict[str, Any], kw: str) -> bool:
                uid_lower = hit.get("uid", "").lower()
                text_lower = hit.get("text", "").lower()
                label_lower = " ".join(hit.get("labels", [])).lower()
                kw_lower = kw.lower()
                return kw_lower in uid_lower or kw_lower in text_lower or kw_lower in label_lower

            if not any(_hit_matches(h, keyword) for h in hits) and \
               not any(_hit_matches(h, kw_singular) for h in hits):
                logger.info(
                    f"SemanticAgent: kNN hits don't match keyword '{keyword}' (singular='{kw_singular}') — "
                    "falling back to type-intent search"
                )
                return self._fulltext_fallback(
                    query, top_k, focus_area=focus_area, node_types=node_types
                )

        # Step 3: Neo4j 2-hop expansion
        expanded: Dict[str, List[Dict]] = {}
        if expand:
            for hit in hits:
                uid = hit.get("uid")
                if uid:
                    expanded[uid] = self._expand(uid)

        return {"hits": hits, "expanded": expanded}

    def semantic_insight(
        self,
        question: str,
        top_k: int = 5,
        focus_area: Optional[str] = None,
        node_types: Optional[List[str]] = None,
        max_nodes: int = 500,
    ) -> Dict[str, Any]:
        """Full RAG pipeline: search → prompt → LLM → answer + sources.

        Returns ``{"answer": str, "sources": [...]}``.
        """
        search_result = self.semantic_search(
            question, top_k=top_k, expand=True,
            focus_area=focus_area, node_types=node_types,
        )
        hits = search_result.get("hits", [])
        expanded = search_result.get("expanded", {})

        is_fallback = search_result.get("fallback", False)
        is_type_match = search_result.get("type_match", False)
        is_structural = search_result.get("structural", False)

        # Build context string
        context_parts: List[str] = []

        if is_structural and hits:
            # Render schema pseudo-hits in a clean, LLM-friendly format
            for hit in hits:
                name = hit.get("name", "")
                desc = hit.get("description", "").strip()
                if name == "Node Types in Graph":
                    context_parts.append(f"### Node Types (Labels)\n{desc}")
                elif name == "Ontology Classes":
                    context_parts.append(f"### Ontology Classes\n{desc}")
                elif name in ("Relationship Types", "Ontology Properties & Relationships"):
                    context_parts.append(f"### Relationship / Property Types\n{desc}")
                elif name.startswith("Property/Relationship: ") or name.startswith("Relationship: "):
                    # Legacy per-type format — still supported
                    rel_label = name.split(": ", 1)[-1]
                    context_parts.append(f"- **{rel_label}**: {desc}")
                else:
                    # Generic Cypher-direct / MBSE intent result — render by name + description
                    context_parts.append(f"### {name}\n{desc}" if desc else f"### {name}")
        else:
            for hit in hits:
                uid = hit.get("uid", "?")
                name = hit.get("name", uid)
                score = hit.get("score", 0)
                hit_labels = hit.get("labels", [])
                desc = hit.get("description", "").strip()
                label_str = ", ".join(hit_labels) if hit_labels else ""
                desc_str = f" — {desc}" if desc else ""
                context_parts.append(
                    f"- {name} [{label_str}] (uid={uid}, score={score:.3f}){desc_str}"
                )
                neighbors = expanded.get(uid, [])
                for nb in neighbors[:5]:
                    rels = " → ".join(nb.get("rel_types", []))
                    context_parts.append(
                        f"    ↳ {rels} → {nb.get('neighbor_name', '?')} "
                        f"({', '.join(nb.get('neighbor_labels', []))})"
                    )

        if context_parts:
            context_text = "\n".join(context_parts)
        else:
            context_text = (
                "No matching nodes were found in the knowledge graph for this query.\n"
                "This may mean the relevant data has not been ingested yet, "
                "or the search terms do not match any stored node names or types."
            )

        # Build prompt — adapt tone for type-match (listing) vs empty context
        focus_note = ""
        if focus_area and focus_area != "ENTERPRISE":
            focus_note = (
                f"The user is currently viewing the **{focus_area}** focus area "
                f"(active node types: {', '.join(node_types or []) or 'all'}; "
                f"max nodes shown: {max_nodes}).\n"
            )

        if is_structural and hits:
            if focus_area == "ONTOLOGY":
                listing_note = (
                    f"{focus_note}"
                    "The context below describes the STEP ISO 10303 ONTOLOGY — OWL classes, "
                    "object/datatype properties, and their domain/range relationships as stored in "
                    "the knowledge graph.\n"
                    "Use this to explain the ontology structure, class hierarchy, and how concepts "
                    "like AP239 PLCS, AP242 Design, AP243 MoSSEC relate to each other.\n"
                )
            else:
                listing_note = (
                    f"{focus_note}"
                    "The context below describes the GRAPH SCHEMA — the node types (labels) "
                    "that exist in the knowledge graph, and the relationship types that connect them.\n"
                    "Use this schema information to answer structural, traceability, and connectivity questions. "
                    "Explain how different node types relate to each other, what the main traceability paths are, "
                    "and how information flows through the graph.\n"
                )
        elif is_type_match and hits:
            listing_note = (
                "The context below is a list of all nodes matching the requested type. "
                "Present them as a numbered or bulleted list with their names and types.\n"
            )
        else:
            listing_note = ""

        if not hits:
            empty_note = (
                "\nIMPORTANT: The search returned no results. "
                "Tell the user clearly that no matching data was found and suggest "
                "they verify that the relevant files have been ingested into the system."
            )
        else:
            empty_note = ""

        # Step 4: LLM synthesis
        prompt = (
            "You are an MBSE knowledge-graph assistant specialised in systems engineering, "
            "PLM (Product Lifecycle Management), and standards-based data models (AP239, OSLC, SysML). "
            f"{listing_note}"
            "Answer the question using ONLY the context provided below. "
            "If the context describes schema/relationship types, synthesise a clear explanation of "
            "how the graph is structured and how entities are connected.\n"
            f"{empty_note}\n\n"
            "## Context (knowledge graph results):\n"
            f"{context_text}\n\n"
            f"## Question:\n{question}\n\n"
            "## Answer (use Markdown with headers and bullet points):"
        )
        answer = self._chat(prompt)

        # Filter out structural pseudo-hits — they don't represent real graph nodes
        sources = [
            {"uid": h.get("uid"), "name": h.get("name"), "score": h.get("score")}
            for h in hits
            if not str(h.get("uid", "")).startswith("__structural_")
        ]
        return {
            "answer": answer,
            "sources": sources,
            "hits": hits,
            "expanded": expanded,
            "fallback": search_result.get("fallback", False),
            "structural": is_structural,
        }

    # -- internal methods ----------------------------------------------------

    def _build_context_and_prompt(
        self,
        question: str,
        search_result: Dict[str, Any],
        focus_area: Optional[str] = None,
        node_types: Optional[List[str]] = None,
        max_nodes: int = 500,
    ) -> Dict[str, Any]:
        """Extract context string and LLM prompt from a semantic_search result.

        Returns a dict with keys: prompt, is_fallback, is_structural, is_type_match, hits, expanded.
        """
        hits = search_result.get("hits", [])
        expanded = search_result.get("expanded", {})
        is_fallback = search_result.get("fallback", False)
        is_type_match = search_result.get("type_match", False)
        is_structural = search_result.get("structural", False)

        context_parts: List[str] = []
        if is_structural and hits:
            for hit in hits:
                name = hit.get("name", "")
                desc = hit.get("description", "").strip()
                if name == "Node Types in Graph":
                    context_parts.append(f"### Node Types (Labels)\n{desc}")
                elif name == "Ontology Classes":
                    context_parts.append(f"### Ontology Classes\n{desc}")
                elif name in ("Relationship Types", "Ontology Properties & Relationships"):
                    context_parts.append(f"### Relationship / Property Types\n{desc}")
                elif name.startswith("Property/Relationship: ") or name.startswith("Relationship: "):
                    rel_label = name.split(": ", 1)[-1]
                    context_parts.append(f"- **{rel_label}**: {desc}")
                else:
                    # Generic Cypher-direct / MBSE intent result — render by name + description
                    context_parts.append(f"### {name}\n{desc}" if desc else f"### {name}")
        else:
            for hit in hits:
                uid = hit.get("uid", "?")
                name = hit.get("name", uid)
                score = hit.get("score", 0)
                hit_labels = hit.get("labels", [])
                desc = hit.get("description", "").strip()
                label_str = ", ".join(hit_labels) if hit_labels else ""
                desc_str = f" — {desc}" if desc else ""
                context_parts.append(
                    f"- {name} [{label_str}] (uid={uid}, score={score:.3f}){desc_str}"
                )
                for nb in expanded.get(uid, [])[:5]:
                    rels = " → ".join(nb.get("rel_types", []))
                    context_parts.append(
                        f"    ↳ {rels} → {nb.get('neighbor_name', '?')} "
                        f"({', '.join(nb.get('neighbor_labels', []))})"
                    )

        context_text = "\n".join(context_parts) if context_parts else (
            "No matching nodes were found in the knowledge graph for this query.\n"
            "This may mean the relevant data has not been ingested yet, "
            "or the search terms do not match any stored node names or types."
        )

        # ── Focus-area specific context guidance ────────────────────────────────
        _FOCUS_AREA_HINTS: Dict[str, str] = {
            "AP242": (
                "**AP242 Product Model focus** — The user is exploring the AP242 Product Data model. "
                "Prioritise: Part/AP242Product nodes and BOM hierarchy (HAS_CHILD_PART, HAS_PART, BOMLink), "
                "material assignments (Material, MADE_OF, HAS_MATERIAL), geometric models (GeometricModel), "
                "configuration items (ConfigurationItem) and product definitions (ProductDefinition). "
                "Present BOM trees with parent→child relationships, highlight missing requirements or materials.\n"
            ),
            "AP243": (
                "**AP243 Simulation / MoSSEC focus** — The user is exploring simulation data conforming to AP243. "
                "Prioritise: SimulationDossier/Dossier nodes, ModelInstance, ModelType, WorkflowMethod, TaskElement, "
                "KPI, AnalysisModel, ParameterStudy, ValidationRecord, EvidenceCategory and their Run/artifact counts. "
                "Show full simulation model hierarchy, evidence category-to-dossier links, and KPI outcomes.\n"
            ),
            "DIGITAL_THREAD": (
                "**Digital Thread focus** — The user wants end-to-end traceability across the lifecycle. "
                "Trace the chain: Requirement → Part/AP242Product → SimulationDossier/Dossier → Run → EvidenceCategory → Activity. "
                "Highlight any broken links (requirements with no dossier, dossiers with no part, etc.). "
                "Include KPI and ValidationRecord nodes where present. Use arrows (→) to show the thread.\n"
            ),
            "TRACEABILITY": (
                "**Traceability focus** — Show requirement verification status. "
                "Split results into ✅ Verified requirements (linked to a dossier/evidence) and "
                "❌ Unverified requirements (no simulation evidence). "
                "Include counts and list requirement IDs with their linked dossier names.\n"
            ),
            "SIMULATION": (
                "**Simulation Models focus** — Enumerate all simulation model types and instances. "
                "Show ModelType → ModelInstance → SimulationDossier → EvidenceCategory chains. "
                "Include run counts and KPI values where available.\n"
            ),
            "ONTOLOGY": (
                "**Ontology focus** — The context describes the STEP ISO 10303 OWL ontology. "
                "Explain class hierarchy, AP239/AP242/AP243 module relationships, and how concepts map to graph labels.\n"
            ),
        }

        focus_note = ""
        if focus_area and focus_area not in ("ENTERPRISE", None):
            hint = _FOCUS_AREA_HINTS.get(focus_area, "")
            focus_note = (
                f"{hint}"
                f"Currently viewing: **{focus_area}** view "
                f"(node types: {', '.join(node_types or []) or 'all'}; limit: {max_nodes}).\n"
            )

        if is_structural and hits:
            if focus_area == "ONTOLOGY":
                listing_note = (
                    f"{focus_note}"
                    "The context below describes the STEP ISO 10303 ONTOLOGY — OWL classes, "
                    "object/datatype properties, and their domain/range relationships as stored in "
                    "the knowledge graph.\n"
                    "Use this to explain the ontology structure, class hierarchy, and how concepts "
                    "like AP239 PLCS, AP242 Design, AP243 MoSSEC relate to each other.\n"
                )
            else:
                listing_note = (
                    f"{focus_note}"
                    "The context below describes the GRAPH SCHEMA — the node types (labels) "
                    "that exist in the knowledge graph, and the relationship types that connect them.\n"
                    "Use this schema information to answer structural, traceability, and connectivity questions. "
                    "Explain how different node types relate to each other, what the main traceability paths are, "
                    "and how information flows through the graph.\n"
                )
        elif is_type_match and hits:
            listing_note = (
                "The context below is a list of all nodes matching the requested type. "
                "Present them as a numbered or bulleted list with their names and types.\n"
            )
        else:
            listing_note = ""

        empty_note = (
            "\nIMPORTANT: The search returned no results. "
            "Tell the user clearly that no matching data was found and suggest "
            "they verify that the relevant files have been ingested into the system."
        ) if not hits else ""

        # Rich MBSE system prompt — covers all AP239/AP242/AP243/Digital Thread domains
        mbse_system = (
            "You are *MoSSEC MBSE Knowledge Graph AI* — an expert assistant for "
            "Model-Based Systems Engineering (MBSE) and Product Lifecycle Management (PLM).\n"
            "You specialise in ISO 10303 STEP standards: AP239 (PLCS), AP242 (Managed Model-Based 3D Engineering), "
            "and AP243 (MoSSEC Simulation), as well as OSLC traceability, SysML block diagrams, "
            "digital thread traceability, and simulation evidence management.\n"
            "When answering: use Markdown with **bold headers**, bullet lists, and → arrows for traceability chains. "
            "Always reference specific node types and relationship names from the graph. "
            "If data is missing, clearly state what is not found and suggest next steps.\n"
        )

        prompt = (
            f"{mbse_system}"
            f"{listing_note if listing_note else focus_note}"
            "Answer the question using ONLY the context provided below. "
            "If the context describes schema/relationship types, synthesise a clear explanation of "
            "how the graph is structured and how entities are connected.\n"
            f"{empty_note}\n\n"
            "## Context (knowledge graph results):\n"
            f"{context_text}\n\n"
            f"## Question:\n{question}\n\n"
            "## Answer (use Markdown with headers and bullet points):"
        )
        # When the result came from _cypher_intent_query, the hits already contain
        # fully-formatted markdown in their description fields.  Build a clean answer
        # from those directly so the LLM can be skipped entirely (avoids Ollama timeouts).
        cypher_direct = search_result.get("cypher_direct", False)
        pre_formatted_answer: Optional[str] = None
        if cypher_direct and hits:
            # Detect if this is an AP242 BOM result and build a product-specific intro
            bom_hit = next((h for h in hits if h.get("uid") == "__cypher_ap242_bom__"), None)
            if bom_hit:
                product_title = bom_hit.get("name", "AP242 Bill of Materials")
                pre_formatted_answer = (
                    f"## {product_title}\n\n"
                    f"*Sourced from: MoSSEC MBSE Knowledge Graph · ISO 10303 AP242*\n\n"
                    + bom_hit.get("description", "").strip()
                )
            else:
                sections = []
                for hit in hits:
                    name = hit.get("name", "")
                    desc = hit.get("description", "").strip()
                    if name and desc:
                        sections.append(f"### {name}\n\n{desc}")
                    elif name:
                        sections.append(f"### {name}")
                if sections:
                    pre_formatted_answer = (
                        "*MoSSEC MBSE Knowledge Graph AI — AP239 · AP242 · AP243 · Digital Thread*\n\n"
                        + "\n\n".join(sections)
                    )

        return {
            "prompt": prompt,
            "context_text": context_text,
            "is_fallback": is_fallback,
            "is_structural": is_structural,
            "is_type_match": is_type_match,
            "cypher_direct": cypher_direct,
            "pre_formatted_answer": pre_formatted_answer,
            "hits": hits,
            "expanded": expanded,
        }

    def _embed(self, text: str) -> Optional[List[float]]:
        """Call Ollama embedding API using the canonical /api/embed batch endpoint."""
        url = f"{OLLAMA_BASE_URL.rstrip('/')}/api/embed"
        try:
            resp = requests.post(
                url,
                json={"model": EMBED_MODEL, "input": [text]},  # new batch API
                timeout=8,  # Ollama is local — 8 s is ample; fail fast if it hangs
            )
            resp.raise_for_status()
            data = resp.json()
            # New API: {"embeddings": [[...]]}
            embeddings = data.get("embeddings")
            if isinstance(embeddings, list) and embeddings:
                return embeddings[0]
            # Legacy fallback: {"embedding": [...]}
            return data.get("embedding")
        except Exception as exc:
            logger.debug(f"SemanticAgent._embed failed: {exc}")
            return None

    def _knn_search(
        self, vector: List[float], top_k: int, threshold: float
    ) -> Optional[List[Dict[str, Any]]]:
        """OpenSearch kNN approximate nearest-neighbor search."""
        url = f"{OPENSEARCH_HOST.rstrip('/')}/{OPENSEARCH_INDEX}/_search"
        body = {
            "size": top_k,
            "query": {
                "knn": {
                    "vector": {
                        "vector": vector,
                        "k": top_k,
                    }
                }
            },
            "_source": {"excludes": ["vector"]},
        }
        try:
            # Use a short timeout so the fallback triggers quickly when OpenSearch is down
            resp = requests.post(url, json=body, timeout=4)
            resp.raise_for_status()
            data = resp.json()
            raw_hits = data.get("hits", {}).get("hits", [])
            results = []
            for h in raw_hits:
                score = h.get("_score", 0)
                if score < threshold:
                    continue
                src = h.get("_source", {})
                meta = src.get("metadata", {})
                results.append({
                    "uid": h.get("_id"),
                    "text": src.get("text", ""),
                    "name": (
                        meta.get("name")
                        or meta.get("item_type")
                        or h.get("_id")
                    ),
                    "labels": meta.get("labels", []),
                    "score": score,
                    "metadata": meta,
                })
            return results
        except Exception as exc:
            logger.debug(f"SemanticAgent._knn_search failed: {exc}")
            return None

    def _expand(self, uid: str) -> List[Dict[str, Any]]:
        """2-hop Neo4j expansion around *uid*."""
        try:
            with self.neo4j.driver.session(database=self.neo4j.database) as session:
                result = session.run(_EXPAND_2HOP, uid=uid)
                return [dict(r) for r in result]
        except Exception as exc:
            logger.debug(f"SemanticAgent._expand failed for {uid}: {exc}")
            return []

    def _exact_id_lookup(
        self,
        token: str,
        top_k: int,
        expand: bool = True,
    ) -> Dict[str, Any]:
        """Look up a node by its ID fields (uid, product_id, item_id, id, name).

        Used when the user's query contains an ID-pattern token like ``DOS-2024-003``.
        Returns a standard ``{"hits": [...], "expanded": {...}}`` dict.
        The hit ``description`` is enriched with all non-null properties so the
        LLM can answer detailed factual questions about the node.
        """
        try:
            with self.neo4j.driver.session(database=self.neo4j.database) as session:
                result = session.run(_EXACT_ID_LOOKUP, token=token, top_k=top_k)
                hits: List[Dict[str, Any]] = []
                for r in result:
                    props = dict(r.get("props") or {})
                    # Build a rich description from all interesting properties
                    skip_keys = {"uid", "id", "elementId", "embedding", "vector"}
                    prop_lines = [
                        f"{k}: {v}"
                        for k, v in props.items()
                        if v is not None and k not in skip_keys and not k.startswith("_")
                    ]
                    description = r.get("description") or ""
                    if prop_lines:
                        description = (description + "\n" if description else "") + "\n".join(prop_lines)
                    hits.append({
                        "uid": r["uid"],
                        "name": r["name"],
                        "labels": list(r["labels"]),
                        "description": description,
                        "score": float(r["score"]),
                    })
                if not hits:
                    return {"hits": [], "expanded": {}, "fallback": True}
                expanded: Dict[str, List[Dict]] = {}
                if expand:
                    for hit in hits:
                        uid = hit.get("uid")
                        if uid:
                            expanded[uid] = self._expand(uid)
                logger.info(
                    f"SemanticAgent._exact_id_lookup: token='{token}' → {len(hits)} hit(s)"
                )
                return {"hits": hits, "expanded": expanded, "fallback": True}
        except Exception as exc:
            logger.warning(f"SemanticAgent._exact_id_lookup failed for '{token}': {exc}")
            return {"hits": [], "expanded": {}, "fallback": True}

    def _cypher_intent_query(
        self,
        query: str,
        top_k: int = 20,
        focus_area: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Detect MBSE intent keywords and run direct Neo4j Cypher queries.

        Bypasses OpenSearch entirely for abstract MBSE queries like
        'digital thread', 'AP242 product model', 'traceability', etc.
        Returns a structural hit-dict or None if no intent is matched.
        """
        q = query.lower()

        is_digital_thread = any(k in q for k in (
            "digital thread", "thread trace", "lifecycle chain", "end-to-end",
            "requirements to evidence", "from requirement", "req to evidence",
        ))
        is_traceability = any(k in q for k in (
            "traceab", "verified requirement", "requirement verif", "unverified",
            "trace to dossier", "requirement trace",
        ))
        is_evidence = any(k in q for k in (
            "evidence categor", "evidencecategor", "evidence type",
        ))
        is_ap243 = any(k in q for k in (
            "ap243", "simulation dossier", "list dossier", "all dossier",
            "simulation model", "model instance", "workflow method",
        ))
        is_ap242 = any(k in q for k in (
            "ap242", "product model", "bom hierarch", "bill of material",
            "material assignment", "assembly tree", "product graph",
            "show bom", "bom", "assembly structure", "parts list",
            # product-name / domain triggers
            "induction motor", "motor assembly", "5hp", "motor bom",
            "step product", "nauo", "assembly occurrence",
            "product structure", "part hierarchy", "part list",
        ))

        # Focus-area overrides when no text intent matched
        if not any([is_digital_thread, is_traceability, is_evidence, is_ap243, is_ap242]):
            if focus_area == "DIGITAL_THREAD":
                is_digital_thread = True
            elif focus_area == "AP242":
                is_ap242 = True
            elif focus_area == "AP243":
                is_ap243 = True
            elif focus_area in ("TRACEABILITY", "REQUIREMENTS"):
                is_traceability = True

        if not any([is_digital_thread, is_traceability, is_evidence, is_ap243, is_ap242]):
            return None

        def _run(cypher: str, limit: int = 30) -> List[Dict[str, Any]]:
            try:
                with self.neo4j.driver.session(database=self.neo4j.database) as _s:
                    result = _s.run(cypher, limit=limit)
                    return [dict(r) for r in result]
            except Exception as _exc:
                logger.warning(f"SemanticAgent._cypher_intent_query: Cypher error — {_exc}")
                return []

        hits: List[Dict[str, Any]] = []

        # ── Digital Thread ───────────────────────────────────────────────────
        if is_digital_thread:
            rows = _run(
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
            if rows:
                lines = "\n".join(
                    f"- REQ `{r.get('req_uid','?')}` ({r.get('req_name','?')}) "
                    f"\u2192 Part `{r.get('part_uid','?')}` "
                    f"\u2192 Dossier `{r.get('dossier_uid','?')}` "
                    f"\u2192 Run `{r.get('run_uid','?')}`"
                    + (f" \u2192 Evidence: {r.get('evidence_name')!r}" if r.get("evidence_name") else "")
                    for r in rows
                )
                hits.append({
                    "uid": "__cypher_digital_thread__",
                    "name": f"Digital Thread \u2014 Req \u2192 Part \u2192 Dossier \u2192 Run ({len(rows)} chains)",
                    "description": lines,
                    "labels": ["CypherResult"],
                    "score": 1.0,
                })
            else:
                # Fallback: any cross-domain relationships
                alt_rows = _run(
                    "MATCH (a)-[r:IMPLEMENTS|VALIDATES_USING|DERIVED_FROM|SATISFIES|"
                    "ALLOCATED_TO|HAS_SIMULATION_RUN]->(b) "
                    "RETURN labels(a)[0] AS from_lbl, coalesce(a.name,a.uid,'?') AS from_name, "
                    "       type(r) AS rel, labels(b)[0] AS to_lbl, coalesce(b.name,b.uid,'?') AS to_name "
                    "ORDER BY rel LIMIT $limit",
                    limit=30,
                )
                if alt_rows:
                    t_lines = "\n".join(
                        f"- [{r.get('from_lbl')}] **{r.get('from_name','?')}** "
                        f"\u2014[{r.get('rel')}]\u2192 [{r.get('to_lbl')}] **{r.get('to_name','?')}**"
                        for r in alt_rows
                    )
                    hits.append({
                        "uid": "__cypher_dt_rels__",
                        "name": f"Digital Thread Relationships ({len(alt_rows)} cross-domain edges)",
                        "description": t_lines,
                        "labels": ["CypherResult"],
                        "score": 1.0,
                    })
            # Always append node count summary for digital thread
            stat_rows = _run(
                "MATCH (n) WHERE n:Requirement OR n:Part OR n:AP242Product "
                "OR n:SimulationDossier OR n:EvidenceCategory OR n:SimulationRun "
                "RETURN labels(n)[0] AS lbl, count(n) AS cnt ORDER BY cnt DESC",
                limit=10,
            )
            if stat_rows:
                stat_lines = "\n".join(f"- **{r['lbl']}**: {r['cnt']:,} nodes" for r in stat_rows)
                hits.append({
                    "uid": "__cypher_dt_stats__",
                    "name": "Digital Thread Node Counts",
                    "description": stat_lines,
                    "labels": ["CypherResult"],
                    "score": 1.0,
                })

        # ── Traceability ─────────────────────────────────────────────────────
        if is_traceability:
            trace_rows = _run(
                "MATCH (req:Requirement) "
                "WHERE req.id IS NOT NULL AND NOT req.id STARTS WITH '_' "
                "OPTIONAL MATCH (req)-[:SATISFIED_BY_PART|ALLOCATED_TO]->(p) "
                "OPTIONAL MATCH (p)-[:VALIDATES_USING|VERIFIED_BY]->(d:SimulationDossier) "
                "OPTIONAL MATCH (d)-[:HAS_SIMULATION_RUN]->(run:SimulationRun) "
                "OPTIONAL MATCH (run)-[:CONTAINS_ARTIFACT]->(art:SimulationArtifact) "
                "OPTIONAL MATCH (art)-[:EVIDENCE_FOR]->(ev:EvidenceCategory) "
                "RETURN coalesce(req.id, req.uid,'?') AS req_uid, req.name AS req_name, "
                "       coalesce(p.name, p.id,'') AS design_element, "
                "       coalesce(d.uid,'') AS dossier_uid, d.name AS dossier_name, "
                "       coalesce(ev.name,'') AS evidence_name, "
                "       CASE WHEN d IS NOT NULL THEN 'verified' ELSE 'unverified' END AS trace_status "
                "ORDER BY trace_status, req.id LIMIT $limit",
                limit=40,
            )
            if trace_rows:
                verified = [r for r in trace_rows if r.get("trace_status") == "verified"]
                unverified = [r for r in trace_rows if r.get("trace_status") != "verified"]
                if verified:
                    v_lines = "\n".join(
                        f"- \u2705 `{r.get('req_uid','?')}` {r.get('req_name','?')}"
                        + (f" \u2192 {r.get('design_element')}" if r.get("design_element") else "")
                        + (f" \u2192 Dossier `{r.get('dossier_uid')}`" if r.get("dossier_uid") else "")
                        + (f" \u2192 Evidence: {r.get('evidence_name')!r}" if r.get("evidence_name") else "")
                        for r in verified[:20]
                    )
                    hits.append({
                        "uid": "__cypher_trace_verified__",
                        "name": f"Requirements Traced via Dossier ({len(verified)} verified)",
                        "description": v_lines,
                        "labels": ["CypherResult"],
                        "score": 1.0,
                    })
                if unverified:
                    u_lines = "\n".join(
                        f"- \u274c `{r.get('req_uid','?')}` {r.get('req_name','?')} *(no dossier link)*"
                        for r in unverified[:20]
                    )
                    hits.append({
                        "uid": "__cypher_trace_unverified__",
                        "name": f"Untraced Requirements ({len(unverified)} without dossier)",
                        "description": u_lines,
                        "labels": ["CypherResult"],
                        "score": 1.0,
                    })

        # ── Evidence Categories ──────────────────────────────────────────────
        if is_evidence:
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
                    f"- `{r.get('uid','?')}` **{r.get('name','?')}**"
                    f" (type: {r.get('category_type','?')}, artifacts: {r.get('artifact_count',0)})"
                    + (f" | dossiers: {', '.join(str(d) for d in (r.get('dossiers') or []) if d and d != '?')[:80]}"
                       if r.get("dossiers") else "")
                    for r in ev_rows
                )
                hits.append({
                    "uid": "__cypher_evidence__",
                    "name": f"Evidence Categories ({len(ev_rows)} found)",
                    "description": e_lines,
                    "labels": ["CypherResult"],
                    "score": 1.0,
                })

        # ── AP243 Simulation ─────────────────────────────────────────────────
        if is_ap243:
            # If user asked for dossiers + evidence together, return a joined table
            want_evidence_join = is_evidence or "evidence" in q
            if want_evidence_join:
                dos_ev_rows = _run(
                    "MATCH (d:SimulationDossier) "
                    "OPTIONAL MATCH (d)-[:HAS_SIMULATION_RUN]->(run:SimulationRun) "
                    "OPTIONAL MATCH (run)-[:CONTAINS_ARTIFACT]->(art:SimulationArtifact) "
                    "OPTIONAL MATCH (art)-[:EVIDENCE_FOR]->(ev:EvidenceCategory) "
                    "RETURN coalesce(d.uid, d.id,'?') AS dossier_uid, "
                    "       coalesce(d.name, d.uid,'?') AS dossier_name, "
                    "       count(DISTINCT run) AS runs, "
                    "       count(DISTINCT art) AS artifacts, "
                    "       collect(DISTINCT coalesce(ev.uid, ev.id,'?'))[0..5] AS ev_uids, "
                    "       collect(DISTINCT coalesce(ev.name,'?'))[0..5] AS ev_names "
                    "ORDER BY d.name LIMIT $limit",
                    limit=30,
                )
                if dos_ev_rows:
                    joined_lines: List[str] = [
                        "| Dossier UID | Dossier Name | Runs | Evidence Category UIDs |",
                        "|-------------|-------------|------|----------------------|",
                    ]
                    for r in dos_ev_rows:
                        ev_uids = [u for u in (r.get("ev_uids") or []) if u and u != "?"]
                        ev_names = [n for n in (r.get("ev_names") or []) if n and n != "?"]
                        ev_cell = (
                            ", ".join(
                                f"`{u}` {nm}" for u, nm in zip(ev_uids, ev_names)
                            ) if ev_uids else "_none_"
                        )
                        joined_lines.append(
                            f"| `{r.get('dossier_uid','?')}` "
                            f"| **{r.get('dossier_name','?')}** "
                            f"| {r.get('runs',0)} "
                            f"| {ev_cell} |"
                        )
                    hits.append({
                        "uid": "__cypher_ap243_dossiers__",
                        "name": f"AP243 Simulation Dossiers with Evidence Categories ({len(dos_ev_rows)} dossiers)",
                        "description": "\n".join(joined_lines),
                        "labels": ["CypherResult"],
                        "score": 1.0,
                    })
            else:
                dos_rows = _run(
                    "MATCH (d:SimulationDossier) "
                    "OPTIONAL MATCH (d)-[:HAS_SIMULATION_RUN]->(run:SimulationRun) "
                    "OPTIONAL MATCH (run)-[:CONTAINS_ARTIFACT]->(art:SimulationArtifact) "
                    "RETURN coalesce(d.uid, d.id,'?') AS uid, d.name AS name, "
                    "       count(DISTINCT run) AS runs, count(DISTINCT art) AS artifacts "
                    "ORDER BY d.name LIMIT $limit",
                    limit=20,
                )
                if dos_rows:
                    d_lines = "\n".join(
                        f"- **{r.get('name','?')}** `{r.get('uid','?')}` "
                        f"\u2014 {r.get('runs',0)} runs, {r.get('artifacts',0)} artifacts"
                        for r in dos_rows
                    )
                    hits.append({
                        "uid": "__cypher_ap243_dossiers__",
                        "name": f"AP243 Simulation Dossiers ({len(dos_rows)} found)",
                        "description": d_lines,
                        "labels": ["CypherResult"],
                        "score": 1.0,
                    })
            model_rows = _run(
                "MATCH (n) WHERE n:ModelInstance OR n:ModelType OR n:WorkflowMethod OR n:KPI "
                "RETURN labels(n)[0] AS lbl, count(n) AS cnt ORDER BY cnt DESC",
                limit=10,
            )
            if model_rows:
                stat_lines = "\n".join(f"- **{r['lbl']}**: {r['cnt']:,} nodes" for r in model_rows)
                hits.append({
                    "uid": "__cypher_ap243_models__",
                    "name": "AP243 Simulation Model Node Counts",
                    "description": stat_lines,
                    "labels": ["CypherResult"],
                    "score": 1.0,
                })

        # ── AP242 Product Model ──────────────────────────────────────────────
        if is_ap242:
            # Resolve the source STEP file name for context (e.g. "INDUCTION MOTOR ASSEMBLY 5HP")
            # (re is already imported at module level)
            step_file_rows = _run(
                "MATCH (f:StepFile) WHERE f.ap_schema = 'AP242' "
                "RETURN coalesce(f.original_name, f.name, f.filename, f.uid, 'AP242 Assembly') AS fname "
                "LIMIT 1",
                limit=1,
            )
            step_file_name: str = (
                step_file_rows[0].get("fname", "AP242 Assembly") if step_file_rows else "AP242 Assembly"
            )
            # Strip timestamp suffix like " (2022_12_17 01_44_39 UTC)_9cfff885"
            clean_name = re.sub(r"\s*\(\d{4}_\d{2}_\d{2}.*?\)_[0-9a-f]+", "", step_file_name).strip()
            clean_name = re.sub(r"\.stp$", "", clean_name, flags=re.IGNORECASE).strip()
            product_title = clean_name or "AP242 Assembly"

            # BOM: AP242 stores assembly occurrences as :AP242AssemblyOccurrence
            # (from STEP NEXT_ASSEMBLY_USAGE_OCCURRENCE entities) linked to
            # :AP242Product parts via [:DEFINES_PRODUCT].
            bom_rows = _run(
                "MATCH (occ:AP242AssemblyOccurrence)-[:DEFINES_PRODUCT]->(prod:AP242Product) "
                "RETURN coalesce(occ.name, occ.uid, '?') AS occurrence, "
                "       coalesce(prod.name, prod.id, '?') AS part_name, "
                "       coalesce(prod.id, '') AS part_id "
                "ORDER BY prod.name LIMIT $limit",
                limit=50,
            )

            # All AP242Product nodes (the parts list)
            prod_rows = _run(
                "MATCH (p:AP242Product) "
                "OPTIONAL MATCH (p)-[:USES_MATERIAL]->(m:Material) "
                "RETURN coalesce(p.id, p.uid, '?') AS part_id, "
                "       coalesce(p.name, p.id, '?') AS part_name, "
                "       coalesce(m.name, '') AS material "
                "ORDER BY part_name LIMIT $limit",
                limit=50,
            )

            ap242_stats = _run(
                "MATCH (n) WHERE 'AP242Product' IN labels(n) "
                "   OR 'AP242AssemblyOccurrence' IN labels(n) OR 'Material' IN labels(n) "
                "   OR 'PartVersion' IN labels(n) OR 'GeometricModel' IN labels(n) "
                "   OR 'StepFile' IN labels(n) "
                "RETURN labels(n)[0] AS label, count(n) AS cnt ORDER BY cnt DESC LIMIT 8",
                limit=8,
            )

            # ── Build one rich combined hit for the product ──────────────────
            combined_lines: List[str] = [
                f"> **Source**: `{step_file_name}`  ",
                f"> **Standard**: ISO 10303 AP242 (Product Data)  ",
                "",
            ]

            if bom_rows:
                combined_lines.append(f"#### Bill of Materials — Assembly Occurrences ({len(bom_rows)} items)")
                combined_lines.append("")
                combined_lines.append("| # | Occurrence Name | Part / Product |")
                combined_lines.append("|---|----------------|---------------|")
                for i, r in enumerate(bom_rows, 1):
                    pn = r.get('part_name', '?')
                    occ = r.get('occurrence', '?')
                    combined_lines.append(f"| {i} | {occ} | **{pn}** |")
                combined_lines.append("")

            if prod_rows:
                combined_lines.append(f"#### Parts List — AP242Product Nodes ({len(prod_rows)} parts)")
                combined_lines.append("")
                for i, r in enumerate(prod_rows, 1):
                    mat = r.get('material', '')
                    pid = r.get('part_id', '?')
                    pname = r.get('part_name', '?')
                    line = f"{i}. **{pname}**"
                    if pid and pid != pname:
                        line += f" — ID: `{pid}`"
                    if mat:
                        line += f" — Material: _{mat}_"
                    combined_lines.append(line)
                combined_lines.append("")

            if ap242_stats:
                combined_lines.append("#### Knowledge Graph Node Counts (AP242)")
                combined_lines.append("")
                for r in ap242_stats:
                    combined_lines.append(f"- **:{r.get('label','?')}**: {r.get('cnt',0):,} nodes")

            hits.append({
                "uid": "__cypher_ap242_bom__",
                "name": f"{product_title} — AP242 Bill of Materials",
                "description": "\n".join(combined_lines),
                "labels": ["CypherResult"],
                "score": 1.0,
            })

        if not hits:
            return None

        return {
            "hits": hits,
            "expanded": {},
            "structural": True,
            "cypher_direct": True,
        }

    def _fulltext_fallback(
        self,
        query: str,
        top_k: int,
        focus_area: Optional[str] = None,
        node_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Full-text index fallback when OpenSearch is unavailable.

        1. Check schema cache for matching labels → run LABEL_SEARCH_FALLBACK (fast).
        2. If fulltext index exists (cached), try it.
        3. Fallback to generic CONTAINS scan (slow — last resort).
        4. Type-intent fallback via schema-matched labels.
        """
        keyword = _strip_intent(query)
        existing_labels = _cached_labels(self.neo4j)
        matched_labels  = _label_match_from_schema(keyword, existing_labels)

        # ── 0. Structural / topology query ───────────────────────────────────
        if _is_structural_query(query):
            logger.info("SemanticAgent: structural query detected — returning schema overview")
            return _structural_context_fallback(
                self.neo4j, query, existing_labels, top_k,
                focus_area=focus_area, node_types=node_types,
            )

        # ── 0b. Exact ID-token lookup ─────────────────────────────────────────
        id_token = _extract_id_token(query)
        if id_token:
            logger.info(f"SemanticAgent._fulltext_fallback: ID token '{id_token}' — exact lookup")
            id_result = self._exact_id_lookup(id_token, top_k, expand=True)
            if id_result.get("hits"):
                return id_result

        with self.neo4j.driver.session(database=self.neo4j.database) as session:

            # ── 1. Schema-aware label-scoped search (fastest when label is known) ──
            if matched_labels:
                try:
                    result = session.run(
                        _LABEL_SEARCH_FALLBACK,
                        labels=matched_labels, query=keyword, top_k=top_k
                    )
                    hits = [
                        {
                            "uid": r["uid"],
                            "name": r["name"],
                            "labels": list(r["labels"]),
                            "description": r.get("description", ""),
                            "score": float(r["score"]),
                            "type_match": True,
                        }
                        for r in result
                    ]
                    if hits:
                        logger.info(
                            f"SemanticAgent: label-scoped search hit {len(hits)} "
                            f"nodes in labels {matched_labels}"
                        )
                        return {"hits": hits, "expanded": {}, "fallback": True, "type_match": True}
                except Exception as exc:
                    logger.debug(f"SemanticAgent: label-scoped search failed ({exc})")

            # ── 2. Full-text index (only if index actually exists) ────────────────
            if _cached_fulltext_index_exists(self.neo4j):
                try:
                    result = session.run(_FULLTEXT_FALLBACK, query=query, top_k=top_k)
                    hits = [
                        {
                            "uid": r["uid"],
                            "name": r["name"],
                            "labels": list(r["labels"]),
                            "score": float(r["score"]),
                        }
                        for r in result
                    ]
                    if hits:
                        return {"hits": hits, "expanded": {}, "fallback": True}
                except Exception as exc:
                    logger.debug(f"SemanticAgent: full-text index unavailable ({exc})")
            else:
                logger.debug("SemanticAgent: skipping fulltext index (not in schema cache)")

            # ── 3. Generic CONTAINS scan — full 483k-node scan, last resort ───────
            try:
                result = session.run(
                    _GENERIC_SEARCH_FALLBACK, query=query, top_k=top_k
                )
                hits = [
                    {
                        "uid": r["uid"],
                        "name": r["name"],
                        "labels": list(r["labels"]),
                        "description": r.get("description", ""),
                        "score": float(r["score"]),
                    }
                    for r in result
                ]
                if hits:
                    return {"hits": hits, "expanded": {}, "fallback": True}
            except Exception as exc:
                logger.debug(f"SemanticAgent: generic search fallback failed: {exc}")

            # ── 4. Type-intent fallback — use schema cache first, raw scan if needed ──
            logger.info(f"SemanticAgent: type-intent fallback keyword='{keyword}'")
            if matched_labels:
                # Already tried label-scoped search above with no hits; return empty
                return {"hits": [], "expanded": {}, "fallback": True, "type_match": True}
            try:
                result = session.run(
                    _TYPE_MATCH_FALLBACK, keyword=keyword, top_k=top_k
                )
                hits = [
                    {
                        "uid": r["uid"],
                        "name": r["name"],
                        "labels": list(r["labels"]),
                        "description": r.get("description", ""),
                        "score": float(r["score"]),
                        "type_match": True,
                    }
                    for r in result
                ]
                return {"hits": hits, "expanded": {}, "fallback": True, "type_match": True}
            except Exception as exc:
                logger.warning(f"SemanticAgent: type-intent fallback failed: {exc}")
                return {"hits": [], "expanded": {}, "fallback": True, "error": str(exc)}

    def _chat(self, prompt: str) -> str:
        """Call Ollama chat API for LLM synthesis (blocking, waits for full response)."""
        url = f"{OLLAMA_BASE_URL.rstrip('/')}/api/chat"
        payload = {
            "model": CHAT_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "keep_alive": "10m",
        }
        try:
            resp = requests.post(url, json=payload, timeout=300)
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "").strip()
        except Exception as exc:
            logger.warning(f"SemanticAgent._chat failed: {exc}")
            return f"(LLM synthesis unavailable: {exc})"

    def _chat_stream(self, prompt: str) -> Generator[str, None, None]:
        """Stream Ollama tokens one by one as they are generated.

        Yields individual text tokens. Callers can reconstruct the full answer
        by joining them. Handles the streaming Ollama JSON line protocol.
        """
        import json as _json
        url = f"{OLLAMA_BASE_URL.rstrip('/')}/api/chat"
        payload = {
            "model": CHAT_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
            "keep_alive": "10m",
        }
        try:
            with requests.post(url, json=payload, stream=True, timeout=300) as resp:
                resp.raise_for_status()
                for raw_line in resp.iter_lines():
                    if not raw_line:
                        continue
                    try:
                        data = _json.loads(raw_line)
                    except _json.JSONDecodeError:
                        continue
                    token = data.get("message", {}).get("content", "")
                    if token:
                        yield token
                    if data.get("done"):
                        break
        except Exception as exc:
            logger.warning(f"SemanticAgent._chat_stream failed: {exc}")
            yield f"(LLM synthesis unavailable: {exc})"
