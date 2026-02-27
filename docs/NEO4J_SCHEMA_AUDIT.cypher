// Neo4j Knowledge Graph “Schema” Audit Pack
// =======================================
// Purpose:
// - Inspect labels + relationship types + common properties
// - Validate AP239/AP242/AP243 layering via ap_level/ap_schema
// - Find cross-level links and missing metadata
//
// Notes:
// - Works on Neo4j 5+ (Aura included)
// - APOC queries are included (safe to skip if not installed)

// ----------------------------
// 0) Basic inventory
// ----------------------------
MATCH (n) RETURN count(n) AS total_nodes;
MATCH ()-[r]->() RETURN count(r) AS total_relationships;

// All labels with counts (top 50)
MATCH (n)
UNWIND labels(n) AS label
RETURN label, count(*) AS count
ORDER BY count DESC
LIMIT 50;

// Relationship types with counts (top 50)
MATCH ()-[r]->()
RETURN type(r) AS rel_type, count(*) AS count
ORDER BY count DESC
LIMIT 50;

// ----------------------------
// 1) “Schema” (Neo4j system schema introspection)
// ----------------------------
// Node label -> property keys, types, and mandatory/optional (Neo4j 5+)
CALL db.schema.nodeTypeProperties();

// Relationship type -> property keys, types, mandatory/optional (Neo4j 5+)
CALL db.schema.relTypeProperties();

// Visual overview (labels + relationship types)
CALL db.schema.visualization();

// ----------------------------
// 2) AP layering health checks (ap_level/ap_schema)
// ----------------------------
// How many nodes per AP level?
MATCH (n)
WHERE n.ap_level IS NOT NULL
RETURN n.ap_level AS ap_level, count(*) AS count
ORDER BY ap_level;

// How many nodes per ap_schema string?
MATCH (n)
WHERE n.ap_schema IS NOT NULL
RETURN n.ap_schema AS ap_schema, count(*) AS count
ORDER BY count DESC;

// Nodes missing ap_level
MATCH (n)
WHERE n.ap_level IS NULL
RETURN labels(n) AS labels, count(*) AS count
ORDER BY count DESC
LIMIT 50;

// Nodes with ap_level but missing ap_schema
MATCH (n)
WHERE n.ap_level IS NOT NULL AND n.ap_schema IS NULL
RETURN n.ap_level AS ap_level, labels(n) AS labels, count(*) AS count
ORDER BY ap_level, count DESC
LIMIT 50;

// Nodes with ap_schema but missing ap_level
MATCH (n)
WHERE n.ap_schema IS NOT NULL AND n.ap_level IS NULL
RETURN n.ap_schema AS ap_schema, labels(n) AS labels, count(*) AS count
ORDER BY count DESC
LIMIT 50;

// Validate AP levels are only 1/2/3 (flag anything else)
MATCH (n)
WHERE n.ap_level IS NOT NULL AND NOT n.ap_level IN ['AP239','AP242','AP243']
RETURN n.ap_level AS invalid_level, labels(n) AS labels, count(*) AS count
ORDER BY count DESC;

// ----------------------------
// 3) Cross-level connectivity (traceability bridges)
// ----------------------------
// Count relationships that connect different AP levels
MATCH (a)-[r]->(b)
WHERE a.ap_level IS NOT NULL AND b.ap_level IS NOT NULL
  AND a.ap_level <> b.ap_level
RETURN a.ap_level AS from_level,
       b.ap_level AS to_level,
       type(r) AS rel_type,
       count(*) AS count
ORDER BY count DESC
LIMIT 100;

// Which labels participate in cross-level links?
MATCH (a)-[r]->(b)
WHERE a.ap_level IS NOT NULL AND b.ap_level IS NOT NULL
  AND a.ap_level <> b.ap_level
RETURN labels(a)[0] AS from_label,
       labels(b)[0] AS to_label,
       type(r) AS rel_type,
       count(*) AS count
ORDER BY count DESC
LIMIT 100;

// End-to-end sample: AP239 Requirement -> AP242 Part -> AP243 ExternalOwlClass (up to 3 hops each)
MATCH (req:Requirement)
WHERE req.ap_level = 'AP239'
OPTIONAL MATCH (req)-[*1..3]->(part:Part)
WHERE part.ap_level = 'AP242'
OPTIONAL MATCH (part)-[*1..3]->(owl:ExternalOwlClass)
WHERE owl.ap_level = 'AP243'
RETURN req.id AS requirement_id,
       req.name AS requirement_name,
       collect(DISTINCT part.id)[0..10] AS parts_sample,
       collect(DISTINCT owl.name)[0..10] AS ontologies_sample
LIMIT 50;

// ----------------------------
// 4) Key domain label sanity checks (AP endpoints depend on these)
// ----------------------------
// AP239 expected: Requirement nodes at level 1
MATCH (n:Requirement) RETURN n.ap_level AS ap_level, count(*) AS count ORDER BY ap_level;

// AP242 expected: Part nodes at level 2
MATCH (n:Part) RETURN n.ap_level AS ap_level, count(*) AS count ORDER BY ap_level;

// AP243 expected: ExternalOwlClass/ExternalUnit nodes at level 3
MATCH (n:ExternalOwlClass) RETURN n.ap_level AS ap_level, count(*) AS count ORDER BY ap_level;
MATCH (n:ExternalUnit) RETURN n.ap_level AS ap_level, count(*) AS count ORDER BY ap_level;

// ----------------------------
// 5) Optional: APOC meta schema (skip if APOC not installed)
// ----------------------------
// Shows a compact schema map of labels, rels, and properties
CALL apoc.meta.schema();

// ============================================================================
// Ontology / Reference-Data ingestion checks (AP243)
// ============================================================================

// Counts of key reference-data labels
MATCH (n)
WHERE any(l IN labels(n) WHERE l IN ['ExternalOntology','ExternalOwlClass','ExternalUnit','ValueType','Classification'])
RETURN labels(n)[0] AS label, count(*) AS count
ORDER BY count DESC;

// Ensure AP243 API filters are satisfied (ap_level='AP243' and ap_schema='AP243')
MATCH (n)
WHERE n.ap_level = 'AP243' AND n.ap_schema = 'AP243'
RETURN labels(n)[0] AS label, count(*) AS count
ORDER BY count DESC;

// Sample ontology node(s)
MATCH (o:ExternalOntology)
RETURN o.name AS name, o.uri AS uri, o.source_file AS source_file, o.loaded_on AS loaded_on
ORDER BY o.loaded_on DESC
LIMIT 10;
