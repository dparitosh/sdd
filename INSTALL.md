# Installation Guide - MBSE Knowledge Graph

This guide provides step-by-step instructions for installing and configuring the MBSE Knowledge Graph application on Windows systems.

## 1. Prerequisites

Before starting, ensure the following software is installed:

- **Windows 10/11 or Windows Server**
- **Python 3.10+** (available on PATH)
- **Node.js 18+** with **npm** (available on PATH)
- **Git**
- **Neo4j Database**:
  - Can be a local Desktop instance or an AuraDB cloud instance.
  - Obtain the URI, Username, and Password.

## 2. Installation Folder Setup

1. **Clone or Copy** the repository to your machine (e.g., `C:\MBSE\mbse-neo4j-graph-rep`).
2. Open **PowerShell** (standard user, no admin required).
3. Navigate to the repository root.

## 3. Automated Installation

The provided script automates the setup of Python environments and Node.js dependencies.

Run the installer:
```powershell
.\scripts\install.ps1
```

If you want the installer to **fail fast** when Neo4j credentials are missing/placeholder (recommended for CI or repeatable setups):
```powershell
.\scripts\install.ps1 -RequireNeo4j
```

**What this does:**
- Validates Python and Node versions.
- Creates a Python Virtual Environment (`.venv`) for isolated dependencies.
- Installs Python libraries from `backend/requirements.txt`.
- Installs Node.js packages and builds the Frontend.
- Copies the reference dataset (`Domain_model.xmi`) to `data/raw/` for initial loading.
- Creates a `.env` template if not present.

**Neo4j credentials safety checks during install:**
- The installer creates (or reuses) `.env` **before** building the frontend so required frontend environment variables are available.
- It checks `NEO4J_URI`, `NEO4J_USER`, and `NEO4J_PASSWORD` for missing/placeholder values (secrets are never printed).
- If credentials look real and Python dependencies were installed, it runs a connectivity check via `scripts/verify_connectivity.py`.

## 4. Configuration

After installation, configure your database credentials.

1. Open the `.env` file in the installation directory.
2. Update the Neo4j settings:

```dotenv
NEO4J_URI=neo4j+s://<your-instance-id>.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=<your-password>
NEO4J_DATABASE=neo4j
```

3. Verify connectivity any time:
```powershell
.\.venv\Scripts\python.exe scripts\verify_connectivity.py
```

3. Verify other settings:
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

### LLM (AI Agent) configuration

The backend includes an optional LangGraph-based agent. You can run it using either:

- **OpenAI** (default): requires `OPENAI_API_KEY`
- **Ollama** (local): requires Ollama running and `OLLAMA_*` configured

In `.env`:

```dotenv
# Choose one: openai | ollama
LLM_PROVIDER=openai

# OpenAI
OPENAI_API_KEY=<your-openai-api-key>
OPENAI_MODEL=gpt-4o
OPENAI_TEMPERATURE=0.7

# Ollama (local)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1
OLLAMA_TEMPERATURE=0.7
```

#### Using Ollama (local)

1. Install Ollama: https://ollama.com/
2. Ensure the Ollama server is running (default: `http://localhost:11434`).
3. Pull a model (example):

```powershell
ollama pull llama3.1
```

4. Set in `.env`:

```dotenv
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1
```

## 5. Starting the Services

Start both Backend and Frontend services using the service manager:

```powershell
.\scripts\service_manager.ps1 start
```

This will launch both services in the background.

If you prefer **step-by-step startup with console inspection output and live logs**, use:
```powershell
.\scripts\service_manager.ps1 start -Interactive -Inspect
```

Or the convenience wrapper:
```powershell
.\scripts\start_all_interactive.ps1 -Inspect
```

