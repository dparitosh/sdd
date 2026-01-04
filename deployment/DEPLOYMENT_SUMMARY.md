# 📦 MBSE Knowledge Graph - Windows Deployment Summary

This repository is deployed in a **Windows** environment.

## Included Automation

### Installation
- `deployment/scripts/install.ps1` (PowerShell, run as Administrator)
- `deployment/scripts/install.bat` (Batch alternative)

Installs dependencies, builds the frontend, and copies the app to:
- `C:\MBSE\mbse-neo4j-graph-rep`

### Service Management
- `deployment/scripts/service_manager.ps1`
- `deployment/scripts/service_manager.bat`

Supports:
- `start`, `stop`, `restart`, `status`, `logs`
- `backend start|stop|restart`
- `frontend start|stop|restart`

### Diagnostics
- `deployment/diagnostics/test_database.ps1`
  - Loads Neo4j credentials from `.env`
  - Verifies connectivity and runs basic checks

## Runtime Ports

- Frontend: `http://localhost:3001`
- Backend: `http://localhost:5000`
- Backend health: `http://localhost:5000/api/health`
- Metrics health: `http://localhost:5000/api/metrics/health`
