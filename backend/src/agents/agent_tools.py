from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Protocol

from loguru import logger

from src.web.services.neo4j_service import get_neo4j_service
from src.agents.embeddings_ollama import OllamaEmbeddings
from src.agents.vectorstore_es import ElasticsearchVectorStore


class AgentTool(Protocol):
    """Interface for tools available to agents."""

    def search_artifacts(self, *args, **kwargs) -> List[Dict[str, Any]]:
        ...

    def index_document(self, *args, **kwargs) -> Any:
        ...


class Neo4jTool:
    """Tool wrapper around the in-process Neo4jService."""

    def __init__(self):
        self.svc = get_neo4j_service()

    def search_artifacts(self, cypher: str, params: Optional[Dict[str, Any]] = None, limit: int = 50) -> List[Dict[str, Any]]:
        params = params or {}
        logger.debug(f"Neo4jTool.search_artifacts - cypher={cypher} params={params} limit={limit}")
        # Only append LIMIT clause if query does not already contain one
        if "LIMIT" not in cypher.upper():
            cypher = cypher + "\nLIMIT $limit"
        # Always pass $limit so the parameter is available whether caller included it or not
        params = {**params, "limit": limit}
        results = self.svc.execute_query(cypher, params)
        return results

    def index_document(self, label: str, uid: str, properties: Dict[str, Any]) -> Any:
        # Upsert node by UID
        props = {**properties, "uid": uid}
        # MERGE by uid
        query = f"MERGE (n:{label} {{uid: $uid}}) SET n += $props RETURN n.uid as uid"
        res = self.svc.execute_write(query, {"uid": uid, "props": properties})
        return res


class VectorStoreTool:
    """Tool wrapper that performs embedding + vectorstore ops (Elasticsearch).

    It can optionally mirror embeddings into Neo4j if NEO4J_EMBEDDING_ENABLED is true.
    """

    def __init__(self, host: Optional[str] = None, index: Optional[str] = None):
        # Accept all naming conventions — canonical is VECTORSTORE_HOST / VECTORSTORE_INDEX
        self.host = (
            host
            or os.getenv("VECTORSTORE_HOST")
            or os.getenv("OPENSEARCH_URL")
            or os.getenv("OPENSEARCH_HOST")
            or "http://localhost:9200"
        )
        self.index = (
            index
            or os.getenv("VECTORSTORE_INDEX")
            or os.getenv("OPENSEARCH_INDEX")
            or "embeddings"
        )
        self.embedder = OllamaEmbeddings()
        self.store = ElasticsearchVectorStore(self.host)
        self.mirror_to_neo4j = os.getenv("NEO4J_EMBEDDING_ENABLED", "false").lower() == "true"
        if self.mirror_to_neo4j:
            self.neo4j = Neo4jTool()

    def index_document(self, doc_id: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # Compute embedding
        emb = self.embedder.embed([text])[0]
        # Ensure index exists (best-effort) - user should create mapping ahead of time
        try:
            self.store.create_index(self.index, dim=len(emb))
        except Exception:
            # ignore if already exists or mapping unsupported
            pass

        r = self.store.upsert(self.index, doc_id, text, emb, metadata)

        # Optionally mirror to Neo4j: attach embedding as property on node with uid == doc_id
        if self.mirror_to_neo4j:
            try:
                # store embedding as property `embedding`
                self.neo4j.svc.update_node("Document", doc_id, {"embedding": emb})
            except Exception as e:
                logger.warning(f"Failed to mirror embedding to Neo4j for {doc_id}: {e}")

        return r

    def search(self, query_text: str, k: int = 10) -> Dict[str, Any]:
        emb = self.embedder.embed([query_text])[0]
        return self.store.search(self.index, emb, k=k)


__all__ = ["AgentTool", "Neo4jTool", "VectorStoreTool"]
