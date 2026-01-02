// ============================================================================
// Migration Script: AP239/AP242/AP243 Hierarchical Schema
// ============================================================================
// Purpose: Add indexes, metadata, and sample data for ISO 10303 integration
// Architecture: AP239 (Requirements) → AP242 (Parts/CAD) → AP243 (Reference Data)
// 
// Run with: cypher-shell -u neo4j -p password < scripts/migrate_to_ap_hierarchy.cypher
// ============================================================================

// ============================================================================
// PHASE 1: CREATE INDEXES FOR AP239 NODES (Requirements Layer)
// ============================================================================

CREATE INDEX idx_requirement_name IF NOT EXISTS FOR (n:Requirement) ON (n.name);
CREATE INDEX idx_requirement_id IF NOT EXISTS FOR (n:Requirement) ON (n.id);
CREATE INDEX idx_requirement_version_name IF NOT EXISTS FOR (n:RequirementVersion) ON (n.name);
CREATE INDEX idx_analysis_name IF NOT EXISTS FOR (n:Analysis) ON (n.name);
CREATE INDEX idx_analysis_model_name IF NOT EXISTS FOR (n:AnalysisModel) ON (n.name);
CREATE INDEX idx_approval_name IF NOT EXISTS FOR (n:Approval) ON (n.name);
CREATE INDEX idx_document_name IF NOT EXISTS FOR (n:Document) ON (n.name);
CREATE INDEX idx_activity_name IF NOT EXISTS FOR (n:Activity) ON (n.name);
CREATE INDEX idx_breakdown_name IF NOT EXISTS FOR (n:Breakdown) ON (n.name);
CREATE INDEX idx_event_name IF NOT EXISTS FOR (n:Event) ON (n.name);

// ============================================================================
// PHASE 2: CREATE INDEXES FOR AP242 NODES (Engineering Layer)
// ============================================================================

CREATE INDEX idx_part_name IF NOT EXISTS FOR (n:Part) ON (n.name);
CREATE INDEX idx_part_id IF NOT EXISTS FOR (n:Part) ON (n.id);
CREATE INDEX idx_part_version_name IF NOT EXISTS FOR (n:PartVersion) ON (n.name);
CREATE INDEX idx_assembly_name IF NOT EXISTS FOR (n:Assembly) ON (n.name);
CREATE INDEX idx_geometric_model_name IF NOT EXISTS FOR (n:GeometricModel) ON (n.name);
CREATE INDEX idx_shape_representation_name IF NOT EXISTS FOR (n:ShapeRepresentation) ON (n.name);
CREATE INDEX idx_material_name IF NOT EXISTS FOR (n:Material) ON (n.name);
CREATE INDEX idx_material_property_name IF NOT EXISTS FOR (n:MaterialProperty) ON (n.name);
CREATE INDEX idx_component_placement_name IF NOT EXISTS FOR (n:ComponentPlacement) ON (n.name);

// ============================================================================
// PHASE 3: CREATE INDEXES FOR AP243 NODES (Reference Data Layer)
// ============================================================================

CREATE INDEX idx_external_owl_class_name IF NOT EXISTS FOR (n:ExternalOwlClass) ON (n.name);
CREATE INDEX idx_external_unit_name IF NOT EXISTS FOR (n:ExternalUnit) ON (n.name);
CREATE INDEX idx_external_property_def_name IF NOT EXISTS FOR (n:ExternalPropertyDefinition) ON (n.name);
CREATE INDEX idx_classification_name IF NOT EXISTS FOR (n:Classification) ON (n.name);
CREATE INDEX idx_value_type_name IF NOT EXISTS FOR (n:ValueType) ON (n.name);

// ============================================================================
// PHASE 4: ADD AP_LEVEL METADATA TO EXISTING NODES
// ============================================================================
// Assign hierarchical level metadata to enable top-down navigation
// Level 1: AP239 (Requirements, Analysis, Approvals)
// Level 2: AP242 (Parts, Materials, CAD Geometry)
// Level 3: AP243 (Ontologies, Units, Reference Types)

// Level 1: AP239 Requirements Layer
MATCH (n:Requirement) SET n.ap_level = 1, n.ap_schema = 'AP239';
MATCH (n:RequirementVersion) SET n.ap_level = 1, n.ap_schema = 'AP239';
MATCH (n:Analysis) SET n.ap_level = 1, n.ap_schema = 'AP239';
MATCH (n:AnalysisModel) SET n.ap_level = 1, n.ap_schema = 'AP239';
MATCH (n:Approval) SET n.ap_level = 1, n.ap_schema = 'AP239';
MATCH (n:Document) SET n.ap_level = 1, n.ap_schema = 'AP239';
MATCH (n:Activity) SET n.ap_level = 1, n.ap_schema = 'AP239';
MATCH (n:Breakdown) SET n.ap_level = 1, n.ap_schema = 'AP239';
MATCH (n:Event) SET n.ap_level = 1, n.ap_schema = 'AP239';

