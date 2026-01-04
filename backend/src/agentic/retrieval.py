"""Retrieval (RAG) abstractions.

This module provides a minimal local retriever stub and a placeholder for an
Azure AI Search-backed retriever.

Actual Azure calls are intentionally not implemented here to keep local runs
dependency-free and to avoid coupling. The goal is to standardize the interface.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .contracts import RetrievedChunk, Retriever


@dataclass
class StaticRetriever(Retriever):
    """Simple retriever that returns a fixed set of chunks.

    Useful for tests and for wiring the RAG boundary without external services.
    """

    chunks: Sequence[RetrievedChunk]

    def retrieve(
        self, query: str, *, top_k: int = 5, filters: Mapping[str, Any] | None = None
    ) -> Sequence[RetrievedChunk]:
        _ = (query, filters)
        return list(self.chunks)[:top_k]


class AzureAISearchRetriever(Retriever):
    """Placeholder for Azure AI Search.

    In an Azure deployment this would:
    - Authenticate using Managed Identity or an API key
    - Query an index (hybrid BM25 + vector)
    - Return top-k chunks with citations/metadata
    """

    def __init__(self, *, endpoint: str, index_name: str, credential: Any):
        self.endpoint = endpoint
        self.index_name = index_name
        self.credential = credential

    def retrieve(
        self, query: str, *, top_k: int = 5, filters: Mapping[str, Any] | None = None
    ) -> Sequence[RetrievedChunk]:
        raise NotImplementedError(
            "AzureAISearchRetriever is a placeholder. Provide a deployment-specific implementation "
            "that calls Azure AI Search."
        )
