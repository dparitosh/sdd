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
MATCH (n:Requirement) SET n.ap_level = 'AP239', n.ap_schema = 'AP239';
MATCH (n:RequirementVersion) SET n.ap_level = 'AP239', n.ap_schema = 'AP239';
MATCH (n:Analysis) SET n.ap_level = 'AP239', n.ap_schema = 'AP239';
MATCH (n:AnalysisModel) SET n.ap_level = 'AP239', n.ap_schema = 'AP239';
MATCH (n:Approval) SET n.ap_level = 'AP239', n.ap_schema = 'AP239';
MATCH (n:Document) SET n.ap_level = 'AP239', n.ap_schema = 'AP239';
MATCH (n:Activity) SET n.ap_level = 'AP239', n.ap_schema = 'AP239';
MATCH (n:Breakdown) SET n.ap_level = 'AP239', n.ap_schema = 'AP239';
MATCH (n:Event) SET n.ap_level = 'AP239', n.ap_schema = 'AP239';

// Level 2: AP242 Engineering Layer
MATCH (n:Part) SET n.ap_level = 'AP242', n.ap_schema = 'AP242';
MATCH (n:PartVersion) SET n.ap_level = 'AP242', n.ap_schema = 'AP242';
MATCH (n:Assembly) SET n.ap_level = 'AP242', n.ap_schema = 'AP242';
MATCH (n:GeometricModel) SET n.ap_level = 'AP242', n.ap_schema = 'AP242';
MATCH (n:ShapeRepresentation) SET n.ap_level = 'AP242', n.ap_schema = 'AP242';
MATCH (n:Material) SET n.ap_level = 'AP242', n.ap_schema = 'AP242';
MATCH (n:MaterialProperty) SET n.ap_level = 'AP242', n.ap_schema = 'AP242';
MATCH (n:ComponentPlacement) SET n.ap_level = 'AP242', n.ap_schema = 'AP242';

// Level 3: AP243 Reference Data Layer
MATCH (n:ExternalOwlClass) SET n.ap_level = 'AP243', n.ap_schema = 'AP243';
MATCH (n:ExternalUnit) SET n.ap_level = 'AP243', n.ap_schema = 'AP243';
MATCH (n:ExternalPropertyDefinition) SET n.ap_level = 'AP243', n.ap_schema = 'AP243';
MATCH (n:Classification) SET n.ap_level = 'AP243', n.ap_schema = 'AP243';
MATCH (n:ValueType) SET n.ap_level = 'AP243', n.ap_schema = 'AP243';

// ============================================================================
// PHASE 5: CREATE SAMPLE AP239 DATA (Requirements Layer)
// ============================================================================

// Sample Requirement with version
MERGE (req1:Requirement {id: 'REQ-001'})
ON CREATE SET
    req1.name = 'Maximum Operating Temperature',
    req1.description = 'System shall operate continuously at temperatures up to 85°C',
    req1.type = 'Performance',
    req1.priority = 'High',
    req1.status = 'Approved',
    req1.ap_level = 'AP239',
    req1.ap_schema = 'AP239',
    req1.created_at = datetime();

MERGE (reqv1:RequirementVersion {version: '1.2', name: 'Maximum Operating Temperature v1.2'})
ON CREATE SET
    reqv1.description = 'Updated thermal requirement with extended range',
    reqv1.status = 'Current',
    reqv1.ap_level = 'AP239',
    reqv1.ap_schema = 'AP239',
    reqv1.created_at = datetime();

// Sample Analysis
MERGE (ana1:Analysis {name: 'Thermal Analysis - Steady State'})
ON CREATE SET
    ana1.type = 'ThermalSimulation',
    ana1.method = 'Finite Element Method',
    ana1.status = 'Completed',
    ana1.ap_level = 'AP239',
    ana1.ap_schema = 'AP239',
    ana1.created_at = datetime();

MERGE (model1:AnalysisModel {name: 'Thermal FEM Model - Rev A'})
ON CREATE SET
    model1.mesh_size = 5000,
    model1.solver = 'ANSYS Mechanical',
    model1.ap_level = 'AP239',
    model1.ap_schema = 'AP239';

// Sample Approval
MERGE (appr1:Approval {name: 'Design Review Board Approval'})
ON CREATE SET
    appr1.status = 'Approved',
    appr1.approved_by = 'Engineering Director',
    appr1.approval_date = date('2024-01-15'),
    appr1.ap_level = 'AP239',
    appr1.ap_schema = 'AP239';

// Sample Document
MERGE (doc1:Document {name: 'System Requirements Specification'})
ON CREATE SET
    doc1.document_id = 'SRS-2024-001',
    doc1.version = '2.0',
    doc1.type = 'Specification',
    doc1.ap_level = 'AP239',
    doc1.ap_schema = 'AP239';

