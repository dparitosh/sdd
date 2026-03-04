#!/usr/bin/env python3
"""OpenSearch setup & health verification script.

Usage:
    python backend/scripts/setup_opensearch.py

Pre-conditions:
    - OpenSearch 3.x running on http://localhost:9200
    - Security plugin disabled (``plugins.security.disabled: true``) or creds set in env vars

Actions:
    1. Check cluster health (green / yellow accepted).
    2. Create the ``embeddings`` index with HNSW knn_vector mapping (dim=768, lucene, cosinesimil).
    3. Print index info and document count.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict

import requests

OPENSEARCH_HOST = (
    os.getenv("VECTORSTORE_HOST")
    or os.getenv("OPENSEARCH_URL")
    or os.getenv("OPENSEARCH_HOST")
    or "http://localhost:9200"
)
INDEX_NAME = os.getenv("OPENSEARCH_INDEX") or os.getenv("VECTORSTORE_INDEX") or "embeddings"
EMBEDDING_DIM = int(os.getenv("OPENSEARCH_DIM", "768"))


def _url(path: str = "") -> str:
    return f"{OPENSEARCH_HOST}{path}"


def _get(path: str) -> Dict[str, Any]:
    resp = requests.get(_url(path), timeout=10)
    resp.raise_for_status()
    return resp.json()


def _put(path: str, body: Dict[str, Any]) -> Dict[str, Any]:
    resp = requests.put(_url(path), json=body, timeout=10)
    resp.raise_for_status()
    return resp.json()


# --------------------------------------------------------------------------
# 1. Cluster health
# --------------------------------------------------------------------------

def check_cluster_health() -> None:
    print("=" * 60)
    print("1. Checking OpenSearch cluster health …")
    print("=" * 60)
    try:
        info = _get("")
        print(f"   Cluster name : {info.get('cluster_name', 'N/A')}")
        print(f"   Version      : {info.get('version', {}).get('number', 'N/A')}")
    except requests.ConnectionError:
        print(f"   ERROR: Cannot connect to OpenSearch at {OPENSEARCH_HOST}")
        print("   Make sure OpenSearch is running and the OPENSEARCH_HOST env var is correct.")
        sys.exit(1)

    health = _get("/_cluster/health")
    status = health.get("status", "unknown")
    print(f"   Status        : {status}")
    if status == "red":
        print("   WARNING: Cluster status is RED. Investigate before proceeding.")
        sys.exit(1)
    print("   ✓ Cluster is healthy.\n")


# --------------------------------------------------------------------------
# 2. Create embeddings index
# --------------------------------------------------------------------------

INDEX_BODY = {
    "settings": {
        "index": {
            "knn": True,
            "knn.algo_param.ef_search": 256,        # search-time accuracy (default 100)
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "refresh_interval": "30s",               # reduce indexing overhead vs default 1s
            "codec": "best_compression",             # zstd — smaller on-disk footprint
        }
    },
    "mappings": {
        "properties": {
            "text": {
                "type": "text",
                "analyzer": "standard",
            },
            "embedding": {
                "type": "knn_vector",
                "dimension": EMBEDDING_DIM,
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
            # ── Structured metadata fields for filtered vector search ──
            "metadata": {"type": "object", "enabled": True},
            "node_id":   {"type": "keyword"},        # exact-match filter
            "node_type": {"type": "keyword"},         # facet / filter
            "label":     {"type": "keyword"},         # facet / filter
            "ap_level":  {"type": "keyword"},         # AP239 / AP242 / AP243
            "source":    {"type": "keyword"},         # origin file / loader name
        }
    },
}


def create_embeddings_index() -> None:
    print("=" * 60)
    print(f"2. Creating index '{INDEX_NAME}' (dim={EMBEDDING_DIM}) …")
    print("=" * 60)

    # Check if already exists
    exists_resp = requests.head(_url(f"/{INDEX_NAME}"), timeout=10)
    if exists_resp.status_code == 200:
        print(f"   Index '{INDEX_NAME}' already exists — skipping creation.")
    else:
        result = _put(f"/{INDEX_NAME}", INDEX_BODY)
        ack = result.get("acknowledged", False)
        print(f"   Acknowledged: {ack}")
        if not ack:
            print("   ERROR: Index creation was not acknowledged.")
            sys.exit(1)
        print(f"   ✓ Index '{INDEX_NAME}' created.\n")


# --------------------------------------------------------------------------
# 3. Verify index
# --------------------------------------------------------------------------

def verify_index() -> None:
    print("=" * 60)
    print(f"3. Verifying index '{INDEX_NAME}' …")
    print("=" * 60)

    info = _get(f"/{INDEX_NAME}")
    mappings = info.get(INDEX_NAME, {}).get("mappings", {})
    emb_prop = mappings.get("properties", {}).get("embedding", {})
    dim = emb_prop.get("dimension", "N/A")
    print(f"   Vector dim    : {dim}")
    print(f"   Method        : {json.dumps(emb_prop.get('method', {}), indent=6)}")

    count_resp = _get(f"/{INDEX_NAME}/_count")
    count = count_resp.get("count", 0)
    print(f"   Document count: {count}")
    print(f"   ✓ Index verified.\n")


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main() -> None:
    print(f"\nOpenSearch Setup   host={OPENSEARCH_HOST}   index={INDEX_NAME}\n")
    check_cluster_health()
    create_embeddings_index()
    verify_index()
    print("All checks passed.\n")


if __name__ == "__main__":
    main()
