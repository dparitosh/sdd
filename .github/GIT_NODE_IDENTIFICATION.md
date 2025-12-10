# Git Integration - Node Identification Strategy

## 🎯 Purpose

Before implementing Git-integrated MBSE knowledge graph synchronization, we must identify which Neo4j nodes represent **versionable engineering artifacts** that should be tracked in Git and which are **derived/metadata** that should not.

---

## 📊 Current Graph Structure Analysis

### Node Types in Database (Based on semantic_loader.py)

From `src/parsers/semantic_loader.py`, we have three categories:

#### 1. **NODE_TYPES** (First-Class Elements - 30+ types)
These are primary model elements with identity that could be versioned:

**Core Structural Elements:**
- `uml:Model` → **Model** (Root container)
- `uml:Package` → **Package** (Organizational structure)
- `uml:Class` → **Class** (Core design elements)
- `uml:Interface` → **Interface** (Contract definitions)
- `uml:Component` → **Component** (System modules)
- `uml:Port` → **Port** (Interface points)
- `uml:Property` → **Property** (Attributes)
- `uml:Operation` → **Operation** (Methods/behaviors)
- `uml:Parameter` → **Parameter** (Operation parameters)
- `uml:DataType` → **DataType** (Custom data types)
- `uml:Enumeration` → **Enumeration** (Enum types)
- `uml:EnumerationLiteral` → **EnumerationLiteral** (Enum values)
- `uml:PrimitiveType` → **PrimitiveType** (Basic types)
- `uml:Stereotype` → **Stereotype** (UML extensions)

**Behavioral Elements:**
- `uml:Actor` → **Actor** (Use case actors)
- `uml:UseCase` → **UseCase** (System use cases)
- `uml:StateMachine` → **StateMachine** (State machines)
- `uml:State` → **State** (Individual states)
- `uml:Activity` → **Activity** (Activities)
- `uml:Action` → **Action** (Activity actions)
- `uml:Transition` → **Transition** (State transitions)
- `uml:Interaction` → **Interaction** (Sequence diagrams)
- `uml:Lifeline` → **Lifeline** (Interaction participants)
- `uml:Message` → **Message** (Interaction messages)

**Instance Specifications:**
- `uml:InstanceSpecification` → **InstanceSpecification** (Object instances)
- `uml:Slot` → **Slot** (Instance property values)

**Constraints and Documentation:**
- `uml:Constraint` → **Constraint** (Design rules)
- `uml:Comment` → **Comment** (Documentation)

**Associations:**
- `uml:Association` → **Association** (Class relationships)
- `uml:AssociationClass` → **AssociationClass** (Association with class behavior)

**SysML Specific:**
- `sysml:Block` → **Block** (SysML blocks)
- `sysml:Requirement` → **Requirement** (Requirements)
- `sysml:ValueType` → **ValueType** (Value types)
- `sysml:FlowPort` → **FlowPort** (Flow ports)
- `sysml:InterfaceBlock` → **InterfaceBlock** (Interface blocks)

#### 2. **RELATIONSHIP_TYPES** (Semantic Connections)
These create edges between nodes, not separate nodes:
- `uml:Generalization` → **GENERALIZES** relationship
- `uml:Realization` → **REALIZES** relationship
- `uml:Dependency` → **DEPENDS_ON** relationship
- `uml:Usage` → **USES** relationship
- `uml:Abstraction` → **ABSTRACTS** relationship
- `uml:Connector` → **CONNECTED_BY** relationship
- `uml:InformationFlow` → **FLOWS_TO** relationship
- `sysml:Allocate` → **ALLOCATED_TO** relationship
- `sysml:Satisfy` → **SATISFIES** relationship
- `sysml:Verify` → **VERIFIES** relationship
- `sysml:Refine` → **REFINES** relationship
- `sysml:Trace` → **TRACES_TO** relationship

#### 3. **METADATA_TYPES** (Stored as Properties)
These are not separate nodes, just property values:
- `uml:LiteralInteger`
- `uml:LiteralString`
- `uml:LiteralBoolean`
- `uml:LiteralReal`
- `uml:InstanceValue`
- etc.

---

## ✅ Git-Versionable Nodes (Should Track in Git)

### **Tier 1: Critical Design Artifacts** (MUST version)

These represent core engineering decisions and design:

1. **Class** (~143 nodes)
   - Core design elements
   - Design decisions embedded in structure
   - **Git Tracking**: YES - Track every change
   - **Properties to track**: `id`, `name`, `comment`, `visibility`, `isAbstract`, `isStatic`

2. **Package** (~34 nodes)
   - Organizational structure
   - Architectural boundaries
   - **Git Tracking**: YES - Track structure changes
   - **Properties to track**: `id`, `name`, `comment`, `visibility`

