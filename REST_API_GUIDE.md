# REST API Integration Guide

## 🔌 MBSE Knowledge Graph REST API

This guide describes the REST API endpoints available for integrating the MBSE knowledge graph with external simulation tools and applications.

## 📍 Base URL

```
http://127.0.0.1:5000/api
```

## 🌐 CORS Support

Cross-Origin Resource Sharing (CORS) is enabled, allowing external applications from different domains to access the API.

## 🔑 Available Endpoints

### 1. Get All Classes

**Endpoint:** `GET /api/v1/Class`

**Description:** Retrieve all UML/SysML Class entities from the knowledge graph.

**Query Parameters:**
- `package` (optional): Filter by package name
- `search` (optional): Search term for class names
- `limit` (optional, default: 100): Maximum number of results

**Example Request:**
```bash
curl "http://127.0.0.1:5000/api/v1/Class?limit=10"
```

**Example Response:**
```json
{
  "count": 10,
  "data": [
    {
      "id": "_18_4_1_1b310459_1505839733696_607128_14329",
      "name": "AccessibleModelInstanceConstituent",
      "description": "UUID from AccessibleModelInstanceConstituent...",
      "parent_classes": ["AssumedItem", "JustifiedItem"],
      "property_count": 10
    }
  ]
}
```

---

### 2. Get Specific Class

**Endpoint:** `GET /api/v1/Class/{id}`

**Description:** Get detailed information about a specific class including properties and relationships.

**Example Request:**
```bash
curl "http://127.0.0.1:5000/api/v1/Class/_18_4_1_1b310459_1505839733696_607128_14329"
```

**Example Response:**
```json
{
  "class": {
    "id": "_18_4_1_1b310459_1505839733696_607128_14329",
    "name": "AccessibleModelInstanceConstituent",
    "description": "UUID from AccessibleModelInstanceConstituent..."
  },
  "properties": [
    {
      "name": "constituent",
      "type": "string",
      "description": "..."
    }
  ],
  "relationships": {
    "generalizes": [...],
    "has_attributes": [...]
  }
}
```

---

### 3. Get All Packages

**Endpoint:** `GET /api/v1/Package`

**Description:** Retrieve all UML/SysML Package entities.

**Example Request:**
```bash
curl "http://127.0.0.1:5000/api/v1/Package"
```

**Example Response:**
```json
{
  "count": 34,
  "data": [
    {
      "id": "_18_4_1_1b310459_1505839733474_404953_14051",
      "name": "ApprovalAssumptionJustification",
      "description": "The capability for representing information...",
      "child_count": 11
    }
  ]
}
```

---

### 4. Get Specific Package

**Endpoint:** `GET /api/v1/Package/{id}`

**Description:** Get detailed information about a specific package including all contained elements.

**Example Request:**
```bash
curl "http://127.0.0.1:5000/api/v1/Package/_18_4_1_1b310459_1505839733474_404953_14051"
```

---

### 5. Execute Custom Query

**Endpoint:** `POST /api/v1/query`

**Description:** Execute a custom Cypher query for advanced data retrieval.

**Request Body:**
```json
{
  "query": "MATCH (c:Class)-[:GENERALIZES]->(p:Class) RETURN c.name, p.name LIMIT 10",
  "params": {}
}
```

**Example Request:**
```bash
curl -X POST http://127.0.0.1:5000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "MATCH (c:Class) WHERE c.name CONTAINS \"Model\" RETURN c.name, c.id LIMIT 5",
    "params": {}
  }'
```

**Example Response:**
```json
{
  "count": 5,
  "data": [
    {
      "c.name": "AccessibleModelInstanceConstituent",
      "c.id": "_18_4_1_1b310459_1505839733696_607128_14329"
    }
  ]
}
```

---

### 6. Get Relationships by Type

**Endpoint:** `GET /api/v1/relationship/{type}`

**Description:** Retrieve all relationships of a specific type.

**Available Types:**
- `GENERALIZES` - Inheritance relationships
- `HAS_ATTRIBUTE` - Property ownership
- `CONTAINS` - Package containment
- `ASSOCIATES_WITH` - Association relationships
- `TYPED_BY` - Type relationships
- `HAS_RULE` - Constraint rules

**Query Parameters:**
- `limit` (optional, default: 100): Maximum number of results

**Example Request:**
```bash
curl "http://127.0.0.1:5000/api/v1/relationship/GENERALIZES?limit=5"
```