- **Frontend UI**: [http://localhost:3001](http://localhost:3001)
- **Backend API Docs**: [http://localhost:5000/docs](http://localhost:5000/docs)

### Service Management Commands

```powershell
# Start all services
.\scripts\service_manager.ps1 start

# Stop all services
.\scripts\service_manager.ps1 stop

# Restart all services
.\scripts\service_manager.ps1 restart

# Check service status
.\scripts\service_manager.ps1 status

# Manage individual services
.\scripts\service_manager.ps1 backend start
.\scripts\service_manager.ps1 backend stop
.\scripts\service_manager.ps1 frontend restart

# View logs
.\scripts\service_manager.ps1 logs backend
.\scripts\service_manager.ps1 logs frontend

# Show help
.\scripts\service_manager.ps1 help
```

## 6. Data Loading

The application comes with scripts to populate the graph from included ISO 10303-4443 reference data.

To reload the database:

```powershell
.\.venv\Scripts\python.exe scripts\reload_database.py
```

This will:
- Clear the existing graph.
- Parse `data/raw/Domain_model.xmi`.
- Populate nodes, relationships (`CONTAINS`, `CONNECTED_BY`, `TYPED_BY`, etc.), and metadata.

## 7. Diagnostics

If you encounter issues, use these diagnostic tools in the `scripts/` folder:

### Health Check
Validate the entire deployment:
```powershell
.\scripts\health_check.ps1
```

For remote VMs, specify the URLs:
```powershell
.\scripts\health_check.ps1 -BackendUrl "http://<your-ip>:5000" -FrontendUrl "http://<your-ip>:3001"
```

This checks:
1. Backend health endpoint
2. API documentation availability
3. Graph data endpoints
4. Frontend accessibility
5. Database connectivity

### Connectivity Check
Verify Neo4j connection and inspect graph structure:
```powershell
.\.venv\Scripts\python.exe scripts\verify_connectivity.py
```

### Duplicate Check
Check for duplicate nodes and relationships:
```powershell
.\.venv\Scripts\python.exe scripts\check_duplicates.py
```

### Cleanup
Remove temporary files and caches:
```powershell
.\scripts\cleanup.ps1

# Include node_modules removal
.\scripts\cleanup.ps1 -IncludeNodeModules
```

## 8. Scripts Reference

All scripts are located in the `scripts/` folder:

| Script | Purpose |
|--------|---------|
| `install.ps1` | Automated installation and setup |
| `service_manager.ps1` | Start, stop, restart, and monitor services |
| `health_check.ps1` | Validate deployment health |
| `cleanup.ps1` | Remove temporary files and caches |
| `reload_database.py` | Clear and reload database from XMI |
| `verify_connectivity.py` | Verify Neo4j connection and graph stats |
| `check_duplicates.py` | Check for duplicate nodes/relationships |
| `start_backend.ps1` | Start backend directly (interactive) |
| `start_ui.ps1` | Start frontend directly (interactive) |
| `stop_all.ps1` | Stop all services |

---

## 9. Azure VM Deployment

When deploying to an Azure Windows VM, additional configuration is required.

### 9.1 Network Security Group (NSG) Rules

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

### 9.2 Windows Firewall Rules

On the VM itself, allow the ports through Windows Firewall (requires Administrator):

```powershell
# Run as Administrator
New-NetFirewallRule -DisplayName "MBSE Backend" -Direction Inbound -Protocol TCP -LocalPort 5000 -Action Allow
New-NetFirewallRule -DisplayName "MBSE Frontend" -Direction Inbound -Protocol TCP -LocalPort 3001 -Action Allow
```

### 9.3 Environment Configuration

Ensure `.env` uses `0.0.0.0` for host bindings (this is the default):

```dotenv
BACKEND_HOST=0.0.0.0
FRONTEND_HOST=0.0.0.0
```

For `API_BASE_URL`:
- **If accessing from the same VM's browser**: Use `http://localhost:5000`
- **If frontend will be accessed externally**: Use the public IP: `http://<public-ip>:5000`

### 9.4 Accessing the Application

After starting services and configuring firewall rules:

- **Frontend UI**: `http://<public-ip>:3001`
- **Backend API**: `http://<public-ip>:5000`
- **API Docs**: `http://<public-ip>:5000/docs`

### 9.5 Production Considerations

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
- Check logs: `.\scripts\service_manager.ps1 logs backend`

### Frontend won't start
- Check Node version: `node --version` (should be 18+)
- Reinstall dependencies: `npm ci`
- Check logs: `.\scripts\service_manager.ps1 logs frontend`

### Cannot connect to Neo4j
- Verify `.env` credentials are correct
- Run: `.\.venv\Scripts\python.exe scripts\verify_connectivity.py`
- Check Neo4j is running and accessible

### Graph is empty
- Run the reload script: `.\.venv\Scripts\python.exe scripts\reload_database.py`
- Check `data/raw/Domain_model.xmi` exists

### Cannot access from external network
- Verify NSG rules allow inbound on ports 5000 and 3001
- Verify Windows Firewall rules are created
- Verify hosts are bound to `0.0.0.0` in `.env`
