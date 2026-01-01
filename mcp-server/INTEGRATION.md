# MCP Server Integration Guide

## 🎯 Overview

This document explains how the **MCP (Model Context Protocol) Server** integrates with the main MBSE Knowledge Graph application.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MBSE Knowledge Graph                     │
│                   (Neo4j Aura Database)                     │
└────────────┬────────────────────────────┬───────────────────┘
             │                            │
             │                            │
    ┌────────▼─────────┐       ┌─────────▼──────────┐
    │   Flask REST API │       │    MCP Server      │
    │   (Port 5000)    │       │   (stdio/MCP)      │
    │                  │       │                    │
    │  • Web UI        │       │  • AI Assistant    │
    │  • Dashboard     │       │  • 12 Tools        │
    │  • 40 Endpoints  │       │  • Claude Desktop  │
    │  • HTTP/JSON     │       │                    │
    └────────┬─────────┘       └─────────┬──────────┘
             │                            │
             │                            │
    ┌────────▼─────────┐       ┌─────────▼──────────┐
    │  Web Browsers    │       │  Claude Desktop    │
    │  • Chrome        │       │  • GPT-4           │
    │  • Firefox       │       │  • Other MCP       │
    │  • Edge          │       │    clients         │
    └──────────────────┘       └────────────────────┘
```

## 📊 Feature Comparison

| Feature | Flask REST API | MCP Server |
|---------|----------------|------------|
| **Purpose** | Web UI + HTTP API | AI assistant integration |
| **Protocol** | HTTP/REST | Model Context Protocol |
| **Transport** | TCP Socket (Port 5000) | stdio |
| **Clients** | Web browsers, curl, Postman | Claude Desktop, AI assistants |
| **Data Format** | JSON | JSON (MCP wrapped) |
| **Authentication** | None (planned) | Environment-based |
| **Endpoints/Tools** | 40 REST endpoints | 12 MCP tools |
| **Use Case** | Human interaction | AI agent interaction |

## 🔄 Coexistence Strategy

Both servers can run simultaneously:

### Option 1: Run Both (Recommended)
```bash
# Terminal 1: Flask API
cd /workspaces/mbse-neo4j-graph-rep
PYTHONPATH=src python src/web/app.py

# Terminal 2: MCP Server (for Claude Desktop)
# Configured in Claude Desktop - runs automatically
```

### Option 2: Flask Only (Web UI)
```bash
cd /workspaces/mbse-neo4j-graph-rep
PYTHONPATH=src python src/web/app.py
# Access: http://localhost:5000
```

### Option 3: MCP Only (AI Assistants)
```bash
# Configure in Claude Desktop config
# MCP server starts automatically when Claude needs it
```

## 🛠️ When to Use Which?

### Use Flask REST API when:
- ✅ Building web applications
- ✅ Human users need visual interface
- ✅ Integration with existing HTTP-based tools
- ✅ Browser-based access required
- ✅ Traditional REST clients (curl, Postman)

### Use MCP Server when:
- ✅ AI assistants need to query the model
- ✅ Claude Desktop integration
- ✅ Conversational interface to data
- ✅ Complex multi-step reasoning needed
- ✅ Natural language queries

## 📝 Example Use Cases

### Flask REST API Use Case
**Scenario**: Engineer needs to view dashboard statistics and search for SysML/UML artifacts

**Web UI**: Visit http://localhost:5000 to see:
- 📊 Dashboard with Node Types and Relationship Types statistics
- 🔍 Advanced Search with filters (type, name, comment)
- 📈 Graph visualization of relationships
- 🔧 REST API testing interface
- 💻 Query Editor for custom Cypher queries

**Direct API**: Access endpoints programmatically
```bash
# Get statistics
curl http://localhost:5000/api/stats

# Search artifacts
curl http://localhost:5000/api/artifacts

# Get all packages (endpoint still available)
curl http://localhost:5000/api/packages

