"""Check DB state and propagate ap_level to StepInstance if needed."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
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

import importlib.util
spec = importlib.util.spec_from_file_location(
    "neo4j_service",
    os.path.join(os.path.dirname(__file__), '..', 'src', 'web', 'services', 'neo4j_service.py')
)
mod = importlib.util.module_from_spec(spec)
sys.modules['neo4j_service'] = mod

# We need to handle dependencies - just use neo4j driver directly
from neo4j import GraphDatabase
uri = os.environ.get('NEO4J_URI', 'neo4j://127.0.0.1:7687')
user = os.environ.get('NEO4J_USER', 'neo4j')
pwd = os.environ.get('NEO4J_PASSWORD', 'tcs12345')
db = os.environ.get('NEO4J_DATABASE', 'mossec')
driver = GraphDatabase.driver(uri, auth=(user, pwd))

def run_query(query, params=None):
    with driver.session(database=db) as session:
        result = session.run(query, params or {})
        return [dict(r) for r in result]

def run_write(query, params=None):
    with driver.session(database=db) as session:
        result = session.run(query, params or {})
        return [dict(r) for r in result]

svc = None  # not used

checks = {
    "Total nodes": "MATCH (n) RETURN count(n) as c",
    "Total rels": "MATCH ()-[r]->() RETURN count(r) as c",
    "StepFile total": "MATCH (f:StepFile) RETURN count(f) as c",
    "StepFile WITH ap_schema": "MATCH (f:StepFile) WHERE f.ap_schema IS NOT NULL RETURN count(f) as c",
    "StepFile NO ap_schema": "MATCH (f:StepFile) WHERE f.ap_schema IS NULL RETURN count(f) as c",
    "StepInstance total": "MATCH (si:StepInstance) RETURN count(si) as c",
    "SI WITH ap_level": "MATCH (si:StepInstance) WHERE si.ap_level IS NOT NULL RETURN count(si) as c",
    "SI NO ap_level": "MATCH (si:StepInstance) WHERE si.ap_level IS NULL RETURN count(si) as c",
    "StepEntityType": "MATCH (t:StepEntityType) RETURN count(t) as c",
}

print("=" * 50)
print("DATABASE STATE")
print("=" * 50)
for label, q in checks.items():
    rows = run_query(q)
    print(f"  {label:30s}: {rows[0]['c']}")

# If StepInstance without ap_level, run propagation
rows = run_query("MATCH (si:StepInstance) WHERE si.ap_level IS NULL RETURN count(si) as c")
missing = rows[0]['c']
if missing > 0:
    print(f"\nPropagating ap_level to {missing} StepInstance nodes...")
    result = run_write(
        """
        MATCH (f:StepFile)-[:CONTAINS_INSTANCE]->(si:StepInstance)
        WHERE f.ap_level IS NOT NULL AND si.ap_level IS NULL
        SET si.ap_level = f.ap_level
        RETURN count(si) as updated
        """)
    print(f"  Updated: {result[0]['updated']} StepInstance nodes")
else:
    print("\nAll StepInstance nodes already have ap_level.")

# Show sample
print("\nSample StepFile:")
rows = run_query(
    "MATCH (f:StepFile) RETURN f.name AS n, f.ap_schema AS ap, f.ap_level AS lvl LIMIT 3"
)
for r in rows:
    print(f"  {r['n']}: ap={r['ap']}, lvl={r['lvl']}")
print("=" * 50)
