# MBSE Knowledge Graph MCP Server

Model Context Protocol (MCP) server that exposes the MBSE Neo4j knowledge graph to AI assistants like Claude Desktop.

## 🎯 What is This?

This MCP server allows AI assistants to directly query and interact with your MBSE knowledge graph stored in Neo4j. It provides 12 powerful tools for:

- **Querying packages, classes, and properties**
- **Searching across the model**
- **Navigating relationships and hierarchies**
- **Executing custom Cypher queries**
- **Getting graph statistics and visualizations**

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd mcp-server
npm install
```

### 2. Configure Environment

Create `.env` file in the `mcp-server` directory:

```env
NEO4J_URI=neo4j+s://your-neo4j-uri.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-neo4j-password
MCP_SERVER_NAME=mbse-knowledge-graph
MCP_SERVER_VERSION=1.0.0
```

### 3. Build the Server

```bash
npm run build
```

### 4. Test Locally

```bash
npm start
```

## 🔌 Integration with Claude Desktop

### Configure Claude Desktop

Add this to your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "mbse-knowledge-graph": {
      "command": "node",
      "args": [
        "/absolute/path/to/mbse-neo4j-graph-rep/mcp-server/dist/index.js"
      ],
      "env": {
        "NEO4J_URI": "neo4j+s://your-neo4j-uri.databases.neo4j.io",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "your-neo4j-password"
      }
    }
  }
}
```

**Important**: Replace `/absolute/path/to/` with your actual repository path.

### Restart Claude Desktop

After saving the config, restart Claude Desktop. You should see the MBSE tools available in the tool picker (🔨 icon).

## 🛠️ Available Tools

### 1. `get_statistics`
Get overall knowledge graph statistics
- Total nodes and relationships
- Breakdown by type

**Example**: "What's in the MBSE model?"

### 2. `list_packages`
List all packages with optional search
- Search by name
- Configurable limit

**Example**: "List all packages containing 'Approval'"

### 3. `get_package`
Get detailed package information
- Package metadata
- Contained elements

**Example**: "Show me details of package _18_4_1_1b310459_1505839733474_404953_14051"

### 4. `list_classes`
List classes with filters
- Search by name
- Filter by package
- Configurable limit

**Example**: "Find all classes in the system"

### 5. `get_class`
Get detailed class information
- Properties
- Parent classes
- Child classes
- Associations

**Example**: "Show me the Person class details"

### 6. `get_class_hierarchy`
Get inheritance hierarchy
- All ancestor classes
- Depth information

**Example**: "What classes does Manager inherit from?"

### 7. `list_properties`
List properties (attributes)
- Filter by owner
- Search by name

**Example**: "What properties does the Person class have?"

### 8. `list_associations`
List all associations
- Display names
- Member ends
- End types

**Example**: "Show me all relationships between classes"

### 9. `search_model`
Search across entire model
- Search by name
- Filter by type
- Fuzzy matching

**Example**: "Find anything related to 'approval'"

### 10. `get_relationships`
Get all relationships for a node
- Incoming and outgoing
- Relationship types

**Example**: "What is connected to this class?"

### 11. `get_subgraph`
Get connected nodes
- Configurable depth
- Full graph structure

**Example**: "Show me everything connected to Person within 2 hops"

### 12. `execute_cypher`
Execute custom Cypher queries
- Full Neo4j query power
- Parameterized queries

**Example**: "Run custom query: MATCH (c:Class) WHERE c.isAbstract = true RETURN c"

## 💬 Example Prompts for Claude

Once integrated, you can ask Claude:

### Statistics & Overview
- "What's in the MBSE knowledge graph?"
- "How many classes and packages are there?"
- "Show me the distribution of node types"

### Navigation
- "List all packages in the model"
- "Show me all classes in the ApprovalAssumptionJustification package"
- "Find the Person class and show its properties"

### Relationships
- "What classes inherit from Person?"
- "Show me all associations involving the Approval class"
- "What's connected to the Organization class?"

### Search & Discovery
- "Find everything related to 'approval'"
- "Search for classes with 'Manager' in the name"
- "Show me all constraints in the system"

### Analysis
- "Analyze the inheritance hierarchy of the Manager class"
- "What would be affected if I change the Person class?"
- "Show me a subgraph centered on the Vehicle class"

### Advanced
- "Execute this Cypher query: MATCH (c:Class)-[:HAS_ATTRIBUTE]->(p:Property) RETURN c.name, count(p) ORDER BY count(p) DESC LIMIT 10"
- "Find all classes with more than 5 properties"

## 📁 Project Structure

```
mcp-server/
├── src/
│   ├── index.ts              # MCP server entry point
│   └── neo4j-client.ts       # Neo4j client with typed methods
├── dist/                      # Compiled JavaScript (generated)
├── package.json              # Dependencies and scripts
├── tsconfig.json             # TypeScript configuration
├── .env.example              # Environment variables template
└── README.md                 # This file
```

## 🔧 Development

### Build
```bash
npm run build
```

### Watch Mode (auto-rebuild)
```bash
npm run dev
```

### Run
```bash
npm start
```

## 🐛 Troubleshooting

### "Failed to connect to Neo4j"
- Check your `.env` file has correct credentials
- Verify Neo4j Aura is accessible
- Test connection: `curl -I https://<your-instance-id>.databases.neo4j.io`

### "Tools not showing in Claude Desktop"
- Verify config file path is correct
- Check absolute path in `args`
- Restart Claude Desktop completely
- Check Claude logs for errors

### "Module not found" errors
- Run `npm install` in `mcp-server/` directory
- Rebuild with `npm run build`

### Neo4j Connection Issues
```bash
# Test connection
node -e "
const neo4j = require('neo4j-driver');
const driver = neo4j.driver(process.env.NEO4J_URI, neo4j.auth.basic(process.env.NEO4J_USER, process.env.NEO4J_PASSWORD));
driver.verifyConnectivity().then(() => console.log('✅ Connected')).catch(e => console.error('❌', e));
"
```

## 📚 Learn More

- [Model Context Protocol Docs](https://modelcontextprotocol.io/)
- [Neo4j Driver Docs](https://neo4j.com/docs/javascript-manual/current/)
- [Claude Desktop MCP Guide](https://docs.anthropic.com/claude/docs/model-context-protocol)

## 🤝 Integration with Main Application

This MCP server complements the Flask REST API:

- **REST API** (`src/web/app.py`): Web UI + HTTP endpoints
- **MCP Server** (`mcp-server/`): AI assistant integration

Both access the same Neo4j database and can coexist.

## 📄 License

MIT - Same as parent repository

---

**Ready to use?** Follow the Quick Start guide above! 🚀