// Level 2: AP242 Engineering Layer
MATCH (n:Part) SET n.ap_level = 2, n.ap_schema = 'AP242';
MATCH (n:PartVersion) SET n.ap_level = 2, n.ap_schema = 'AP242';
MATCH (n:Assembly) SET n.ap_level = 2, n.ap_schema = 'AP242';
MATCH (n:GeometricModel) SET n.ap_level = 2, n.ap_schema = 'AP242';
MATCH (n:ShapeRepresentation) SET n.ap_level = 2, n.ap_schema = 'AP242';
MATCH (n:Material) SET n.ap_level = 2, n.ap_schema = 'AP242';
MATCH (n:MaterialProperty) SET n.ap_level = 2, n.ap_schema = 'AP242';
MATCH (n:ComponentPlacement) SET n.ap_level = 2, n.ap_schema = 'AP242';

// Level 3: AP243 Reference Data Layer
MATCH (n:ExternalOwlClass) SET n.ap_level = 3, n.ap_schema = 'AP243';
MATCH (n:ExternalUnit) SET n.ap_level = 3, n.ap_schema = 'AP243';
MATCH (n:ExternalPropertyDefinition) SET n.ap_level = 3, n.ap_schema = 'AP243';
MATCH (n:Classification) SET n.ap_level = 3, n.ap_schema = 'AP243';
MATCH (n:ValueType) SET n.ap_level = 3, n.ap_schema = 'AP243';

// ============================================================================
// PHASE 5: CREATE SAMPLE AP239 DATA (Requirements Layer)
// ============================================================================

// Sample Requirement with version
CREATE (req1:Requirement {
    id: 'REQ-001',
    name: 'Maximum Operating Temperature',
    description: 'System shall operate continuously at temperatures up to 85°C',
    type: 'Performance',
    priority: 'High',
    status: 'Approved',
    ap_level: 1,
    ap_schema: 'AP239',
    created_at: datetime()
});

CREATE (reqv1:RequirementVersion {
    name: 'Maximum Operating Temperature v1.2',
    version: '1.2',
    description: 'Updated thermal requirement with extended range',
    status: 'Current',
    ap_level: 1,
    ap_schema: 'AP239',
    created_at: datetime()
});

// Sample Analysis
CREATE (ana1:Analysis {
    name: 'Thermal Analysis - Steady State',
    type: 'ThermalSimulation',
    method: 'Finite Element Method',
    status: 'Completed',
    ap_level: 1,
    ap_schema: 'AP239',
    created_at: datetime()
});

CREATE (model1:AnalysisModel {
    name: 'Thermal FEM Model - Rev A',
    mesh_size: 5000,
    solver: 'ANSYS Mechanical',
    ap_level: 1,
    ap_schema: 'AP239'
});

// Sample Approval
CREATE (appr1:Approval {
    name: 'Design Review Board Approval',
    status: 'Approved',
    approved_by: 'Engineering Director',
    approval_date: date('2024-01-15'),
    ap_level: 1,
    ap_schema: 'AP239'
});

// Sample Document
CREATE (doc1:Document {
    name: 'System Requirements Specification',
    document_id: 'SRS-2024-001',
    version: '2.0',
    type: 'Specification',
    ap_level: 1,
    ap_schema: 'AP239'
});

// ============================================================================
// PHASE 6: CREATE SAMPLE AP242 DATA (Engineering Layer)
// ============================================================================

// Sample Part
CREATE (part1:Part {
    id: 'PRT-1001',
    name: 'Heat Sink Assembly',
    description: 'Aluminum heat sink with thermal interface',
    part_number: 'HS-AL-500',
    status: 'Released',
    ap_level: 2,
    ap_schema: 'AP242',
    created_at: datetime()
});

CREATE (partv1:PartVersion {
    name: 'Heat Sink Assembly Rev B',
    version: 'B',
    status: 'Current',
    ap_level: 2,
    ap_schema: 'AP242'
});

// Sample Assembly
CREATE (asm1:Assembly {
    name: 'Cooling System Assembly',
    assembly_type: 'Mechanical',
    component_count: 5,
    ap_level: 2,
    ap_schema: 'AP242'
});

