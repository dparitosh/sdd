# MBSE-Led Simulation Engineering Collaboration

A distributed collaboration platform for Model-Based Systems Engineering (MBSE) enabling simulation engineering collaboration across locations, organisations, and software platforms. Built on Neo4j knowledge graph technology with ISO 10303 SMRL compliance.

## 🎯 Overview

**MBSE-Led Simulation Engineering Collaboration** provides distributed infrastructure for collaborative systems engineering and simulation workflows. Transform XMI files into intelligent knowledge graphs, enabling secure multi-location collaboration with multiple modeling and simulation tools.

### Distributed Infrastructure
- **Multi-Location Collaboration**: Secure collaboration across distributed teams
- **Multi-Organisation Support**: Cross-organisational data sharing and integration
- **Multi-Platform Integration**: Connect diverse software platforms and tools
- **Distributed Processes**: Support for distributed modeling and simulation workflows
- **Distributed Datasets**: Unified access to distributed engineering data

### MBSE-Led Simulation Workflow
1. **Step 1 - Generate Geometry**: Create 3D models and CAD geometry across distributed design teams
2. **Step 2 - Mesh & Simulate**: Apply mesh generation and run simulations with multiple tools
3. **Step 3 - Results Interpretation**: Analyze and visualize simulation results collaboratively

**✨ Key Capabilities:**
- ✅ **100% ISO SMRL Compliance** - Full alignment with ISO 10303-4443 standard
- 🚀 **High-Performance Service Layer** - Connection pooling + caching (99% faster)
- 📊 **Optimized Database** - 25 indexes for lightning-fast queries
- 🤖 **AI Integration** - MCP server for Claude Desktop and AI assistants
- 🔄 **SMRL v1 API** - Full CRUD operations compliant with ISO standard
- 🌐 **Distributed Collaboration** - Multi-site, multi-tool, multi-organisation

## Features

### Core Capabilities
- **XMI Parser**: Parse XMI files from ISO 10303 SMRL v12 technical specifications
- **Semantic Loader**: OMG UML/SysML metamodel-based classification
- **Knowledge Graph Builder**: Transform XMI data into Neo4j graph database (3,257 nodes, 10,027 relationships)
- **Web UI**: Interactive visualization and query interface
- **REST API**: Full REST API for simulation tool integration (50+ endpoints)
- **MCP Server**: Model Context Protocol server for AI assistant integration 🤖
- **OpenAPI Support**: ISO 10303-4443 compliant API specification
- **CORS Enabled**: Cross-origin support for external applications
- **Batch Processing**: Process multiple XMI files efficiently
- **Graph Queries**: Pre-built Cypher queries for common MBSE patterns
- **Cloud-Ready**: Configured for Neo4j Aura cloud database
- **Multi-Tool Integration**: Support for multiple modeling and simulation platforms
- **Distributed Workflows**: Coordinate geometry generation, meshing, simulation, and analysis

### Enterprise Features (NEW! ✨)
- **ISO SMRL Compliance**: 100% alignment with ISO 10303-4443 standard
- **Requirements Management**: Full traceability with 5 requirements and links
- **Service Layer Architecture**: Connection pooling (50 max connections)
- **High-Performance Caching**: TTL-based caching (99% faster repeated queries)

## Installation

See [INSTALL.md](INSTALL.md) for detailed step-by-step installation instructions for Windows.

### Quick Start
1. Clone the repository
2. Run `.\scripts\install.ps1`
3. Configure `.env` with Neo4j credentials
4. Run `.\scripts\service_manager.ps1 start`
- **Database Optimization**: 25 indexes + 7 constraints for fast queries
- **Governance**: Person nodes and audit trails (created_by, modified_by)
- **SMRL v1 API**: Full CRUD with `/api/v1/` endpoints

## Quick Start

### 1. Start the FastAPI Backend Server

```powershell
# From the repo root

# Using uvicorn directly
cd backend
python -m uvicorn src.web.app_fastapi:app --host 127.0.0.1 --port 5000 --reload

# If you explicitly need remote access, set BACKEND_HOST (e.g. 0.0.0.0)
# $env:BACKEND_HOST = "0.0.0.0"
# python -m uvicorn src.web.app_fastapi:app --host $env:BACKEND_HOST --port 5000 --reload

# Or using the PowerShell startup script
cd ..
./scripts/start_backend.ps1
```

