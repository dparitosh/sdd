"""Quick verification of ReqIF ingestion results."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from neo4j import GraphDatabase

d = GraphDatabase.driver("neo4j://127.0.0.1:7687", auth=("neo4j", "tcs12345"))
s = d.session(database="mossec")

print("=== Bearing Requirements (BREQ-*) ===")
for r in s.run('MATCH (r:Requirement) WHERE r.id STARTS WITH "BREQ" RETURN r.id AS id, r.name AS name, r.description AS desc ORDER BY r.sort_order'):
    desc = (r["desc"] or "")[:70]
    print(f'  {r["id"]:8s} | {r["name"][:50]:50s} | {desc}')

print("\n=== RequirementSpecification ===")
for r in s.run("MATCH (s:RequirementSpecification) RETURN s.name AS name, s.identifier AS id"):
    print(f'  {r["name"]}  (id={r["id"]})')

print("\n=== ReqIFFile ===")
for r in s.run("MATCH (f:ReqIFFile) RETURN f.filename AS fn, f.source_tool AS tool"):
    print(f'  {r["fn"]}  (tool={r["tool"]})')

print("\n=== Traceability Chain ===")
for r in s.run('MATCH (f:ReqIFFile)-[:CONTAINS]->(sp:RequirementSpecification)-[:CONTAINS_REQUIREMENT]->(req:Requirement) WHERE req.id STARTS WITH "BREQ" RETURN count(req) AS cnt'):
    print(f'  ReqIFFile -> Spec -> Requirements: {r["cnt"]}')

print("\n=== Total Requirement count ===")
for r in s.run("MATCH (n:Requirement) RETURN count(n) AS total"):
    print(f'  Total Requirement nodes: {r["total"]}')

s.close()
d.close()
