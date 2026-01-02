# ISO 10303-4443 SMRL API Comparison

**Date**: December 7, 2025  
**Standard**: ISO/TS 10303-4443 - System Modeling Representation Language (SMRL)  
**Reference**: https://standards.iso.org/iso/ts/10303/-4443/ed-1/tech/openapi-schema/domain_model/DomainModel.json

---

## 📊 Overview

### Current MBSE API vs ISO SMRL Standard

| Aspect | Current Implementation | ISO 10303-4443 SMRL | Gap Analysis |
|--------|----------------------|---------------------|--------------|
| **Total Endpoints** | 41 | 151 | 110 endpoints missing |
| **Resources** | 9 core types | 81 resource types | 72 resource types missing |
| **Schemas** | Basic UML/SysML | 237 standardized schemas | Need full SMRL compliance |
| **HTTP Methods** | GET, POST (limited) | GET, POST, PUT, PATCH | Need full CRUD |
| **API Standard** | Custom REST | ISO SMRL OpenAPI 3.0 | Need standardization |
| **Versioning** | None | ISO standard versioned | Need API versioning |
| **Authentication** | None | Standard-based (planned) | Need OAuth/JWT |

---

## 🏗️ Architecture Comparison

### Current Implementation (UML/SysML Focused)

**Core Node Types**:
- Class (188 nodes)
- Package (34 nodes)
- Property (1,217 nodes)
- Port (188 nodes)
- Association (502 nodes)
- Constraint
- Comment (854 nodes)
- Slot
- InstanceSpecification

**Relationships**:
- HAS_COMMENT
- CONTAINS
- HAS_ATTRIBUTE
- TYPED_BY
- HAS_END
- ASSOCIATES_WITH
- CONNECTED_BY
- GENERALIZES
- HAS_RULE

### ISO SMRL Standard (Full Systems Engineering)

**Key Resource Categories** (81 total):

#### 1. **Model Structure** (13 resources)
- AccessibleModelInstanceConstituent
- AccessibleModelTypeConstituent
- Architecture
- ArchitectureElementInclusion
- AssociativeModelNetwork
- BreakdownElement
- BreakdownElementAssociation
- ModelingStandard
- SystemReference
- View
- Viewpoint

#### 2. **Requirements** (3 resources)
- Requirement
- RequirementRelationship
- RequirementShouldBeSatisfied

#### 3. **Activities & Behavior** (9 resources)
- ActualActivity
- PlannedActivity
- StateOccurrence
- Activity
- BehaviorSpecification
- FunctionInstance
- FunctionType
- OperationalActivity

#### 4. **Interfaces & Ports** (6 resources)
- InterfaceInstance
- InterfacePortInstance
- InterfacePortType
- InterfaceRealization
- InterfaceType
- Port

#### 5. **Properties & Values** (8 resources)
- PropertyDefinition
- PropertyValue
- ParameterDefinition
- ParameterValue
- Attribute
- AttributeValueAssignment

#### 6. **Verification & Validation** (4 resources)
- Approval
- ApprovalAssignment
- Assumption
- Justification

#### 7. **Configuration & Versioning** (5 resources)
- ConfigurationItem
- VersionChain
- VersionPoint
- Change
- ChangeRequest

#### 8. **Organization & People** (4 resources)
- Organization
- Person
- PersonOrganization
- SecurityClassification

---

## 🔍 Detailed Gap Analysis

### ✅ What We Have (Aligned with SMRL)

**1. Basic UML/SysML Elements**
- ✅ Class (maps to TypeConstituent)
- ✅ Package (maps to BreakdownElement)
- ✅ Property (maps to PropertyDefinition)
- ✅ Port (partial - maps to InterfacePortType)
- ✅ Association (maps to relationship types)
- ✅ Constraint (partial support)

**2. Basic Relationships**
- ✅ Containment (CONTAINS)
- ✅ Generalization (GENERALIZES)
- ✅ Association (ASSOCIATES_WITH)
- ✅ Typing (TYPED_BY)

**3. Documentation**
- ✅ Comments (HAS_COMMENT)
- ✅ Descriptions (in properties)

### ❌ What We're Missing (SMRL Standard)