### 2. Access the Application

- **Web UI (React):** http://localhost:3001 (start with `npm run dev`)
- **REST API:** http://localhost:5000/api/
- **SMRL v1 API:** http://localhost:5000/api/v1/ ✨
- **Health Check:** http://localhost:5000/api/health
- **OpenAPI Docs:** http://localhost:5000/api/docs 🎯 **Interactive API Documentation**
- **ReDoc:** http://localhost:5000/api/redoc
- **OpenAPI JSON:** http://localhost:5000/api/openapi.json
- **MCP Server:** See [mcp-server/README.md](mcp-server/README.md) for AI assistant integration

### 3. Test the APIs

```bash
# Test legacy REST API
python backend/scripts/test_rest_api.py

# Test SMRL v1 API (NEW!)
curl http://127.0.0.1:5000/api/v1/health
curl http://127.0.0.1:5000/api/v1/Requirement?limit=5
curl http://127.0.0.1:5000/api/v1/Class?limit=5

# Check statistics (cached for performance)
curl http://127.0.0.1:5000/api/stats
```

## 📊 Performance Metrics

### Database
- **Nodes**: 3,257 (100% SMRL compliant)
- **Relationships**: 10,027
- **Indexes**: 25 (optimized for fast queries)
- **Constraints**: 7 (data integrity)

### API Performance
- **Cached Queries**: 99% faster (0.007s vs 0.7s)
- **Indexed Searches**: 50-70% faster
- **Connection Pooling**: Eliminates connection overhead
- **SMRL Compliance**: 100% (improved from 40%)

### Service Layer
- **Connection Pool**: 50 max connections
- **Cache Hit Rate**: ~90% for repeated queries
- **TTL Caching**: Default 5 minutes (configurable)
- **Total Endpoints**: 50+ (40 legacy + SMRL v1)

## REST API Endpoints

### SMRL v1 API (ISO 10303-4443 Compliant) ✨ NEW

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | Health check with version info |
| GET | `/api/v1/{ResourceType}` | List resources (Class, Package, Property, etc.) |
| GET | `/api/v1/{ResourceType}/{uid}` | Get specific resource by UID |
| POST | `/api/v1/{ResourceType}` | Create new resource |
| PUT | `/api/v1/{ResourceType}/{uid}` | Update resource (full replacement) |
| PATCH | `/api/v1/{ResourceType}/{uid}` | Partial update |
| DELETE | `/api/v1/{ResourceType}/{uid}` | Delete resource |
| POST | `/api/v1/match` | Advanced query with filters |
| GET | `/api/v1/Requirement` | List requirements with traceability |

**Supported Resource Types**: `Class`, `Package`, `Property`, `Port`, `Association`, `Requirement`, `Person`, `Constraint`, and more.

### Legacy API (Backward Compatible)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stats` | Get graph statistics (cached) |
| GET | `/api/packages` | Get all packages |
| GET | `/api/package/<id>` | Get specific package details |
| GET | `/api/classes` | Get all classes |
| GET | `/api/class/<id>` | Get specific class details |
| GET | `/api/search?q=<term>` | Search entities |
| GET | `/api/v1/Port` | Get all ports (interface elements) |
| GET | `/api/v1/Property` | Get all properties (supports ?owner, ?search, ?limit) |
| GET | `/api/v1/Constraint` | Get all constraints |
| POST | `/api/v1/query` | Execute custom Cypher query |
| GET | `/api/v1/relationship/{type}` | Get relationships by type |
| GET | `/api/openapi.json` | Download OpenAPI specification |

**✅ Schema Alignment:** All REST APIs are 100% aligned with Neo4j graph schema and ISO SMRL standard.  
See **[API_SCHEMA_ALIGNMENT.md](API_SCHEMA_ALIGNMENT.md)** for detailed validation report.

### Example Usage

