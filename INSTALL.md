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
NEO4J_URI=neo4j://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=tcs12345
NEO4J_DATABASE=mossec
```

3. Verify connectivity any time:
```powershell
.\.venv\Scripts\python.exe scripts\verify_connectivity.py
```

4. Verify other settings:
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
- **Backend API Docs**: [http://localhost:5000/api/docs](http://localhost:5000/api/docs)

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

This section covers the full seeding pipeline for a clean Neo4j instance.
All scripts read credentials from `.env` — ensure Section 4 configuration is complete before proceeding.

### 6.1 Source Files

The seeded graph is built from two sets of files that are already in the repository:

| Source | Path | Content |
|--------|------|---------|
| XMI domain model | `data/raw/Domain_model.xmi` | ISO 10303-4443 MOSSEC domain model — classes, properties, containment and semantic relationships |
| OSLC vocabularies | `backend/data/seed/oslc/*.ttl` | 5 Turtle files: `oslc-core`, `oslc-rm`, `oslc-ap239`, `oslc-ap242`, `oslc-ap243` |

> **If `data/raw/Domain_model.xmi` is missing** (e.g. fresh clone without the `smrlv12` submodule), copy it manually:
> ```powershell
> Copy-Item smrlv12\data\domain_models\mossec\Domain_model.xmi data\raw\Domain_model.xmi
> ```
> Or re-run the installer, which copies it automatically:
> ```powershell
> .\scripts\install.ps1 -RequireNeo4j
> ```

---

### 6.2 Full Database Reload (recommended)

The single reload script performs all seeding steps in order:

1. **Clear** all existing nodes and relationships (`DETACH DELETE`)
2. **Create constraints and indexes** in Neo4j for the schema
3. **Load the XMI domain model** → creates nodes and relationships (`CONTAINS`, `CONNECTED_BY`, `TYPED_BY`, etc.)
4. **Seed OSLC ontologies** via `OntologyIngestService` → creates `ExternalOntology` / `ExternalOwlClass` nodes
5. **Seed OSLC vocabulary** via `load_oslc_seed` → creates `OntologyClass` / `OntologyProperty` nodes
6. **Create cross-schema links** between XMI, XSD, and OSLC nodes

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts\reload_database.py
```

Expected output summary:

```
✅ XMI load complete!
  Nodes: ~3249
  Total Relationships: ~5322
🔗 Seeding OSLC ontologies...
📚 Loading OSLC seed vocabulary (OntologyClass/OntologyProperty)...
🌐 Creating cross-schema links (XMI ↔ XSD ↔ OSLC)...
✅ Full database reload complete!
```

#### Optional: Modular engine pipeline

An alternative pipeline using the `IngestionPipeline` / `GraphStore` abstraction:

```powershell
# Default (Neo4j bolt)
.\.venv\Scripts\python.exe scripts\reload_database.py --engine

# Using the Neo4j Spark Connector
.\.venv\Scripts\python.exe scripts\reload_database.py --engine --store spark
```

Use `--engine` when you need pluggable store backends or are testing the `IngesterRegistry`. For standard deployments, the default (no flag) is sufficient.

---

### 6.3 Seeding Steps Individually

If you need to run steps separately (e.g., to re-seed only OSLC without clearing the graph):

**Load domain model only** (clears DB first):
```powershell
.\.venv\Scripts\python.exe backend\scripts\reload_database.py --yes
```

**Load OSLC vocabulary only** (additive — does not clear existing nodes):
```powershell
.\.venv\Scripts\python.exe backend\scripts\load_oslc_seed.py
```

> Note: `backend\scripts\reload_database.py` is the per-step variant that requires `--yes` as a safety guard.
> `scripts\reload_database.py` (root-level) is the full pipeline used in normal deployments.

---

### 6.4 Verify After Loading

Confirm node and relationship counts match expectations:

```powershell
.\.venv\Scripts\python.exe scripts\verify_connectivity.py
```

Or query Neo4j directly:

```cypher
MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count ORDER BY count DESC;
MATCH ()-[r]->() RETURN type(r) AS rel, count(r) AS count ORDER BY count DESC;
```

---

### 6.5 Alternative: Restore from Neo4j Dump

For environments where you want to clone an already-populated database rather than re-ingesting from source files:

```bash
# On the SOURCE machine — stop Neo4j first, then dump
neo4j-admin database dump mossec --to-path=./backup/

# On the TARGET machine — load the dump (overwrites existing)
neo4j-admin database load mossec --from-path=./backup/ --overwrite-destination
```

> Requires Neo4j 4.4+ and the same edition on both machines. The scripted reload (Section 6.2) is preferred for reproducibility.

---

### 6.6 Additional Datasets: Requirements, Traceability, SDD, and SimulationRun

The base reload (Section 6.2) populates the MBSE domain model and OSLC vocabulary. The datasets below layer application-level data on top and must be run **after** the base reload, in the order shown.

#### Dataset overview

| Dataset | Node labels created | Source | Script |
|---------|--------------------|---------|---------| 
| AP hierarchy indexes & metadata | Stamps `ap_level`/`ap_schema` on all nodes; creates indexes for AP239/AP242/AP243 types | Migration 001 | `schema_migrator.py` |
| AP hierarchy sample data | `Requirement`, `RequirementVersion`, `Analysis`, `AnalysisModel`, `Part`, `Assembly`, `Material`, cross-level relationships | Migration 002 | `schema_migrator.py` |
| Requirements + traceability | `Requirement`, `Constraint`, `DataType` units; `SHOULD_BE_SATISFIED_BY` and `HAS_RULE` edges | In-script data | `create_sample_data.py` |
| SDD schema (Sprint 1) | 7 Neo4j uniqueness constraints, 10 indexes, AP239 stubs `REQ-01`–`REQ-V1` | `sdd_schema_migration.cypher` | `run_sdd_schema_migration.py` |
| SDD dossier data | 5 `SimulationDossier`, 45 `SimulationArtifact`, 40 `EvidenceCategory`, MOSSEC links | `backend/data/raw/sdd_mock_data.json` | `ingest_sdd_data.py` |
| SimulationRun workflow (Sprint 2) | 3 `SimulationRun`, `GENERATED` and `HAS_SIMULATION_RUN` edges, 2 constraints, 4 indexes | `sdd_simulation_run_migration.cypher` | `run_simulation_run_migration.py` |

---

#### Step 1 — AP hierarchy migrations (indexes + sample data)

The migration framework applies numbered files from `backend/scripts/migrations/` in order and tracks applied migrations via `:SchemaMigration` nodes (idempotent re-runs are safe).

```powershell
# Show migration status
.\.venv\Scripts\python.exe backend\scripts\schema_migrator.py --status

# Apply all pending migrations
.\.venv\Scripts\python.exe backend\scripts\schema_migrator.py
```

This applies:
- **001** — creates AP239/AP242/AP243 indexes; stamps `ap_level` and `ap_schema` on all existing nodes
- **002** — creates AP239 (`Requirement`, `Analysis`, `Approval`, `Document`), AP242 (`Part`, `Assembly`, `Material`), and AP243 sample nodes with cross-level `SATISFIES`/`BASED_ON` relationships

---

#### Step 2 — Requirements and traceability sample data

Creates `Requirement` nodes, `SHOULD_BE_SATISFIED_BY` traceability links to existing `Class` nodes, `Constraint` nodes on `Property` nodes, and `DataType` unit definitions.

```powershell
.\.venv\Scripts\python.exe backend\scripts\create_sample_data.py
```

Expected output:
```
1. Creating Requirements...        (4 Requirement nodes)
2. Creating Traceability Links...  (SHOULD_BE_SATISFIED_BY: Requirement → Class)
3. Creating Constraints...         (HAS_RULE: Property → Constraint)
4. Enhancing Properties...         (adds lower/upper/defaultValue metadata)
5. Creating Unit DataTypes...      (Meter, Second, Kilogram, Celsius, Pascal)
```

---

#### Step 3 — SDD schema migration (Sprint 1)

Applies `backend/scripts/migrations/sdd_schema_migration.cypher` — creates uniqueness constraints, performance indexes, and AP239 requirement stubs (`REQ-01` through `REQ-V1`) required as link targets for dossier artifacts.

```powershell
.\.venv\Scripts\python.exe backend\scripts\run_sdd_schema_migration.py
```

Expected: 7 constraints created, 10 indexes created, 8 AP239 requirement stubs seeded.

---

#### Step 4 — Ingest SDD dossier data

Reads `backend/data/raw/sdd_mock_data.json` and creates `SimulationDossier` / `SimulationArtifact` / `EvidenceCategory` nodes with MOSSEC relationship links to AP239 requirements.

```powershell
# Normal ingest (additive)
.\.venv\Scripts\python.exe backend\scripts\ingest_sdd_data.py

# Clear existing SDD nodes and re-ingest from scratch
.\.venv\Scripts\python.exe backend\scripts\ingest_sdd_data.py --clear

# Dry run — shows what would be created without writing to Neo4j
.\.venv\Scripts\python.exe backend\scripts\ingest_sdd_data.py --dry-run
```

Expected: 5 `SimulationDossier`, 45 `SimulationArtifact`, 40 `EvidenceCategory`, 65 MOSSEC links.

---

#### Step 5 — SimulationRun workflow migration (Sprint 2)

Applies `backend/scripts/migrations/sdd_simulation_run_migration.cypher` — adds `SimulationRun` nodes linked to dossiers and artifacts.

> **Requires Step 4 first** — `SimulationDossier` and `SimulationArtifact` nodes must exist.

```powershell
.\.venv\Scripts\python.exe backend\scripts\run_simulation_run_migration.py
```

Expected: 2 constraints, 4 indexes, 3 `SimulationRun` nodes, 4 `GENERATED` relationships, 3 `HAS_SIMULATION_RUN` relationships.

---

#### Full additional-dataset sequence

```powershell
# 1. AP hierarchy migrations (indexes + sample nodes)
.\.venv\Scripts\python.exe backend\scripts\schema_migrator.py

# 2. Requirements + traceability
.\.venv\Scripts\python.exe backend\scripts\create_sample_data.py

# 3. SDD schema (constraints / indexes / requirement stubs)
.\.venv\Scripts\python.exe backend\scripts\run_sdd_schema_migration.py

# 4. SDD dossier + artifact data
.\.venv\Scripts\python.exe backend\scripts\ingest_sdd_data.py

# 5. SimulationRun workflow
.\.venv\Scripts\python.exe backend\scripts\run_simulation_run_migration.py
```

Verify afterwards:
```powershell
.\.venv\Scripts\python.exe scripts\verify_connectivity.py
.\.venv\Scripts\python.exe backend\scripts\check_ap243_data.py
```

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

### PowerShell scripts (`scripts/`)

| Script | Purpose |
|--------|---------|
| `install.ps1` | Automated installation and setup |
| `reinstall.ps1` | Clean reinstall with optional backup/restore |
| `service_manager.ps1` | Start, stop, restart, and monitor services |
| `start_all_interactive.ps1` | Convenience wrapper for interactive start |
| `start_backend.ps1` | Start backend directly (interactive) |
| `start_ui.ps1` | Start frontend directly (interactive) |
| `stop_all.ps1` | Stop all services |
| `stop_backend.ps1` | Stop the backend service |
| `stop_ui.ps1` | Stop the frontend service |
| `health_check.ps1` | Validate deployment health |
| `cleanup.ps1` | Remove temporary files and caches |

### Python scripts (`scripts/`)

| Script | Purpose | Key flags |
|--------|---------|-----------|
| `reload_database.py` | **Full seeding pipeline** — clears DB, loads XMI domain model, seeds OSLC ontologies and vocabulary, creates cross-schema links | `--engine` (modular pipeline), `--store neo4j\|spark` |
| `verify_connectivity.py` | Verify Neo4j connection and inspect graph node/relationship counts | — |
| `check_duplicates.py` | Check for duplicate nodes and relationships | — |

### Python scripts (`backend/scripts/`)

These scripts are step-level utilities used individually or during development:

| Script | Purpose | Key flags |
|--------|---------|-----------|
| `reload_database.py` | Load domain model from XMI only (clears DB) — step-level variant | `--yes` (required safety guard), `--xmi-file <path>` |
| `load_oslc_seed.py` | Seed OSLC vocabulary (`OntologyClass` / `OntologyProperty` nodes) from `backend/data/seed/oslc/*.ttl` — additive, does not clear DB | — |
| `validate_api_alignment.py` | Validate API route alignment against the Neo4j schema | — |
| `check_kg.py` | Query and inspect knowledge graph structure | `--database <name>` |
| `check_kg_status.py` | Report overall graph health and statistics | — |
| `check_ap243_data.py` | Check `SimulationDossier` node counts and AP243 data integrity | — |
| `schema_migrator.py` | Run versioned migrations from `backend/scripts/migrations/` | `--status`, `--rollback`, `--create "desc"` |
| `create_sample_data.py` | Create `Requirement`, traceability links, `Constraint`, and `DataType` unit nodes | — |
| `run_sdd_schema_migration.py` | Apply SDD Sprint 1 schema: 7 constraints, 10 indexes, AP239 requirement stubs | — |
| `ingest_sdd_data.py` | Load `sdd_mock_data.json` → `SimulationDossier`, `SimulationArtifact`, `EvidenceCategory`, MOSSEC links | `--clear`, `--dry-run` |
| `run_simulation_run_migration.py` | Apply Sprint 2 `SimulationRun` schema and seed 3 `SimulationRun` nodes | — |

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
- **API Docs**: `http://<public-ip>:5000/api/docs`

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

If you want a clean reinstall (keeps your repo, optionally backs up `.env`/`data`):
```powershell
.\scripts\reinstall.ps1 -BackupEnv -Start
```

### Frontend won't start
- Check Node version: `node --version` (should be 18+)
- Reinstall dependencies: `npm install`
- Check logs: `.\scripts\service_manager.ps1 logs frontend`

If Vite/TypeScript tools are missing (e.g. `'vite' is not recognized`), do a clean reinstall:
```powershell
.\scripts\reinstall.ps1 -BackupEnv -ForceNodeModulesClean -Start
```

### Cannot connect to Neo4j
- Verify `.env` credentials are correct
- Run: `.\.venv\Scripts\python.exe scripts\verify_connectivity.py`
- Check Neo4j is running and accessible

### Graph is empty
- Check `data/raw/Domain_model.xmi` exists. If missing, copy it from `smrlv12\data\domain_models\mossec\` or re-run `.\scripts\install.ps1`
- Run the full seeding pipeline (see [Section 6.2](#62-full-database-reload-recommended)):
  ```powershell
  .\.venv\Scripts\python.exe scripts\reload_database.py
  ```
- If requirement / traceability / SDD data is also missing, run the additional-dataset sequence (see [Section 6.6](#66-additional-datasets-requirements-traceability-sdd-and-simulationrun))
- After reload, verify counts:
  ```powershell
  .\.venv\Scripts\python.exe scripts\verify_connectivity.py
  ```

### Cannot access from external network
- Verify NSG rules allow inbound on ports 5000 and 3001
- Verify Windows Firewall rules are created
- Verify hosts are bound to `0.0.0.0` in `.env`
