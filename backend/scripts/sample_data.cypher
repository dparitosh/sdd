// ============================================================
// Sample Test Data - Cypher Queries for Neo4j Browser
// Execute these queries in Neo4j Browser or via REST API
// ============================================================

// 1. CREATE ADDITIONAL REQUIREMENTS
// ----------------------------------
MERGE (r1:Requirement {id: '_REQ_PERF_002'})
ON CREATE SET
    r1.name = 'Response Time',
    r1.type = 'uml:Requirement',
    r1.text = 'System shall respond to user inputs within 100ms',
    r1.priority = 'High',
    r1.status = 'Approved',
    r1.created_on = datetime(),
    r1.last_modified = datetime();

MERGE (r2:Requirement {id: '_REQ_SEC_002'})
ON CREATE SET
    r2.name = 'Data Encryption',
    r2.type = 'uml:Requirement',
    r2.text = 'All sensitive data shall be encrypted using AES-256',
    r2.priority = 'High',
    r2.status = 'Approved',
    r2.created_on = datetime(),
    r2.last_modified = datetime();

MERGE (r3:Requirement {id: '_REQ_FUNC_001'})
ON CREATE SET
    r3.name = 'User Authentication',
    r3.type = 'uml:Requirement',
    r3.text = 'System shall support multi-factor authentication',
    r3.priority = 'Medium',
    r3.status = 'Approved',
    r3.created_on = datetime(),
    r3.last_modified = datetime();

MERGE (r4:Requirement {id: '_REQ_FUNC_002'})
ON CREATE SET
    r4.name = 'Data Export',
    r4.type = 'uml:Requirement',
    r4.text = 'System shall allow export of data in CSV and JSON formats',
    r4.priority = 'Low',
    r4.status = 'Draft',
    r4.created_on = datetime(),
    r4.last_modified = datetime();

// 2. CREATE TRACEABILITY LINKS (Requirements → Classes)
// ------------------------------------------------------
// Get first 10 classes and link requirements to them
MATCH (c:Class)
WITH c LIMIT 10
WITH COLLECT(c) as classes
MATCH (r1:Requirement {id: '_REQ_PERF_002'})
MATCH (r2:Requirement {id: '_REQ_SEC_002'})
MATCH (r3:Requirement {id: '_REQ_FUNC_001'})
MATCH (r4:Requirement {id: '_REQ_FUNC_002'})
FOREACH (i IN RANGE(0, 4) |
    FOREACH (c IN [classes[i]] |
        MERGE (r1)-[rel1:SHOULD_BE_SATISFIED_BY]->(c)
        ON CREATE SET rel1.created_on = datetime()
    )
)
FOREACH (i IN RANGE(1, 5) |
    FOREACH (c IN [classes[i]] |
        MERGE (r2)-[rel2:SHOULD_BE_SATISFIED_BY]->(c)
        ON CREATE SET rel2.created_on = datetime()
    )
)
FOREACH (i IN RANGE(2, 6) |
    FOREACH (c IN [classes[i]] |
        MERGE (r3)-[rel3:SHOULD_BE_SATISFIED_BY]->(c)
        ON CREATE SET rel3.created_on = datetime()
    )
);

// 3. CREATE CONSTRAINTS FOR PROPERTIES
// -------------------------------------
// Get some existing Properties and add constraints
MATCH (p:Property)
WITH p LIMIT 5
WITH COLLECT(p) as props
UNWIND props as prop
MERGE (c:Constraint {id: 'CONSTRAINT_' + prop.id})
ON CREATE SET
    c.name = 'Validate_' + prop.name,
    c.body = 'self.' + prop.name + ' <> null and self.' + prop.name + '.size() > 0',
    c.language = 'OCL',
    c.type = 'invariant'
MERGE (prop)-[r:HAS_RULE]->(c)
ON CREATE SET r.created_on = datetime()
RETURN count(c) as constraints_created;

// 4. ENHANCE PROPERTIES WITH SIMULATION METADATA
// -----------------------------------------------
MATCH (p:Property)
WHERE p.lower IS NULL OR p.upper IS NULL
WITH p LIMIT 100
SET p.lower = COALESCE(p.lower, 1),
    p.upper = COALESCE(p.upper, 1),
    p.defaultValue = COALESCE(p.defaultValue, '0'),
    p.isDerived = COALESCE(p.isDerived, false),
    p.isReadOnly = COALESCE(p.isReadOnly, false)
RETURN count(p) as properties_enhanced;

// 5. CREATE UNIT DATATYPES
// -------------------------
MERGE (dt1:DataType {id: '_DT_METER'})
ON CREATE SET
    dt1.name = 'Meter',
    dt1.type = 'uml:DataType',
    dt1.created_on = datetime();

MERGE (dt2:DataType {id: '_DT_SECOND'})
ON CREATE SET
    dt2.name = 'Second',
    dt2.type = 'uml:DataType',
    dt2.created_on = datetime();

MERGE (dt3:DataType {id: '_DT_KILOGRAM'})
ON CREATE SET
    dt3.name = 'Kilogram',
    dt3.type = 'uml:DataType',
    dt3.created_on = datetime();

MERGE (dt4:DataType {id: '_DT_CELSIUS'})
ON CREATE SET
    dt4.name = 'Celsius',
    dt4.type = 'uml:DataType',
    dt4.created_on = datetime();

MERGE (dt5:DataType {id: '_DT_PASCAL'})
ON CREATE SET
    dt5.name = 'Pascal',
    dt5.type = 'uml:DataType',
    dt5.created_on = datetime();

// ============================================================
// VERIFICATION QUERIES - Run these to check results
// ============================================================

// Check Requirements
MATCH (r:Requirement)
RETURN r.id as id, r.name as name, r.status as status
ORDER BY r.id;

// Check Traceability Links
MATCH (r:Requirement)-[rel:SHOULD_BE_SATISFIED_BY]->(c:Class)
RETURN r.name as requirement, c.name as satisfies_class, type(rel) as relationship
ORDER BY r.name
LIMIT 20;

// Check Constraints
MATCH (p:Property)-[:HAS_RULE]->(c:Constraint)
RETURN p.name as property, c.name as constraint, c.body as rule
LIMIT 10;

// Check DataTypes
MATCH (dt:DataType)
WHERE dt.id STARTS WITH '_DT_'
RETURN dt.id as id, dt.name as name, dt.type as type
ORDER BY dt.name;

// Summary Statistics
MATCH (r:Requirement) WITH count(r) as req_count
MATCH ()-[rel:SHOULD_BE_SATISFIED_BY]->() WITH req_count, count(rel) as trace_count
MATCH (c:Constraint) WITH req_count, trace_count, count(c) as constraint_count
MATCH (dt:DataType) WITH req_count, trace_count, constraint_count, count(dt) as datatype_count
RETURN 
    req_count as requirements,
    trace_count as traceability_links,
    constraint_count as constraints,
    datatype_count as datatypes;