**Example Response:**
```json
{
  "count": 5,
  "data": [
    {
      "source_id": "_18_4_1_1b310459_1505839733514_450704_14138",
      "source_name": "Person",
      "source_type": "Class",
      "target_id": "_18_4_1_1b310459_1505839733876_143414_14785",
      "target_name": "PersonOrOrganizationItem",
      "target_type": "Class"
    }
  ]
}
```

---

### 7. Get OpenAPI Specification

**Endpoint:** `GET /api/openapi.json`

**Description:** Download the full ISO 10303-4443 OpenAPI 3.0 specification.

**Details:**
- 237 schema definitions
- 151 REST API endpoint definitions
- 81 category tags

**Example Request:**
```bash
curl "http://127.0.0.1:5000/api/openapi.json" -o openapi_spec.json
```

---

## 💡 Integration Examples

### Python Integration

```python
import requests

# Get all classes in a specific package
response = requests.get(
    'http://127.0.0.1:5000/api/v1/Class',
    params={'package': 'CommonResources', 'limit': 20}
)
classes = response.json()['data']

# Execute custom Cypher query
query = {
    "query": """
        MATCH (c:Class)-[:HAS_ATTRIBUTE]->(p:Property)
        WHERE c.name = 'Person'
        RETURN p.name, p.type
    """,
    "params": {}
}
response = requests.post('http://127.0.0.1:5000/api/v1/query', json=query)
properties = response.json()['data']
```

---

### JavaScript/Node.js Integration

```javascript
// Fetch all packages
fetch('http://127.0.0.1:5000/api/v1/Package')
  .then(res => res.json())
  .then(data => {
    console.log(`Found ${data.count} packages`);
    data.data.forEach(pkg => console.log(pkg.name));
  });

// Execute custom query
const query = {
  query: "MATCH (c:Class) RETURN c.name LIMIT 10",
  params: {}
};

fetch('http://127.0.0.1:5000/api/v1/query', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify(query)
})
  .then(res => res.json())
  .then(data => console.log(data));
```

---

### MATLAB/Simulink Integration

```matlab
% Get classes for simulation model
url = 'http://127.0.0.1:5000/api/v1/Class?search=Architecture&limit=10';
options = weboptions('ContentType', 'json');
data = webread(url, options);
classes = data.data;

% Execute custom query
query_data = struct(...
    'query', 'MATCH (a:Class {name: "Architecture"}) RETURN a', ...
    'params', struct() ...
);
url = 'http://127.0.0.1:5000/api/v1/query';
options = weboptions('MediaType', 'application/json', 'RequestMethod', 'post');
result = webwrite(url, query_data, options);
```

---

### cURL Examples

```bash
# Get graph statistics
curl http://127.0.0.1:5000/api/stats

# Search for specific class
curl "http://127.0.0.1:5000/api/v1/Class?search=Person&limit=5"

# Get generalization relationships
curl "http://127.0.0.1:5000/api/v1/relationship/GENERALIZES?limit=10"

# Query for all ports
curl -X POST http://127.0.0.1:5000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "MATCH (p:Port) RETURN p.name, p.id LIMIT 10", "params": {}}'
```

---

## 🚀 Web UI

The REST API is also accessible through a web interface:

**URL:** http://127.0.0.1:5000

**Features:**
- Browse packages and classes
- Interactive API tester
- Query editor with Cypher support
- Graph statistics dashboard
- API documentation with examples

**REST API Tab:**
- Complete endpoint documentation
- Interactive API testing interface
- Integration code examples for Python, JavaScript, MATLAB
- One-click OpenAPI spec download

---

## 📊 Knowledge Graph Statistics

Current graph contains:
- **1,893 nodes** across multiple types
- **3,021 relationships**
- **143 Classes**
- **1,217 Properties**
- **188 Ports**
- **34 Packages**

---

## 🔒 Security Notes

- This is a development server running on localhost
- For production deployment, use a WSGI server (e.g., Gunicorn, uWSGI)
- Consider adding authentication for production use
- CORS is currently enabled for all origins (adjust for production)

---

## 📝 Additional Resources

- **Cypher Queries:** See `CYPHER_QUERIES.md` for comprehensive query examples
- **OpenAPI Spec:** Download from `/api/openapi.json` for Swagger/Postman
- **Source Data:** ISO 10303 SMRL v12 XMI files in `smrlv12/` directory

---

## 🛠️ Running the Server

```bash
cd /workspaces/mbse-neo4j-graph-rep
PYTHONPATH=src python3 src/web/app.py
```

The server will start on:
- **UI:** http://127.0.0.1:5000
- **API:** http://127.0.0.1:5000/api/v1/
- **OpenAPI:** http://127.0.0.1:5000/api/openapi.json
