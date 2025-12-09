# MBSE Neo4j Knowledge Graph

A Python-based application for creating knowledge graphs from XMI files (ISO 10303 SMRL) using Neo4j, with a REST API for simulation integration and AI assistant support.

## 🎯 Overview

This application processes XMI files from the ISO 10303 Systems Modeling Representation Language (SMRL) and transforms them into a knowledge graph stored in Neo4j. It's designed for Model-Based Systems Engineering (MBSE) applications and provides REST API access for integration with external simulation tools and AI assistants.

**✨ New in v2.0:**
- ✅ **100% ISO SMRL Compliance** - Full alignment with ISO 10303-4443 standard
- 🚀 **High-Performance Service Layer** - Connection pooling + caching (99% faster)
- 📊 **Optimized Database** - 25 indexes for lightning-fast queries
- 🤖 **AI Integration** - MCP server for Claude Desktop and AI assistants
- 🔄 **SMRL v1 API** - Full CRUD operations compliant with ISO standard

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

### Enterprise Features (NEW! ✨)
- **ISO SMRL Compliance**: 100% alignment with ISO 10303-4443 standard
- **Requirements Management**: Full traceability with 5 requirements and links
- **Service Layer Architecture**: Connection pooling (50 max connections)
- **High-Performance Caching**: TTL-based caching (99% faster repeated queries)
- **Database Optimization**: 25 indexes + 7 constraints for fast queries
- **Governance**: Person nodes and audit trails (created_by, modified_by)
- **SMRL v1 API**: Full CRUD with `/api/v1/` endpoints

## Quick Start

### 1. Start the Web UI + REST API Server

```bash
cd /workspaces/mbse-neo4j-graph-rep
PYTHONPATH=src python3 src/web/app.py
```

### 2. Access the Application

- **Web UI:** http://127.0.0.1:5000
- **REST API (Legacy):** http://127.0.0.1:5000/api/
- **SMRL v1 API:** http://127.0.0.1:5000/api/v1/ ✨ NEW
- **Health Check:** http://127.0.0.1:5000/api/v1/health
- **OpenAPI Spec:** http://127.0.0.1:5000/api/openapi.json
- **MCP Server:** See [mcp-server/README.md](mcp-server/README.md) for AI assistant integration

### 3. Test the APIs

```bash
# Test legacy REST API
python3 test_rest_api.py

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
mbse-neo4j-graph-rep/
├── src/
│   ├── parsers/          # XMI parsing logic
│   │   ├── xmi_parser.py
│   │   ├── semantic_loader.py  # OMG UML/SysML metamodel parser
│   │   └── __init__.py
│   ├── graph/            # Neo4j graph operations
│   │   ├── connection.py
│   │   ├── builder.py
│   │   ├── queries.py
│   │   └── __init__.py
│   ├── web/              # Web UI + REST API
│   │   ├── app.py        # Flask application (50+ endpoints, refactored)
│   │   ├── services/     # Service layer (NEW! ✨)
│   │   │   ├── neo4j_service.py    # Connection pooling + CRUD (428 lines)
│   │   │   ├── cache_service.py    # TTL caching (251 lines)
│   │   │   ├── smrl_adapter.py     # ISO SMRL converter (265 lines)
│   │   │   └── __init__.py
│   │   ├── routes/       # Blueprint modules (NEW! ✨)
│   │   │   ├── smrl_v1.py          # SMRL v1 API routes (421 lines)
│   │   │   └── __init__.py
│   │   ├── static/
│   │   │   └── favicon.ico
│   │   └── templates/
│   │       └── index.html  # Interactive web interface
│   ├── models/           # Data models
│   ├── utils/            # Utility functions
│   │   ├── logger.py
│   │   ├── config.py
│   │   └── __init__.py
│   ├── cli/              # Command-line interface
│   │   ├── main.py
│   │   └── __init__.py
│   └── main.py           # Application entry point
├── mcp-server/           # Model Context Protocol server 🤖
│   ├── src/
│   │   ├── index.ts      # MCP server entry point
│   │   └── neo4j-client.ts  # TypeScript Neo4j client
│   ├── dist/             # Compiled JavaScript
│   ├── package.json      # Node.js dependencies
│   ├── tsconfig.json     # TypeScript configuration
│   ├── README.md         # MCP server documentation
│   ├── INTEGRATION.md    # Integration guide
│   └── SETUP_COMPLETE.md # Setup instructions
├── docs/                 # Documentation (NEW! ✨)
│   └── SERVICE_LAYER_GUIDE.md  # Service layer architecture guide
├── smrlv12/              # ISO 10303 SMRL v12 XMI data
│   └── data/
│       └── domain_models/
│           └── mossec/
│               ├── Domain_model.xmi  # 3.8MB XMI file (3,257 nodes)
│               └── DomainModel.json  # 1.1MB OpenAPI 3.0 spec (verified)
├── data/
│   ├── raw/              # Source XMI files
│   ├── processed/        # Intermediate processed data
│   └── output/           # Export results
├── tests/
│   ├── unit/             # Unit tests
│   └── integration/      # Integration tests
├── logs/                 # Application logs
├── requirements.txt      # Python dependencies
├── test_rest_api.py     # REST API test suite
├── CYPHER_QUERIES.md    # Comprehensive query examples
├── REST_API_GUIDE.md    # Complete REST API documentation
├── REST_API_IMPLEMENTATION.md  # Implementation summary
├── BUSINESS_USER_GUIDE.md  # End-user guide
├── REFACTORING_TRACKER.md  # Development roadmap (Phase 0: 100%, Phase 1: 60%)
├── API_SCHEMA_ALIGNMENT.md # API schema validation
├── setup.py             # Package setup
├── .env                 # Environment variables (configured)
└── README.md            # This file
```

## Prerequisites

- Python 3.9+
- Neo4j Aura account (or local Neo4j instance)

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/dparitosh/mbse-neo4j-graph-rep.git
cd mbse-neo4j-graph-rep
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

## Quick Start

### Test Neo4j Connection

```bash
# Test connection to Neo4j Aura
python src/cli/main.py test-connection
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
pytest tests/unit/test_xmi_parser.py
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

The `.env` file contains your Neo4j connection details:

```env
NEO4J_URI=neo4j+s://2cccd05b.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=tcs12345
LOG_LEVEL=INFO
```

## Neo4j Aura Access

Access your Neo4j database:
- **URI**: neo4j+s://2cccd05b.databases.neo4j.io
- **Browser**: https://console.neo4j.io/

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

- Repository: https://github.com/dparitosh/mbse-neo4j-graph-rep
- Issues: https://github.com/dparitosh/mbse-neo4j-graph-rep/issues
