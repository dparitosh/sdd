"""Live Neo4j graph diagnostic — pair query focused."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from dotenv import load_dotenv
load_dotenv(str(Path(__file__).resolve().parent.parent.parent / ".env"))
from backend.src.graph.connection import Neo4jConnection
from backend.src.utils.config import Config

c = Config()
conn = Neo4jConnection(c.neo4j_uri, c.neo4j_user, c.neo4j_password)
conn.connect()

r0 = conn.execute_query("MATCH (n) RETURN count(n) AS c")[0]["c"]
r1 = conn.execute_query("MATCH ()-[r]->() RETURN count(r) AS c")[0]["c"]
print(f"NODES: {r0}   RELS: {r1}")

WC_N = ("(NOT 'Documentation' IN labels(n) AND NOT 'DomainConcept' IN labels(n) AND NOT 'OWLObjectProperty' IN labels(n) AND NOT 'OWLDatatypeProperty' IN labels(n))")
WC_M = WC_N.replace("labels(n)", "labels(m)")

print("\n[1] Pair count (ENTERPRISE no-filter):")
r2 = conn.execute_query(f"MATCH (n)-[r]->(m) WHERE {WC_N} AND {WC_M} RETURN count(*) AS c")[0]["c"]
print(f"    {r2}")

print("\n[2] Sample 8 pairs:")
for row in conn.execute_query(f"MATCH (n)-[r]->(m) WHERE {WC_N} AND {WC_M} RETURN labels(n)[0] AS sl, coalesce(n.name,n.id) AS sn, type(r) AS rel, labels(m)[0] AS tl, coalesce(m.name,m.id) AS tn LIMIT 8"):
    print(f"    ({row['sl']}:{row['sn']}) -[{row['rel']}]-> ({row['tl']}:{row['tn']})")

print("\n[3] Pair LIMIT 1500 returns:")
r3 = conn.execute_query(f"MATCH (n)-[r]->(m) WHERE {WC_N} AND {WC_M} WITH n,r,m LIMIT 1500 RETURN count(*) AS c")[0]["c"]
print(f"    {r3}")

print("\n[4] Null-id check (5 rows):")
for row in conn.execute_query(f"MATCH (n)-[r]->(m) WHERE {WC_N} AND {WC_M} WITH n,r,m LIMIT 5 RETURN coalesce(n.id,elementId(n)) AS nid, coalesce(m.id,elementId(m)) AS mid, type(r) AS rel, elementId(r) AS rid"):
    print(f"    nid={row['nid']}  mid={row['mid']}  rel={row['rel']}")

print("\n[5] Rel types excl metadata:")
for row in conn.execute_query("MATCH (n)-[r]->(m) WHERE NOT 'Documentation' IN labels(n) AND NOT 'DomainConcept' IN labels(n) RETURN type(r) AS t, count(*) AS c ORDER BY c DESC LIMIT 15"):
    print(f"    {row['t']}: {row['c']}")

conn.close()
print("\n=== Done ===")
