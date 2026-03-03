"""Debug script to test list_all_nodes query."""
import sys
sys.path.insert(0, ".")
from src.web.services.neo4j_service import get_neo4j_service

neo4j = get_neo4j_service()
q = "MATCH (n) RETURN n AS node, labels(n) AS node_labels SKIP 0 LIMIT 3"
results = neo4j.execute_query(q, {"skip": 0, "limit": 3})
print(f"got {len(results)} rows")
for i, r in enumerate(results):
    node = dict(r["node"])
    labels = r["node_labels"]
    print(f"row {i}: labels={labels} node_keys={list(node.keys())[:5]}")
print("OK")
