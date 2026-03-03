"""Check existing domain nodes for OSLC linking."""
from neo4j import GraphDatabase
d = GraphDatabase.driver('neo4j://127.0.0.1:7687', auth=('neo4j','tcs12345'))
s = d.session(database='mossec')

for label in ['Part', 'Requirement', 'Assembly', 'MBSEElement']:
    r = list(s.run(f'MATCH (n:{label}) RETURN n.name as name, n.id as id LIMIT 5'))
    print(f'\n{label} ({len(r)} shown):')
    for x in r:
        print(f'  id={x["id"]}, name={x["name"]}')

print('\nAP242Product:')
r = list(s.run('MATCH (p:AP242Product) RETURN p.name as name, p.product_id as pid LIMIT 10'))
for x in r:
    print(f'  pid={x["pid"]}, name={x["name"]}')

# Check OSLC-related relationships
print('\nExisting OSLC relationships:')
r = list(s.run("MATCH ()-[r]->() WHERE type(r) CONTAINS 'OSLC' OR type(r) CONTAINS 'oslc' RETURN type(r) as t, count(*) as c"))
for x in r:
    print(f'  {x["t"]}: {x["c"]}')

# Requirement-Part links
print('\nRequirement-Part links:')
r = list(s.run("MATCH (req:Requirement)-[r:SATISFIED_BY_PART]->(p:Part) RETURN req.name as rn, p.name as pn LIMIT 10"))
for x in r:
    print(f'  {x["rn"]} -> {x["pn"]}')

s.close()
d.close()
