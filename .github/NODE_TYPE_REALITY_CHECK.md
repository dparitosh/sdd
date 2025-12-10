# Node Type Comparison: Documentation vs. Current Database

## 📊 Summary

**Current Database** (from API_SCHEMA_ALIGNMENT.md & GRAPH_SMRL_ALIGNMENT.md):
- **12 node types**, 1,893-3,249 total nodes
- **6-9 relationship types**, 3,021-10,024 total relationships

**Git Identification Document** (proposed):
- **30+ node types** listed (many not present in database)
- **14 node types** prioritized for Git versioning

---

## ✅ Node Types PRESENT in Current Database

### Actually in Database (12 types):

| Node Type | Count | In Git Doc? | Should Version? |
|-----------|-------|-------------|-----------------|
| **Property** | 1,217 | ✅ Yes | ✅ Tier 2 (SHOULD) |
| **Port** | 188 | ✅ Yes | ✅ Tier 2 (SHOULD) |
| **Class** | 143 | ✅ Yes | ✅ Tier 1 (MUST) |
| **Slot** | 119 | ✅ Yes | ❌ NO (Runtime) |
| **InstanceSpecification** | 118 | ✅ Yes | ❌ NO (Runtime) |
| **Constraint** | 74 | ✅ Yes | ✅ Tier 2 (SHOULD) |
| **Package** | 34 | ✅ Yes | ✅ Tier 1 (MUST) |
| **Comment** | 854 | ✅ Yes | ⚠️ Tier 4 (OPTIONAL) |
| **Association** | 502 | ✅ Yes | ✅ Tier 2 (SHOULD) |
| Component | 0 | ✅ Yes | ✅ Tier 1 (MUST)* |
| Interface | 0 | ✅ Yes | ✅ Tier 1 (MUST)* |
| Requirement | 0 | ✅ Yes | ✅ Tier 1 (MUST)* |

*Node type exists in schema but has 0 instances

### Summary:
- ✅ **7 types with data** should be versioned (Class, Package, Property, Port, Association, Constraint, Comment)
- ❌ **2 types with data** should NOT be versioned (Slot, InstanceSpecification)
- ⚠️ **3 types with 0 instances** (Component, Interface, Requirement) - defined but unused

---

## ❌ Node Types NOT PRESENT in Database

### Listed in Git Doc but NOT in Database:

**Tier 1 (Critical):**
- ❌ **Model** - Not found (may be implied by root Package)
- ⚠️ **Requirement** - Schema exists, 0 instances
- ⚠️ **Interface** - Schema exists, 0 instances
- ⚠️ **Component** - Schema exists, 0 instances
- ❌ **Block** (SysML) - Not found

**Tier 2 (Important):**
- ❌ **Operation** - Not found
- ❌ **Parameter** - Schema exists, 0 instances?
- ❌ **DataType** - Not found
- ❌ **Enumeration** - Not found
- ❌ **EnumerationLiteral** - Not found
- ❌ **PrimitiveType** - Not found
- ❌ **Stereotype** - Not found

**Tier 3 (Behavioral):**
- ❌ **StateMachine** - Not found
- ❌ **State** - Not found
- ❌ **Activity** - Not found
- ❌ **Action** - Not found
- ❌ **Transition** - Not found
- ❌ **UseCase** - Not found
- ❌ **Actor** - Not found
- ❌ **Interaction** - Not found
- ❌ **Lifeline** - Not found
- ❌ **Message** - Not found

**SysML Specific:**
- ❌ **ValueType** - Not found
- ❌ **FlowPort** - Not found
- ❌ **InterfaceBlock** - Not found

---

## 🎯 Revised Git Version Strategy (Based on Actual Database)

### **What We CAN Version (Present with Data):**

#### Tier 1 - MUST Version:
1. ✅ **Class** (143 nodes) - Core design elements
2. ✅ **Package** (34 nodes) - Architecture structure

#### Tier 2 - SHOULD Version:
3. ✅ **Property** (1,217 nodes) - Attributes  
4. ✅ **Port** (188 nodes) - Interface points
5. ✅ **Association** (502 nodes) - Relationships
6. ✅ **Constraint** (74 nodes) - Design rules

#### Tier 4 - OPTIONAL Version:
7. ⚠️ **Comment** (854 nodes) - Documentation (if needed for compliance)