// Sample Geometric Model
CREATE (geo1:GeometricModel {
    name: 'Heat Sink CAD Model',
    model_type: 'Solid',
    units: 'millimeters',
    ap_level: 2,
    ap_schema: 'AP242'
});

CREATE (shape1:ShapeRepresentation {
    name: 'Heat Sink External Shape',
    representation_type: 'BRep',
    ap_level: 2,
    ap_schema: 'AP242'
});

// Sample Material
CREATE (mat1:Material {
    name: 'Aluminum 6061-T6',
    material_type: 'Metal',
    specification: 'ASTM B221',
    ap_level: 2,
    ap_schema: 'AP242'
});

CREATE (prop1:MaterialProperty {
    name: 'Thermal Conductivity',
    value: 167.0,
    unit: 'W/(m·K)',
    temperature: 20.0,
    ap_level: 2,
    ap_schema: 'AP242'
});

// ============================================================================
// PHASE 7: CREATE SAMPLE AP243 DATA (Reference Data Layer)
// ============================================================================

// Sample External Ontology Class
CREATE (owl1:ExternalOwlClass {
    name: 'ThermalMaterial',
    ontology: 'EMMO (Elementary Multiperspective Material Ontology)',
    uri: 'http://emmo.info/emmo#EMMO_ThermalMaterial',
    description: 'Material with defined thermal properties',
    ap_level: 3,
    ap_schema: 'AP243'
});

// Sample External Unit
CREATE (unit1:ExternalUnit {
    name: 'Watt per meter Kelvin',
    symbol: 'W/(m·K)',
    unit_type: 'ThermalConductivity',
    si_conversion: 1.0,
    ap_level: 3,
    ap_schema: 'AP243'
});

CREATE (unit2:ExternalUnit {
    name: 'Degree Celsius',
    symbol: '°C',
    unit_type: 'Temperature',
    si_conversion: 1.0,
    ap_level: 3,
    ap_schema: 'AP243'
});

// Sample Classification
CREATE (class1:Classification {
    name: 'Thermal Management Components',
    classification_system: 'ISO 13584-501',
    code: 'TMC-100',
    ap_level: 3,
    ap_schema: 'AP243'
});

// Sample Value Type
CREATE (vt1:ValueType {
    name: 'TemperatureValue',
    data_type: 'double',
    unit_reference: 'degC',
    ap_level: 3,
    ap_schema: 'AP243'
});

// ============================================================================
// PHASE 8: CREATE AP239 INTERNAL RELATIONSHIPS
// ============================================================================

MATCH (req:Requirement {id: 'REQ-001'})
MATCH (reqv:RequirementVersion {version: '1.2'})
CREATE (req)-[:HAS_VERSION]->(reqv);

MATCH (req:Requirement {id: 'REQ-001'})
MATCH (ana:Analysis {name: 'Thermal Analysis - Steady State'})
CREATE (req)-[:VERIFIES]->(ana);

MATCH (ana:Analysis {name: 'Thermal Analysis - Steady State'})
MATCH (model:AnalysisModel {name: 'Thermal FEM Model - Rev A'})
CREATE (ana)-[:USES_MODEL]->(model);

MATCH (req:Requirement {id: 'REQ-001'})
MATCH (appr:Approval {name: 'Design Review Board Approval'})
CREATE (req)-[:APPROVES]->(appr);

MATCH (req:Requirement {id: 'REQ-001'})
MATCH (doc:Document {name: 'System Requirements Specification'})
CREATE (doc)-[:DOCUMENTS]->(req);

// ============================================================================
// PHASE 9: CREATE AP242 INTERNAL RELATIONSHIPS
// ============================================================================

MATCH (part:Part {id: 'PRT-1001'})
MATCH (partv:PartVersion {version: 'B'})
CREATE (part)-[:HAS_VERSION]->(partv);

MATCH (part:Part {id: 'PRT-1001'})
MATCH (asm:Assembly {name: 'Cooling System Assembly'})
CREATE (asm)-[:ASSEMBLES_WITH]->(part);

MATCH (part:Part {id: 'PRT-1001'})
MATCH (geo:GeometricModel {name: 'Heat Sink CAD Model'})
CREATE (part)-[:HAS_GEOMETRY]->(geo);

MATCH (geo:GeometricModel {name: 'Heat Sink CAD Model'})
MATCH (shape:ShapeRepresentation {name: 'Heat Sink External Shape'})
CREATE (geo)-[:HAS_REPRESENTATION]->(shape);

