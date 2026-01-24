# Installation Guide - MBSE Knowledge Graph

This guide provides step-by-step instructions for installing and configuring the MBSE Knowledge Graph application in a new Windows environment.

## 1. Prerequisites

Before starting, ensuring the following software is installed:

- **Windows 10/11 or Windows Server**
- **Python 3.12** (available on PATH)
- **Node.js 20** + **npm** (available on PATH)
- **Git**
- **Neo4j Database**:
  - Can be a local Desktop instance or an AuraDB cloud instance.
  - Obtain the URI, Username, and Password.

## 2. Installation Folder Setup

You can deploy the application anywhere on your system (e.g., `C:\MBSE\mbse-neo4j-graph-rep`).

1. **Clone or Copy** the repository to your machine.
2. Open **PowerShell As Administrator**.
3. Navigate to the repository root.

## 3. Automated Installation and Dependency Check

The provided scripts automate the setup of Python environments and Node.js dependencies.

Run the installer:
```powershell
powershell -ExecutionPolicy Bypass -File deployment\scripts\install.ps1
```

**What this does:**
- Validates Python and Node versions.
- Creates a target directory (if installing away from the repo) or sets up the local environment.
- Creates a Python Virtual Environment (`.venv`) for isolated dependencies.
- Installs Python libraries from `backend/requirements.txt`.
- Installs Node.js packages and builds the Frontend.
- Copies the reference dataset (`Domain_model.xmi`) to `data/raw/` for initial loading.
- Generates `start_all.ps1` and `.env` template.

## 4. Configuration

After installation, you must configure your database credentials.

1. Open the `.env` file created in the installation directory.
2. Update the Neo4j settings:

```dotenv
NEO4J_URI=neo4j+s://<your-instance-id>.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=<your-password>
```

3. Ensure other settings are correct:
```dotenv
LOG_LEVEL=INFO
DATA_DIR=./data
OUTPUT_DIR=./data/output
BACKEND_HOST=0.0.0.0
BACKEND_PORT=5000
FRONTEND_HOST=0.0.0.0
FRONTEND_PORT=3001
API_BASE_URL=http://localhost:5000
```

## 5. Starting the Services

You can start both Backend and Frontend services using the generated script:

```powershell
& '.\start_all.ps1'
```

This will launch two new windows: one for the FastAPI backend and one for the Vite frontend server.

- **Frontend UI**: [http://localhost:3001](http://localhost:3001)
- **Backend API Docs**: [http://localhost:5000/docs](http://localhost:5000/docs)

## 6. Data Loading (If starting fresh)

The application comes with scripts to populate the graph from the included ISO 10303-4443 reference data.

To reload the database:

1. Ensure the services are running (or at least the `.venv` is available).
2. Run the reload script using the virtual environment python:

```powershell
$env:PYTHONPATH="backend"; .\.venv\Scripts\python.exe backend/scripts/reload_database.py
```

This will:
- Clear the existing graph.
- Parse `data/raw/Domain_model.xmi`.
- Populate nodes, relationships (`CONTAINS`, `CONNECTED_BY`, `TYPED_BY`, etc.), and metadata.

## 7. Diagnostics

If you encounter issues, use the diagnostics tools located in `deployment/diagnostics/`:

- **Connectivity Check**:
  ```powershell
  $env:PYTHONPATH="backend"; .\.venv\Scripts\python.exe deployment/diagnostics/verify_connectivity.py
  ```
- **Duplicate Check**:
  ```powershell
  $env:PYTHONPATH="backend"; .\.venv\Scripts\python.exe deployment/diagnostics/check_duplicates.py
  ```

## 8. Service Management

For more granular control, use the Service Manager:

```powershell
.\deployment\scripts\service_manager.ps1 status
.\deployment\scripts\service_manager.ps1 stop
.\deployment\scripts\service_manager.ps1 backend restart
```
