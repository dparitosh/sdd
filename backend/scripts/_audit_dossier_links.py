#!/usr/bin/env python3
"""Audit dossier relationships in Neo4j."""
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from dotenv import load_dotenv; load_dotenv()
from neo4j import GraphDatabase

d = GraphDatabase.driver(os.getenv('NEO4J_URI'), auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD')))
with d.session(database=os.getenv('NEO4J_DATABASE', 'neo4j')) as s:
    print("=== Dossier relationships (direct) ===")
    rows = s.run("""
        MATCH (d:SimulationDossier)-[r]-(other)
        RETURN type(r) AS rel, labels(other) AS other_labels, count(*) AS cnt
        ORDER BY cnt DESC
    """)
    for r in rows:
        print(f"  {r['rel']} -> {r['other_labels']}  (x{r['cnt']})")

    print("\n=== Dossier motor_id values ===")
    rows = s.run("MATCH (d:SimulationDossier) RETURN d.id AS id, d.motor_id AS motor_id, d.name AS name ORDER BY d.id")
    for r in rows:
        print(f"  {r['id']}  motor={r['motor_id']}  name={r['name']}")

    print("\n=== Parts / SimulationModel / Study nodes (sample) ===")
    for lbl in ['Part', 'SimulationModel', 'Study', 'Requirement', 'SimulationRun']:
        cnt = s.run(f"MATCH (n:{lbl}) RETURN count(n) AS c").single()['c']
        print(f"  {lbl}: {cnt}")

    print("\n=== Artifact relationships ===")
    rows = s.run("""
        MATCH (a:SimulationArtifact)-[r]-(other)
        RETURN type(r) AS rel, labels(other) AS other_labels, count(*) AS cnt
        ORDER BY cnt DESC
    """)
    for r in rows:
        print(f"  {r['rel']} -> {r['other_labels']}  (x{r['cnt']})")

    print("\n=== EvidenceCategory sample ===")
    rows = s.run("MATCH (e:EvidenceCategory) RETURN e LIMIT 3")
    for r in rows:
        print(f"  {dict(r['e'])}")

d.close()
