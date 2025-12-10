# ISO 10303 Application Protocol (AP) Schema Analysis

## Executive Summary

Based on analysis of SMRL v12 data schemas in `/workspaces/mbse-neo4j-graph-rep/smrlv12/data/`, there are **three ISO 10303 Application Protocols** relevant to end-to-end MBSE flow:

| AP | Standard | Domain | File Location | Status |
|----|----------|--------|---------------|--------|
| **AP239** | ISO 10303-239 | Product Life Cycle Support (PLCS) | `domain_models/product_life_cycle_support/Domain_model.xsd` | ✅ Present |
| **AP242** | ISO 10303-242 | Managed Model-Based 3D Engineering | `business_object_models/managed_model_based_3d_engineering/bom.xsd`<br>`domain_models/managed_model_based_3d_engineering_domain/DomainModel.xsd` | ✅ Present |
| **AP243** | ISO 10303-243 | Product Data Management | Referenced in `mossec/Domain_model.xmi` (20+ references) | ⚠️ Referenced only |

---

## 📊 Schema Details

### 1. AP239 - Product Life Cycle Support (PLCS)
**File**: `/workspaces/mbse-neo4j-graph-rep/smrlv12/data/domain_models/product_life_cycle_support/Domain_model.xsd`

**Scope**: Comprehensive lifecycle management across entire product journey

**Key Elements** (24,509 lines):
- `AP239DataContainer` root element
- 400+ complex types including:
  - `Activity`, `ActivityMethod`, `ActivityAssignment`
  - `Analysis`, `AnalysisModel`, `AnalysisVersion`
  - `Breakdown`, `BreakdownElement`, `BreakdownVersion`
  - `Document`, `DocumentDefinition`, `DocumentVersion`
  - `Requirement`, `RequirementVersion`, `RequirementSource`
  - `Effectivity`, `Approval`, `Certification`
  - `IndividualPart`, `IndividualPartVersion`, `IndividualPartView`
  - `Contract`, `Event`, `Evidence`, `Condition`
  - `Environment`, `EnvironmentDefinition`, `EnvironmentView`

**Use Cases**:
- Configuration management
- Requirements management
- Product lifecycle tracking
- Change management
- Compliance and certification
- Contract and approval workflows
- Analysis and simulation tracking
- Document management

**Namespace**: `https://standards.iso.org/iso/ts/10303/-4439/ed-2/tech/xml-schema/domain_model`  
**Version**: N11407;2024-02-14

---

### 2. AP242 - Managed Model-Based 3D Engineering
**Files**: 
- `/workspaces/mbse-neo4j-graph-rep/smrlv12/data/business_object_models/managed_model_based_3d_engineering/bom.xsd` (21,099 lines)
- `/workspaces/mbse-neo4j-graph-rep/smrlv12/data/domain_models/managed_model_based_3d_engineering_domain/DomainModel.xsd` (16,688 lines)

**Scope**: 3D CAD models, geometric representations, product structure, and manufacturing information

**Key Elements**:
- `AP242DataContainer` root element
- **Business Object Model (bom.xsd)** - 200+ types:
  - `Activity`, `ActivityMethod`, `Address`
  - `Breakdown`, `BreakdownElement`
  - `Class`, `Classification`, `ComponentPlacement`
  - `ConfiguredAssemblyEffectivity`
  - `Document`, `File`, `FormatProperty`
  - `IndividualPart`, `Part`, `PartVersion`, `PartView`
  - `GeometricModel`, `ShapeRepresentation`
  - `Assembly`, `AssemblyRelationship`
  - `NumericalContext`, `PhysicalBreakdownElementViewAssociation`
  - `Product`, `ProductVersion`, `ProductView`
  
- **Domain Model (DomainModel.xsd)** - 300+ types (adds):
  - `Analysis`, `AnalysisRepresentationContext`
  - `Envelope`, `Evidence`, `EvaluatedRequirement`
  - `CurveAppearance`, `GeometricTolerance`
  - `MakeFrom`, `Material`, `MaterialProperty`
  - `MultiLevelReference`, `PropertyValueRepresentation`
  - `Requirement`, `RequirementAssignment`, `RequirementSource`
  - `ShapeAspect`, `ShapeRepresentation`, `ShapeRepresentationRelationship`

