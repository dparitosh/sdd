# 🚀 Windows Deployment Package

This deployment package is **Windows-only**.

## 📦 Package Contents

### 1) Installation (`deployment/scripts/`)
- `install.ps1` / `install.bat`
  - Copies the repo to `C:\MBSE\mbse-neo4j-graph-rep`
  - Installs Python + Node dependencies
  - Builds the frontend
  - Creates a starter `.env`

### 2) Service Management (`deployment/scripts/`)
- `service_manager.ps1` / `service_manager.bat`
  - `start`, `stop`, `restart`, `status`, `logs`
  - Also supports `backend start|stop|restart` and `frontend start|stop|restart`

### 3) Cleanup (`deployment/scripts/`)
- `cleanup.ps1` / `cleanup.bat`
  - Removes caches, build artifacts, and temp files

### 4) Diagnostics (`deployment/diagnostics/`)
- `test_database.ps1`
  - Validates Neo4j credentials from `.env` and runs basic connectivity/performance checks

## 🚀 Quick Start

Run PowerShell as Administrator from the repo root:

```powershell
powershell -ExecutionPolicy Bypass -File deployment\scripts\install.ps1
```

Then:
- Edit `C:\MBSE\mbse-neo4j-graph-rep\.env`
- Start: `C:\MBSE\mbse-neo4j-graph-rep\start_all.ps1`
- Verify:
  - `http://localhost:5000/api/health`
  - `http://localhost:3001`
