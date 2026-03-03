# MBSE Knowledge Graph - Windows Deployment Guide

This repository is deployed in a **Windows** environment. Linux/bash/systemd instructions and `.sh` scripts have been removed.

## What's Included

### Primary scripts (canonical location: `scripts/`)

```
scripts/
├── install.ps1                # Automated installation (no admin required)
├── reinstall.ps1              # Clean reinstall with backup/restore
├── reinstall_clean.ps1        # Full re-clone + reinstall
├── service_manager.ps1        # Start/stop/restart/status/logs
├── start_all_interactive.ps1  # Interactive startup with prereq checks
├── start_backend.ps1          # Start backend directly
├── start_ui.ps1               # Start frontend directly
├── start_opensearch.ps1       # OpenSearch lifecycle management
├── stop_all.ps1               # Stop all services
├── stop_backend.ps1           # Stop backend
├── stop_ui.ps1                # Stop frontend
├── health_check.ps1           # Deployment health validation
├── cleanup.ps1                # Remove temp files / caches
├── reload_database.py         # Full Neo4j seeding pipeline
└── verify_connectivity.py     # Neo4j connection test
```

### Legacy wrappers (`deployment/scripts/`)

These forward to `scripts/` for backward compatibility:

```
deployment/
├── scripts/
│   ├── install.ps1            # → forwards to scripts/install.ps1
│   └── service_manager.ps1    # → forwards to scripts/service_manager.ps1
└── diagnostics/
    ├── health_check.ps1       # Health checker
    ├── test_database.ps1      # Neo4j connectivity diagnostics
    └── verify_connectivity.py # Connection test
```

## Prerequisites

- Windows 10/11 or Windows Server
- Python 3.10+ installed and available on PATH
- Node.js 18+ with npm installed and available on PATH
- Git
- Neo4j (local Desktop or AuraDB) with credentials: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
- OpenSearch 2.x+ (for vector search / AI features)
- Ollama (optional, for local LLM / embeddings)

## Quick Start (recommended)

### 1) Run the installer (from repo root, no admin required)

```powershell
.\scripts\install.ps1
```

### 2) Configure environment

Edit `.env` in the repo root. At minimum set:
- `NEO4J_URI=neo4j://127.0.0.1:7687`
- `NEO4J_USER`, `NEO4J_PASSWORD`, `NEO4J_DATABASE=mossec`

### 3) Start services

```powershell
# Start backend + frontend (background)
.\scripts\service_manager.ps1 start

# Or interactive with live logs
.\scripts\start_all_interactive.ps1 -Inspect
```

### 4) Verify

- Backend health: `http://localhost:5000/api/health`
- API docs: `http://localhost:5000/api/docs`
- Frontend UI: `http://localhost:3001`

## Diagnostics

```powershell
.\scripts\health_check.ps1
```

## In-repo development (no copy/install)

From the repo root:

```powershell
./scripts/start_backend.ps1
./scripts/start_ui.ps1
```

To run either detached:

```powershell
./scripts/start_backend.ps1 -Detach
./scripts/start_ui.ps1 -Detach
```
