#!/usr/bin/env python3
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from dotenv import load_dotenv; load_dotenv()
from neo4j import GraphDatabase

d = GraphDatabase.driver(os.getenv('NEO4J_URI'), auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD')))
with d.session(database=os.getenv('NEO4J_DATABASE', 'neo4j')) as s:
    print("=== OntologyClass nodes ===")
    rows = s.run("MATCH (n:OntologyClass) RETURN n ORDER BY n.ap_level, n.name LIMIT 60")
    for r in rows:
        n = dict(r['n'])
        print(f"  ap={n.get('ap_level')}  id={n.get('id')}  name={n.get('name')}  owl_uri={n.get('owl_uri','')}")

    print("\n=== OntologyProperty nodes ===")
    rows = s.run("MATCH (n:OntologyProperty) RETURN n ORDER BY n.ap_level, n.name LIMIT 30")
    for r in rows:
        n = dict(r['n'])
        print(f"  ap={n.get('ap_level')}  id={n.get('id')}  name={n.get('name')}  domain={n.get('domain_class')}  range={n.get('range_class')}")

    print("\n=== Ontology root nodes ===")
    rows = s.run("MATCH (n:Ontology) RETURN n LIMIT 10")
    for r in rows:
        n = dict(r['n'])
        print(f"  {n}")
d.close()