#### DO NOT Version:
- ❌ **Slot** (119 nodes) - Runtime data
- ❌ **InstanceSpecification** (118 nodes) - Runtime instances

### **Total Versionable Nodes in Current Database:**
- **Tier 1**: 177 nodes (Class + Package)
- **Tier 2**: 1,981 nodes (Property + Port + Association + Constraint)
- **Tier 4**: 854 nodes (Comment - optional)
- **TOTAL**: ~2,158-3,012 versionable nodes (depending on Comment inclusion)

---

## ⚠️ Implications for Git Integration

### What This Means:

1. **Simplified Implementation** ✅
   - Only need to handle **7-9 node types** (not 30+)
   - Reduced complexity for Git integration
   - Easier to test and validate

2. **Missing Behavioral Models** ⚠️
   - No StateMachine, Activity, UseCase nodes
   - Current XMI only contains structural models
   - May need different XMI files for behavioral models

3. **Missing SysML Blocks** ⚠️
   - No `sysml:Block`, `sysml:Requirement` nodes with data
   - Current model is UML-focused, not SysML
   - May need SysML-specific XMI files

4. **Empty Schema Types** ⚠️
   - Component, Interface, Requirement defined but unused
   - Either:
     - Not in current XMI files
     - Parser not extracting them
     - Not applicable to current domain model

### Recommendations:

#### Option 1: Version Current Database (Pragmatic)
```python
# Actual versionable types
VERSIONABLE_NODE_TYPES = {
    # Tier 1 - Core design
    'Class': {'tier': 1, 'count': 143},
    'Package': {'tier': 1, 'count': 34},
    
    # Tier 2 - Design details
    'Property': {'tier': 2, 'count': 1217},
    'Port': {'tier': 2, 'count': 188},
    'Association': {'tier': 2, 'count': 502},
    'Constraint': {'tier': 2, 'count': 74},
    
    # Tier 4 - Optional documentation
    'Comment': {'tier': 4, 'count': 854},  # Optional
}

# Total: 2,158 nodes (or 3,012 with Comments)
```

#### Option 2: Wait for Full Model (Ideal)
- Import behavioral models (StateMachine, Activity, etc.)
- Import SysML models (Block, Requirement, etc.)
- Import interface/component models
- Then implement Git versioning for all types

#### Option 3: Hybrid Approach (Recommended)
- **Phase 1**: Version current 7 types (Class, Package, Property, Port, Association, Constraint, Comment)
- **Phase 2**: Add behavioral models when available
- **Phase 3**: Add SysML models when available

---

## 📝 Updated Node Identification Checklist

### Currently in Database ✅
- [x] Class (143 nodes)
- [x] Package (34 nodes)
- [x] Property (1,217 nodes)
- [x] Port (188 nodes)
- [x] Association (502 nodes)
- [x] Constraint (74 nodes)
- [x] Comment (854 nodes)
- [x] Slot (119 nodes) - Don't version
- [x] InstanceSpecification (118 nodes) - Don't version

### Not in Current Database ❌
- [ ] Operation (0 nodes)
- [ ] Parameter (0 nodes?)
- [ ] Component (0 nodes - schema only)
- [ ] Interface (0 nodes - schema only)
- [ ] Requirement (0 nodes - schema only)
- [ ] StateMachine, State, Activity, UseCase (not present)
- [ ] Actor, Interaction, Lifeline, Message (not present)
- [ ] DataType, Enumeration, PrimitiveType (not present)
- [ ] Block, ValueType, FlowPort (SysML - not present)

---

## 🚀 Action Items

1. **Verify Database Schema** ✅
   - Confirmed: 12 node types in database
   - 7 types have data and should be versioned
   - 2 types have data but should NOT be versioned
   - 3 types are empty (Component, Interface, Requirement)

2. **Update Git Integration Design** 
   - Focus on 7 actual node types
   - Remove references to non-existent types
   - Update count estimates

3. **Test XMI Parser**
   - Check if current XMI files contain other node types
   - Verify parser correctly extracts all available types
   - Check for behavioral/SysML models in XMI

4. **Plan for Missing Types**
   - Document what's missing
   - Identify source for behavioral models
   - Plan SysML model integration

---

**Conclusion**: The Git identification document lists many node types that **don't exist** in the current database. We should focus Git integration on the **7 types that actually have data**, with a plan to expand as more model types are added.
