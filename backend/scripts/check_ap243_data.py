"""Check for unit-related labels and AP243 data in Neo4j"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.src.graph.connection import Neo4jConnection
from backend.src.utils.config import Config

config = Config()
conn = Neo4jConnection(config.neo4j_uri, config.neo4j_user, config.neo4j_password)
conn.connect()

# Get all labels
result = conn.execute_query('CALL db.labels() YIELD label RETURN label ORDER BY label')
labels = [r['label'] for r in result]

# Search for unit-related labels
unit_labels = [l for l in labels if 'unit' in l.lower()]
print('Unit-related labels:', unit_labels if unit_labels else 'None found')

# Count AP243 nodes
ap243_query = "MATCH (n) WHERE n.ap_level = 'AP243' RETURN count(n) AS count"
ap243_count = conn.execute_query(ap243_query)
print(f'Nodes with ap_level=AP243: {ap243_count[0]["count"]}')

# Count SDD nodes
sdd_query = "MATCH (n:SimulationDossier) RETURN count(n) AS count"
sdd_count = conn.execute_query(sdd_query)
print(f'SimulationDossier nodes: {sdd_count[0]["count"]}')

# Sample AP243 node
if ap243_count[0]["count"] > 0:
    sample = conn.execute_query("MATCH (n) WHERE n.ap_level = 'AP243' RETURN labels(n) AS labels, properties(n) AS props LIMIT 3")
    print('\nSample AP243 nodes:')
    for s in sample:
        print(f'  Labels: {s["labels"]}')
        props = s["props"]
        print(f'  Properties: name={props.get("name", "N/A")}, type={props.get("type", "N/A")}')

conn.close()