# Get specific class
curl http://localhost:5000/api/v1/Class/_18_4_1_12a90368_1520275673819_823814_15093
```

### MCP Server Use Case
**Scenario**: AI assistant helps with impact analysis

**User**: "What classes would be affected if I modify the Person class?"

**Claude** (via MCP):
1. Uses `get_class` to get Person class details
2. Uses `get_class_hierarchy` to find child classes
3. Uses `get_relationships` to find associations
4. Analyzes and presents impact report

## 🔧 Shared Components

Both servers share:

### Database
- Same Neo4j Aura instance
- Same credentials
- Same data model
- Real-time consistency

### Configuration
- Environment variables (`.env`)
- Neo4j connection settings

### Data Access Patterns
Similar queries, different implementations:

**Flask (Python)**:
```python
query = "MATCH (c:Class) WHERE c.name CONTAINS $search RETURN c"
result = conn.execute_query(query, {'search': 'Person'})
```

**MCP (TypeScript)**:
```typescript
const query = `MATCH (c:Class) WHERE c.name CONTAINS $search RETURN c`;
const result = await session.run(query, { search: 'Person' });
```

## 🚀 Migration Path

### Phase 1: Current State ✅
- Flask REST API operational
- 40 endpoints serving web UI
- Manual queries via UI

### Phase 2: MCP Integration (NEW) ✅
- MCP server created
- Claude Desktop configured
- AI-assisted queries enabled

### Phase 3: Unified Experience (Future)
- Web UI calls MCP server tools
- Single source of truth
- Shared business logic

## 🖥️ Web UI Structure

The Flask web interface provides a streamlined view:

### Available Tabs
1. **SysML/UML Artifacts** (default)
   - 📊 Dashboard: Statistics overview (Node Types, Relationship Types)
   - 🔍 Advanced Search: Filter by type, name, comment with results table
   - 📊 Graph View: Interactive relationship visualization
   - 📝 Object Details: Properties and connections

2. **REST API**
   - Interactive CRUD operations
   - Test all 40 endpoints
   - PLM, Simulation, Export, Version control operations

3. **Query Editor**
   - Custom Cypher queries
   - Direct database access
   - Results visualization

### REST API Endpoints

All REST endpoints remain available even if not exposed in UI tabs:
- `/api/packages` - List all packages (no UI tab)
- `/api/classes` - List all classes (no UI tab)
- `/api/stats` - Statistics (shown in Dashboard)
- `/api/artifacts` - SysML/UML artifacts (shown in search)
- ... and 36 more endpoints

## 📚 API Mapping

### REST → MCP Tool Mapping

| REST Endpoint | MCP Tool | Notes |
|---------------|----------|-------|
| `GET /api/stats` | `get_statistics` | Same data |
| `GET /api/packages` | `list_packages` | MCP adds search |
| `GET /api/package/<id>` | `get_package` | Same functionality |
| `GET /api/classes` | `list_classes` | MCP adds filters |
| `GET /api/class/<id>` | `get_class` | Enhanced with relationships |
| `GET /api/search` | `search_model` | MCP adds type filters |
| `POST /api/cypher` | `execute_cypher` | Same Cypher execution |

### MCP-Only Features
- `get_class_hierarchy` - Inheritance tree
- `get_relationships` - Relationship explorer
- `get_subgraph` - Graph visualization data

## 🔐 Security Considerations

### Flask REST API
- Currently: No authentication
- Planned: JWT tokens, API keys
- Access: Network-based (port 5000)

### MCP Server
- Currently: Environment-based credentials
- Access: Local process only (stdio)
- Security: Relies on OS user permissions

## 🐛 Troubleshooting

### Both Servers Need Same Database
```bash
# Check .env file exists in both locations
ls -la /workspaces/mbse-neo4j-graph-rep/.env
ls -la /workspaces/mbse-neo4j-graph-rep/mcp-server/.env

# Or, MCP server can read parent .env
```

### Port Conflict
Flask uses port 5000, MCP uses stdio - no conflict possible!

### Database Connection Issues
Both servers need same credentials:
```env
NEO4J_URI=neo4j+s://your-neo4j-uri.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-neo4j-password
```

## 📈 Performance Considerations

### Flask REST API
- **Concurrent Users**: Handles multiple HTTP connections
- **Caching**: Can add Redis/in-memory cache
- **Scaling**: Can deploy multiple instances

### MCP Server
- **Concurrent Requests**: Single Claude Desktop instance
- **Caching**: Neo4j driver handles connection pooling
- **Scaling**: One instance per AI assistant

## 🔮 Future Enhancements

### Short Term (1-2 months)
- [ ] Add authentication to Flask API
- [ ] MCP server metrics/logging
- [ ] Shared configuration management

### Medium Term (3-6 months)
- [ ] Web UI calls MCP tools
- [ ] Unified business logic layer
- [ ] GraphQL endpoint (alternative to REST)

### Long Term (6-12 months)
- [ ] Real-time updates (WebSocket)
- [ ] Multi-tenant support
- [ ] Advanced caching strategy

## 📞 Getting Help

### Flask REST API Issues
- See [REST_API_GUIDE.md](../REST_API_GUIDE.md)
- Check Flask logs in terminal

### MCP Server Issues
- See [mcp-server/README.md](README.md)
- Check Claude Desktop logs
- Test with `npm start`

### Database Issues
- See [README.md](../README.md#troubleshooting)
- Test Neo4j connection
- Check Aura dashboard

---

**Both systems are complementary, not competitive!** Use them together for maximum productivity. 🚀
