"""Analyze AP243 data distribution in Neo4j"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.src.graph.connection import Neo4jConnection
from backend.src.utils.config import Config

config = Config()
conn = Neo4jConnection(config.neo4j_uri, config.neo4j_user, config.neo4j_password)
conn.connect()

# Get AP243 nodes breakdown by label
result = conn.execute_query("""
    MATCH (n) 
    WHERE n.ap_level = 'AP243' 
    RETURN DISTINCT labels(n) AS labels, count(*) AS count 
    ORDER BY count DESC 
    LIMIT 20
""")

print('\n' + '='*60)
print('AP243 NODES DISTRIBUTION')
print('='*60)
print(f"{'Label':<35} {'Count':>10}")
print('-' * 60)

for r in result:
    label = str(r['labels'])[2:-2]  # Remove ['...'] brackets
    count = r['count']
    print(f'{label:<35} {count:>10}')

# Check for ExternalOwlClass nodes specifically
owl_count = conn.execute_query("""
    MATCH (o:ExternalOwlClass)
    WHERE o.ap_level = 'AP243'
    RETURN count(o) AS count
""")

print(f'\n{"ExternalOwlClass (AP243)":<35} {owl_count[0]["count"]:>10}')

# Sample ExternalOwlClass nodes
if owl_count[0]["count"] > 0:
    samples = conn.execute_query("""
        MATCH (o:ExternalOwlClass)
        WHERE o.ap_level = 'AP243'
        RETURN o.name AS name, o.domain AS domain, o.definition AS definition
        LIMIT 10
    """)
    
    print('\n' + '='*60)
    print('SAMPLE ExternalOwlClass NODES')
    print('='*60)
    
    for s in samples:
        print(f"\nName: {s['name']}")
        print(f"Domain: {s.get('domain', 'N/A')}")
        definition = s.get('definition', 'N/A')
        if definition and len(definition) > 80:
            definition = definition[:77] + '...'
        print(f"Definition: {definition}")

conn.close()
print('\n' + '='*60 + '\n')