3. **Requirement** (SysML)
   - Requirements definition
   - Critical for traceability
   - **Git Tracking**: YES - Track every change
   - **Properties to track**: `id`, `name`, `text`, `priority`, `status`, `requirement_type`

4. **Interface** 
   - Contract definitions between components
   - **Git Tracking**: YES - Track interface changes
   - **Properties to track**: `id`, `name`, `comment`, `visibility`

5. **Component**
   - System modularization
   - **Git Tracking**: YES - Track component structure
   - **Properties to track**: `id`, `name`, `comment`, `visibility`, `isAbstract`

### **Tier 2: Important Design Details** (SHOULD version)

These represent important design decisions but change less frequently:

6. **Property** (~1,217 nodes)
   - Attributes of classes
   - **Git Tracking**: YES - Track attribute changes
   - **Properties to track**: `id`, `name`, `type`, `visibility`, `multiplicity`, `default`, `isDerived`, `isReadOnly`

7. **Operation** 
   - Methods/behaviors
   - **Git Tracking**: YES - Track method signatures
   - **Properties to track**: `id`, `name`, `visibility`, `isAbstract`, `isStatic`, `parameters`

8. **Port** (~188 nodes)
   - Interface connection points
   - **Git Tracking**: YES - Track interface changes
   - **Properties to track**: `id`, `name`, `type`, `visibility`

9. **Association** (~502 nodes)
   - Relationships between classes
   - **Git Tracking**: YES - Track relationship changes
   - **Properties to track**: `id`, `name`, `memberEnd`, `navigableOwnedEnd`, `aggregation`

10. **Constraint** (~74 nodes)
    - Design rules and invariants
    - **Git Tracking**: YES - Track rule changes
    - **Properties to track**: `id`, `name`, `body`, `language`, `constrainedElement`

11. **Block** (SysML)
    - SysML blocks for system design
    - **Git Tracking**: YES - Track system structure
    - **Properties to track**: `id`, `name`, `comment`, `visibility`

### **Tier 3: Behavioral Models** (SHOULD version)

12. **StateMachine**
    - State machine definitions
    - **Git Tracking**: YES - Track state machine changes
    - **Properties to track**: `id`, `name`, `region`, `submachine`

13. **State**
    - Individual states
    - **Git Tracking**: YES - Track state changes
    - **Properties to track**: `id`, `name`, `entry`, `exit`, `doActivity`

14. **Activity**
    - Activity diagrams
    - **Git Tracking**: YES - Track activity changes
    - **Properties to track**: `id`, `name`, `node`, `edge`

15. **UseCase**
    - Use case specifications
    - **Git Tracking**: YES - Track requirements
    - **Properties to track**: `id`, `name`, `description`, `actors`

### **Tier 4: Documentation** (OPTIONAL version)

16. **Comment** (~854 nodes)
    - Documentation and notes
    - **Git Tracking**: OPTIONAL - May change frequently
    - **Consideration**: Track only if attached to versioned artifacts
    - **Properties to track**: `id`, `body`, `annotatedElement`

---

## ❌ Non-Versionable Nodes (Should NOT Track in Git)

### **Derived/Computed Data**

These are generated from other data and shouldn't be version-controlled:

1. **GitCommit** (NEW - proposed for Git integration)
   - Represents Git commits
   - **Git Tracking**: NO - This IS the version metadata
   - **Purpose**: Track which commit modified which artifacts

2. **InstanceSpecification** (~118 nodes)
   - Runtime instances
   - **Git Tracking**: NO - Runtime data, not design
   - **Exception**: Unless representing test fixtures

3. **Slot** (~119 nodes)
   - Runtime property values
   - **Git Tracking**: NO - Runtime data
   - **Exception**: Unless representing configuration

### **Metadata/Auxiliary Data**

These support other nodes but aren't primary artifacts:

4. **Parameter** 
   - Operation parameters
   - **Git Tracking**: NO - Tracked as part of Operation
   - **Reason**: Already captured in operation signature

5. **EnumerationLiteral**
   - Enum values
   - **Git Tracking**: NO - Tracked as part of Enumeration
   - **Reason**: Part of enumeration definition

6. **PrimitiveType**
   - Basic types (int, string, etc.)
   - **Git Tracking**: NO - Standard library types
   - **Reason**: Not project-specific

7. **Stereotype**
   - UML profile extensions
   - **Git Tracking**: NO - Profile definition, not model
   - **Exception**: Track if custom profiles

---

## 🏗️ Graph Schema Extensions for Git Integration

### New Node Type: GitCommit

