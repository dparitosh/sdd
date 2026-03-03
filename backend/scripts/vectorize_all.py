#!/usr/bin/env python3
"""Checkpointed vectorization script (Neo4j -> Ollama embeddings -> OpenSearch/Elasticsearch)

Usage (run from the backend/ directory):

    # Vectorize all unique nodes (recommended - avoids duplicates):
    python scripts/vectorize_all.py --label ALL --index embeddings --batch 64

    # Vectorize a specific label:
    python scripts/vectorize_all.py --label Class --index embeddings --batch 32 --limit 200

A progress checkpoint is saved so the run can be resumed after interruption.
"""
import os
import sys
import time
import json
import argparse
import pathlib

# Allow running directly from backend/ without installing the package
_backend_dir = pathlib.Path(__file__).resolve().parent.parent  # backend/
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

# Force unbuffered stdout so progress lines are visible when output is piped/redirected
sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]

# Auto-load .env (project root = backend/../.env)
_env_file = _backend_dir.parent / ".env"
if _env_file.is_file():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _k, _, _v = _line.partition("=")
        _k = _k.strip()
        if _k and _k not in os.environ:   # don't overwrite existing env vars
            os.environ[_k] = _v.strip()

from src.web.services.neo4j_service import get_neo4j_service  # noqa: E402
from src.agents.embeddings_ollama import OllamaEmbeddings      # noqa: E402
from src.agents.vectorstore_es import ElasticsearchVectorStore # noqa: E402

PROGRESS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "vectorize_progress")


def ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)


def node_to_text(node: dict) -> str:
    parts = []
    # Include label info when present (injected by list_all_nodes)
    node_labels = node.get("__labels")
    if node_labels:
        parts.append("labels: " + ", ".join(node_labels))
    if node.get("name"):
        parts.append(str(node["name"]))
    if node.get("description"):
        parts.append(str(node["description"]))
    # Include all other properties as key: value lines
    skip_keys = {"uid", "uuid", "id", "name", "description", "__labels"}
    for k, v in node.items():
        if k in skip_keys:
            continue
        try:
            parts.append(f"{k}: {v}")
        except Exception:
            pass
    return "\n\n".join(parts)[:2000]


def list_all_nodes(neo4j, skip: int, limit: int) -> list:
    """Fetch all unique nodes with their labels, ordered by a stable id for pagination."""
    query = """
        MATCH (n)
        WHERE n.uuid IS NOT NULL OR n.uid IS NOT NULL
        WITH n, COALESCE(n.uuid, n.uid) AS stable_id
        RETURN n AS node, labels(n) AS node_labels
        ORDER BY stable_id
        SKIP $skip
        LIMIT $limit
    """
    results = neo4j.execute_query(query, {"skip": skip, "limit": limit})
    nodes = []
    for r in results:
        d = dict(r["node"])
        d["__labels"] = list(r["node_labels"])
        nodes.append(d)
    return nodes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="ALL",
                        help="Neo4j node label to vectorize, or ALL for every unique node")
    parser.add_argument("--index", default=os.getenv("VECTORSTORE_INDEX", "embeddings"),
                        help="OpenSearch/Elasticsearch index name")
    parser.add_argument("--batch", type=int, default=64)
    parser.add_argument("--limit", type=int, default=10000)
    parser.add_argument("--start-skip", type=int, default=0)
    args = parser.parse_args()

    neo4j = get_neo4j_service()
    embedder = OllamaEmbeddings()
    es = ElasticsearchVectorStore()

    ensure_dir(PROGRESS_DIR)
    progress_file = os.path.join(PROGRESS_DIR, f"{args.label}.progress.json")
    progress = {"skip": args.start_skip}
    if os.path.exists(progress_file):
        try:
            with open(progress_file, "r", encoding="utf-8") as fh:
                progress = json.load(fh)
        except Exception:
            pass

    skip = progress.get("skip", args.start_skip)
    processed = 0
    total_to_process = args.limit
    index_created = False

    print(f"Vectorizing label={args.label} into index={args.index} starting at skip={skip}")

    while processed < total_to_process:
        to_fetch = min(args.batch, total_to_process - processed)

        if args.label.upper() == "ALL":
            nodes = list_all_nodes(neo4j, skip=skip, limit=to_fetch)
        else:
            nodes = neo4j.list_nodes(args.label, limit=to_fetch, skip=skip)
            for n in nodes:
                n.setdefault("__labels", [args.label])

        if not nodes:
            print("No more nodes returned; finishing")
            break

        texts = [node_to_text(n) or json.dumps(n) for n in nodes]

        # Compute embeddings
        try:
            embeddings = embedder.embed(texts)
        except Exception as e:
            print(f"Embedding failed: {e}")
            time.sleep(5)
            continue

        # Create index on first successful embed (dimension auto-detected)
        if not index_created and embeddings:
            dim = len(embeddings[0])
            result = es.create_index(args.index, dim)
            if result.get("existed"):
                print(f"Index {args.index} already exists (dim={dim})")
            else:
                print(f"Created index {args.index} with dim={dim}")
            index_created = True

        # Upsert documents
        ok = fail = 0
        for node, text, emb in zip(nodes, texts, embeddings):
            uid = node.get("uid") or node.get("uuid") or node.get("id") or str(node.get("_id", "no-id"))
            metadata = {"labels": node.get("__labels", [])}
            try:
                es.upsert(args.index, uid, text, emb, metadata=metadata)
                ok += 1
            except Exception as e:
                print(f"Failed to upsert {uid}: {e}")
                fail += 1

        # Update progress
        processed += len(nodes)
        skip += len(nodes)
        progress["skip"] = skip
        with open(progress_file, "w", encoding="utf-8") as fh:
            json.dump(progress, fh)

        print(f"Processed {processed} nodes (skip={skip})  ok={ok} fail={fail}")

    print("Vectorization run complete")


if __name__ == "__main__":
    main()