**Python:**
```python
import requests

# Test health check (SMRL v1)
response = requests.get('http://127.0.0.1:5000/api/v1/health')
print(response.json())  # {'status': 'healthy', 'version': '1.0.0', ...}

# Get requirements
response = requests.get('http://127.0.0.1:5000/api/v1/Requirement?limit=5')
requirements = response.json()['resources']

# Get classes (legacy API)
response = requests.get('http://127.0.0.1:5000/api/classes?limit=10')
classes = response.json()

# Execute custom query
query = {"query": "MATCH (c:Class) RETURN c.name LIMIT 5", "params": {}}
response = requests.post('http://127.0.0.1:5000/api/v1/query', json=query)
```

**cURL:**
```bash
# Health check
curl http://127.0.0.1:5000/api/v1/health

# Get requirements with traceability
curl http://127.0.0.1:5000/api/v1/Requirement

# Search classes
curl "http://127.0.0.1:5000/api/search?q=Person"

# Get relationships
curl "http://127.0.0.1:5000/api/v1/relationship/GENERALIZES?limit=10"

# Get statistics (cached for performance)
curl http://127.0.0.1:5000/api/stats
```

See **[REST_API_GUIDE.md](REST_API_GUIDE.md)** for complete API documentation with MATLAB, JavaScript, and Simulink examples.  
See **[docs/SERVICE_LAYER_GUIDE.md](docs/SERVICE_LAYER_GUIDE.md)** for service layer architecture and usage.

## Project Structure

```
sdd/
├── backend/
│   ├── src/
│   │   ├── parsers/          # XMI parsing logic
│   │   │   ├── xmi_parser.py
│   │   │   ├── semantic_loader.py
│   │   │   └── __init__.py
│   │   ├── graph/            # Neo4j graph operations
│   │   │   ├── connection.py
│   │   │   ├── builder.py
│   │   │   ├── queries.py
│   │   │   └── __init__.py
│   │   ├── web/              # FastAPI application + REST API
│   │   │   ├── app_fastapi.py    # FastAPI entry point (50+ endpoints)
│   │   │   ├── services/         # Service layer
│   │   │   │   ├── neo4j_service.py    # Connection pooling + CRUD
│   │   │   │   ├── cache_service.py    # TTL caching
│   │   │   │   ├── insights_service.py # AI Insights analytics
│   │   │   │   └── smrl_adapter.py     # ISO SMRL converter
│   │   │   └── routes/           # Route modules
│   │   │       ├── smrl_v1.py         # SMRL v1 API routes
│   │   │       └── insights_fastapi.py
│   │   ├── models/           # Data models
│   │   └── utils/            # Utility functions
│   ├── scripts/              # Backend-specific scripts
│   ├── tests/                # Unit + integration tests
│   ├── requirements.txt      # Python dependencies
│   └── setup.py
├── frontend/
│   ├── src/                  # React + Vite frontend
│   ├── public/
│   ├── index.html
│   ├── vite.config.ts
│   └── vitest.config.ts
├── mcp-server/               # Model Context Protocol server 🤖
│   ├── src/
│   │   ├── index.ts          # MCP server entry point
│   │   └── neo4j-client.ts   # TypeScript Neo4j client
│   ├── package.json
│   └── README.md
├── scripts/                  # Lifecycle scripts (PowerShell)
│   ├── install.ps1           # Automated installation
│   ├── reinstall.ps1         # Clean reinstall with backup
│   ├── service_manager.ps1   # Start/stop/restart/status/logs
│   ├── start_all_interactive.ps1
│   ├── start_backend.ps1
│   ├── start_ui.ps1
│   ├── start_opensearch.ps1  # OpenSearch lifecycle management
│   ├── stop_all.ps1
│   ├── health_check.ps1      # Deployment health validation
│   ├── reload_database.py    # Full seeding pipeline
│   └── verify_connectivity.py
├── smrlv12/                  # ISO 10303 SMRL v12 XMI data
│   └── data/domain_models/mossec/
│       └── Domain_model.xmi
├── data/
│   ├── raw/                  # Source XMI files
│   ├── processed/            # Intermediate processed data
│   └── output/               # Export results
├── deployment/               # Legacy deployment wrappers
├── docs/                     # Documentation
├── .env                      # Environment variables (see .env.example)
├── .env.example              # Template with all supported variables
├── INSTALL.md                # Full installation guide
├── package.json              # Root Node.js dependencies (Vite/React)
├── vite.config.ts
└── README.md                 # This file
```

