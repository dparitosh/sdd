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
.\deployment\scripts\service_manager.ps1 logs backend    # View backend logs
.\deployment\scripts\service_manager.ps1 logs frontend   # View frontend logs
```

## 9. Health Check

After starting services, validate the deployment:

```powershell
.\deployment\diagnostics\health_check.ps1
```

This checks:
1. Backend health endpoint
2. API documentation availability
3. Graph data endpoints
4. Frontend accessibility
5. Database connectivity

For remote VMs, specify the URLs:
```powershell
.\deployment\diagnostics\health_check.ps1 -BackendUrl "http://<your-ip>:5000" -FrontendUrl "http://<your-ip>:3001"
```

---

## 10. Azure VM Deployment

When deploying to an Azure Windows VM, additional configuration is required.

### 10.1 Network Security Group (NSG) Rules

Allow inbound traffic on the required ports:

| Priority | Name          | Port | Protocol | Source    | Action |
|----------|---------------|------|----------|-----------|--------|
| 100      | AllowBackend  | 5000 | TCP      | Any       | Allow  |
| 110      | AllowFrontend | 3001 | TCP      | Any       | Allow  |

**Azure CLI command:**
```bash
# Replace <resource-group> and <nsg-name> with your values
az network nsg rule create \
  --resource-group <resource-group> \
  --nsg-name <nsg-name> \
  --name AllowBackend \
  --priority 100 \
  --direction Inbound \
  --access Allow \
  --protocol Tcp \
  --destination-port-range 5000

az network nsg rule create \
  --resource-group <resource-group> \
  --nsg-name <nsg-name> \
  --name AllowFrontend \
  --priority 110 \
  --direction Inbound \
  --access Allow \
  --protocol Tcp \
  --destination-port-range 3001
```

### 10.2 Windows Firewall Rules

On the VM itself, allow the ports through Windows Firewall:

```powershell
# Run as Administrator
New-NetFirewallRule -DisplayName "MBSE Backend" -Direction Inbound -Protocol TCP -LocalPort 5000 -Action Allow
New-NetFirewallRule -DisplayName "MBSE Frontend" -Direction Inbound -Protocol TCP -LocalPort 3001 -Action Allow
```

### 10.3 Environment Configuration

Ensure `.env` uses `0.0.0.0` for host bindings (this is the default in `.env.example`):

```dotenv
BACKEND_HOST=0.0.0.0
FRONTEND_HOST=0.0.0.0
```

For `API_BASE_URL`, you have two options:

1. **If accessing from the same VM's browser**: Use `http://localhost:5000`
2. **If frontend will be accessed externally**: Use the public IP: `http://<public-ip>:5000`

### 10.4 Accessing the Application

After starting services and configuring firewall rules:

- **Frontend UI**: `http://<public-ip>:3001`
- **Backend API**: `http://<public-ip>:5000`
- **API Docs**: `http://<public-ip>:5000/docs`

### 10.5 Production Considerations

For production deployments, consider:

1. **Use a reverse proxy** (IIS or nginx) for SSL termination
2. **Enable HTTPS** with a proper SSL certificate
3. **Restrict NSG rules** to specific IP ranges
4. **Use Azure Key Vault** for secrets management
5. **Enable Azure Monitor** for logging and alerting

---

## Troubleshooting

### Backend won't start
- Check `.venv` exists: `Test-Path .\.venv\Scripts\python.exe`
- Check Python version: `.\.venv\Scripts\python.exe --version`
- Verify requirements: `.\.venv\Scripts\pip.exe list`

### Frontend won't start
- Check Node version: `node --version` (should be 20+)
- Reinstall dependencies: `npm ci`

### Cannot connect to Neo4j
- Verify `.env` credentials are correct
- Test with the connectivity diagnostic
- Check Neo4j is running and accessible

### Graph is empty
- Run the reload script (Section 6)
- Check `data/raw/Domain_model.xmi` exists

### Cannot access from external network
- Verify NSG rules allow inbound on ports 5000 and 3001
- Verify Windows Firewall rules are created
- Verify hosts are bound to `0.0.0.0` in `.env`
