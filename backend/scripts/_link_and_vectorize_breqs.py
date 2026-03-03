"""Link BREQ requirements to Parts/AP242Products, then vectorize."""
import sys, pathlib, time, json, os
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

# Load .env
_env_file = pathlib.Path(__file__).resolve().parent.parent.parent / ".env"
if _env_file.is_file():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _k, _, _v = _line.partition("=")
        _k = _k.strip()
        if _k and _k not in os.environ:
            os.environ[_k] = _v.strip()

from neo4j import GraphDatabase
import requests as http_requests

uri = os.environ.get("NEO4J_URI", "neo4j://127.0.0.1:7687")
user = os.environ.get("NEO4J_USER", "neo4j")
pwd = os.environ.get("NEO4J_PASSWORD", "tcs12345")
db = os.environ.get("NEO4J_DATABASE", "mossec")

driver = GraphDatabase.driver(uri, auth=(user, pwd))

def run(cypher, params=None):
    with driver.session(database=db) as s:
        return [r.data() for r in s.run(cypher, params or {})]

# ── 1. Survey current state ──────────────────────────────────────────
print("=" * 60)
print("STEP 1: Survey existing graph state")
print("=" * 60)

parts = run("MATCH (p:Part) RETURN p.id AS id, p.name AS name")
print(f"\nParts ({len(parts)}):")
for p in parts:
    print(f"  {p['id']:12s} | {p['name']}")

products = run("MATCH (p:AP242Product) RETURN p.name AS name, p.product_id AS pid, p.source_file AS sf ORDER BY p.name")
print(f"\nAP242Products ({len(products)}):")
for p in products:
    print(f"  {p['name'][:45]:45s} | pid={p['pid']} | {p['sf']}")

breqs = run('MATCH (r:Requirement) WHERE r.id STARTS WITH "BREQ" RETURN r.id AS id, r.name AS name ORDER BY r.sort_order')
print(f"\nBearing Requirements ({len(breqs)}):")
for r in breqs:
    print(f"  {r['id']:8s} | {r['name']}")

# Check existing links
existing = run('MATCH (r:Requirement)-[rel]->() WHERE r.id STARTS WITH "BREQ" RETURN type(rel) AS t, count(*) AS cnt')
existing2 = run('MATCH ()-[rel]->(r:Requirement) WHERE r.id STARTS WITH "BREQ" RETURN type(rel) AS t, count(*) AS cnt')
print(f"\nExisting BREQ outbound links: {existing}")
print(f"Existing BREQ inbound links: {existing2}")

# ── 2. Link bearing requirements to parts ────────────────────────────
print("\n" + "=" * 60)
print("STEP 2: Link BREQ requirements to Parts and AP242Products")
print("=" * 60)

# Find bearing-related parts and products by name matching
bearing_products = run("""
    MATCH (p:AP242Product)
    WHERE toLower(p.name) CONTAINS 'bearing'
       OR toLower(p.source_file) CONTAINS 'bearing'
    RETURN p.name AS name, p.product_id AS pid
""")
print(f"\nBearing-related AP242Products: {len(bearing_products)}")
for p in bearing_products:
    print(f"  {p['name']} (pid={p['pid']})")

bearing_parts = run("""
    MATCH (p:Part)
    WHERE toLower(p.name) CONTAINS 'bearing'
    RETURN p.id AS id, p.name AS name
""")
print(f"\nBearing-related Parts: {len(bearing_parts)}")

# Link all BREQ requirements to ALL parts (motor system-level requirements apply to all parts)
link_count = 0
res = run("""
    MATCH (r:Requirement) WHERE r.id STARTS WITH "BREQ"
    MATCH (p:Part)
    MERGE (r)-[lnk:APPLIES_TO_PART]->(p)
    ON CREATE SET lnk.created_at = datetime(), lnk.source = 'reqif_linker'
    RETURN count(lnk) AS cnt
""")
link_count += res[0]["cnt"] if res else 0
print(f"\nLinked BREQ -> Part (APPLIES_TO_PART): {res[0]['cnt'] if res else 0}")

# Link to AP242Products
res = run("""
    MATCH (r:Requirement) WHERE r.id STARTS WITH "BREQ"
    MATCH (p:AP242Product)
    MERGE (p)-[lnk:SATISFIES_REQUIREMENT]->(r)
    ON CREATE SET lnk.created_at = datetime(), lnk.source = 'reqif_linker'
    RETURN count(lnk) AS cnt
""")
link_count += res[0]["cnt"] if res else 0
print(f"Linked AP242Product -> BREQ (SATISFIES_REQUIREMENT): {res[0]['cnt'] if res else 0}")

