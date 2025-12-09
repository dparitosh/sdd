# MBSE Knowledge Graph - Cypher Queries

## Overview
This document contains essential Cypher queries for accessing entities and their key values in the MBSE Knowledge Graph.

---

## 📊 Basic Statistics

### Get Total Nodes and Relationships
```cypher
MATCH (n)
RETURN count(n) AS total_nodes;

MATCH ()-[r]->()
RETURN count(r) AS total_relationships;
```

### Get Node Counts by Type
```cypher
MATCH (n)
RETURN labels(n)[0] AS entity_type, count(n) AS count
ORDER BY count DESC;
```

### Get Relationship Counts by Type
```cypher
MATCH ()-[r]->()
RETURN type(r) AS relationship_type, count(r) AS count
ORDER BY count DESC;
```

---

## 🔍 Entity Queries with Key Values

### 1. All Classes with Properties and Types
```cypher
MATCH (c:Class)
OPTIONAL MATCH (c)-[:HAS_ATTRIBUTE]->(p:Property)
OPTIONAL MATCH (p)-[:TYPED_BY]->(t:Class)
RETURN c.id AS class_id,
       c.name AS class_name,
       c.comment AS description,
       collect({
         property_id: p.id,
         property_name: p.name,
         property_type: t.name
       }) AS properties
ORDER BY c.name;
```

### 2. All Packages with Their Contents
```cypher
MATCH (pkg:Package)
OPTIONAL MATCH (pkg)-[:CONTAINS]->(child)
RETURN pkg.id AS package_id,
       pkg.name AS package_name,
       pkg.comment AS description,
       collect({
         element_type: labels(child)[0],
         element_id: child.id,
         element_name: child.name
       }) AS contents
ORDER BY pkg.name;
```

### 3. Specific Entity by ID
```cypher
MATCH (n {id: 'YOUR_ELEMENT_ID'})
RETURN labels(n)[0] AS entity_type,
       properties(n) AS all_properties;
```

### 4. Specific Entity by Name
```cypher
MATCH (n)
WHERE n.name = 'YOUR_ELEMENT_NAME'
RETURN labels(n)[0] AS entity_type,
       properties(n) AS all_properties;
```

### 5. All Properties of an Entity Type
```cypher
MATCH (n:Class)  // Replace Class with any entity type
WITH n LIMIT 1
RETURN keys(n) AS available_properties;
```

---

## 🌳 Hierarchical Queries

### 6. Package Hierarchy (Full Tree)
```cypher
MATCH path = (root:Package)-[:CONTAINS*]->(child)
WHERE root.name = 'Domain_model'
RETURN root.name AS root_package,
       [node IN nodes(path) | {type: labels(node)[0], name: node.name}] AS hierarchy_path
LIMIT 20;
```

### 7. Class with All Properties (Deep)
```cypher
MATCH (c:Class {name: 'YOUR_CLASS_NAME'})
OPTIONAL MATCH (c)-[:HAS_ATTRIBUTE]->(p:Property)
OPTIONAL MATCH (p)-[:TYPED_BY]->(t)
RETURN c.id AS class_id,
       c.name AS class_name,
       c.comment AS description,
       collect({
         property_id: p.id,
         property_name: p.name,
         property_type: t.name,
         property_type_id: t.id
       }) AS properties;
```

### 8. Full Path: Package → Class → Property → Type
```cypher
MATCH path = (pkg:Package)-[:CONTAINS]->(c:Class)-[:HAS_ATTRIBUTE]->(p:Property)-[:TYPED_BY]->(t:Class)
RETURN pkg.name AS package,
       c.name AS class,
       p.name AS property,
       t.name AS type,
       [rel IN relationships(path) | type(rel)] AS relationship_chain;
```

---

## 🧬 Relationship Queries

### 9. Inheritance Hierarchy (Generalization)
```cypher
MATCH (child:Class)-[:GENERALIZES]->(parent:Class)
RETURN child.id AS child_id,
       child.name AS child_class,
       parent.id AS parent_id,
       parent.name AS parent_class
ORDER BY parent.name, child.name;
```

### 10. Association Networks
```cypher
MATCH (a:Association)-[:ASSOCIATES_WITH]->(p:Property)
OPTIONAL MATCH (p)-[:TYPED_BY]->(t:Class)
RETURN a.id AS association_id,
       a.name AS association_name,
       collect({
         property_id: p.id,
         property_name: p.name,
         connected_class: t.name
       }) AS associated_elements;
```

