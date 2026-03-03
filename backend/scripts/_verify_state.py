"""Quick verification of current Neo4j state after backfill."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
# Load .env
env_file = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, _, v = line.partition('=')
            if k.strip() not in os.environ:
                os.environ[k.strip()] = v.strip()

from web.services.neo4j_service import get_neo4j_service
svc = get_neo4j_service()

queries = [
    ("Total nodes", "MATCH (n) RETURN count(n) as c"),
    ("Total relationships", "MATCH ()-[r]->() RETURN count(r) as c"),
    ("StepFile nodes", "MATCH (f:StepFile) RETURN count(f) as c"),
    ("StepFile WITH ap_schema", "MATCH (f:StepFile) WHERE f.ap_schema IS NOT NULL RETURN count(f) as c"),
    ("StepFile WITHOUT ap_schema", "MATCH (f:StepFile) WHERE f.ap_schema IS NULL RETURN count(f) as c"),
    ("StepInstance nodes", "MATCH (si:StepInstance) RETURN count(si) as c"),
    ("StepInstance WITH ap_level", "MATCH (si:StepInstance) WHERE si.ap_level IS NOT NULL RETURN count(si) as c"),
    ("StepInstance WITHOUT ap_level", "MATCH (si:StepInstance) WHERE si.ap_level IS NULL RETURN count(si) as c"),
    ("StepEntityType nodes", "MATCH (t:StepEntityType) RETURN count(t) as c"),
    ("Node labels", "CALL db.labels() YIELD label RETURN collect(label) as c"),
    ("Relationship types", "CALL db.relationshipTypes() YIELD relationshipType RETURN collect(relationshipType) as c"),
]

print("=" * 60)
print("NEO4J DATABASE STATE VERIFICATION")
print("=" * 60)
for label, q in queries:
    try:
        rows = svc.execute_query(q, {})
        val = rows[0]['c'] if rows else 'N/A'
        print(f"  {label:40s}: {val}")
    except Exception as e:
        print(f"  {label:40s}: ERROR - {e}")

# Show a sample StepFile
print("\nSample StepFile (first 3):")
rows = svc.execute_query(
    "MATCH (f:StepFile) RETURN f.name AS name, f.ap_schema AS ap, f.ap_level AS lvl, f.file_schema AS fs LIMIT 3", {}
)
for r in rows:
    print(f"  {r['name']}: ap={r['ap']}, level={r['lvl']}, schema={r['fs'][:50] if r['fs'] else 'None'}...")
print("=" * 60)
