"""
Sprint 2 AP243 Integration - Linkable Resources Analysis
Shows what AP243 reference data is available for linking to SDD artifacts
"""
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
print('SPRINT 2: AP243 INTEGRATION FEASIBILITY ANALYSIS')
print('='*70)

# 1. Check OntologyClass (potential replacement for ExternalOwlClass)
print('\n### 1. OntologyClass Nodes')
print('-' * 70)

ontology_count = conn.execute_query("MATCH (o:OntologyClass) WHERE o.ap_level = 'AP243' RETURN count(o) AS count")
print(f"Total OntologyClass nodes (AP243): {ontology_count[0]['count']}")

if ontology_count[0]['count'] > 0:
    samples = conn.execute_query("""
        MATCH (o:OntologyClass)
        WHERE o.ap_level = 'AP243'
        RETURN o.name AS name, o.domain AS domain, o.description AS description
        LIMIT 10
    """)
    print('\nSample ontologies:')
    for s in samples:
        name = s.get('name', 'N/A')
        domain = s.get('domain', 'N/A')
        desc = s.get('description', '')
        if desc and len(desc) > 60:
            desc = desc[:57] + '...'
        print(f'  - {name} ({domain}): {desc}')

# 2. Check for any OWL-related nodes
print('\n\n### 2. OWL-Related Nodes')
print('-' * 70)

owl_labels = ['OWLClass', 'ExternalOwlClass', 'OWLProperty']
for label in owl_labels:
    count_result = conn.execute_query(f"MATCH (n:{label}) RETURN count(n) AS count")
    count = count_result[0]['count']
    print(f"{label}: {count}")
    
    if count > 0 and count < 20:
        # Show sample
        samples = conn.execute_query(f"MATCH (n:{label}) RETURN n.name AS name LIMIT 5")
        names = [s.get('name', 'N/A') for s in samples]
        print(f"  Sample: {', '.join(names)}")

# 3. Check Requirements (AP239) for linking
print('\n\n### 3. Requirements (AP239) for Linking')
print('-' * 70)

req_count = conn.execute_query("MATCH (r:Requirement) WHERE r.ap_level = 'AP239' RETURN count(r) AS count")
print(f"Total Requirement nodes (AP239): {req_count[0]['count']}")

if req_count[0]['count'] > 0:
    samples = conn.execute_query("""
        MATCH (r:Requirement)
        WHERE r.ap_level = 'AP239'
        RETURN r.id AS id, r.name AS name
        LIMIT 10
    """)
    print('\nSample requirements:')
    for s in samples:
        rid = s.get('id', 'N/A')
        name = s.get('name', 'N/A')
        print(f'  - {rid}: {name}')

# 4. Check current SDD artifact-requirement links
print('\n\n### 4. Current Artifact-Requirement Links')
print('-' * 70)

link_query = """
MATCH (a:SimulationArtifact)-[r:LINKED_TO_REQUIREMENT]->(req:Requirement)
RETURN a.id AS artifact, req.id AS requirement, type(r) AS rel_type
"""
links = conn.execute_query(link_query)
print(f"Existing links: {len(links)}")
if links:
    for link in links[:10]:
        print(f"  {link['artifact']} --> {link['requirement']}")

# 5. Recommended integration strategy
print('\n\n### 5. RECOMMENDED SPRINT 2 STRATEGY')
print('-' * 70)
print("""
Based on available data, here's what we can implement:

✅ FEASIBLE (High Priority):
  1. Artifact → OntologyClass linking
     - 17 OntologyClass nodes available (AP243)
     - Link artifacts based on domain/type (e.g., thermal, mechanical)
  
  2. Artifact → Requirement strengthening
     - Currently have 9 links created in Sprint 1
     - Add metadata properties (trace_depth, validation_status)
  
  3. SimulationRun workflow implementation
     - Create SimulationRun nodes
     - Link Run → Artifact (GENERATED relationship)
     - Add execution metadata (solver, parameters, timestamp)

❌ NOT FEASIBLE (Missing Data):
  1. ExternalUnit linking - No ExternalUnit nodes in database
  2. ExternalOwlClass linking - No ExternalOwlClass nodes in database
  
⏸️ DEFERRED (Requires Data Ingestion):
  - AP243 reference data ingestion needed first
  - Units, external ontologies, etc.

PRIORITY ORDER:
  [1] OntologyClass linking (12h) - Use what exists
  [2] SimulationRun workflow (15h) - Core functionality
  [3] Validation case tracking (12h) - MOSSEC compliance  
  [4] AP243 reference data ingestion (TBD) - Future sprint
""")

conn.close()
print('\n' + '='*70 + '\n')