## Prerequisites

- Python 3.10+
- Node.js 18+ with npm
- Neo4j (local Desktop instance or AuraDB cloud)
- OpenSearch 2.x+ (for vector search / AI features)
- Ollama (optional, for local LLM / embeddings)

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/dparitosh/sdd.git
cd sdd
```

### 2. Run the automated installer

```powershell
.\scripts\install.ps1
```

This creates `.venv`, installs Python/Node dependencies, and builds the frontend.
See [INSTALL.md](INSTALL.md) for the full guide including OpenSearch and Ollama setup.

### 3. Configure environment

```powershell
# Copy template if .env doesn't exist yet
Copy-Item .env.example .env
# Edit .env with your Neo4j credentials
```

At minimum set:
```dotenv
NEO4J_URI=neo4j://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
NEO4J_DATABASE=mossec
```

## Quick Start

### Test Neo4j Connection

```powershell
..\.venv\Scripts\python.exe scripts\verify_connectivity.py
```

### Processing XMI Files

1. Place your XMI files in the `data/raw/` directory:

```bash
# Download ISO 10303 SMRL XMI files
wget -P data/raw/ https://standards.iso.org/iso/10303/smrl/v12/tech/[filename].xmi
```

2. Run the application:

```bash
# Process all XMI files in data/raw/
python src/main.py

# Or use CLI for specific file
python src/cli/main.py build-graph --input data/raw/example.xmi
```

### CLI Commands

```bash
# Test connection
python src/cli/main.py test-connection

# Parse XMI file
python src/cli/main.py parse --input data/raw/model.xmi

# Build knowledge graph
python src/cli/main.py build-graph --input data/raw/model.xmi

# Clear graph (careful!)
python src/cli/main.py clear-graph
```

## Data Source

This application processes XMI files from:
- **ISO 10303 SMRL (Systems Modeling Representation Language)**
- Version: 12
- Source: https://standards.iso.org/iso/10303/smrl/v12/tech/

## Neo4j Graph Schema

The knowledge graph follows this schema:

### Node Types
- `System`: System components
- `Component`: Sub-components
- `Requirement`: System requirements
- `Interface`: Component interfaces
- `Parameter`: Configuration parameters
- `Element`: Generic elements

### Relationship Types
- `HAS_COMPONENT`: System to Component
- `SATISFIES`: Component to Requirement
- `CONNECTS_TO`: Interface relationships
- `HAS_PARAMETER`: Component to Parameter
- `RELATES_TO`: Generic relationships

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test
pytest backend/tests/unit/test_xmi_parser.py
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
flake8 src/ tests/

# Type checking
mypy src/
```

## Configuration

The `.env` file contains your connection details (see `.env.example` for all available settings):

```dotenv
# Neo4j — local instance (default)
NEO4J_URI=neo4j://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
NEO4J_DATABASE=mossec

# For Neo4j Aura (cloud), use:
# NEO4J_URI=neo4j+s://<instance-id>.databases.neo4j.io

# Runtime
BACKEND_HOST=0.0.0.0
BACKEND_PORT=5000
FRONTEND_HOST=0.0.0.0
FRONTEND_PORT=3001
API_BASE_URL=http://127.0.0.1:5000
```

## Troubleshooting

### Connection Issues
- Verify Neo4j Aura instance is running
- Check credentials in `.env` file
- Ensure you have internet connectivity for cloud database

### XMI Parsing Errors
- Validate XMI file format
- Check logs in `logs/` directory
- Ensure XMI follows ISO 10303 SMRL schema

## Next Steps

1. Download XMI files from ISO 10303 SMRL repository
2. Place files in `data/raw/` directory
3. Run `python src/main.py` to process them
4. Access Neo4j Browser to visualize your knowledge graph
5. Run Cypher queries to explore the data

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Contact

- Repository: https://github.com/dparitosh/sdd
- Issues: https://github.com/dparitosh/sdd/issues
