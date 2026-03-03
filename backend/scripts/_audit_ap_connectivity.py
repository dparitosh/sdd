#!/usr/bin/env python3
"""Audit AP239 / AP242 connectivity in Neo4j."""
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from dotenv import load_dotenv; load_dotenv()
from neo4j import GraphDatabase

d = GraphDatabase.driver(os.getenv('NEO4J_URI'), auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD')))
with d.session(database=os.getenv('NEO4J_DATABASE', 'neo4j')) as s:

    print("=== AP239 / AP242 node counts by label ===")
    for lbl in ['Requirement','RequirementVersion','Service','ServiceProvider','Ontology',
                'OntologyClass','OntologyProperty','ExternalOntology','ExternalOwlClass',
                'OWLClass','OWLObjectProperty','OWLDatatypeProperty']:
        cnt = s.run(f"MATCH (n:{lbl}) RETURN count(n) AS c").single()['c']
        if cnt:
            print(f"  {lbl}: {cnt}")

    print("\n=== Nodes with ap_level='AP239' ===")
    r = s.run("MATCH (n) WHERE n.ap_level='AP239' RETURN labels(n) AS lbl, count(n) AS c ORDER BY c DESC")
    for row in r: print(f"  {row['lbl']}: {row['c']}")

    print("\n=== Nodes with ap_level='AP242' ===")
    r = s.run("MATCH (n) WHERE n.ap_level='AP242' RETURN labels(n) AS lbl, count(n) AS c ORDER BY c DESC")
    for row in r: print(f"  {row['lbl']}: {row['c']}")

    print("\n=== Nodes with ap_level='AP243' ===")
    r = s.run("MATCH (n) WHERE n.ap_level='AP243' RETURN labels(n) AS lbl, count(n) AS c ORDER BY c DESC")
    for row in r: print(f"  {row['lbl']}: {row['c']}")

    print("\n=== Ontology / OSLC nodes and their relationships ===")
    r = s.run("""
        MATCH (n) WHERE 'Ontology' IN labels(n) OR 'ExternalOntology' IN labels(n)
        RETURN n.id AS id, COALESCE(n.name, n.label) AS name, labels(n) AS lbls
        LIMIT 10
    """)
    for row in r: print(f"  {row['id']}  {row['name']}  {row['lbls']}")

    print("\n=== OWLClass relationship counts from top ===")
    r = s.run("""
        MATCH (n:OWLClass)-[rel]-()
        RETURN type(rel) AS rtype, count(*) AS cnt
        ORDER BY cnt DESC LIMIT 15
    """)
    for row in r: print(f"  {row['rtype']}: {row['cnt']}")

    print("\n=== ExternalOwlClass relationship counts ===")
    r = s.run("""
        MATCH (n:ExternalOwlClass)-[rel]-()
        RETURN type(rel) AS rtype, count(*) AS cnt
        ORDER BY cnt DESC LIMIT 15
    """)
    for row in r: print(f"  {row['rtype']}: {row['cnt']}")

    print("\n=== Requirement relationship counts ===")
    r = s.run("""
        MATCH (n:Requirement)-[rel]-()
        RETURN type(rel) AS rtype, labels(startNode(rel)) AS from_lbl, labels(endNode(rel)) AS to_lbl, count(*) AS cnt
        ORDER BY cnt DESC LIMIT 20
    """)
    for row in r: print(f"  {row['rtype']}  {row['from_lbl']} -> {row['to_lbl']}: {row['cnt']}")

    print("\n=== Sample isolated OWLClass nodes (degree=0) ===")
    r = s.run("""
        MATCH (n:OWLClass)
        WHERE NOT (n)--()
        RETURN n.id AS id, COALESCE(n.name, n.label) AS name
        LIMIT 5
    """)
    rows = list(r)
    print(f"  Isolated OWLClass nodes: {len(rows)} (sample below)")
    for row in rows: print(f"    {row['id']}  {row['name']}")

    print("\n=== Sample isolated ExternalOwlClass nodes (degree=0) ===")
    r = s.run("""
        MATCH (n:ExternalOwlClass)
        WHERE NOT (n)--()
        RETURN count(n) AS c
    """)
    print(f"  Isolated ExternalOwlClass: {r.single()['c']}")

    print("\n=== Total isolated nodes (any label, degree=0) ===")
    r = s.run("MATCH (n) WHERE NOT (n)--() RETURN labels(n) AS lbl, count(n) AS c ORDER BY c DESC LIMIT 20")
    for row in r: print(f"  {row['lbl']}: {row['c']}")

d.close()
