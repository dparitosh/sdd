#!/usr/bin/env python3
"""Vectorize STEP/AP242 semantic data into OpenSearch.

Targets:
  - StepEntityType (90 node types with structural meaning)
  - AP242Product (18 products with names + descriptions)
  - AP242AssemblyOccurrence (114 assembly BOM components)
  - AP242ProductDefinition (18 product definitions)
  - AP242Shape (18 shapes)

Usage:
    python scripts/vectorize_step_data.py
    python scripts/vectorize_step_data.py --index step_embeddings
"""
import os, sys, json, time, argparse, pathlib

_backend_dir = pathlib.Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

sys.stdout.reconfigure(line_buffering=True)

_env_file = _backend_dir.parent / ".env"
if _env_file.is_file():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _k, _, _v = _line.partition("=")
        _k = _k.strip()
        if _k and _k not in os.environ:
            os.environ[_k] = _v.strip()

import requests as http_requests
from neo4j import GraphDatabase
from src.agents.embeddings_ollama import OllamaEmbeddings
from src.agents.vectorstore_es import ElasticsearchVectorStore


def node_to_text(node: dict) -> str:
    """Convert a node dict to a text representation for embedding."""
    parts = []
    if node.get("__labels"):
        parts.append("Type: " + ", ".join(node["__labels"]))
    if node.get("name"):
        parts.append(f"Name: {node['name']}")
    if node.get("product_id"):
        parts.append(f"Product ID: {node['product_id']}")
    if node.get("description"):
        parts.append(f"Description: {node['description']}")
    if node.get("source_file"):
        parts.append(f"Source File: {node['source_file']}")
    if node.get("ap_level"):
        parts.append(f"AP Level: {node['ap_level']}")
    if node.get("nauo_id"):
        parts.append(f"Assembly Component: {node['nauo_id']}")
    if node.get("parent_step_id") and node.get("child_step_id"):
        parts.append(f"Assembly: parent=#{node['parent_step_id']} child=#{node['child_step_id']}")
    # Include remaining properties
    skip_keys = {"__labels", "name", "product_id", "description", "source_file",
                 "ap_level", "nauo_id", "parent_step_id", "child_step_id",
                 "updated_on", "oslc_uri", "oslc_resource_type", "oslc_domain"}
    for k, v in node.items():
        if k in skip_keys or v is None:
            continue
        try:
            parts.append(f"{k}: {v}")
        except Exception:
            pass
    return "\n".join(parts)[:2000]


QUERIES = [
    {
        "label": "StepEntityType",
        "query": """
            MATCH (t:StepEntityType)
            OPTIONAL MATCH (t)<-[:INSTANCE_OF]-(si:StepInstance)
            WITH t, count(si) AS instance_count
            RETURN t{.*, instance_count: instance_count} AS node, labels(t) AS lbls
            ORDER BY t.name
        """,
        "node_type": "StepEntityType",
    },
    {
        "label": "AP242Product",
        "query": """
            MATCH (p:AP242Product)
            RETURN p{.*} AS node, labels(p) AS lbls
            ORDER BY p.name
        """,
        "node_type": "AP242Product",
    },
    {
        "label": "AP242AssemblyOccurrence",
        "query": """
            MATCH (ao:AP242AssemblyOccurrence)
            RETURN ao{.*} AS node, labels(ao) AS lbls
            ORDER BY ao.name
        """,
        "node_type": "AP242AssemblyOccurrence",
    },
    {
        "label": "AP242ProductDefinition",
        "query": """
            MATCH (pd:AP242ProductDefinition)
            RETURN pd{.*} AS node, labels(pd) AS lbls
            ORDER BY pd.step_id
        """,
        "node_type": "AP242ProductDefinition",
    },
    {
        "label": "AP242Shape",
        "query": """
            MATCH (sh:AP242Shape)
            RETURN sh{.*} AS node, labels(sh) AS lbls
            ORDER BY sh.name
        """,
        "node_type": "AP242Shape",
    },
]


