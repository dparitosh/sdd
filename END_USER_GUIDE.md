# MBSE Knowledge Graph - End User Guide

## Table of Contents
- [Getting Started](#getting-started)
- [Navigation Overview](#navigation-overview)
- [Dashboard](#dashboard)
- [Advanced Search](#advanced-search)
- [Query Editor](#query-editor)
- [Requirements Manager](#requirements-manager)
- [Traceability Matrix](#traceability-matrix)
- [PLM Integration](#plm-integration)
- [System Monitoring](#system-monitoring)
- [REST API Explorer](#rest-api-explorer)
- [Authentication](#authentication)
- [Tips & Best Practices](#tips--best-practices)

---

## Getting Started

### Accessing the Application

1. **Open your web browser** and navigate to:
   ```
   http://localhost:3001
   ```

2. **Backend API** is available at:
   ```
   http://localhost:5000
   ```

### System Requirements
- Modern web browser (Chrome, Firefox, Edge, Safari)
- JavaScript enabled
- Internet connection for Neo4j Cloud database

---

## Navigation Overview

The application uses a **left sidebar navigation** with the following main sections:

```
┌─────────────────────────────────────┐
│  🏠 Dashboard                       │
│  🔍 Advanced Search                 │
│  💻 Query Editor                    │
│  📋 Requirements Manager            │
│  🔗 Traceability Matrix            │
│  🔌 PLM Integration                │
│  📊 System Monitoring              │
│  🌐 REST API Explorer              │
│  🔐 Login / Profile                │
└─────────────────────────────────────┘
```

### Top Navigation Bar
- **Theme Toggle**: Switch between light/dark mode (moon/sun icon)
- **User Menu**: Access profile, settings, and logout (top-right corner)
- **Current Page Title**: Shows which page you're viewing

---

## Dashboard

**Purpose**: Overview of your MBSE knowledge graph with key statistics and quick access to recent items.

### Navigation Steps:
1. Click **"Dashboard"** in the left sidebar (or it loads by default)
2. View the statistics cards showing:
   - Total nodes in the graph
   - Total relationships
   - Node type distribution
   - Recent activities

### What You Can Do:
- **View Statistics**: See real-time counts of model elements
- **Quick Actions**: Access frequently used features via quick action buttons
- **Recent Items**: View recently accessed or modified elements
- **System Health**: Check database connection status at the top

### Common Actions:
```
📊 Statistics Cards → View graph metrics
🔍 Search Bar → Quick search across all elements
⚡ Quick Actions → Jump to common tasks
```

---

## Advanced Search

**Purpose**: Search and filter model elements with multiple criteria.

### Navigation Steps:
1. Click **"Advanced Search"** in the left sidebar
2. The search interface loads with filter options

### How to Search:

#### Basic Search:
1. **Enter Keywords**: Type in the main search box (e.g., "Motor", "Sensor")
2. **Click "Search"**: Results appear in the table below

#### Advanced Filtering:
1. **Select Node Type**: Choose from dropdown (Class, Association, Package, etc.)
2. **Add Properties**: Filter by specific attributes
3. **Set Date Range**: Filter by creation/modification date
4. **Apply Filters**: Click "Search" to see filtered results

### Search Results:
```
┌──────────────────────────────────────────────┐
│  Name          │  Type     │  Properties     │
├──────────────────────────────────────────────┤
│  Motor Control │  Class    │  [View Details] │
│  Temperature   │  Property │  [View Details] │
└──────────────────────────────────────────────┘
```

### Actions on Results:
- **Click Row**: View detailed information
- **Sort Columns**: Click column headers to sort
- **Export Results**: Use export button to download as CSV/JSON
- **View in Graph**: Click "View Graph" to see visual representation

---

## Query Editor

**Purpose**: Execute custom Cypher queries against the Neo4j database.

### Navigation Steps:
1. Click **"Query Editor"** in the left sidebar
2. The code editor interface loads

### How to Use:

#### Writing Queries:
1. **Type Your Query** in the editor:
   ```cypher
   MATCH (n:Class)
   RETURN n.name, n.id
   LIMIT 10
   ```

2. **Click "Run Query"** or press `Ctrl+Enter`

3. **View Results** in the results panel below

#### Query Templates:
1. Click **"Templates"** dropdown
2. Select a pre-built query:
   - Find all Classes
   - Show Relationships
   - Get Package Structure
   - Find Dependencies
3. Query auto-populates in editor

#### Example Queries:

**Find all Classes:**
```cypher
MATCH (n:Class)
RETURN n.name AS Name, n.visibility AS Visibility
LIMIT 25
```

**Find Relationships:**
```cypher
MATCH (a)-[r]->(b)
RETURN a.name, type(r), b.name
LIMIT 50
```

**Complex Query:**
```cypher
MATCH path = (req:Requirement)-[:TRACES_TO*1..3]->(comp:Component)
RETURN path
```

### Results View:
- **Table View**: Tabular display of query results
- **Graph View**: Visual network diagram
- **JSON View**: Raw JSON output
- **Export**: Download results in multiple formats

---

## Requirements Manager

**Purpose**: Manage system requirements, specifications, and their relationships.

### Navigation Steps:
1. Click **"Requirements Manager"** in the left sidebar
2. Requirements list loads with filtering options

### How to Use:

#### Viewing Requirements:
1. **Browse List**: Scroll through all requirements
2. **Filter by Status**: 
   - Draft
   - Approved
   - Implemented
   - Verified
3. **Filter by Priority**: High, Medium, Low
4. **Search**: Use search box to find specific requirements

#### Managing Requirements:

**Create New Requirement:**
1. Click **"+ New Requirement"** button
2. Fill in the form:
   - Requirement ID
   - Title
   - Description
   - Priority
   - Status
   - Owner
3. Click **"Save"**

**Edit Requirement:**
1. Click on a requirement in the list
2. Click **"Edit"** button
3. Modify fields
4. Click **"Save Changes"**

**Link Requirements:**
1. Select a requirement
2. Click **"Add Link"**
3. Choose relationship type:
   - Derives from
   - Refines
   - Traces to
4. Select target requirement
5. Click **"Link"**

### Requirements View:
```
┌─────────────────────────────────────────────┐
│  REQ-001  │  High  │  Approved              │
│  Motor Control System                       │
│  [Edit] [Link] [Delete] [View Traces]      │
├─────────────────────────────────────────────┤
│  REQ-002  │  Med   │  Draft                 │
│  Temperature Monitoring                     │
│  [Edit] [Link] [Delete] [View Traces]      │
└─────────────────────────────────────────────┘
```

---

## Traceability Matrix

**Purpose**: Visualize and analyze requirement traceability across the system.

### Navigation Steps:
1. Click **"Traceability Matrix"** in the left sidebar
2. Matrix view loads with source and target selection

### How to Use:

#### Setting Up Matrix:
1. **Select Source Type**: Choose starting elements (e.g., Requirements)
2. **Select Target Type**: Choose ending elements (e.g., Components)
3. **Set Depth**: How many hops to trace (1-5)
4. **Click "Generate Matrix"**

#### Reading the Matrix:
```
         │ Comp-A │ Comp-B │ Comp-C
─────────┼────────┼────────┼────────
REQ-001  │   ✓    │        │   ✓
REQ-002  │        │   ✓    │   ✓
REQ-003  │   ✓    │   ✓    │
```

- **✓ (Checkmark)**: Direct trace exists
- **~ (Tilde)**: Indirect trace exists
- **Empty**: No trace found

#### Matrix Actions:
- **Click Cell**: View detailed trace path
- **Export Matrix**: Download as Excel/CSV
- **Filter**: Show only specific requirement types
- **Highlight Gaps**: Identify missing traces
- **Coverage Report**: See traceability coverage percentage

### Analysis Features:
1. **Gap Analysis**: Identify untraceable requirements
2. **Coverage Metrics**: View traceability statistics
3. **Path Visualization**: See complete trace chains
4. **Impact Analysis**: Understand change propagation

---

## PLM Integration

**Purpose**: Connect and synchronize with Product Lifecycle Management systems.

### Navigation Steps:
1. Click **"PLM Integration"** in the left sidebar
2. PLM dashboard loads showing connector status

### Supported PLM Systems:
- **PTC Windchill**: Product data management
- **SAP PLM**: Enterprise PLM integration
- **Siemens Teamcenter**: Engineering data management

### How to Use:

#### Setting Up a Connector:

**Step 1: Configure Connection**
1. Click **"+ Add Connector"** button
2. Select PLM system type
3. Fill in connection details:
   - Server URL
   - Username/Password or API Key
   - Database name
4. Click **"Test Connection"**
5. If successful, click **"Save"**

**Step 2: Manage Connector**
```
┌─────────────────────────────────────────┐
│  Windchill Production                   │
│  Status: ● Connected                    │
│  Last Sync: 2 hours ago                 │
│  [Sync Now] [Configure] [Disconnect]    │
└─────────────────────────────────────────┘
```

#### Synchronization:

**Manual Sync:**
1. Select connector
2. Click **"Sync Now"** button
3. Choose direction:
   - PLM → Neo4j (Import)
   - Neo4j → PLM (Export)
   - Bi-directional
4. Monitor progress in sync status panel

**Automatic Sync:**
1. Click **"Configure"** on connector
2. Enable **"Auto Sync"**
3. Set sync interval (e.g., every 4 hours)
4. Choose sync direction
5. Click **"Save"**

#### Viewing Sync History:
1. Navigate to **"Sync History"** tab
2. View timeline of all sync operations
3. Click on sync entry to see:
   - Items synced
   - Success/failure status
   - Error logs (if any)
   - Conflict resolution

#### BOM Viewer:
1. Click **"BOM View"** tab
2. Select product/assembly
3. View hierarchical Bill of Materials
4. Expand/collapse levels
5. See properties and relationships

---

## System Monitoring

**Purpose**: Monitor system health, performance metrics, and resource usage.

### Navigation Steps:
1. Click **"System Monitoring"** in the left sidebar
2. Monitoring dashboard loads with real-time metrics

### Dashboard Sections:

#### 1. System Health
```
┌─────────────────────────────────┐
│  Backend:    ● Healthy          │
│  Database:   ● Connected        │
│  Response:   432ms avg          │
│  Uptime:     5h 23m             │
└─────────────────────────────────┘
```

#### 2. Performance Metrics
**Charts Display:**
- **Response Time**: Average API response time (line chart)
- **Request Rate**: Requests per minute (area chart)
- **Error Rate**: Percentage of failed requests
- **Database Queries**: Query performance metrics

**How to Read Charts:**
1. Hover over data points for exact values
2. Use time range selector (1h, 6h, 24h, 7d)
3. Click legend items to hide/show series

#### 3. Database Statistics
```
Total Nodes:          3,257
Total Relationships:  5,421
Node Types:           15
Average Query Time:   145ms
Cache Hit Rate:       89%
```

#### 4. Resource Usage
- **Memory Usage**: Current memory consumption
- **CPU Usage**: Processor utilization
- **Connection Pool**: Active/idle connections
- **Cache Statistics**: Hit/miss ratios

#### 5. Recent Activity Log
```
[12:34:56] Query executed: MATCH (n:Class) RETURN n
[12:34:55] User login: admin@example.com
[12:34:50] Export completed: requirements.csv
[12:34:45] Sync started: Windchill connector
```

### Setting Alerts:
1. Click **"Configure Alerts"** button
2. Set thresholds:
   - Response time > 1000ms
   - Error rate > 5%
   - Database unavailable
3. Choose notification method:
   - Email
   - Webhook
   - In-app notification
4. Click **"Save Alert Rules"**

---

## REST API Explorer

**Purpose**: Explore and test REST API endpoints interactively.

### Navigation Steps:
1. Click **"REST API Explorer"** in the left sidebar
2. API documentation loads with endpoint list

### How to Use:

#### Browsing Endpoints:
1. **Endpoint Categories** (left panel):
   - Core APIs
   - Requirements APIs
   - PLM APIs
   - Export APIs
   - Authentication APIs

2. **Click an Endpoint** to expand details

#### Testing an Endpoint:

**Example: Get All Classes**

**Step 1: Select Endpoint**
```
GET /api/v1/classes
```

**Step 2: Set Parameters**
- Query Parameters:
  - `limit`: 10
  - `offset`: 0
  - `name`: (optional filter)

**Step 3: Add Headers** (if needed)
- `Authorization`: Bearer <token>
- `Content-Type`: application/json

**Step 4: Execute Request**
1. Click **"Try It Out"** button
2. Click **"Execute"**

**Step 5: View Response**
```json
{
  "status": "success",
  "data": [
    {
      "id": "class_001",
      "name": "Motor",
      "type": "Class",
      "properties": {...}
    }
  ],
  "total": 143,
  "page": 1
}
```

#### Common API Workflows:

**1. Search Elements:**
```
POST /api/v1/search
Body: {
  "query": "motor",
  "type": "Class",
  "limit": 20
}
```

**2. Get Element Details:**
```
GET /api/v1/elements/{id}
```

**3. Create Relationship:**
```
POST /api/v1/relationships
Body: {
  "source_id": "elem_001",
  "target_id": "elem_002",
  "type": "DEPENDS_ON"
}
```

**4. Export Data:**
```
POST /api/v1/export
Body: {
  "format": "json",
  "type": "requirements",
  "filter": {...}
}
```

#### Understanding Responses:

**Success Response (200):**
```json
{
  "status": "success",
  "data": {...},
  "message": "Operation completed"
}
```

**Error Response (400/500):**
```json
{
  "status": "error",
  "error": "Invalid parameter",
  "details": "The 'id' field is required"
}
```

### API Documentation Features:
- **Code Examples**: See sample requests in multiple languages
- **Schema Viewer**: Understand request/response formats
- **OpenAPI Spec**: Download full API specification
- **Authentication**: Test with your credentials

---

## Authentication

**Purpose**: Secure access to the application with OAuth2/OIDC authentication.

### Navigation Steps:
1. Click **"Login"** in the top-right corner (or you're redirected if not logged in)
2. Login page loads with provider options

### How to Log In:

#### OAuth Providers:
The application supports multiple authentication providers:

**1. Azure AD / Microsoft**
1. Click **"Sign in with Microsoft"** button
2. Redirected to Microsoft login page
3. Enter your Microsoft credentials
4. Grant permissions (if prompted)
5. Redirected back to application

**2. Google**
1. Click **"Sign in with Google"** button
2. Select your Google account
3. Grant permissions
4. Redirected back to application

**3. Okta**
1. Click **"Sign in with Okta"** button
2. Enter your Okta credentials
3. Complete MFA (if enabled)
4. Redirected back to application

**4. Generic OIDC**
1. Select **"Other Provider"** tab
2. Enter your OIDC provider URL
3. Click **"Sign In"**
4. Complete authentication flow

### User Profile:

**Accessing Your Profile:**
1. Click **user avatar** in top-right corner
2. Select **"Profile"** from dropdown

**Profile Information:**
```
┌─────────────────────────────────┐
│  👤 John Doe                    │
│  📧 john.doe@company.com        │
│  🏢 Engineering Team            │
│  👔 Role: Engineer              │
│  🔑 Permissions: Read, Write    │
└─────────────────────────────────┘
```

### Session Management:

**Active Session:**
- Your session remains active for 8 hours
- Activity extends the session automatically
- Token stored securely in browser

**Logging Out:**
1. Click user avatar (top-right)
2. Select **"Logout"**
3. Confirm logout
4. Redirected to login page
5. Session token cleared

### Security Features:
- **Token-based Authentication**: Secure JWT tokens
- **Automatic Token Refresh**: Seamless session extension
- **Role-based Access**: Permissions based on your role
- **Audit Logging**: All actions are logged

---

## Tips & Best Practices

### General Navigation
- **Use Keyboard Shortcuts**: 
  - `Ctrl+K`: Quick search
  - `Ctrl+/`: Show shortcuts
  - `Esc`: Close dialogs
- **Breadcrumbs**: Use breadcrumb navigation to track your location
- **Browser Back Button**: Works for navigation history

### Efficient Searching
- **Use Wildcards**: Search with `*` for partial matches (e.g., `motor*`)
- **Combine Filters**: Use multiple filters for precise results
- **Save Searches**: Bookmark frequently used search URLs
- **Export Results**: Download search results for offline analysis

### Query Editor Best Practices
- **Start Simple**: Test basic queries before complex ones
- **Use LIMIT**: Always limit results during development
- **Save Queries**: Use templates for frequently used queries
- **Check Syntax**: Look for syntax highlighting errors

### Performance Tips
- **Paginate Results**: Use smaller page sizes for faster loading
- **Filter Early**: Apply filters before loading large datasets
- **Cache Awareness**: Repeated queries are faster due to caching
- **Batch Operations**: Use bulk operations instead of single updates

### Data Management
- **Regular Exports**: Backup important data periodically
- **Verify Syncs**: Check PLM sync logs for errors
- **Monitor Health**: Review system monitoring regularly
- **Clean Data**: Remove obsolete elements to maintain performance

### Collaboration
- **Consistent Naming**: Follow naming conventions for elements
- **Add Descriptions**: Document requirements and components
- **Link Properly**: Maintain traceability links
- **Review Changes**: Check recent activity for team updates

### Troubleshooting

**Application Won't Load:**
1. Clear browser cache
2. Check network connection
3. Verify backend is running (http://localhost:5000/api/health)
4. Check browser console for errors

**Slow Performance:**
1. Reduce result set size (use LIMIT)
2. Clear browser cache
3. Check system monitoring for issues
4. Optimize complex queries

**Authentication Issues:**
1. Clear cookies and tokens
2. Log out and log in again
3. Check token expiration
4. Verify OAuth provider configuration

**Database Connection Errors:**
1. Check system monitoring dashboard
2. Verify Neo4j credentials in settings
3. Test connection in health endpoint
4. Review backend logs

### Getting Help
- **Health Check**: Always start with http://localhost:5000/api/health
- **Backend Logs**: Check `/tmp/backend.log` for errors
- **Frontend Logs**: Open browser DevTools Console (F12)
- **API Documentation**: Use REST API Explorer for endpoint details

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+K` | Quick search |
| `Ctrl+/` | Show all shortcuts |
| `Ctrl+B` | Toggle sidebar |
| `Esc` | Close dialog/modal |
| `Ctrl+Enter` | Execute query (Query Editor) |
| `Ctrl+S` | Save (in editors) |
| `Alt+←` | Navigate back |
| `Alt+→` | Navigate forward |

---

## Quick Reference URLs

| Resource | URL |
|----------|-----|
| **Application UI** | http://localhost:3001 |
| **API Base** | http://localhost:5000/api/v1/ |
| **Health Check** | http://localhost:5000/api/health |
| **Metrics** | http://localhost:5000/metrics |
| **OpenAPI Spec** | http://localhost:5000/api/openapi.json |

---

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review system monitoring for errors
3. Check backend logs: `/tmp/backend.log`
4. Review API documentation in REST API Explorer
5. Contact your system administrator

---

**Last Updated**: December 9, 2025  
**Version**: 1.0.0  
**Application**: MBSE Knowledge Graph UI + REST API
