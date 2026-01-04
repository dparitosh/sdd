# MBSE Knowledge Graph - Windows Deployment Guide

This repository is deployed in a **Windows** environment. Linux/bash/systemd instructions and `.sh` scripts have been removed.

## What's Included

```
deployment/
├── scripts/
│   ├── install.ps1            # Automated installation (PowerShell, run as Administrator)
│   ├── install.bat            # Automated installation (Batch)
│   ├── cleanup.ps1            # Cleanup caches/artifacts
│   ├── cleanup.bat            # Cleanup caches/artifacts
│   ├── service_manager.ps1    # Start/stop/restart/status/logs
│   └── service_manager.bat    # Start/stop/restart/status/logs
├── diagnostics/
│   └── test_database.ps1      # Neo4j connectivity diagnostics
└── README.md                  # This file
```

## Prerequisites

- Windows 10/11 or Windows Server
- Python 3.12 installed and available on PATH
- Node.js 20 + npm installed and available on PATH
- Git
- Neo4j credentials: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`

## Quick Start (recommended)

### 1) Run the installer (copies to `C:\MBSE\mbse-neo4j-graph-rep`)

Open **PowerShell as Administrator**, then from the repo root:

```powershell
powershell -ExecutionPolicy Bypass -File deployment\scripts\install.ps1
```

### 2) Configure environment

Edit:
- `C:\MBSE\mbse-neo4j-graph-rep\.env`

At minimum set:
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`

### 3) Start services

Option A (created by the installer):

```powershell
& 'C:\MBSE\mbse-neo4j-graph-rep\start_all.ps1'
```

Option B (use the service manager):

```powershell
powershell -ExecutionPolicy Bypass -File C:\MBSE\mbse-neo4j-graph-rep\deployment\scripts\service_manager.ps1 start
```

### 4) Verify

- Backend health: `http://localhost:5000/api/health`
- Metrics health: `http://localhost:5000/api/metrics/health`
- Frontend UI: `http://localhost:3001`

## Diagnostics

From the installed directory (or repo root if running in-place), run:

```powershell
powershell -ExecutionPolicy Bypass -File deployment\diagnostics\test_database.ps1
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