def main():
    parser = argparse.ArgumentParser(description="Vectorize STEP semantic data")
    parser.add_argument("--index", default="embeddings",
                        help="OpenSearch index name (default: embeddings)")
    parser.add_argument("--batch", type=int, default=32)
    args = parser.parse_args()

    uri = os.environ.get('NEO4J_URI', 'neo4j://127.0.0.1:7687')
    user = os.environ.get('NEO4J_USER', 'neo4j')
    pwd = os.environ.get('NEO4J_PASSWORD', 'tcs12345')
    db = os.environ.get('NEO4J_DATABASE', 'mossec')

    driver = GraphDatabase.driver(uri, auth=(user, pwd))
    embedder = OllamaEmbeddings()
    es = ElasticsearchVectorStore()

    print(f"Vectorizing STEP data into index={args.index}")
    print(f"Neo4j: {uri}, database={db}")
    print(f"Ollama: {embedder.base_url}, model={embedder.model}")
    print(f"OpenSearch: {es.host}")
    print("=" * 60)

    total_ok = 0
    total_fail = 0

    for spec in QUERIES:
        label = spec["label"]
        print(f"\nProcessing {label}...")

        with driver.session(database=db) as s:
            results = [r.data() for r in s.run(spec["query"])]

        if not results:
            print(f"  No {label} nodes found, skipping")
            continue

        nodes = []
        for r in results:
            node = dict(r["node"])
            node["__labels"] = list(r["lbls"])
            nodes.append(node)

        print(f"  Found {len(nodes)} {label} nodes")

        # Process in batches
        for i in range(0, len(nodes), args.batch):
            batch = nodes[i:i + args.batch]
            texts = [node_to_text(n) for n in batch]

            try:
                embeddings = embedder.embed(texts)
            except Exception as e:
                print(f"  Embedding failed: {e}")
                total_fail += len(batch)
                time.sleep(2)
                continue

            # Ensure index exists
            if i == 0 and embeddings:
                dim = len(embeddings[0])
                result = es.create_index(args.index, dim)
                if result.get("existed"):
                    print(f"  Index {args.index} exists (dim={dim})")
                else:
                    print(f"  Created index {args.index} (dim={dim})")

            # Build NDJSON bulk payload
            bulk_lines = []
            for node, text, emb in zip(batch, texts, embeddings):
                # Include file_uri hash so different revisions of the same part
                # get separate documents (e.g. two STEP file versions of Rotor Shaft Key)
                name_part = node.get('name', node.get('step_id', 'unknown'))
                file_part = node.get('file_uri', node.get('source_file', ''))
                import hashlib
                file_hash = hashlib.md5(file_part.encode()).hexdigest()[:8] if file_part else ''
                uid = f"{spec['node_type']}_{name_part}"
                if file_hash:
                    uid += f"_{file_hash}"
                uid = uid.replace(' ', '_').replace(';', '_').replace('(', '').replace(')', '')
                action = json.dumps({"index": {"_index": args.index, "_id": uid}})
                doc = json.dumps({
                    "text": text,
                    "vector": emb,
                    "metadata": {
                        "labels": node.get("__labels", []),
                        "node_type": spec["node_type"],
                        "ap_level": node.get("ap_level", "AP242"),
                        "source": "step_vectorizer",
                    }
                })
                bulk_lines.append(action)
                bulk_lines.append(doc)

            bulk_body = "\n".join(bulk_lines) + "\n"

            # Submit bulk with retry
            ok = 0
            for retry in range(5):
                try:
                    resp = http_requests.post(
                        f"{es.host}/_bulk",
                        data=bulk_body,
                        headers={"Content-Type": "application/x-ndjson"},
                        timeout=120,
                    )
                    resp.raise_for_status()
                    result = resp.json()
                    if result.get("errors"):
                        for item in result.get("items", []):
                            idx_result = item.get("index", {})
                            if idx_result.get("status", 200) < 300:
                                ok += 1
                            else:
                                total_fail += 1
                                print(f"  Bulk item error: {idx_result.get('error', {}).get('reason', 'unknown')}")
                    else:
                        ok = len(batch)
                    break
                except Exception as e:
                    if retry < 4:
                        wait = 2 ** (retry + 1)
                        print(f"  Bulk request failed (attempt {retry+1}), retrying in {wait}s: {e}")
                        time.sleep(wait)
                    else:
                        print(f"  Bulk request failed permanently: {e}")
                        total_fail += len(batch)

            total_ok += ok
            print(f"  Batch {i // args.batch + 1}: {ok}/{len(batch)} ok")
            time.sleep(1)  # brief pause between batches

    print("=" * 60)
    print(f"Vectorization complete: {total_ok} ok, {total_fail} failed")
    driver.close()


if __name__ == "__main__":
    main()
