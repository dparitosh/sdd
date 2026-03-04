import os
import time
import requests
from typing import Any, Dict, List, Optional


class ElasticsearchVectorStore:
    """Minimal Elasticsearch/OpenSearch vector store via HTTP REST API.

    Stores documents with a dense_vector field named `vector`. Uses the
    script_score + cosineSimilarity for KNN-style searches.
    """

    def __init__(self, host: Optional[str] = None, timeout: int = 120, max_retries: int = 3):
        # Accept all naming conventions — canonical is VECTORSTORE_HOST
        self.host = (
            host
            or os.getenv("VECTORSTORE_HOST")
            or os.getenv("OPENSEARCH_URL")
            or os.getenv("OPENSEARCH_HOST")
            or "http://localhost:9200"
        ).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Execute a request with exponential-backoff retry on transient errors."""
        delay = 2.0
        last_exc: Exception = RuntimeError("No attempts made")
        for attempt in range(1, self.max_retries + 1):
            try:
                r = requests.request(method, url, timeout=self.timeout, **kwargs)
                r.raise_for_status()
                return r
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    time.sleep(delay)
                    delay = min(delay * 2, 30.0)
            except requests.exceptions.HTTPError as exc:
                # 4xx errors are not retriable
                raise exc
        raise last_exc

    def create_index(self, index_name: str, dim: int) -> Dict[str, Any]:
        """Create an OpenSearch index with knn_vector mapping (HNSW/Lucene engine).

        If the index already exists, returns immediately with {"existed": True}.
        """
        url = f"{self.host}/{index_name}"
        # Check existence first to avoid 400 "already exists" noise
        try:
            requests.head(url, timeout=self.timeout).raise_for_status()
            return {"existed": True}
        except requests.exceptions.HTTPError:
            pass  # 404 → index doesn't exist, proceed to create

        mapping = {
            "settings": {
                "knn": True,
                "index.knn.algo_param.ef_search": 256,
                "index.refresh_interval": "30s",
            },
            "mappings": {
                "properties": {
                    "text": {"type": "text"},
                    "vector": {
                        "type": "knn_vector",
                        "dimension": dim,
                        "method": {
                            "name": "hnsw",
                            "engine": "lucene",
                            "space_type": "cosinesimil",
                            "parameters": {
                                "ef_construction": 256,
                                "m": 16,
                            },
                        },
                    },
                    "metadata": {"type": "object", "enabled": True},
                    "node_id":   {"type": "keyword"},
                    "node_type": {"type": "keyword"},
                    "label":     {"type": "keyword"},
                    "ap_level":  {"type": "keyword"},
                    "source":    {"type": "keyword"},
                }
            },
        }
        return self._request("PUT", url, json=mapping).json()

    def upsert(self, index_name: str, doc_id: str, text: str, embedding: List[float], metadata: Optional[Dict] = None) -> Dict[str, Any]:
        body = {"text": text, "vector": embedding, "metadata": metadata or {}}
        url = f"{self.host}/{index_name}/_doc/{doc_id}"
        return self._request("PUT", url, json=body).json()

    def search(
        self,
        index_name: str,
        query_vector: List[float],
        k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """KNN approximate-nearest-neighbor search using OpenSearch knn_vector index.

        Args:
            index_name: Index to search.
            query_vector: Dense query embedding.
            k: Number of nearest neighbors to return.
            filters: Optional dict of keyword fields to filter on before kNN,
                     e.g. ``{"node_type": "Requirement", "ap_level": "AP239"}``.
        """
        knn_body: Dict[str, Any] = {
            "vector": query_vector,
            "k": k,
        }

        # Attach a boolean pre-filter if any structured filters were provided.
        if filters:
            must_clauses = [
                {"term": {field: value}}
                for field, value in filters.items()
                if value is not None
            ]
            if must_clauses:
                knn_body["filter"] = {"bool": {"must": must_clauses}}

        query = {
            "size": k,
            "query": {
                "knn": {
                    "vector": knn_body,
                }
            },
        }
        url = f"{self.host}/{index_name}/_search"
        return self._request("POST", url, json=query).json()


__all__ = ["ElasticsearchVectorStore"]
