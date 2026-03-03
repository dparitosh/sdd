#!/usr/bin/env python3
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from dotenv import load_dotenv; load_dotenv()
from neo4j import GraphDatabase

d = GraphDatabase.driver(os.getenv('NEO4J_URI'), auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD')))
with d.session(database=os.getenv('NEO4J_DATABASE', 'neo4j')) as s:
    print("=== OntologyClass: with uri vs without ===")
    r = s.run("MATCH (n:OntologyClass) WHERE n.uri IS NOT NULL RETURN count(n) AS c")
    print(f"  With uri: {r.single()['c']}")
    r = s.run("MATCH (n:OntologyClass) WHERE n.uri IS NULL RETURN count(n) AS c")
    print(f"  Without uri (ghost): {r.single()['c']}")

    print("\n=== OntologyClass with uri — sample labels/ap_level ===")
    rows = s.run("""MATCH (n:OntologyClass) WHERE n.uri IS NOT NULL
        RETURN n.ap_level AS ap, n.label AS lbl, n.uri AS uri, n.comment AS comment
        ORDER BY n.ap_level, n.label LIMIT 20""")
    for r in rows:
        print(f"  ap={r['ap']}  label={r['lbl']}  uri={r['uri']}")

    print("\n=== Ghost OntologyClass sample (no uri) ===")
    rows = s.run("""MATCH (n:OntologyClass) WHERE n.uri IS NULL
        RETURN properties(n) AS props LIMIT 5""")
    for r in rows:
        print(f"  {r['props']}")

    print("\n=== OntologyProperty: with uri vs without ===")
    r = s.run("MATCH (n:OntologyProperty) WHERE n.uri IS NOT NULL RETURN count(n) AS c")
    print(f"  With uri: {r.single()['c']}")
    r = s.run("MATCH (n:OntologyProperty) WHERE n.uri IS NULL RETURN count(n) AS c")
    print(f"  Without uri (ghost): {r.single()['c']}")

    print("\n=== OntologyProperty with uri — sample ===")
    rows = s.run("""MATCH (n:OntologyProperty) WHERE n.uri IS NOT NULL
        RETURN n.ap_level AS ap, n.label AS lbl, n.uri AS uri LIMIT 20""")
    for r in rows:
        print(f"  ap={r['ap']}  label={r['lbl']}  uri={r['uri']}")

    print("\n=== OntologyClass cross-AP relationships currently ===")
    rows = s.run("""MATCH (n:OntologyClass)-[r]-() RETURN type(r) AS rtype, count(*) AS cnt ORDER BY cnt DESC""")
    for r in rows:
        print(f"  {r['rtype']}: {r['cnt']}")

    print("\n=== ExternalOwlClass sample (to understand naming vs OntologyClass) ===")
    rows = s.run("""MATCH (n:ExternalOwlClass) RETURN n.name AS name, n.uri AS uri, n.ap_level AS ap LIMIT 10""")
    for r in rows:
        print(f"  ap={r['ap']}  name={r['name']}  uri={r['uri']}")

    print("\n=== How many data nodes (Part/Requirement/Analysis/etc) have no INSTANCE_OF or DEFINED_BY links ===")
    for lbl in ['Part','Requirement','Analysis','AnalysisModel','Approval','Document','Assembly','GeometricModel','Material']:
        r = s.run(f"""
            MATCH (n:{lbl})
            WHERE NOT (n)-[:INSTANCE_OF|DEFINED_BY|CLASSIFIED_AS|INSTANCE_OF_CONCEPT]->()
            RETURN count(n) AS c
        """)
        print(f"  {lbl} without ontology link: {r.single()['c']}")

d.close()
