"""Check SimulationRun constraints"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.src.graph.connection import Neo4jConnection
from backend.src.utils.config import Config

config = Config()
conn = Neo4jConnection(config.neo4j_uri, config.neo4j_user, config.neo4j_password)
conn.connect()

# Show all constraints
constraints = conn.execute_query("SHOW CONSTRAINTS")

print('\nAll SimulationRun constraints:')
print('-' * 70)

for c in constraints:
    labels = c.get('labelsOrTypes', [])
    if 'SimulationRun' in str(labels):
        name = c.get('name', 'N/A')
        constraint_type = c.get('type', 'N/A')
        properties = c.get('properties', [])
        print(f'\nConstraint: {name}')
        print(f'  Type: {constraint_type}')
        print(f'  Labels: {labels}')
        print(f'  Properties: {properties}')

conn.close()
