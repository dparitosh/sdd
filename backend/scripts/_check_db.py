"""Quick check of Neo4j database contents."""
import sys, pathlib, os
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

# Load .env from project root
env_file = pathlib.Path(__file__).resolve().parent.parent.parent / ".env"
if env_file.is_file():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        if k and k not in os.environ:
            os.environ[k] = v.strip()

from src.web.services.neo4j_service import get_neo4j_service

neo = get_neo4j_service()

print("=== Neo4j Node Counts ===")
stats = neo.execute_query(
    "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS cnt ORDER BY cnt DESC LIMIT 25", {}
)
for r in stats:
    print(f"  {r['label']}: {r['cnt']:,}")

total = neo.execute_query("MATCH (n) RETURN count(n) AS total", {})
rels = neo.execute_query("MATCH ()-[r]->() RETURN count(r) AS total", {})
print(f"\nTotal nodes: {total[0]['total']:,}")
print(f"Total rels:  {rels[0]['total']:,}")

# Check STEP data specifically
step = neo.execute_query(
    "MATCH (f:StepFile) RETURN f.name AS name, f.ap_schema AS ap, f.file_schema AS schema LIMIT 10", {}
)
print(f"\n=== StepFile nodes ({len(step)}) ===")
for s in step:
    print(f"  {s['name']} | AP: {s.get('ap','-')} | Schema: {s.get('schema','-')}")

si = neo.execute_query("MATCH (n:StepInstance) RETURN count(n) AS cnt", {})
print(f"StepInstance nodes: {si[0]['cnt']:,}")

se = neo.execute_query("MATCH (n:StepEntityType) RETURN count(n) AS cnt", {})
print(f"StepEntityType nodes: {se[0]['cnt']:,}")

sr = neo.execute_query("MATCH ()-[r:STEP_REF]->() RETURN count(r) AS cnt", {})
print(f"STEP_REF relationships: {sr[0]['cnt']:,}")

# Check database name
db = neo.execute_query("CALL db.info() YIELD name RETURN name", {})
print(f"\nDatabase: {db}")
