# MBSE Knowledge Graph - User Guide

This guide provides instructions for using the MBSE Knowledge Graph applications, including the Web UI and the OSLC Client.

## 1. Accessing the Applications

Once the services are running (see `INSTALL.md`), you can access the applications at:

*   **Frontend Web UI:** [http://localhost:3001](http://localhost:3001)
*   **Backend API & Documentation:** [http://localhost:5000/api/docs](http://localhost:5000/api/docs)
*   **Neo4j Browser (Database Admin):** [http://localhost:7474](http://localhost:7474)

## 2. Using the Web UI (Frontend)

The Frontend application provides a visual interface for interacting with the Knowledge Graph.

### **Features**
*   **Graph Explorer:** Visualize nodes and relationships. You can click on nodes to expand their connections.
*   **Search:** Search for specific entities (Requirements, Parts, Systems) by name or ID.
*   **Schema Browser:** View the underlying ontology (OSLC Core, OSLC RM, ISO 10303 standards).

### **Navigation**
*   **Dashboard:** Overview of the graph metrics (node counts, relationship types).
*   **Data Ingestion:** Upload XMI, RDF, or STEP files directly via the UI (if configured).
*   **Settings:** Configure connection endpoints.

## 3. OSLC Capabilities

The system functions as both an **OSLC Server** (provider) and an **OSLC Client** (consumer). This allows it to integrate with other PLM/ALM tools (like IBM DOORS, Jazz, Teamcenter, etc.).

### **3.1 As an OSLC Server**
The system exposes standard OSLC endpoints for **Requirements Management (RM)**.
*   **Catalog:** `http://localhost:5000/oslc/catalog`
*   **Service Provider:** `http://localhost:5000/oslc/provider/{id}`
*   **Resource Shapes:** `http://localhost:5000/oslc/shapes/{type}`

External tools can connect to these endpoints to query requirements stored in the Neo4j graph.

### **3.2 Using the OSLC Client**
The built-in OSLC Client allows this application to connect to *other* OSLC providers.

#### **Using the API (Swagger)**
Navigate to `http://localhost:5000/api/docs` and look for the `OSLC Client` section.

1.  **Discover Services:**
    *   Endpoint: `POST /api/oslc/client/discover`
    *   Input: The URL of the external OSLC Catalog.
    *   Result: Returns available Service Providers and capabilities (Selection Dialogs, Creation Factories).

2.  **Fetch Resources:**
    *   Endpoint: `GET /api/oslc/client/resource`
    *   Input: URI of the external resource.
    *   Result: Returns the RDF data of the external resource formatted as JSON-LD.

#### **Using the Command Line Script**
A utility script is provided to test OSLC connectivity from the command line.

**Location:** `backend/scripts/test_oslc_client.py`

**Usage:**
```bash
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Run the test client
python backend/scripts/test_oslc_client.py
```

This script will attempt to:
1.  Initialize the OSLC Client.
2.  Connect to a target OSLC Provider (default is `localhost:5000`).
3.  Perform Service Discovery.
4.  List available Query Capabilities and Creation Factories.

You can modify the `target_url` in the script to test connections against real external systems (e.g., a DOORS Web Access server).

## 4. Search Functionality

**Note on OpenSearch:** 
While the architecture supports advanced search capabilities, **OpenSearch (Elasticsearch) integration is not currently active** in the core deployment. 

*   **Current Search:** The application uses **Neo4j-based search** (Cypher queries). This supports exact matching, wildcard text matching, and graph traversal queries.
*   **Future Advanced Search:** Migration to OpenSearch for full-text indexing is planned for a future release (Phase 3).
