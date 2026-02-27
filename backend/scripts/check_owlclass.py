"""Check OWLClass nodes for ontology linking"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.src.graph.connection import Neo4jConnection
from backend.src.utils.config import Config

config = Config()
conn = Neo4jConnection(config.neo4j_uri, config.neo4j_user, config.neo4j_password)
conn.connect()

print('\n' + '='*70)
print('OWLClass NODES ANALYSIS')
print('='*70)

# Sample OWLClass nodes
samples = conn.execute_query("""
    MATCH (o:OWLClass)
    RETURN o.name AS name, o.domain AS domain, o.definition AS definition, o.ap_level AS ap_level
    LIMIT 20
""")

print(f'\n### Sample OWLClass Nodes (first 20 of 1,581)')
print('-' * 70)

for i, s in enumerate(samples, 1):
    name = s.get('name', 'N/A')
    domain = s.get('domain', 'N/A')
    ap_level = s.get('ap_level', 'N/A')
    definition = s.get('definition', '')
    
    print(f'\n{i}. {name}')
    print(f'   Domain: {domain}')
    print(f'   AP Level: {ap_level}')
    if definition:
        if len(definition) > 80:
            definition = definition[:77] + '...'
        print(f'   Definition: {definition}')

# Check for relevant simulation domains
print('\n\n### Simulation-Relevant OWLClass Nodes')
print('-' * 70)

sim_owl = conn.execute_query("""
    MATCH (o:OWLClass)
    WHERE o.name CONTAINS 'thermal' 
       OR o.name CONTAINS 'mechanical'
       OR o.name CONTAINS 'electromagnetic'
       OR o.name CONTAINS 'vibration'
       OR o.name CONTAINS 'efficiency'
       OR o.name CONTAINS 'performance'
    RETURN o.name AS name, o.domain AS domain
    LIMIT 15
""")

if sim_owl:
    print(f'\nFound {len(sim_owl)} simulation-relevant OWL classes:')
    for s in sim_owl:
        print(f'  - {s["name"]} (domain: {s.get("domain", "N/A")})')
else:
    print('No simulation-specific OWL classes found by name matching')
    
    # Try broader search
    print('\nTrying domain-based search...')
    domain_owl = conn.execute_query("""
        MATCH (o:OWLClass)
        WHERE o.domain IS NOT NULL
        RETURN DISTINCT o.domain AS domain, count(*) AS count
        ORDER BY count DESC
        LIMIT 10
    """)
    
    print('\nTop domains in OWLClass:')
    for d in domain_owl:
        print(f'  {d["domain"]}: {d["count"]} classes')

conn.close()
print('\n' + '='*70 + '\n')
