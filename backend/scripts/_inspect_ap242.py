"""Inspect key AP242 entities for semantic decomposition."""
from neo4j import GraphDatabase
d = GraphDatabase.driver('neo4j://127.0.0.1:7687', auth=('neo4j','tcs12345'))
s = d.session(database='mossec')

# PRODUCT_DEFINITION_FORMATION
print("=== PRODUCT_DEFINITION_FORMATION ===")
r = list(s.run("""
    MATCH (si:StepInstance)-[:INSTANCE_OF]->(t:StepEntityType {name: 'PRODUCT_DEFINITION_FORMATION'})
    RETURN si.raw_args as args, si.step_id as sid, si.file_uri as f LIMIT 5
"""))
for row in r:
    fname = row['f'].split('\\')[-1]
    print(f"  #{row['sid']} [{fname}]: {row['args'][:150]}")

# NEXT_ASSEMBLY_USAGE_OCCURRENCE (assembly hierarchy)
print("\n=== NEXT_ASSEMBLY_USAGE_OCCURRENCE ===")
r = list(s.run("""
    MATCH (si:StepInstance)-[:INSTANCE_OF]->(t:StepEntityType {name: 'NEXT_ASSEMBLY_USAGE_OCCURRENCE'})
    RETURN si.raw_args as args, si.step_id as sid, si.file_uri as f LIMIT 10
"""))
for row in r:
    fname = row['f'].split('\\')[-1]
    print(f"  #{row['sid']} [{fname}]: {row['args'][:150]}")

# APPLICATION_CONTEXT
print("\n=== APPLICATION_CONTEXT ===")
r = list(s.run("""
    MATCH (si:StepInstance)-[:INSTANCE_OF]->(t:StepEntityType {name: 'APPLICATION_CONTEXT'})
    RETURN si.raw_args as args, si.step_id as sid LIMIT 3
"""))
for row in r:
    print(f"  #{row['sid']}: {row['args'][:150]}")

# Count files that have assembly occurrences
print("\n=== Files with NAUO ===")
r = list(s.run("""
    MATCH (f:StepFile)-[:CONTAINS]->(si:StepInstance)-[:INSTANCE_OF]->(t:StepEntityType {name: 'NEXT_ASSEMBLY_USAGE_OCCURRENCE'})
    RETURN f.name as name, count(si) as cnt ORDER BY cnt DESC
"""))
for row in r:
    print(f"  {row['name']}: {row['cnt']} NAUO")

# Show unique product names
print("\n=== Unique PRODUCT names ===")
r = list(s.run("""
    MATCH (si:StepInstance)-[:INSTANCE_OF]->(t:StepEntityType {name: 'PRODUCT'})
    RETURN DISTINCT split(si.raw_args, \"'\")[1] as product_name, count(*) as cnt
    ORDER BY cnt DESC
"""))
for row in r:
    print(f"  {row['product_name']}: {row['cnt']}")

s.close()
d.close()