```cypher
CREATE CONSTRAINT git_commit_sha IF NOT EXISTS
FOR (gc:GitCommit) REQUIRE gc.sha IS UNIQUE;

// GitCommit node structure
CREATE (gc:GitCommit {
  sha: 'a1b2c3d4e5f6',              // Git commit SHA
  short_sha: 'a1b2c3d',              // Short SHA for display
  author: 'john.doe@example.com',   // Commit author
  author_name: 'John Doe',           // Author display name
  committer: 'john.doe@example.com', // Committer (if different)
  branch: 'feature/brake-system',    // Git branch
  timestamp: datetime(),             // Commit timestamp
  message: 'feat(brakes): update brake caliper material', // Commit message
  files_changed: ['data/raw/Domain_model.xmi'], // Changed files
  synced_at: datetime(),             // When synced to Neo4j
  sync_status: 'completed',          // completed, failed, partial
  artifacts_modified: 15             // Count of modified artifacts
})
```

### Enhanced Artifact Properties

All **versionable nodes** should have these properties:

```cypher
// Add to all Tier 1 & Tier 2 nodes
{
  // Existing properties...
  id: '_CLASS_ABC123',
  name: 'BrakeCaliper',
  
  // NEW: Git metadata
  git_sha: 'a1b2c3d4e5f6',          // Current commit SHA
  git_author: 'john.doe@example.com', // Last modifier
  git_branch: 'main',                 // Source branch
  git_timestamp: datetime(),          // Last modification time
  git_file: 'data/raw/Domain_model.xmi', // Source file
  
  // NEW: Version tracking
  version: 5,                         // Version number (incremental)
  version_chain: '_CLASS_ABC123_v5',  // Version identifier
  is_latest: true,                    // Is this the latest version?
  
  // Existing timestamps
  createdAt: datetime(),
  modifiedAt: datetime(),
  loadSource: 'Domain_model.xmi'
}
```

### New Relationships

```cypher
// GitCommit modified artifact
(gc:GitCommit)-[:MODIFIED {
  change_type: 'updated',  // created, updated, deleted
  timestamp: datetime(),
  diff_summary: 'Changed material property from steel to titanium'
}]->(artifact)

// Version history
(older:Class)-[:VERSION_OF {
  from_sha: 'abc123',
  to_sha: 'def456',
  from_version: 4,
  to_version: 5,
  change_type: 'property_update',
  timestamp: datetime()
}]->(newer:Class)

// Artifact traced in commit
(artifact)-[:TRACED_IN {
  git_sha: 'a1b2c3d4',
  traced_at: datetime()
}]->(gc:GitCommit)
```

---

## 📋 Node Identification Criteria

### Should a Node Type be Git-Versioned?

Use this decision matrix:

| Criteria | Yes = +1 | No = 0 |
|----------|----------|--------|
| **Represents engineering design decision** | ✅ | ❌ |
| **Created/modified by engineer (not tool)** | ✅ | ❌ |
| **Stored in XMI/model files** | ✅ | ❌ |
| **Required for traceability** | ✅ | ❌ |
| **Changes affect system behavior** | ✅ | ❌ |
| **Part of deliverable artifacts** | ✅ | ❌ |
| **Compliance/audit requirement** | ✅ | ❌ |
| **NOT derived/computed** | ✅ | ❌ |

**Score ≥ 5**: MUST version (Tier 1)  
**Score 3-4**: SHOULD version (Tier 2-3)  
**Score ≤ 2**: DON'T version

### Example Applications

#### Class Node
- Engineering design decision: ✅ (+1)
- Created by engineer: ✅ (+1)
- Stored in XMI: ✅ (+1)
- Required for traceability: ✅ (+1)
- Changes affect behavior: ✅ (+1)
- Part of deliverables: ✅ (+1)
- Compliance requirement: ✅ (+1)
- Not derived: ✅ (+1)
- **SCORE: 8/8 → TIER 1 (MUST version)**

#### Slot Node (Instance Value)
- Engineering design decision: ❌ (0)
- Created by engineer: ❌ (runtime) (0)
- Stored in XMI: ✅ (+1)
- Required for traceability: ❌ (0)
- Changes affect behavior: ❌ (runtime only) (0)
- Part of deliverables: ❌ (0)
- Compliance requirement: ❌ (0)
- Not derived: ❌ (runtime data) (0)
- **SCORE: 1/8 → DON'T version**

#### Comment Node
- Engineering design decision: ⚠️ (documentation) (+0.5)
- Created by engineer: ✅ (+1)
- Stored in XMI: ✅ (+1)
- Required for traceability: ⚠️ (sometimes) (+0.5)
- Changes affect behavior: ❌ (0)
- Part of deliverables: ⚠️ (sometimes) (+0.5)
- Compliance requirement: ⚠️ (if formal docs) (+0.5)
- Not derived: ✅ (+1)
- **SCORE: 5/8 → TIER 4 (OPTIONAL version)**