**Use Cases**:
- 3D CAD model management
- Product structure (BOM) management
- Geometric representation
- Configuration management
- Manufacturing planning
- Tolerancing and annotations
- Material specifications
- Assembly definitions

**Namespace**: 
- BOM: `http://standards.iso.org/iso/ts/10303/-3001/-ed-2/tech/xml-schema/bo_model`
- Domain: `https://standards.iso.org/iso/ts/10303/-4442/ed-5/tech/xml-schema/domain_model`

**Version**: 
- BOM: 2016-03-30
- Domain: N11493;2024-12-03

---

### 3. AP243 - Product Data Management
**Reference**: `/workspaces/mbse-neo4j-graph-rep/smrlv12/data/domain_models/mossec/Domain_model.xmi`

**Status**: ⚠️ **Referenced but not directly provided as XSD schema**

**Evidence** (20+ references in mossec/Domain_model.xmi):
```xml
<!-- Value types from AP243 ontology -->
<value>http://standards.iso.org/iso/10303/-243/tech/refdata/ap243_v1#3380ac3c-e884-4e2c-a7b5-e31ed352dad0</value>
<value>http://standards.iso.org/iso/10303/-243/tech/refdata/ap243_v1#96f3907e-9688-48fe-883f-fac34f4094ed</value>

<!-- Constraints referencing AP243 value types -->
<body>ValueType.mustBeSubClassOf('http://standards.iso.org/iso/10303/-243/tech/refdata/ap243_v1#83615252-c407-47c3-bec5-9b3c1945703e')</body>

<!-- Property definitions -->
<body>numericDefinition = if ValueType = 'http://standards.iso.org/iso/10303/-243/tech/refdata/ap243_v1#6c72ff4d-ec5c-4a67-950a-f2c2fd3f4633' then propertyDefinition...</body>
```

**Scope**: Reference data, ontologies, and standardized property definitions

**Use Cases**:
- Standardized value types
- Reference ontologies (OWL)
- Property value classifications
- Data format definitions (DXF, IGES, STEP, etc.)
- Unit definitions
- Enumeration definitions

**Comment in XMI**:
```xml
<body>To do: Remove the enumerations when checked all in ap243:v1.owl</body>
<body>subClassOf 'data format' (subClassOf 'format property' subClassOf 'file') 
Sub classes: DXF, IGES, ISO 10303-203, ISO 10303-214, ISO 10303-239, ISO 10303-242, TIFF CCITT GR4, VDAFS, VOXEL.</body>
```

**Note**: AP243 appears to be used as reference data ontology rather than full schema, providing standardized vocabularies and value types used by AP239 and AP242.

---

## 🔄 End-to-End MBSE Flow Integration