# Assign OSLC URIs to the new requirements
base_url = "http://localhost:5000/api/v1"
res = run("""
    MATCH (r:Requirement) WHERE r.id STARTS WITH "BREQ" AND r.oslc_uri IS NULL
    SET r.oslc_uri = $base + '/Requirement/' + r.id,
        r.oslc_resource_type = 'http://open-services.net/ns/rm#Requirement',
        r.oslc_domain = 'http://open-services.net/ns/rm#'
    RETURN count(r) AS cnt
""", {"base": base_url})
print(f"Assigned OSLC URIs: {res[0]['cnt'] if res else 0}")

# Link to RequirementSpecification's parent ReqIFFile -> existing data
res = run("""
    MATCH (f:ReqIFFile)-[:CONTAINS]->(sp:RequirementSpecification)-[:CONTAINS_REQUIREMENT]->(r:Requirement)
    WHERE r.id STARTS WITH "BREQ"
    RETURN f.filename AS file, sp.name AS spec, count(r) AS reqs
""")
print(f"Traceability: {res}")

# ── 3. Vectorize bearing requirements ────────────────────────────────
print("\n" + "=" * 60)
print("STEP 3: Vectorize bearing requirements into OpenSearch")
print("=" * 60)

from src.agents.embeddings_ollama import OllamaEmbeddings
from src.agents.vectorstore_es import ElasticsearchVectorStore

embedder = OllamaEmbeddings()
es = ElasticsearchVectorStore()

# Fetch all BREQ requirements
reqs = run("""
    MATCH (r:Requirement) WHERE r.id STARTS WITH "BREQ"
    RETURN r{.*} AS node, labels(r) AS lbls
    ORDER BY r.sort_order
""")

if not reqs:
    print("No BREQ requirements found!")
else:
    print(f"Vectorizing {len(reqs)} bearing requirements...")

    texts = []
    nodes = []
    for rec in reqs:
        node = dict(rec["node"])
        node["__labels"] = list(rec["lbls"])
        nodes.append(node)
        text_parts = [
            f"Type: Requirement, Bearing",
            f"Name: {node.get('name', '')}",
            f"Description: {node.get('description', '')}",
            f"ID: {node.get('id', '')}",
            f"Source: {node.get('source', '')} / {node.get('source_tool', '')}",
            f"Priority: {node.get('priority', '')}",
            f"Status: {node.get('status', '')}",
        ]
        texts.append("\n".join(text_parts)[:2000])

    # Embed all at once
    try:
        embeddings = embedder.embed(texts)
        print(f"  Generated {len(embeddings)} embeddings (dim={len(embeddings[0])})")
    except Exception as e:
        print(f"  Embedding failed: {e}")
        embeddings = []

    if embeddings:
        # Ensure index exists
        es.create_index("embeddings", len(embeddings[0]))

        # Bulk upsert
        bulk_lines = []
        for node, text, emb in zip(nodes, texts, embeddings):
            uid = f"Requirement_{node['id']}"
            action = json.dumps({"index": {"_index": "embeddings", "_id": uid}})
            doc = json.dumps({
                "text": text,
                "vector": emb,
                "metadata": {
                    "labels": node.get("__labels", []),
                    "node_type": "Requirement",
                    "ap_level": node.get("ap_level", "AP239"),
                    "source": "reqif_vectorizer",
                    "requirement_type": "Bearing",
                }
            })
            bulk_lines.append(action)
            bulk_lines.append(doc)

        bulk_body = "\n".join(bulk_lines) + "\n"

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
                    errs = [i for i in result["items"] if i.get("index", {}).get("status", 200) >= 300]
                    print(f"  Bulk upsert: {len(result['items']) - len(errs)} ok, {len(errs)} errors")
                else:
                    print(f"  Bulk upsert: {len(result['items'])}/{len(result['items'])} ok")
                break
            except Exception as e:
                if retry < 4:
                    print(f"  Retry {retry+1}: {e}")
                    time.sleep(2 ** retry)
                else:
                    print(f"  Bulk failed: {e}")

# ── 4. Final summary ────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 4: Final verification")
print("=" * 60)

total_reqs = run("MATCH (n:Requirement) RETURN count(n) AS cnt")[0]["cnt"]
breq_reqs = run('MATCH (n:Requirement) WHERE n.id STARTS WITH "BREQ" RETURN count(n) AS cnt')[0]["cnt"]
req_specs = run("MATCH (n:RequirementSpecification) RETURN count(n) AS cnt")[0]["cnt"]
reqif_files = run("MATCH (n:ReqIFFile) RETURN count(n) AS cnt")[0]["cnt"]
breq_links = run('MATCH (r:Requirement)-[]-() WHERE r.id STARTS WITH "BREQ" RETURN count(*) AS cnt')[0]["cnt"]

print(f"  Total Requirements:    {total_reqs}")
print(f"  Bearing Requirements:  {breq_reqs}")
print(f"  Req Specifications:    {req_specs}")
print(f"  ReqIF Files:           {reqif_files}")
print(f"  BREQ total links:      {breq_links}")

driver.close()
print("\nDone.")