// ============================================================================
// PHASE 6: CREATE SAMPLE AP242 DATA (Engineering Layer)
// ============================================================================

// Sample Part
MERGE (part1:Part {id: 'PRT-1001'})
ON CREATE SET
    part1.name = 'Heat Sink Assembly',
    part1.description = 'Aluminum heat sink with thermal interface',
    part1.part_number = 'HS-AL-500',
    part1.status = 'Released',
    part1.ap_level = 'AP242',
    part1.ap_schema = 'AP242',
    part1.created_at = datetime();

MERGE (partv1:PartVersion {version: 'B', name: 'Heat Sink Assembly Rev B'})
ON CREATE SET
    partv1.status = 'Current',
    partv1.ap_level = 'AP242',
    partv1.ap_schema = 'AP242';

// Sample Assembly
MERGE (asm1:Assembly {name: 'Cooling System Assembly'})
ON CREATE SET
    asm1.assembly_type = 'Mechanical',
    asm1.component_count = 5,
    asm1.ap_level = 'AP242',
    asm1.ap_schema = 'AP242';

// Sample Geometric Model
MERGE (geo1:GeometricModel {name: 'Heat Sink CAD Model'})
ON CREATE SET
    geo1.model_type = 'Solid',
    geo1.units = 'millimeters',
    geo1.ap_level = 'AP242',
    geo1.ap_schema = 'AP242';

MERGE (shape1:ShapeRepresentation {name: 'Heat Sink External Shape'})
ON CREATE SET
    shape1.representation_type = 'BRep',
    shape1.ap_level = 'AP242',
    shape1.ap_schema = 'AP242';

// Sample Material
MERGE (mat1:Material {name: 'Aluminum 6061-T6'})
ON CREATE SET
    mat1.material_type = 'Metal',
    mat1.specification = 'ASTM B221',
    mat1.ap_level = 'AP242',
    mat1.ap_schema = 'AP242';

MERGE (prop1:MaterialProperty {name: 'Thermal Conductivity'})
ON CREATE SET
    prop1.value = 167.0,
    prop1.unit = 'W/(m·K)',
    prop1.temperature = 20.0,
    prop1.ap_level = 'AP242',
    prop1.ap_schema = 'AP242';

// ============================================================================
// PHASE 7: CREATE SAMPLE AP243 DATA (Reference Data Layer)
// ============================================================================

// Sample External Ontology Class
MERGE (owl1:ExternalOwlClass {name: 'ThermalMaterial'})
ON CREATE SET
    owl1.ontology = 'EMMO (Elementary Multiperspective Material Ontology)',
    owl1.uri = 'http://emmo.info/emmo#EMMO_ThermalMaterial',
    owl1.description = 'Material with defined thermal properties',
    owl1.ap_level = 'AP243',
    owl1.ap_schema = 'AP243';

// Sample External Unit
MERGE (unit1:ExternalUnit {symbol: 'W/(m·K)'})
ON CREATE SET
    unit1.name = 'Watt per meter Kelvin',
    unit1.unit_type = 'ThermalConductivity',
    unit1.si_conversion = 1.0,
    unit1.ap_level = 'AP243',
    unit1.ap_schema = 'AP243';

MERGE (unit2:ExternalUnit {symbol: '°C'})
ON CREATE SET
    unit2.name = 'Degree Celsius',
    unit2.unit_type = 'Temperature',
    unit2.si_conversion = 1.0,
    unit2.ap_level = 'AP243',
    unit2.ap_schema = 'AP243';

// Sample Classification
MERGE (class1:Classification {name: 'Thermal Management Components'})
ON CREATE SET
    class1.classification_system = 'ISO 13584-501',
    class1.code = 'TMC-100',
    class1.ap_level = 'AP243',
    class1.ap_schema = 'AP243';

// Sample Value Type
MERGE (vt1:ValueType {name: 'TemperatureValue'})
ON CREATE SET
    vt1.data_type = 'double',
    vt1.unit_reference = 'degC',
    vt1.ap_level = 'AP243',
    vt1.ap_schema = 'AP243';

// ============================================================================
// PHASE 8: CREATE AP239 INTERNAL RELATIONSHIPS
// ============================================================================

MATCH (req:Requirement {id: 'REQ-001'})
MATCH (reqv:RequirementVersion {version: '1.2'})
MERGE (req)-[:HAS_VERSION]->(reqv);

MATCH (req:Requirement {id: 'REQ-001'})
MATCH (ana:Analysis {name: 'Thermal Analysis - Steady State'})
MERGE (req)-[:VERIFIES]->(ana);

MATCH (ana:Analysis {name: 'Thermal Analysis - Steady State'})
MATCH (model:AnalysisModel {name: 'Thermal FEM Model - Rev A'})
MERGE (ana)-[:USES_MODEL]->(model);

MATCH (req:Requirement {id: 'REQ-001'})
MATCH (appr:Approval {name: 'Design Review Board Approval'})
MERGE (req)-[:APPROVES]->(appr);