### Recommended Schema Selection Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                    End-to-End MBSE Flow                         │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌────────────────┐   ┌────────────────┐   ┌────────────────┐
│   AP242        │   │   AP239        │   │   AP243        │
│   (3D Models)  │◄─►│   (Lifecycle)  │◄─►│   (Reference)  │
│                │   │                │   │                │
│ • CAD Models   │   │ • Requirements │   │ • Value Types  │
│ • Geometry     │   │ • Activities   │   │ • Ontologies   │
│ • Product BOM  │   │ • Documents    │   │ • Units        │
│ • Assemblies   │   │ • Analysis     │   │ • Standards    │
│ • Manufacturing│   │ • Approvals    │   │ • Enumerations │
└────────────────┘   └────────────────┘   └────────────────┘
```

### Integration Architecture

#### **Primary Schema: AP239 (Product Life Cycle Support)**
**Reason**: Most comprehensive for MBSE knowledge graph
- ✅ Contains requirements, analysis, activities, documents
- ✅ Supports lifecycle management (versions, effectivity, approvals)
- ✅ Includes breakdown structures (WBS, PBS, FBS)
- ✅ Tracks change management and configuration
- ✅ Supports compliance and certification
- ✅ **Already partially implemented** (current `Domain_model.xsd`)

**Current Usage**: 
- Your existing parser (`semantic_loader.py`) loads UML/SysML from XMI
- AP239 provides lifecycle wrapper around design models

#### **Secondary Schema: AP242 (3D Engineering)**
**Reason**: Essential for geometric and manufacturing data
- ✅ Provides 3D CAD model integration
- ✅ Manages product structure (BOM)
- ✅ Supports geometric tolerancing
- ✅ Includes material specifications
- ✅ Covers manufacturing planning

**Integration Point**: 
- Link AP242 geometric models to AP239 requirements/analysis
- AP242 `Part`/`PartVersion` ↔ AP239 `IndividualPart`/`BreakdownElement`
- AP242 `ShapeRepresentation` ↔ AP239 `Analysis` nodes

#### **Reference Schema: AP243 (Reference Data)**
**Reason**: Provides standardized vocabularies
- ✅ Ontology-based value types
- ✅ Standardized units and measures
- ✅ Data format classifications
- ✅ Reference enumerations

**Integration Point**:
- Use AP243 URIs for `ExternalOwlClass` nodes
- Reference AP243 ontology for property validation
- Import AP243 value types for standardized classification

---

## 📋 Decision Matrix: Which Schema to Use?

### Use Case 1: **Systems Engineering & Requirements** → **AP239**
- Requirements management ✅
- Verification & validation ✅
- Lifecycle tracking ✅
- Analysis integration ✅
- Document management ✅
- Change management ✅

### Use Case 2: **Mechanical Design & Manufacturing** → **AP242**
- 3D CAD models ✅
- Product structure (BOM) ✅
- Geometric representations ✅
- Assemblies and components ✅
- Manufacturing process planning ✅
- Tolerancing and GD&T ✅

### Use Case 3: **Reference Data & Ontologies** → **AP243**
- Standardized value types ✅
- Units and measures ✅
- Data format definitions ✅
- Classification ontologies ✅
- Enumerated values ✅

---

## 🎯 Recommendation for MBSE Knowledge Graph

### **Hybrid Approach: AP239 + AP242 + AP243**

```python
# Proposed Integration Strategy

# 1. PRIMARY: AP239 for Systems Engineering Core
AP239_FOCUS = [
    'Requirement',           # Requirements management
    'RequirementVersion',    # Version control
    'Analysis',              # Simulation/analysis tracking
    'AnalysisVersion',       # Analysis versions
    'Activity',              # Workflow activities
    'Document',              # Documentation
    'Breakdown',             # Work breakdown structure
    'BreakdownElement',      # WBS elements
    'Approval',              # Approval workflows
    'Effectivity',           # Configuration management
    'Event',                 # Lifecycle events
]

# 2. SECONDARY: AP242 for CAD/Manufacturing
AP242_FOCUS = [
    'Part',                  # Product parts
    'PartVersion',           # Part versions
    'PartView',              # Part views (design, manufacturing)
    'Assembly',              # Assembly structure
    'GeometricModel',        # 3D geometry
    'ShapeRepresentation',   # Shape definitions
    'Material',              # Material specifications
    'ComponentPlacement',    # Assembly positioning
    'ProductView',           # Product configurations
]

# 3. REFERENCE: AP243 for Ontologies
AP243_FOCUS = [
    'ExternalOwlClass',      # Ontology classes
    'ExternalOwlObject',     # Ontology instances
    'ExternalUnit',          # Unit definitions
    'ValueType',             # Standardized value types
]

