# MBSE Knowledge Graph - Business User Guide

## 📋 Table of Contents
1. [What is This Application?](#what-is-this-application)
2. [Who Should Use This?](#who-should-use-this)
3. [Key Features & Benefits](#key-features--benefits)
4. [Getting Started](#getting-started)
5. [User Interface Overview](#user-interface-overview)
6. [Step-by-Step Usage Guide](#step-by-step-usage-guide)
7. [Common Business Use Cases](#common-business-use-cases)
8. [Understanding the Data](#understanding-the-data)
9. [API Integration & Advanced Features](#api-integration--advanced-features)
10. [Tips for Effective Use](#tips-for-effective-use)
11. [Troubleshooting](#troubleshooting)
12. [Support & Resources](#support--resources)

---

## What is This Application?

The **MBSE Knowledge Graph** is a web-based visualization and exploration tool for Model-Based Systems Engineering (MBSE) data. It transforms complex technical models from XMI files (ISO 10303 SMRL standard) into an interactive, searchable knowledge graph that makes relationships and dependencies visible and understandable.

### In Simple Terms:
Think of it as **Google Maps for your engineering models** – instead of navigating streets, you're exploring the relationships between systems, components, requirements, and their properties.

### What Problem Does It Solve?
- **Complexity Management**: Large engineering models with thousands of components are hard to understand
- **Relationship Discovery**: Finding how different parts of a system connect is time-consuming
- **Impact Analysis**: Understanding what's affected when making changes requires extensive manual review
- **Knowledge Transfer**: Onboarding new team members to complex systems takes months
- **Compliance & Traceability**: Tracking requirements and constraints across the system is challenging

---

## Who Should Use This?

### Primary Users:
- **Systems Engineers**: Navigate system architectures, trace requirements, analyze dependencies
- **Project Managers**: Understand project scope, assess change impacts, track relationships
- **Technical Leads**: Review model quality, verify completeness, identify gaps
- **Quality Assurance**: Validate models against standards, check constraint compliance
- **Business Analysts**: Understand system structure without deep technical knowledge
- **New Team Members**: Learn existing system architecture quickly

### Technical Knowledge Required:
✅ **None Required** - The UI is designed for non-technical users  
✅ **Helpful but Optional** - Basic understanding of systems engineering concepts  
✅ **Advanced Users** - Can write custom queries for deeper analysis

---

## Key Features & Benefits

### 🔍 **Interactive Navigation**
- **Browse by Package**: Explore your model organized by logical packages
- **Search Everything**: Find any class, property, or constraint instantly
- **Click-to-Explore**: Navigate relationships by clicking on connected items
- **Visual Hierarchy**: Tree-view shows parent-child relationships clearly

### 📊 **Rich Visualizations**
- **Graph View**: See components and their connections as an interactive network
- **Property Tables**: View all attributes, types, and multiplicity in structured tables
- **Relationship Explorer**: Trace inheritance, composition, and associations
- **Statistics Dashboard**: Get quick insights (total nodes, relationships, node types)

### 🔗 **Relationship Discovery**
- **Generalizations**: See inheritance hierarchies (which classes extend others)
- **Associations**: View connections between components with clear "Property1 ↔ Property2" labels
- **Compositions**: Understand containment (which packages contain which elements)
- **Dependencies**: Track constraints and requirements linked to components

### 🎯 **Business Value**
- **Faster Understanding**: Reduce onboarding time from weeks to days
- **Better Decisions**: See impact before making changes
- **Quality Assurance**: Catch missing relationships and incomplete models
- **Compliance**: Export data for audits and documentation
- **Integration Ready**: REST API for connecting to simulation tools, PLM systems

---

## Getting Started

### Prerequisites
✅ **Web Browser** (Chrome, Firefox, Edge, Safari)  
✅ **Network Access** to the server running the application  
✅ **No Installation** required on your computer

### Access the Application

**Option 1: Local Development**
```
URL: http://127.0.0.1:5000
```

**Option 2: Cloud/Remote Server**
```
URL: https://[your-server-domain]:5000
```

### First Login
1. Open the URL in your web browser
2. You'll see the **MBSE Knowledge Graph Viewer** home page
3. The application loads automatically – no login required for viewing
4. All data is read-only for business users

---

## User Interface Overview

### Main Layout

```
┌─────────────────────────────────────────────────────┐
│  MBSE Knowledge Graph Viewer                        │
│  ISO 10303 SMRL Domain Model Explorer               │
└─────────────────────────────────────────────────────┘
┌──────────────┬──────────────────────────────────────┐
│              │  Packages | Classes | Artifacts |    │
│   Sidebar    │  Search | Graph | REST API           │
│              ├──────────────────────────────────────┤
│   Stats      │                                      │
│   Filters    │         Content Area                 │
│   Actions    │    (Shows selected tab content)      │
│              │                                      │
└──────────────┴──────────────────────────────────────┘
```

### Navigation Tabs

| Tab | Purpose | Best For |
|-----|---------|----------|
| **Packages** | Browse model organized by logical groupings | Exploring high-level structure |
| **Classes** | View all system components/classes | Finding specific components |
| **Artifacts** | Browse all elements by type (Classes, Associations, Packages, etc.) | Comprehensive exploration |
| **Search** | Find anything by name | Quick lookups |
| **Graph** | Visual network view | Understanding relationships |
| **REST API** | Developer documentation | Integration tasks |

---

## Step-by-Step Usage Guide

### 🎯 Task 1: Explore the Model Structure

**Goal**: Understand what's in your model

1. **Click the "Packages" tab** at the top
2. You'll see a tree of packages (folders of related components)
3. **Click the ► arrow** next to any package to expand it
4. Notice the colored badges showing item counts (e.g., "5 classes", "3 packages")
5. **Click on a package name** to see its details in the right panel

**What You'll See**:
- Package name and ID
- Description/documentation
- Contained elements (sub-packages, classes)
- Relationships to other packages

---

### 🎯 Task 2: Find a Specific Component

**Goal**: Locate a system component quickly

1. **Click the "Search" tab**
2. **Type a keyword** in the search box (e.g., "Person", "Approval", "Vehicle")
3. Results appear instantly as you type
4. You'll see:
   - **Type badge** (Class, Package, Association)
   - **Name** of the item
   - **ID** for reference
5. **Click any result** to view full details

**Search Tips**:
- Search is case-insensitive ("person" finds "Person")
- Partial matches work ("Appr" finds "Approval")
- Search looks in names only (not descriptions)

---

### 🎯 Task 3: Understand a Component's Properties

**Goal**: See what attributes a component has

1. Navigate to a Class (via Packages or Search)
2. **Click on the class name** to view details
3. In the details panel, look for:

**Properties Table**:
```
┌───────────────┬──────────────┬──────────────┬─────────────┐
│ Property Name │ Type         │ Multiplicity │ Visibility  │
├───────────────┼──────────────┼──────────────┼─────────────┤
│ name          │ String       │ 1..1         │ public      │
│ age           │ Integer      │ 0..1         │ private     │
│ address       │ Address      │ 1..*         │ public      │
└───────────────┴──────────────┴──────────────┴─────────────┘
```

**Understanding Multiplicity**:
- `1..1` = Exactly one (required)
- `0..1` = Optional (zero or one)
- `1..*` = One or more (required, multiple allowed)
- `0..*` = Zero or more (optional, multiple allowed)

---

### 🎯 Task 4: Trace Relationships

**Goal**: See how components connect to each other

1. **View a class** (as in Task 3)
2. Look for the **"Relationships"** section
3. You'll see different relationship types:

**Generalizations (Inheritance)**:
```
Manager ──extends──> Person
```
- Manager inherits all properties from Person
- "Is-a" relationship (Manager *is a* Person)

**Associations (Connections)**:
```
Person ↔ Organization
```
- Shows connections between classes
- Format: "[Property1] ↔ [Property2]"
- Example: "Person's employer ↔ Organization's employees"

**Compositions (Containment)**:
```
Package "Models" ──contains──> Class "Vehicle"
```
- Shows ownership/containment
- "Has-a" relationship (Package *has* Classes)

4. **Click on any related item** to navigate to it

---

### 🎯 Task 5: Visual Graph Exploration

**Goal**: See the big picture of connections

1. **Click the "Graph" tab**
2. **Select visualization type**:
   - **Package Hierarchy**: Shows how packages nest
   - **Class Relationships**: Shows classes and their connections
   - **Full Graph**: Everything together (can be large)
3. **Interact with the graph**:
   - **Hover** over nodes to see details
   - **Click** nodes to highlight connections
   - **Drag** nodes to rearrange
   - **Zoom** with mouse wheel
   - **Pan** by dragging background

**Reading the Graph**:
- **Circles/Boxes** = Components (Classes, Packages)
- **Lines** = Relationships
- **Colors** = Different types (blue=Class, green=Package, etc.)
- **Arrows** = Direction (from child to parent, from part to whole)

---

### 🎯 Task 6: Browse All Components by Type

**Goal**: See all items of a specific type

1. **Click the "Artifacts" tab**
2. **Select a filter** from the dropdown:
   - **All Types**: Everything
   - **Class**: System components
   - **Association**: Relationships between components
   - **Package**: Organizational containers
   - **Property**: Attributes of classes
   - **Constraint**: Rules and restrictions
3. **View the filtered list** in tree format
4. **Click any item** to see details

**Association Display**:
When you see Associations, they display as:
```
[Approval] ↔ ActualApprover
```
This means:
- `[Approval]` = The type on one side (brackets mean unnamed property)
- `ActualApprover` = Named property on the other side
- `↔` = Bidirectional relationship

---

## Common Business Use Cases

### 📌 Use Case 1: Impact Analysis

**Scenario**: "We need to modify the Person class. What else might be affected?"

**Steps**:
1. Search for "Person" in the Search tab
2. Click on Person class to view details
3. Review the **Relationships** section:
   - See which classes **extend** Person (will inherit changes)
   - See which classes **use** Person (via associations)
   - See which packages **contain** Person
4. Click on each related item to understand the depth of impact
5. **Document findings**: Export or screenshot relationship data

**Business Value**: Prevent unexpected breaks, estimate change effort accurately

---

### 📌 Use Case 2: Requirement Traceability

**Scenario**: "Show me all constraints related to the Approval workflow"

**Steps**:
1. Click **Artifacts** tab
2. Filter by **Constraint** type
3. Search/scroll for approval-related constraints
4. Click each constraint to see:
   - Which classes it applies to
   - The constraint logic/rules
   - Related documentation
5. Navigate to connected classes via relationships

**Business Value**: Compliance verification, audit preparation, requirement coverage

---

### 📌 Use Case 3: Onboarding New Team Members

**Scenario**: "Help a new engineer understand the system architecture"

**Steps**:
1. Start with **Packages** tab – show top-level organization
2. Walk through each major package:
   - Expand to show contained classes
   - Explain the purpose (based on names/descriptions)
3. Pick a key class (e.g., "Vehicle") and show:
   - Its properties (attributes it has)
   - Its generalizations (what it inherits from)
   - Its associations (what it connects to)
4. Use **Graph** tab to show visual big picture
5. Encourage self-exploration using Search

**Business Value**: Reduce onboarding time from weeks to days

---

### 📌 Use Case 4: Model Completeness Check

**Scenario**: "Verify all classes have proper documentation and properties"

**Steps**:
1. Go to **Statistics** (on homepage)
2. Note total number of Classes
3. Click **Artifacts** → Filter by **Class**
4. Scroll through classes looking for:
   - ❌ Empty descriptions
   - ❌ Classes with zero properties
   - ❌ Classes with no relationships (orphaned)
5. Document incomplete items for follow-up

**Business Value**: Quality assurance, model maturity assessment

---

### 📌 Use Case 5: Change Request Validation

**Scenario**: "Engineering proposes adding a new class. Check if it fits the model."

**Steps**:
1. Search for **similar existing classes**
2. Check if the proposed class:
   - Duplicates an existing class (name collision)
   - Should inherit from an existing class
   - Has naming consistent with conventions
3. Review the target **Package**:
   - Does it logically belong there?
   - What other classes are in that package?
4. Check **related associations**:
   - Are the proposed connections valid?
   - Do they already exist elsewhere?

**Business Value**: Prevent model duplication, maintain consistency

---

## Understanding the Data

### Data Source
The knowledge graph is built from **XMI files** (XML Metadata Interchange) following the **ISO 10303 SMRL** (Systems Modeling Representation Language) standard. This data typically comes from:
- Enterprise Architect
- MagicDraw/Cameo Systems Modeler
- IBM Rational Rhapsody
- Other UML/SysML modeling tools

### Current Model Statistics
Based on the loaded domain model (`Domain_model.xmi`):
- **3,249 Nodes** (components)
- **10,024 Relationships** (connections)
- **502 Associations** (relationships between classes)
- **Multiple Types**: Classes, Packages, Properties, Constraints, etc.

### Data Quality
✅ **Semantic Validation**: All data follows OMG UML/SysML metamodel  
✅ **Relationship Integrity**: All references are validated during loading  
✅ **Enhanced Display**: Association names improved from empty to descriptive  
✅ **Cloud Storage**: Data persisted in Neo4j Aura cloud database

---

## Tips for Effective Use

### 💡 Navigation Tips
1. **Use Search first** for specific lookups, then explore relationships
2. **Start broad, go narrow**: Begin with Packages, drill down to Classes
3. **Follow the relationships**: Click on related items to understand connections
4. **Use back button**: Browser back button works for navigation history
5. **Bookmark frequently used packages** in your browser

### 💡 Search Best Practices
- Search for **partial names** when you're not sure of exact spelling
- Use **distinctive terms** (e.g., "Approval" not "Class")
- Try **singular and plural** forms if you don't find results
- Search is **case-insensitive** – don't worry about capitalization

### 💡 Understanding Complex Relationships
- **[Brackets] in Association names** mean the property is unnamed, showing the type instead
- **Arrows in Graph view** point from child to parent (inheritance) or from part to whole (composition)
- **Multiplicity matters**: `0..1` means optional, `1..*` means required with multiple allowed

### 💡 Performance Tips
- **Filter early**: Use the Artifacts filters to reduce data displayed
- **Graph view caution**: Full graph visualization can be slow on large models
- **Search limits**: Only first 100 results shown by default (narrow your search if needed)
- **Refresh if slow**: Browser refresh (F5) reloads the page cleanly

---

## Troubleshooting

### ❓ "I can't find a component I know exists"

**Possible Causes**:
- Misspelled name in search
- Component has a different name than expected
- Component is of a different type (try Artifacts → All Types)

**Solutions**:
1. Try partial name search (e.g., "Appr" instead of "Approval")
2. Use Artifacts tab with "All Types" filter
3. Browse through Packages hierarchically
4. Check if it was recently added (may need data reload)

---

### ❓ "The Association name shows brackets like [Approval] ↔ ActualApprover"

**This is Normal**: In UML/SysML, Associations often have unnamed ends. The brackets show the **type** instead of a property name.

**How to Read**:
- `[Type]` = Unnamed property showing its type
- `PropertyName` = Named property
- `↔` = Bidirectional relationship

**Example**: `[Approval] ↔ ActualApprover` means:
- One side points to Approval type (unnamed)
- Other side is named ActualApprover property

---

### ❓ "Graph visualization is slow or unresponsive"

**Solutions**:
1. **Reduce graph size**: Use filtered views instead of "Full Graph"
2. **Close other browser tabs**: Free up memory
3. **Try different browser**: Chrome/Edge often perform better
4. **Use tabular views**: Classes/Packages tabs for large datasets
5. **Contact admin**: May need server performance tuning

---

### ❓ "I see duplicate class names"

**This is Normal**: Different packages can contain classes with the same name. Check the **full ID** (e.g., `_18_4_1_...`) to distinguish them.

**How to Identify**:
- Look at the **parent package** in the tree view
- Check the **full qualified name** in details
- Compare the **ID** property (unique identifier)

---

### ❓ "Some properties show '0..*' or '1..1' – what does this mean?"

**Multiplicity Explained**:
- `0..1` = Optional, maximum one (e.g., middle name)
- `1..1` = Exactly one, required (e.g., birth date)
- `0..*` = Zero or more (e.g., phone numbers)
- `1..*` = At least one, multiple allowed (e.g., email addresses)

---

## Support & Resources

### 📚 Additional Documentation
- **[README.md](README.md)**: Technical setup and architecture
- **[REST_API_GUIDE.md](REST_API_GUIDE.md)**: API integration for developers
- **[CYPHER_QUERIES.md](CYPHER_QUERIES.md)**: Advanced query examples
- **[ARTIFACTS_BROWSER.md](ARTIFACTS_BROWSER.md)**: Detailed artifact browsing guide

---

## API Integration & Advanced Features

### 🔌 REST API Access

The MBSE Knowledge Graph provides a comprehensive REST API for integration with external tools and automation. The API is built with **FastAPI** and provides interactive documentation.

#### Access the API Documentation
**OpenAPI/Swagger UI**: `http://[server-url]:5000/api/docs`

This interactive documentation allows you to:
- Browse all available endpoints
- See request/response schemas
- Test endpoints directly in your browser
- Download the OpenAPI specification

### Available API Endpoints

#### 🔐 Authentication (`/api/auth`)
Secure access to the API with JWT tokens:
- `POST /auth/login` - Authenticate and get access token
- `POST /auth/refresh` - Refresh expired token
- `POST /auth/logout` - Revoke token
- `GET /auth/verify` - Verify token validity
- `POST /auth/change-password` - Update password

#### 🏭 PLM Integration (`/api/plm`)
Product Lifecycle Management integration:
- `GET /plm/traceability` - Requirements traceability matrix
- `GET /plm/composition/{node_id}` - Bill of Materials hierarchy
- `GET /plm/impact/{node_id}` - Change impact analysis (upstream/downstream)
- `GET /plm/parameters` - Extract simulation parameters
- `GET /plm/constraints` - Get validation constraints

**Business Use Case**: Integrate with Windchill, Teamcenter, or other PLM systems to sync engineering data.

#### 🔬 Simulation Integration (`/api/simulation`)
Connect to simulation tools (Simulink, ANSYS, etc.):
- `GET /simulation/parameters` - Extract parameters with types and constraints
- `POST /simulation/validate` - Validate parameter values against constraints
- `GET /simulation/units` - Get unit definitions and conversions

**Business Use Case**: Automate parameter extraction for simulation runs, validate inputs before execution.

#### 📤 Data Export (`/api/export`)
Export graph data in multiple formats:
- `GET /export/graphml` - GraphML XML for Gephi, yEd, Cytoscape
- `GET /export/jsonld` - JSON-LD for semantic web applications
- `GET /export/csv` - CSV tables in ZIP archive
- `GET /export/step` - ISO STEP AP242 format for CAD systems

**Business Use Case**: Generate reports, import into analysis tools, create documentation.

#### 📜 Version Control (`/api/version`)
Track changes and manage versions:
- `GET /version/versions/{node_id}` - Get version history for a node
- `POST /version/diff` - Compare two versions or nodes
- `GET /version/history/{node_id}` - Full audit trail
- `POST /version/checkpoint` - Create graph snapshot

**Business Use Case**: Track model evolution, perform change audits, rollback to previous versions.

#### 📊 Core Operations (`/api`)
Basic CRUD and search:
- `GET /packages` - List all packages
- `GET /classes` - List classes with filtering
- `GET /search` - Full-text search across all nodes
- `GET /stats` - Database statistics
- `GET /health` - System health check

#### 🔗 Graph Queries (`/api/graph`)
Advanced graph operations:
- `GET /graph/traverse` - Graph traversal with depth control
- `GET /graph/neighbors` - Get connected nodes
- `POST /graph/path` - Find paths between nodes

#### 🌳 Hierarchy & Traceability (`/api/hierarchy`)
Navigate model structure:
- `GET /hierarchy/tree` - Full tree structure
- `GET /hierarchy/trace` - Bidirectional traceability

#### 📐 ISO Standard Compliance
- `GET /api/ap239` - ISO 10303-239 (Requirements Management)
- `GET /api/ap242` - ISO 10303-242 (CAD Integration)
- `GET /api/ap243` - ISO 10303-243 (Product Structures)
- `GET /api/v1` - SMRL v1 (ISO 10303-4443)

### API Usage Examples

#### Example 1: Search for Components
```bash
curl http://localhost:5000/api/search?q=motor
```

#### Example 2: Get Traceability Matrix
```bash
curl http://localhost:5000/api/plm/traceability?source_type=Requirement&depth=3
```

#### Example 3: Export to GraphML
```bash
curl -o graph.graphml "http://localhost:5000/api/export/graphml?limit=1000"
```

#### Example 4: Check System Health
```bash
curl http://localhost:5000/api/health
```

### Integration Scenarios

#### Scenario 1: Automated Testing Pipeline
Use `/api/simulation/validate` to validate parameter sets before running expensive simulations.

#### Scenario 2: PLM Synchronization
Query `/api/plm/composition/{id}` to sync BOM data with external PLM systems.

#### Scenario 3: Documentation Generation
Export via `/api/export/csv` to generate Excel reports for stakeholders.

#### Scenario 4: Change Management
Use `/api/plm/impact/{id}` to assess affected components before implementing changes.

#### Scenario 5: Compliance Audits
Query `/api/version/history/{id}` to generate change audit trails for certification.

### API Performance Notes
- **Pagination**: Most endpoints support `limit` and `offset` parameters
- **Caching**: Responses are cached for frequently accessed data
- **Rate Limiting**: 100 requests per minute per IP (configurable)
- **Timeouts**: 30-second timeout for complex queries



### 🔧 Technical Support
- **Server Issues**: Contact your IT administrator
- **Data Updates**: Contact the model manager to reload from updated XMI files
- **Feature Requests**: Submit via your organization's process

### 🎓 Training Resources
- **Self-Guided Tour**: Follow the Step-by-Step Usage Guide above
- **Video Tutorials**: (To be created by your organization)
- **Live Training**: Contact your systems engineering team

### 📞 Who to Contact
- **Data Questions**: Model owners/systems engineers
- **Access Issues**: IT support
- **Feature Enhancement**: Product owner/technical lead
- **Bug Reports**: Development team

---

## Quick Reference Card

### Essential Actions

| I Want To... | Click This | Then... |
|--------------|-----------|---------|
| Browse structure | **Packages** tab | Expand packages, click items |
| Find something specific | **Search** tab | Type name, click result |
| See component details | (Click any item name) | View properties/relationships |
| Understand connections | **Graph** tab | Select visualization type |
| Filter by type | **Artifacts** tab | Choose filter dropdown |
| Get statistics | (Scroll on home page) | View sidebar stats |

### Keyboard Shortcuts
- **Ctrl+F** (or Cmd+F): Browser find on page
- **F5**: Refresh page
- **Ctrl+Click**: Open link in new tab
- **Backspace**: Go back (in some browsers)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | Dec 2025 | FastAPI migration complete - Added comprehensive REST API documentation with 15 endpoint groups |
| 1.0 | Dec 2025 | Initial release with Association display enhancement |

---

## Glossary

**Association**: A relationship between two classes (e.g., Person works for Organization)  
**Class**: A system component or concept with properties and relationships  
**Constraint**: A rule or restriction applied to a class or property  
**Generalization**: Inheritance relationship (Child extends Parent)  
**Multiplicity**: How many instances are allowed (e.g., 0..1, 1..*)  
**Package**: A container/folder for organizing related classes  
**Property**: An attribute of a class (e.g., Person has "name" property)  
**XMI**: XML Metadata Interchange – standard format for model exchange  
**ISO 10303 SMRL**: International standard for systems modeling representation  

---

**Questions?** Contact your systems engineering team or refer to the technical documentation for advanced usage.

**Happy Exploring! 🚀**