---

## 🎯 Implementation Strategy

### Phase 1: Core Design Artifacts (Week 1)
**Focus**: Class, Package, Requirement, Interface, Component

```python
# In sync_models_to_graph.py
VERSIONABLE_NODE_TYPES = {
    'Class': {'tier': 1, 'track_properties': ['id', 'name', 'comment', 'visibility', 'isAbstract']},
    'Package': {'tier': 1, 'track_properties': ['id', 'name', 'comment', 'visibility']},
    'Requirement': {'tier': 1, 'track_properties': ['id', 'name', 'text', 'priority', 'status']},
    'Interface': {'tier': 1, 'track_properties': ['id', 'name', 'comment', 'visibility']},
    'Component': {'tier': 1, 'track_properties': ['id', 'name', 'comment', 'visibility', 'isAbstract']},
}

def should_version_node(node_label: str, node_properties: dict) -> bool:
    """Determine if node should be Git-versioned"""
    return node_label in VERSIONABLE_NODE_TYPES
```

### Phase 2: Design Details (Week 2)
**Add**: Property, Operation, Port, Association, Constraint, Block

### Phase 3: Behavioral Models (Week 3)
**Add**: StateMachine, State, Activity, UseCase

### Phase 4: Documentation (Week 4)
**Optional**: Comment (if needed for compliance)

---

## 🔍 Detection Queries

### Find All Versionable Nodes
```cypher
// Get nodes by type
MATCH (n)
WHERE labels(n)[0] IN [
  'Class', 'Package', 'Requirement', 'Interface', 'Component',
  'Property', 'Operation', 'Port', 'Association', 'Constraint', 'Block',
  'StateMachine', 'State', 'Activity', 'UseCase'
]
RETURN labels(n)[0] AS type, count(n) AS count
ORDER BY count DESC
```

### Find Nodes Modified in Specific XMI File
```cypher
MATCH (n)
WHERE n.loadSource CONTAINS 'Domain_model.xmi'
  AND labels(n)[0] IN ['Class', 'Package', 'Requirement']
RETURN n.id, n.name, labels(n)[0] AS type
LIMIT 100
```

### Find Nodes Without Git Metadata (Need Initial Sync)
```cypher
MATCH (n)
WHERE labels(n)[0] IN ['Class', 'Package', 'Requirement']
  AND n.git_sha IS NULL
RETURN labels(n)[0] AS type, count(n) AS unversioned_count
```

---

## 📊 Summary Statistics

### Estimated Versionable Nodes (Based on Current Graph)

| Tier | Node Types | Approx. Count | Priority |
|------|------------|---------------|----------|
| **Tier 1** | Class, Package, Requirement, Interface, Component | ~177+ | MUST |
| **Tier 2** | Property, Operation, Port, Association, Constraint, Block | ~1,679+ | SHOULD |
| **Tier 3** | StateMachine, State, Activity, UseCase | ~50+ | SHOULD |
| **Tier 4** | Comment | ~854 | OPTIONAL |
| **TOTAL** | 14 node types | **~2,760 nodes** | - |

### Non-Versionable Nodes

| Category | Node Types | Approx. Count | Reason |
|----------|------------|---------------|--------|
| **Runtime** | InstanceSpecification, Slot | ~237 | Runtime data |
| **Metadata** | Parameter, EnumerationLiteral | ~100+ | Part of parent |
| **System** | GitCommit (new) | 0 | Version metadata |
| **TOTAL** | - | **~337+ nodes** | - |

---

## ✅ Validation Checklist

Before implementing Git integration:

- [ ] Confirm all Tier 1 node types exist in current graph
- [ ] Verify XMI files contain these node types
- [ ] Test XMI parser correctly identifies node types
- [ ] Add `git_sha` index to Neo4j
- [ ] Create GitCommit constraint
- [ ] Update SemanticXMILoader to accept git metadata
- [ ] Implement version detection logic
- [ ] Test with sample XMI file change
- [ ] Document exclusions (non-versionable nodes)
- [ ] Create migration script for existing nodes

---

## 🚀 Next Steps

1. **Review this document** with architecture team
2. **Confirm node type priorities** (Tier 1 vs Tier 2)
3. **Create indexes** for `git_sha` on versionable nodes
4. **Update semantic_loader.py** to add git metadata
5. **Implement sync script** with node filtering
6. **Test with Domain_model.xmi** file

---

**Status**: Ready for review and implementation planning.
