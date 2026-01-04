# 🚀 MBSE Knowledge Graph - Windows Deployment Checklist

## Pre-Deployment

- [ ] Windows host prepared (Windows 10/11 or Windows Server)
- [ ] Python 3.12 installed (and on PATH)
- [ ] Node.js 20 + npm installed (and on PATH)
- [ ] Git installed
- [ ] Neo4j credentials ready (`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`)

## Deploy (recommended path)

### Step 1: Run installer (Administrator)

- [ ] Open PowerShell **as Administrator**
- [ ] From repo root, run:

```powershell
powershell -ExecutionPolicy Bypass -File deployment\scripts\install.ps1
```

- [ ] Confirm files are copied to `C:\MBSE\mbse-neo4j-graph-rep`

### Step 2: Configure `.env`

- [ ] Edit `C:\MBSE\mbse-neo4j-graph-rep\.env`
- [ ] Set Neo4j values:
  - `NEO4J_URI`
  - `NEO4J_USER`
  - `NEO4J_PASSWORD`

### Step 3: Validate database connectivity

- [ ] In PowerShell, from `C:\MBSE\mbse-neo4j-graph-rep` run:

```powershell
powershell -ExecutionPolicy Bypass -File deployment\diagnostics\test_database.ps1
```

### Step 4: Start services

- [ ] Start both services:

```powershell
& 'C:\MBSE\mbse-neo4j-graph-rep\start_all.ps1'
```

or using the service manager:

```powershell
powershell -ExecutionPolicy Bypass -File C:\MBSE\mbse-neo4j-graph-rep\deployment\scripts\service_manager.ps1 start
```

### Step 5: Verify

- [ ] Backend health: `http://localhost:5000/api/health`
- [ ] Metrics health: `http://localhost:5000/api/metrics/health`
- [ ] Frontend UI: `http://localhost:3001`

## Smoke Troubleshooting

- Check logs (service manager):

```powershell
powershell -ExecutionPolicy Bypass -File C:\MBSE\mbse-neo4j-graph-rep\deployment\scripts\service_manager.ps1 logs
```

- Confirm ports are listening:

```powershell
netstat -ano | findstr ":5000"
netstat -ano | findstr ":3001"
```