### 11. Find All Relationships for a Specific Entity
```cypher
MATCH (n {name: 'YOUR_ENTITY_NAME'})
OPTIONAL MATCH (n)-[r]->(target)
RETURN n.name AS source,
       type(r) AS relationship,
       labels(target)[0] AS target_type,
       target.name AS target_name;
```

---

## 🔗 Cross-Cutting Queries

### 12. Connected Components (Find All Paths)
```cypher
MATCH path = (start)-[*1..3]->(end)
WHERE start.name = 'YOUR_START_ENTITY'
RETURN [node IN nodes(path) | {type: labels(node)[0], name: node.name}] AS path_nodes,
       [rel IN relationships(path) | type(rel)] AS path_relationships
LIMIT 50;
```

### 13. Find All Classes Using a Specific Type
```cypher
MATCH (c:Class)-[:HAS_ATTRIBUTE]->(p:Property)-[:TYPED_BY]->(type:Class {name: 'YOUR_TYPE_NAME'})
RETURN c.name AS class_using_type,
       collect(p.name) AS properties_of_that_type;
```

### 14. Instance Specifications with Slots
```cypher
MATCH (inst:InstanceSpecification)
OPTIONAL MATCH (inst)-[:HAS_SLOT]->(slot:Slot)
OPTIONAL MATCH (slot)-[:TYPED_BY]->(classifier)
RETURN inst.id AS instance_id,
       inst.name AS instance_name,
       collect({
         slot_id: slot.id,
         slot_name: slot.name,
         classifier: classifier.name
       }) AS slots;
```

---

## 🎯 Advanced Analytics Queries

### 15. Most Connected Entities
```cypher
MATCH (n)
OPTIONAL MATCH (n)-[r]->()
WITH n, count(r) AS outgoing
OPTIONAL MATCH (n)<-[r2]-()
WITH n, outgoing, count(r2) AS incoming
RETURN labels(n)[0] AS entity_type,
       n.name AS entity_name,
       outgoing + incoming AS total_connections
ORDER BY total_connections DESC
LIMIT 20;
```

### 16. Classes with No Properties
```cypher
MATCH (c:Class)
WHERE NOT (c)-[:HAS_ATTRIBUTE]->()
RETURN c.id AS class_id,
       c.name AS class_name,
       c.comment AS description;
```

### 17. Orphan Nodes (No Relationships)
```cypher
MATCH (n)
WHERE NOT (n)--()
RETURN labels(n)[0] AS entity_type,
       n.name AS entity_name,
       n.id AS entity_id
LIMIT 20;
```

### 18. Dependency Graph
```cypher
MATCH (source)-[:DEPENDS_ON]->(target)
RETURN labels(source)[0] AS source_type,
       source.name AS source_name,
       labels(target)[0] AS target_type,
       target.name AS target_name;
```

---

## 📋 Export Queries

### 19. Export All Entities as JSON
```cypher
MATCH (n)
RETURN labels(n)[0] AS entity_type,
       properties(n) AS properties
LIMIT 1000;
```

### 20. Export Full Graph Structure
```cypher
MATCH (n)-[r]->(m)
RETURN labels(n)[0] AS source_type,
       n.name AS source_name,
       type(r) AS relationship,
       labels(m)[0] AS target_type,
       m.name AS target_name
LIMIT 10000;
```

---

## 🔧 Utility Queries

### Get Schema (All Node Labels and Properties)
```cypher
CALL db.schema.visualization();
```

### Get Relationship Types
```cypher
CALL db.relationshipTypes();
```

### Get Node Labels
```cypher
CALL db.labels();
```

### Get Property Keys
```cypher
CALL db.propertyKeys();
```

---

## 💡 Tips

1. **Replace placeholders**: Replace `YOUR_ELEMENT_ID`, `YOUR_ELEMENT_NAME`, etc. with actual values
2. **Limit results**: Add `LIMIT n` to prevent overwhelming results
3. **Case sensitivity**: Node labels are case-sensitive, property names are not
4. **Performance**: Create indexes on frequently queried properties:
   ```cypher
   CREATE INDEX FOR (n:Class) ON (n.name);
   CREATE INDEX FOR (n:Class) ON (n.id);
   ```
5. **Visualization**: Use Neo4j Browser or Neo4j Bloom for visual exploration

---

## 📊 Graph Statistics

Current graph contains:
- **Nodes**: 1,893 (Class: 143, Property: 1,217, Port: 188, Package: 34, etc.)
- **Relationships**: 2,393 (CONTAINS, HAS_ATTRIBUTE, GENERALIZES, TYPED_BY, ASSOCIATES_WITH)
- **Fully connected** hierarchical structure representing UML/SysML MBSE model