**1. Requirements Management** (CRITICAL)
- ❌ Requirement resource
- ❌ RequirementRelationship
- ❌ RequirementShouldBeSatisfied
- ❌ Verification/validation tracking

**2. Architecture & Views** (HIGH)
- ❌ Architecture resource
- ❌ ArchitectureElementInclusion
- ❌ View/Viewpoint management
- ❌ Multi-view support

**3. Lifecycle & Configuration** (HIGH)
- ❌ VersionChain/VersionPoint
- ❌ ConfigurationItem
- ❌ Change/ChangeRequest
- ❌ Approval workflow

**4. Activities & Behavior** (MEDIUM)
- ❌ ActualActivity/PlannedActivity
- ❌ BehaviorSpecification
- ❌ StateOccurrence
- ❌ OperationalActivity

**5. Advanced Interfaces** (MEDIUM)
- ❌ InterfaceInstance/InterfaceType
- ❌ InterfaceRealization
- ❌ Port instances vs types distinction

**6. Organizational** (MEDIUM)
- ❌ Person/Organization as first-class resources
- ❌ SecurityClassification
- ❌ ApprovalAssignment

**7. Metadata & Traceability** (LOW but important)
- ❌ CreatedBy/ModifiedBy tracking
- ❌ CreatedOn/LastModified timestamps
- ❌ Identifiers (multiple ID schemes)
- ❌ Names/Descriptions (localized)

---

## 📝 API Endpoint Comparison

### Current API Structure

```
GET  /api/stats                    - Graph statistics
GET  /api/packages                 - List all packages
GET  /api/package/<id>             - Get package details
GET  /api/classes                  - List all classes
GET  /api/class/<id>               - Get class details
GET  /api/artifacts                - List artifact types
GET  /api/artifacts/<type>         - List artifacts by type
GET  /api/artifacts/<type>/<id>    - Get artifact details
POST /api/cypher                   - Execute Cypher query
GET  /api/search                   - Search artifacts
... (31 more endpoints)
```

### ISO SMRL Standard Structure

```
POST   /{ResourceType}              - Create resource
GET    /{ResourceType}/{uid}        - Read resource
PUT    /{ResourceType}/{uid}        - Replace resource
PATCH  /{ResourceType}/{uid}        - Update resource
DELETE /{ResourceType}/{uid}        - Delete resource (implied)

Examples:
POST   /Requirement                 - Create requirement
GET    /Requirement/{uid}            - Get requirement
PUT    /Requirement/{uid}            - Update requirement
PATCH  /Requirement/{uid}            - Partial update
```

**Standard Features**:
- ✅ RESTful resource-based URLs
- ✅ Full CRUD operations
- ✅ Consistent URL patterns
- ✅ Standard HTTP status codes
- ✅ JSON and XML support
- ✅ Hypermedia links ($href)

---

## 🎯 Standardization Recommendations

### Phase 1: Foundation (Immediate - 2-4 weeks)

**1.1 Add SMRL Metadata to Existing Resources**
```python
# Add to all resources
{
    "id": "unique_id",
    "$href": "/api/v1/Class/{id}",  # SMRL standard
    "CreatedBy": "user_id",
    "CreatedOn": "2025-12-07T00:00:00Z",
    "LastModified": "2025-12-07T00:00:00Z",
    "ModifiedBy": "user_id",
    "Names": [{"context": "en", "value": "MyClass"}],
    "Descriptions": [{"locale": "en", "value": "Description"}]
}
```

**1.2 Implement Full CRUD**
- Add PUT/PATCH endpoints for all resources
- Add DELETE endpoints (with cascade options)
- Standardize response formats

**1.3 API Versioning**
```
Current: /api/packages
SMRL:    /api/v1/Package  (ISO compliant)
```

### Phase 2: Requirements & Lifecycle (4-6 weeks)

**2.1 Add Requirements Management**
```python
@app.route('/api/v1/Requirement', methods=['POST'])
@app.route('/api/v1/Requirement/<uid>', methods=['GET', 'PUT', 'PATCH'])

# Schema matches SMRL Requirement
{
    "Requirement": {
        "$href": "/api/v1/Requirement/{uid}",
        "Identifiers": [...],
        "Names": [...],
        "Descriptions": [...],
        "RequirementText": "System shall...",
        "Priority": "High",
        "Status": "Approved",
        "SatisfiedBy": [...],  # Links to design elements
        "VerifiedBy": [...]    # Links to test cases
    }
}
```