# Integration Points
CROSS_REFERENCES = {
    # AP239 Requirement ↔ AP242 Part
    'SATISFIES': ('Requirement', 'Part'),
    
    # AP239 Analysis ↔ AP242 GeometricModel
    'ANALYZES': ('Analysis', 'GeometricModel'),
    
    # AP239 Document ↔ AP242 Part
    'DESCRIBES': ('Document', 'Part'),
    
    # AP239 BreakdownElement ↔ AP242 Part
    'REALIZES': ('BreakdownElement', 'Part'),
    
    # AP243 ExternalOwlClass ↔ AP239/AP242 Classes
    'CLASSIFIES': ('ExternalOwlClass', '*'),
}
```

---

## 🔧 Implementation Plan

### Phase 1: Extend Current AP239 Implementation
1. ✅ **Current State**: Using `product_life_cycle_support/Domain_model.xsd`
2. 🔄 **Extend Parser**: Add AP239 lifecycle elements
   - Requirements (currently missing from database)
   - Analysis versions
   - Approvals and certifications
   - Effectivity and configuration

### Phase 2: Add AP242 Geometric Models
1. 📝 **Create AP242 Parser**: Handle `bom.xsd` and `DomainModel.xsd`
2. 🔗 **Link to AP239**: Connect parts to requirements/analysis
3. 📊 **Import CAD Data**: 3D models, assemblies, BOMs

### Phase 3: Integrate AP243 Reference Data
1. 📚 **Import Ontologies**: Load AP243 reference ontologies
2. 🔗 **Link Classifications**: Use AP243 URIs for value types
3. ✅ **Validate Data**: Ensure compliance with AP243 standards

---

## 📁 Current File Locations

```
smrlv12/data/
├── domain_models/
│   ├── product_life_cycle_support/
│   │   └── Domain_model.xsd          ← AP239 (24,509 lines)
│   ├── managed_model_based_3d_engineering_domain/
│   │   └── DomainModel.xsd           ← AP242 Domain (16,688 lines)
│   └── mossec/
│       └── Domain_model.xmi          ← Contains AP243 references
│
└── business_object_models/
    └── managed_model_based_3d_engineering/
        └── bom.xsd                   ← AP242 BOM (21,099 lines)
```

---

## 🚦 Status Summary

| Schema | Standard | Lines | Status | Priority |
|--------|----------|-------|--------|----------|
| **AP239** | ISO 10303-239 | 24,509 | ✅ Present, Partially Implemented | **HIGH** |
| **AP242** | ISO 10303-242 | 37,787 (2 files) | ✅ Present, Not Implemented | **MEDIUM** |
| **AP243** | ISO 10303-243 | N/A (References) | ⚠️ Referenced, Not Schema | **LOW** |

---

## 📝 Next Steps

1. **Clarify DevOps Metadata Integration Requirements**
   - Understand how DevOps metadata relates to AP239/AP242/AP243
   - Determine if Git versioning should map to AP239 versioning elements
   - Identify PLM system integration points (Teamcenter/Windchill → AP239/AP242)

2. **Extend AP239 Implementation**
   - Add missing node types: Requirement, Analysis, Approval, Effectivity
   - Implement version control using AP239 structures
   - Add lifecycle state management

3. **Create AP242 Integration**
   - Parse AP242 schemas (bom.xsd, DomainModel.xsd)
   - Import product structure (BOM) into graph
   - Link geometric models to requirements/analysis

4. **Import AP243 Reference Data**
   - Extract AP243 ontology URIs from mossec/Domain_model.xmi
   - Create reference nodes for value types and units
   - Implement validation using AP243 constraints

---

## ❓ Questions for Clarification

1. **DevOps Integration**: How do AP239/AP242 versioning elements relate to Git commits and CI/CD pipelines?

2. **PLM Integration**: Should Teamcenter/Windchill data map to:
   - AP239 (lifecycle/configuration)?
   - AP242 (CAD/BOM)?
   - Both?

3. **Priority**: Which schema should we implement first?
   - AP239 (systems engineering focus)?
   - AP242 (mechanical/manufacturing focus)?
   - Hybrid (both in parallel)?

4. **Data Source**: Where will AP242 CAD data come from?
   - Export from CAD tools (SolidWorks, CATIA, NX)?
   - From PLM systems (Teamcenter already has AP242 export)?
   - STEP files (ISO 10303-242 native format)?

5. **Scope**: Should we support all 400+ AP239 types or focus on subset?
   - Requirements, Analysis, Documents only?
   - Full lifecycle (Approvals, Certifications, Contracts)?
   - Product breakdown structures (WBS, PBS, FBS)?
