# Configuration and Integration Guide (MBSE Graph Platform)

This guide provides step-by-step instructions for configuring the MBSE Graph Platform and integrating it with external engineering tools, PLM systems, and analysis software.

---

## 1. System Configuration

The platform is designed to be modular. You define your environment in a single `.env` file, and the application creates services based on that configuration.

### A. Environment Setup (.env)
Create a `.env` file in the `backend/` directory if one does not exist.

#### **Core Database Connection**
```ini
# Neo4j Graph Database Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
NEO4J_DATABASE=neo4j
```

#### **API Configuration**
```ini
# Backend Server Settings
HOST=0.0.0.0
PORT=8000
API_V1_PREFIX=/api/v1
LOG_LEVEL=INFO

# Security (JWT Auth)
SECRET_KEY=your-super-secret-key-change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

#### **Module Specific Flags**
```ini
# Feature Flags (Enable/Disable Modules)
ENABLE_OSLC=true
ENABLE_PLM_INTEGRATION=true
ENABLE_SIMULATION=false
```

### B. Service Ports
| Service | Default Port | Description |
| :--- | :--- | :--- |
| **Frontend** | `5173` | The web user interface (React). |
| **Backend API** | `8000` | The main REST & OSLC API (FastAPI). |
| **Neo4j DB** | `7474` / `7687` | The graph database browser/bolt port. |
| **Redis** | `6379` | Cache for TRS events (Semantic Linking). |

---

## 2. Capability Integration Guide

The platform offers distinct capabilities that can be integrated independently.

### 🔷 Capability 1: OSLC (Open Services for Lifecycle Collaboration)
**Purpose:** Connect to tools like IBM DOORS, Jira, or Polarion without duplicating data.

*   **Integration Point:** `http://localhost:8000/oslc`
*   **Root Services:** `http://localhost:8000/oslc/rootservices`
*   **Catalog:** `http://localhost:8000/oslc/catalog`
*   **Authentication:** Supports Basic Auth and OAuth headers.

**How to Integrate:**
1.  Open your external tool (e.g., Engineering Lifecycle Manager).
2.  Add a "Friend" server pointing to the Root Services URL.
3.  The platform will expose **Selection Dialogs** allowing users in the external tool to pick Requirements or Artifacts from this graph.

### 🔷 Capability 2: Data Import & Export
**Purpose:** Bulk data movement for specific engineering needs.

*   **UI Location:** `Data Management` Page (`/import`)
*   **Supported Formats:**
    *   **STEP (AP242):** For CAD/PLM geometry metadata exchange.
    *   **GraphML:** For visual graph analysis (Gephi, yEd).
    *   **JSON-LD:** For semantic web applications.
    *   **CSV:** For Excel/Spreadsheet reporting.
    *   **PlantUML:** For generating class diagrams automatically.

**Automated Integration (cURL example):**
```bash
# Export the entire graph to GraphML
curl -X GET "http://localhost:8000/api/export/graphml" -H "Authorization: Bearer <token>" -o graph.graphml

# Export Schema
curl -X GET "http://localhost:8000/api/export/schema"
```

### 🔷 Capability 3: PLM & Digital Thread
**Purpose:** Manage the lifecycle of parts, requirements, and verify traceability.

*   **API Endpoints:** `/api/plm/*`
*   **Features:**
    *   **Impact Analysis:** `/api/plm/impact/{node_id}` - Returns a graph of nodes affected if the target node changes.
    *   **Composition:** `/api/plm/composition/{node_id}` - Returns the Bill of Materials (BOM) structure.

### 🔷 Capability 4: Semantic Knowledge Graph (RDF/TRS)
**Purpose:** Advanced reasoning and tracked resource sets (Change Logs).

*   **TRS Endpoint:** `/oslc/trs/changelog`
*   **Usage:** External indexers (like LQE) can poll this endpoint to discover changes (Creates, Updates, Deletes) in real-time.

---

## 3. Developer Integration (Python Client)

If you are building a custom Python script to interact with the platform, use the following pattern:

```python
import requests

BASE_URL = "http://localhost:8000"
TOKEN = "your-auth-token"

def get_requirement(req_id):
    headers = {"Authorization": f"Bearer {TOKEN}"}
    response = requests.get(f"{BASE_URL}/api/ap239/requirements/{req_id}", headers=headers)
    return response.json()

def export_data():
    headers = {"Authorization": f"Bearer {TOKEN}"}
    # Download STEP file
    response = requests.get(f"{BASE_URL}/api/export/step", headers=headers)
    with open("model.stp", "w") as f:
        f.write(response.text)

if __name__ == "__main__":
    data = get_requirement("REQ-001")
    print(f"Requirement: {data['name']}")
```

---

## 4. Troubleshooting Integration

**Issue: Connecton Refused**
*   **Check:** Is the Neo4j container/service running? (`docker ps` or Service Manager)
*   **Fix:** verifying `NEO4J_URI` in `.env`.

**Issue: OSLC "Friend" Handshake Fails**
*   **Check:** Ensure the `rootservices` XML is returning valid content.
*   **Fix:** Visit `/oslc/rootservices` in a browser. It should be an RDF/XML document.

**Issue: Export is Empty**
*   **Check:** Does the database contain nodes with the correct labels?
*   **Fix:** Use the `/api/stats` endpoint to verify node counts.

---

## 5. Deployment Options

1.  **Docker Compose:** (Recommended for Production)
    *   `docker-compose up -d --build`
    *   Orchestrates Backend, Frontend, Redis, and Neo4j automatically.

2.  **Local Development:**
    *   **Backend:** `cd backend && uvicorn src.main:app --reload`
    *   **Frontend:** `cd frontend && npm run dev`