**2.2 Add Version Management**
```python
@app.route('/api/v1/VersionChain', methods=['POST'])
@app.route('/api/v1/VersionPoint/<uid>', methods=['GET'])
```

**2.3 Add Approval Workflow**
```python
@app.route('/api/v1/Approval', methods=['POST', 'GET'])
@app.route('/api/v1/ApprovalAssignment/<uid>', methods=['GET', 'PUT'])
```

### Phase 3: Architecture & Views (6-8 weeks)

**3.1 Add Architecture Resources**
```python
@app.route('/api/v1/Architecture', methods=['POST', 'GET'])
@app.route('/api/v1/ArchitectureElementInclusion', methods=['POST'])
```

**3.2 Add View/Viewpoint**
```python
@app.route('/api/v1/View', methods=['POST', 'GET'])
@app.route('/api/v1/Viewpoint/<uid>', methods=['GET'])
```

### Phase 4: Advanced Features (8-12 weeks)

**4.1 Behavior & Activities**
```python
@app.route('/api/v1/ActualActivity', methods=['POST', 'GET'])
@app.route('/api/v1/BehaviorSpecification/<uid>', methods=['GET'])
```

**4.2 Interface Management**
```python
@app.route('/api/v1/InterfaceInstance', methods=['POST'])
@app.route('/api/v1/InterfaceRealization/<uid>', methods=['GET'])
```

**4.3 Configuration Management**
```python
@app.route('/api/v1/ConfigurationItem', methods=['POST', 'GET'])
@app.route('/api/v1/Change/<uid>', methods=['GET', 'PUT'])
```

---

## 🔧 Implementation Strategy

### Step 1: Create SMRL Adapter Layer

```python
# src/api/smrl_adapter.py
class SMRLAdapter:
    """Adapts Neo4j graph to SMRL standard format"""
    
    @staticmethod
    def to_smrl_resource(node, resource_type):
        """Convert Neo4j node to SMRL resource format"""
        return {
            resource_type: {
                "$href": f"/api/v1/{resource_type}/{node['id']}",
                "Identifiers": [{
                    "context": "neo4j",
                    "value": node['id']
                }],
                "Names": [{
                    "context": "en",
                    "value": node.get('name', '')
                }],
                "Descriptions": [{
                    "locale": "en",
                    "value": node.get('comment', '')
                }],
                "CreatedBy": node.get('created_by', 'system'),
                "CreatedOn": node.get('created_on', '2025-01-01T00:00:00Z'),
                "LastModified": node.get('last_modified', '2025-01-01T00:00:00Z'),
                "ModifiedBy": node.get('modified_by', 'system'),
                # ... resource-specific properties
            }
        }
```

### Step 2: Create SMRL Schema Validation

```python
# src/api/smrl_validator.py
import jsonschema

class SMRLValidator:
    """Validates requests against SMRL schema"""
    
    def __init__(self, schema_path='/tmp/smrl_schema.json'):
        with open(schema_path) as f:
            self.schema = json.load(f)
    
    def validate_request(self, resource_type, data):
        """Validate request data against SMRL schema"""
        schema_ref = f"#/components/schemas/{resource_type}"
        # ... validation logic
```

### Step 3: Refactor Existing Endpoints

```python
# Migrate from:
@app.route('/api/classes')
def get_classes():
    ...

# To:
@app.route('/api/v1/Class', methods=['GET', 'POST'])
def class_collection():
    if request.method == 'GET':
        return list_classes_smrl()
    elif request.method == 'POST':
        return create_class_smrl()

@app.route('/api/v1/Class/<uid>', methods=['GET', 'PUT', 'PATCH'])
def class_resource(uid):
    ...
```

---

## 📊 Compliance Roadmap

### Immediate Actions (Week 1-2)
- [ ] Download and study ISO 10303-4443 SMRL specification
- [ ] Create SMRL adapter layer for existing resources
- [ ] Add metadata fields (CreatedBy, LastModified, etc.)
- [ ] Implement API versioning (/api/v1/)
- [ ] Update documentation with SMRL references

