"""Debug: trace RAG highlight data flow end-to-end."""
import sys, os, json
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.web.services.neo4j_service import get_neo4j_service

neo4j = get_neo4j_service()

# 1. What IDs does the graph API use for SimulationDossier nodes?
print("=== Graph node IDs for SimulationDossier ===")
rows = neo4j.execute_query(
    "MATCH (n:SimulationDossier) "
    "RETURN coalesce(n.id, elementId(n)) AS graph_id, n.id AS n_id, n.uid AS n_uid, n.name AS name "
    "LIMIT 5"
)
for r in rows:
    print(f"  graph_id={r['graph_id']!r}  n.id={r['n_id']!r}  n.uid={r['n_uid']!r}  name={r['name']!r}")

# 2. What UIDs does the RAG pipeline return?
from src.agents.semantic_agent import SemanticAgent
agent = SemanticAgent()
result = agent.semantic_insight("list of dossiers", top_k=5)

print("\n=== RAG source UIDs ===")
for s in result.get("sources", []):
    print(f"  uid={s.get('uid')!r}  name={s.get('name')!r}")

# 3. Compare
graph_ids = set(str(r['graph_id']) for r in rows)
source_uids = set(s.get('uid') for s in result.get('sources', []) if s.get('uid'))
print(f"\n=== Comparison ===")
print(f"Graph IDs:  {sorted(graph_ids)}")
print(f"Source UIDs: {sorted(source_uids)}")
print(f"Intersection: {sorted(graph_ids & source_uids)}")
print(f"Only in graph: {sorted(graph_ids - source_uids)}")
print(f"Only in RAG:   {sorted(source_uids - graph_ids)}")
