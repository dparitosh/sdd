"""Check orphan StepInstance nodes without ap_level."""
from neo4j import GraphDatabase
d = GraphDatabase.driver('neo4j://127.0.0.1:7687', auth=('neo4j', 'tcs12345'))
s = d.session(database='mossec')

r = list(s.run("""
    MATCH (si:StepInstance) WHERE si.ap_level IS NULL 
    AND NOT EXISTS { MATCH (f:StepFile)-[:CONTAINS]->(si) }
    RETURN count(si) as c
"""))
print(f"Orphan SI (no StepFile parent): {r[0]['c']}")

r2 = list(s.run("""
    MATCH (si:StepInstance) WHERE si.ap_level IS NULL 
    RETURN si.step_type as t, count(*) as c ORDER BY c DESC LIMIT 10
"""))
print("Types without ap_level:")
for x in r2:
    print(f"  {x['t']}: {x['c']}")

# Set orphans to AP242 directly since all files are AP242
r3 = list(s.run("""
    MATCH (si:StepInstance) WHERE si.ap_level IS NULL
    SET si.ap_level = 'AP242'
    RETURN count(si) as c
"""))
print(f"\nForce-set remaining {r3[0]['c']} orphans to AP242")

# Final count
r4 = list(s.run("MATCH (si:StepInstance) WHERE si.ap_level IS NULL RETURN count(si) as c"))
print(f"Remaining without ap_level: {r4[0]['c']}")

s.close()
d.close()
