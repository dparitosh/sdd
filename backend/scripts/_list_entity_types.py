"""List STEP entity types and count to understand AP242 data."""
from neo4j import GraphDatabase
d = GraphDatabase.driver('neo4j://127.0.0.1:7687', auth=('neo4j','tcs12345'))
s = d.session(database='mossec')

r = list(s.run("""
    MATCH (t:StepEntityType)<-[:INSTANCE_OF]-(si:StepInstance)
    RETURN t.name as name, count(si) as cnt 
    ORDER BY cnt DESC LIMIT 40
"""))

print("STEP Entity Types (top 40):")
print("-" * 65)
for row in r:
    print(f"  {row['name']:50s} {row['cnt']:>8}")

# Check for semantically important AP242 entities
important = [
    'PRODUCT', 'PRODUCT_DEFINITION', 'PRODUCT_DEFINITION_FORMATION',
    'SHAPE_REPRESENTATION', 'NEXT_ASSEMBLY_USAGE_OCCURRENCE',
    'PRODUCT_DEFINITION_SHAPE', 'SHAPE_DEFINITION_REPRESENTATION',
    'ADVANCED_BREP_SHAPE_REPRESENTATION', 'MANIFOLD_SOLID_BREP',
    'GEOMETRIC_REPRESENTATION_CONTEXT', 'APPLICATION_CONTEXT',
    'PRODUCT_CONTEXT', 'PRODUCT_DEFINITION_CONTEXT',
    'MECHANICAL_DESIGN_GEOMETRIC_PRESENTATION_REPRESENTATION',
    'PROPERTY_DEFINITION', 'PROPERTY_DEFINITION_REPRESENTATION',
    'REPRESENTATION_MAP', 'MAPPED_ITEM',
]
print("\nKey AP242 semantic entities:")
print("-" * 65)
for et in important:
    r = list(s.run(
        "MATCH (si:StepInstance)-[:INSTANCE_OF]->(t:StepEntityType {name: $name}) "
        "RETURN count(si) as cnt", {"name": et}
    ))
    cnt = r[0]['cnt'] if r else 0
    if cnt > 0:
        print(f"  {et:50s} {cnt:>8}")

# Show sample PRODUCT_DEFINITION raw_args
print("\nSample PRODUCT_DEFINITION instances:")
r = list(s.run("""
    MATCH (si:StepInstance)-[:INSTANCE_OF]->(t:StepEntityType {name: 'PRODUCT_DEFINITION'})
    RETURN si.raw_args as args, si.step_id as sid, si.file_uri as f 
    LIMIT 5
"""))
for row in r:
    fname = row['f'].split('\\')[-1] if row['f'] else '?'
    print(f"  #{row['sid']} [{fname}]: {row['args'][:120]}")

# Show sample PRODUCT raw_args
print("\nSample PRODUCT instances:")
r = list(s.run("""
    MATCH (si:StepInstance)-[:INSTANCE_OF]->(t:StepEntityType {name: 'PRODUCT'})
    RETURN si.raw_args as args, si.step_id as sid, si.file_uri as f 
    LIMIT 5
"""))
for row in r:
    fname = row['f'].split('\\')[-1] if row['f'] else '?'
    print(f"  #{row['sid']} [{fname}]: {row['args'][:120]}")

s.close()
d.close()