MATCH (part:Part {id: 'PRT-1001'})
MATCH (mat:Material {name: 'Aluminum 6061-T6'})
CREATE (part)-[:USES_MATERIAL]->(mat);

MATCH (mat:Material {name: 'Aluminum 6061-T6'})
MATCH (prop:MaterialProperty {name: 'Thermal Conductivity'})
CREATE (mat)-[:HAS_PROPERTY]->(prop);

// ============================================================================
// PHASE 10: CREATE AP243 INTERNAL RELATIONSHIPS
// ============================================================================

MATCH (mat:Material {name: 'Aluminum 6061-T6'})
MATCH (owl:ExternalOwlClass {name: 'ThermalMaterial'})
CREATE (mat)-[:CLASSIFIED_AS]->(owl);

MATCH (prop:MaterialProperty {name: 'Thermal Conductivity'})
MATCH (unit:ExternalUnit {symbol: 'W/(m·K)'})
CREATE (prop)-[:HAS_UNIT]->(unit);

MATCH (part:Part {id: 'PRT-1001'})
MATCH (class:Classification {name: 'Thermal Management Components'})
CREATE (part)-[:CLASSIFIED_AS]->(class);

MATCH (prop:MaterialProperty {name: 'Thermal Conductivity'})
MATCH (vt:ValueType {name: 'TemperatureValue'})
CREATE (prop)-[:HAS_VALUE_TYPE]->(vt);

// ============================================================================
// PHASE 11: CREATE CROSS-LEVEL RELATIONSHIPS (AP239 → AP242 → AP243)
// ============================================================================

// Requirement → Part (Level 1 → Level 2)
MATCH (req:Requirement {id: 'REQ-001'})
MATCH (part:Part {id: 'PRT-1001'})
CREATE (req)-[:SATISFIED_BY_PART]->(part);

// Analysis → Material (Level 1 → Level 2)
MATCH (ana:Analysis {name: 'Thermal Analysis - Steady State'})
MATCH (mat:Material {name: 'Aluminum 6061-T6'})
CREATE (ana)-[:ANALYZED_BY_MODEL {notes: 'Thermal conductivity validated'}]->(mat);

// Approval → PartVersion (Level 1 → Level 2)
MATCH (appr:Approval {name: 'Design Review Board Approval'})
MATCH (partv:PartVersion {version: 'B'})
CREATE (appr)-[:APPROVED_FOR_VERSION]->(partv);

// Material → Ontology (Level 2 → Level 3)
MATCH (mat:Material {name: 'Aluminum 6061-T6'})
MATCH (owl:ExternalOwlClass {name: 'ThermalMaterial'})
CREATE (mat)-[:MATERIAL_CLASSIFIED_AS]->(owl);

// MaterialProperty → Unit (Level 2 → Level 3)
MATCH (prop:MaterialProperty {name: 'Thermal Conductivity'})
MATCH (unit:ExternalUnit {symbol: 'W/(m·K)'})
CREATE (prop)-[:USES_UNIT]->(unit);

// Requirement → Unit (Level 1 → Level 3 - direct skip)
MATCH (req:Requirement {id: 'REQ-001'})
MATCH (unit:ExternalUnit {symbol: '°C'})
CREATE (req)-[:REQUIREMENT_VALUE_TYPE {context: 'Temperature specification'}]->(unit);

// ============================================================================
// PHASE 12: VALIDATION QUERIES
// ============================================================================

// Count nodes by AP level
// MATCH (n) WHERE n.ap_level IS NOT NULL
// RETURN n.ap_schema AS schema, n.ap_level AS level, count(n) AS node_count
// ORDER BY level;

// Verify cross-level relationships exist
// MATCH (n1)-[r]->(n2)
// WHERE n1.ap_level IS NOT NULL AND n2.ap_level IS NOT NULL 
//   AND n1.ap_level <> n2.ap_level
// RETURN n1.ap_schema AS from_schema, type(r) AS relationship, 
//        n2.ap_schema AS to_schema, count(*) AS count
// ORDER BY from_schema, to_schema;

// Find complete traceability chains (AP239 → AP242 → AP243)
// MATCH path = (req:Requirement)-[*1..3]->(part:Part)-[*1..3]->(owl:ExternalOwlClass)
// WHERE req.ap_level = 1 AND part.ap_level = 2 AND owl.ap_level = 3
// RETURN req.name, part.name, owl.name, length(path) AS chain_length
// LIMIT 5;

// ============================================================================
// END OF MIGRATION SCRIPT
// ============================================================================