MATCH (req:Requirement {id: 'REQ-001'})
MATCH (doc:Document {name: 'System Requirements Specification'})
MERGE (doc)-[:DOCUMENTS]->(req);

// ============================================================================
// PHASE 9: CREATE AP242 INTERNAL RELATIONSHIPS
// ============================================================================

MATCH (part:Part {id: 'PRT-1001'})
MATCH (partv:PartVersion {version: 'B'})
MERGE (part)-[:HAS_VERSION]->(partv);

MATCH (part:Part {id: 'PRT-1001'})
MATCH (asm:Assembly {name: 'Cooling System Assembly'})
MERGE (asm)-[:ASSEMBLES_WITH]->(part);

MATCH (part:Part {id: 'PRT-1001'})
MATCH (geo:GeometricModel {name: 'Heat Sink CAD Model'})
MERGE (part)-[:HAS_GEOMETRY]->(geo);

MATCH (geo:GeometricModel {name: 'Heat Sink CAD Model'})
MATCH (shape:ShapeRepresentation {name: 'Heat Sink External Shape'})
MERGE (geo)-[:HAS_REPRESENTATION]->(shape);

MATCH (part:Part {id: 'PRT-1001'})
MATCH (mat:Material {name: 'Aluminum 6061-T6'})
MERGE (part)-[:USES_MATERIAL]->(mat);

MATCH (mat:Material {name: 'Aluminum 6061-T6'})
MATCH (prop:MaterialProperty {name: 'Thermal Conductivity'})
MERGE (mat)-[:HAS_PROPERTY]->(prop);

// ============================================================================
// PHASE 10: CREATE AP243 INTERNAL RELATIONSHIPS
// ============================================================================

MATCH (mat:Material {name: 'Aluminum 6061-T6'})
MATCH (owl:ExternalOwlClass {name: 'ThermalMaterial'})
MERGE (mat)-[:CLASSIFIED_AS]->(owl);

MATCH (prop:MaterialProperty {name: 'Thermal Conductivity'})
MATCH (unit:ExternalUnit {symbol: 'W/(m·K)'})
MERGE (prop)-[:HAS_UNIT]->(unit);

MATCH (part:Part {id: 'PRT-1001'})
MATCH (class:Classification {name: 'Thermal Management Components'})
MERGE (part)-[:CLASSIFIED_AS]->(class);

MATCH (prop:MaterialProperty {name: 'Thermal Conductivity'})
MATCH (vt:ValueType {name: 'TemperatureValue'})
MERGE (prop)-[:HAS_VALUE_TYPE]->(vt);

// ============================================================================
// PHASE 11: CREATE CROSS-LEVEL RELATIONSHIPS (AP239 → AP242 → AP243)
// ============================================================================

// Requirement → Part (Level 1 → Level 2)
MATCH (req:Requirement {id: 'REQ-001'})
MATCH (part:Part {id: 'PRT-1001'})
MERGE (req)-[:SATISFIED_BY_PART]->(part);

// Analysis → Material (Level 1 → Level 2)
MATCH (ana:Analysis {name: 'Thermal Analysis - Steady State'})
MATCH (mat:Material {name: 'Aluminum 6061-T6'})
MERGE (ana)-[:ANALYZED_BY_MODEL {notes: 'Thermal conductivity validated'}]->(mat);

// Approval → PartVersion (Level 1 → Level 2)
MATCH (appr:Approval {name: 'Design Review Board Approval'})
MATCH (partv:PartVersion {version: 'B'})
MERGE (appr)-[:APPROVED_FOR_VERSION]->(partv);

// Material → Ontology (Level 2 → Level 3)
MATCH (mat:Material {name: 'Aluminum 6061-T6'})
MATCH (owl:ExternalOwlClass {name: 'ThermalMaterial'})
MERGE (mat)-[:MATERIAL_CLASSIFIED_AS]->(owl);

// MaterialProperty → Unit (Level 2 → Level 3)
MATCH (prop:MaterialProperty {name: 'Thermal Conductivity'})
MATCH (unit:ExternalUnit {symbol: 'W/(m·K)'})
MERGE (prop)-[:USES_UNIT]->(unit);

// Requirement → Unit (Level 1 → Level 3 - direct skip)
MATCH (req:Requirement {id: 'REQ-001'})
MATCH (unit:ExternalUnit {symbol: '°C'})
MERGE (req)-[:REQUIREMENT_VALUE_TYPE {context: 'Temperature specification'}]->(unit);

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
// WHERE req.ap_level = 'AP239' AND part.ap_level = 'AP242' AND owl.ap_level = 'AP243'
// RETURN req.name, part.name, owl.name, length(path) AS chain_length
// LIMIT 5;

// ============================================================================
// END OF MIGRATION SCRIPT
// ============================================================================