### Short Term (Month 1)
- [ ] Implement full CRUD for Class, Package, Property
- [ ] Add Requirements resource (SMRL compliant)
- [ ] Add Version management (VersionChain, VersionPoint)
- [ ] Implement schema validation against SMRL
- [ ] Add Approval workflow

### Medium Term (Month 2-3)
- [ ] Add Architecture and View resources
- [ ] Implement Interface management (Instance/Type/Realization)
- [ ] Add Activity and Behavior resources
- [ ] Implement Configuration management
- [ ] Add Person/Organization resources

### Long Term (Month 4-6)
- [ ] Full SMRL compliance (all 81 resources)
- [ ] Complete test coverage against SMRL test suite
- [ ] OSLC integration (if needed)
- [ ] Certification/validation against ISO standard
- [ ] Performance optimization for SMRL queries

---

## 🎓 Learning Resources

### ISO Standards
- **ISO/TS 10303-4443**: System Modeling Representation Language (SMRL)
- **ISO 10303-233**: Application protocol: Systems engineering
- **ISO 15288**: Systems and software engineering - System life cycle processes

### Related Standards
- **OMG SysML**: Systems Modeling Language
- **OMG UML**: Unified Modeling Language
- **OSLC**: Open Services for Lifecycle Collaboration
- **ReqIF**: Requirements Interchange Format

### OpenAPI
- [OpenAPI 3.0 Specification](https://swagger.io/specification/)
- [ISO SMRL OpenAPI Schema](https://standards.iso.org/iso/ts/10303/-4443/ed-1/tech/openapi-schema/)

---

## 💡 Key Benefits of SMRL Compliance

### For Users
- ✅ **Interoperability**: Exchange data with other SMRL-compliant tools
- ✅ **Standardization**: Industry-standard API patterns and schemas
- ✅ **Completeness**: Full systems engineering lifecycle support
- ✅ **Traceability**: Requirements to design to verification links

### For Developers
- ✅ **Clear specification**: ISO standard provides detailed guidance
- ✅ **Tooling**: Can use standard SMRL validators and generators
- ✅ **Future-proof**: Based on ISO standard, not proprietary format
- ✅ **Integration**: Easier to integrate with PLM, ALM tools

### For Organization
- ✅ **Compliance**: Meets ISO/IEC systems engineering standards
- ✅ **Tool independence**: Not locked into proprietary formats
- ✅ **Certification**: Can pursue ISO certification if needed
- ✅ **Best practices**: Follows established SE standards

---

## 🚨 Critical Gaps to Address

### Priority 1 (CRITICAL)
1. **Requirements Management**: No requirement tracking currently
2. **Versioning**: No version control or change tracking
3. **API Versioning**: Need /api/v1/ structure
4. **Metadata**: Missing CreatedBy, LastModified fields

### Priority 2 (HIGH)
5. **Architecture Views**: No view/viewpoint support
6. **Approval Workflow**: No approval tracking
7. **Full CRUD**: Only GET supported for most resources
8. **Schema Validation**: No validation against SMRL schemas

### Priority 3 (MEDIUM)
9. **Interface Management**: Basic port support only
10. **Activity/Behavior**: No activity or state tracking
11. **Configuration**: No configuration item management
12. **Organization**: Person/Organization not first-class resources

---

## 📈 Success Metrics

### Compliance Level
- **Current**: ~10% SMRL compliant (basic UML/SysML elements)
- **Target Phase 1**: 30% compliant (metadata, CRUD, versioning)
- **Target Phase 2**: 60% compliant (+requirements, lifecycle)
- **Target Phase 3**: 80% compliant (+architecture, views)
- **Target Phase 4**: 95%+ compliant (full SMRL support)

### Quality Metrics
- [ ] All endpoints follow SMRL URL patterns
- [ ] All resources have SMRL-compliant schemas
- [ ] All requests validated against SMRL schemas
- [ ] 100% test coverage for SMRL endpoints
- [ ] Response times < 200ms for single resource GET
- [ ] Support 1000+ SMRL resources in database

---

**Last Updated**: December 7, 2025  
**Next Review**: After Phase 1 completion

**Reference**: ISO/TS 10303-4443 Ed. 1 - System Modeling Representation Language  
**Schema URL**: https://standards.iso.org/iso/ts/10303/-4443/ed-1/tech/openapi-schema/domain_model/DomainModel.json
