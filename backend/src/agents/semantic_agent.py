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
from typing import Any, Dict, List, Optional

import requests
from loguru import logger

from src.web.services import get_neo4j_service

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL") or os.getenv("OLLAMA_MODEL") or "llama3:latest"
OPENSEARCH_HOST = os.getenv("VECTORSTORE_HOST", "http://localhost:9200")
OPENSEARCH_INDEX = os.getenv("OPENSEARCH_INDEX", "embeddings")

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
RETURN COALESCE(node.id, node.uid, elementId(node))        AS uid,
       COALESCE(node.name, node.label, node.uid)            AS name,
       labels(node)                                         AS labels,
       COALESCE(node.description, node.definition, '')      AS description,
       1.0                                                  AS score
ORDER BY CASE WHEN toLower(COALESCE(node.name, '')) STARTS WITH toLower($query) THEN 0 ELSE 1 END
LIMIT $top_k
"""

# Matches nodes whose *label* (type name) contains the keyword.
# Used when the user asks a list/inventory question like "list of dossiers".
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
    ) -> Dict[str, Any]:
        """Embed *query*, run kNN, optionally expand hits in graph.

        Returns ``{"hits": [...], "expanded": {...}}``.
        """
        # Step 1: embed
        embedding = self._embed(query)
        if embedding is None:
            logger.warning("SemanticAgent: embedding failed, falling back to full-text")
            return self._fulltext_fallback(query, top_k)

        # Step 2: kNN search
        hits = self._knn_search(embedding, top_k, threshold)
        if hits is None:
            logger.warning("SemanticAgent: OpenSearch unreachable, falling back to full-text")
            return self._fulltext_fallback(query, top_k)
        if not hits:
            logger.info("SemanticAgent: kNN returned 0 hits (threshold too high or no embeddings found), falling back to Neo4j search")
            return self._fulltext_fallback(query, top_k)

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
                return self._fulltext_fallback(query, top_k)

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
    ) -> Dict[str, Any]:
        """Full RAG pipeline: search → prompt → LLM → answer + sources.

        Returns ``{"answer": str, "sources": [...]}``.
        """
        search_result = self.semantic_search(question, top_k=top_k, expand=True)
        hits = search_result.get("hits", [])
        expanded = search_result.get("expanded", {})

        is_fallback = search_result.get("fallback", False)
        is_type_match = search_result.get("type_match", False)

        # Build context string
        context_parts: List[str] = []
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
        if is_type_match and hits:
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
            "You are an MBSE knowledge-graph assistant. "
            f"{listing_note}"
            "Answer the question using the context below. "
            "If the context contains a list of nodes, enumerate them clearly.\n"
            f"{empty_note}\n\n"
            "## Context (knowledge graph results):\n"
            f"{context_text}\n\n"
            f"## Question:\n{question}\n\n"
            "## Answer (Markdown):"
        )
        answer = self._chat(prompt)

        sources = [
            {"uid": h.get("uid"), "name": h.get("name"), "score": h.get("score")}
            for h in hits
        ]
        return {
            "answer": answer,
            "sources": sources,
            "hits": hits,
            "expanded": expanded,
            "fallback": search_result.get("fallback", False),
        }

    # -- internal methods ----------------------------------------------------

    def _embed(self, text: str) -> Optional[List[float]]:
        """Call Ollama embedding API."""
        url = f"{OLLAMA_BASE_URL.rstrip('/')}/api/embeddings"
        try:
            resp = requests.post(
                url,
                json={"model": EMBED_MODEL, "prompt": text},
                timeout=8,  # Ollama is local — 8 s is ample; fail fast if it hangs
            )
            resp.raise_for_status()
            return resp.json().get("embedding")
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

    def _fulltext_fallback(
        self, query: str, top_k: int
    ) -> Dict[str, Any]:
        """Full-text index fallback when OpenSearch is unavailable.

        Tries Neo4j full-text index first; if that index does not exist,
        falls back to a generic case-insensitive CONTAINS match.
        """
        with self.neo4j.driver.session(database=self.neo4j.database) as session:
            # Try full-text index first
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
                # Empty result — fall through to generic search
            except Exception as exc:
                logger.debug(f"SemanticAgent: full-text index unavailable ({exc}), using generic search")

            # Generic CONTAINS fallback
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
                # No name/description match — try type-intent search
            except Exception as exc:
                logger.debug(f"SemanticAgent: generic search fallback failed: {exc}")

            # Type-intent fallback: interpret the query as "list nodes of type X"
            keyword = _strip_intent(query)
            # Try singular form too (e.g. "dossiers" → "dossier" matches "SimulationDossier")
            kw_singular = keyword[:-1] if keyword.endswith("s") and len(keyword) > 3 else keyword
            logger.info(f"SemanticAgent: type-intent fallback with keyword='{keyword}' (singular='{kw_singular}')")
            try:
                result = session.run(
                    _TYPE_MATCH_FALLBACK, keyword=kw_singular, top_k=top_k
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
                logger.warning(f"SemanticAgent: type-intent fallback also failed: {exc}")
                return {"hits": [], "expanded": {}, "fallback": True, "error": str(exc)}

    def _chat(self, prompt: str) -> str:
        """Call Ollama chat API for LLM synthesis."""
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
