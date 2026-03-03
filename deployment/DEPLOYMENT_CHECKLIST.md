# 🚀 MBSE Knowledge Graph - Windows Deployment Checklist

## Pre-Deployment

- [ ] Windows host prepared (Windows 10/11 or Windows Server)
- [ ] Python 3.10+ installed (and on PATH)
- [ ] Node.js 18+ and npm installed (and on PATH)
- [ ] Git installed
- [ ] Neo4j running with credentials ready (`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`)
- [ ] OpenSearch 2.x+ installed and running on `:9200` (for vector search / AI)
- [ ] Ollama installed and running on `:11434` (optional, for local LLM)

## Deploy (recommended path)

### Step 1: Run installer (no admin required)

- [ ] Open PowerShell
- [ ] From repo root, run:

```powershell
.\scripts\install.ps1
```

### Step 2: Configure `.env`

- [ ] Edit `.env` in the repo root
- [ ] Set Neo4j values:
  - `NEO4J_URI=neo4j://127.0.0.1:7687`
  - `NEO4J_USER=neo4j`
  - `NEO4J_PASSWORD=<your-password>`
  - `NEO4J_DATABASE=mossec`
- [ ] Verify OpenSearch connectivity:
  - `OPENSEARCH_URL=http://localhost:9200`
- [ ] Verify Ollama settings (if using local LLM):
  - `LLM_PROVIDER=ollama`
  - `OLLAMA_BASE_URL=http://localhost:11434`

### Step 3: Validate database connectivity

- [ ] Run:

```powershell
.\.venv\Scripts\python.exe scripts\verify_connectivity.py
```

### Step 4: Start services

- [ ] Start all services:

```powershell
.\scripts\service_manager.ps1 start
```

or with live logs:

```powershell
.\scripts\start_all_interactive.ps1 -Inspect
```

### Step 5: Verify

- [ ] Backend health: `http://localhost:5000/api/health`
- [ ] API docs: `http://localhost:5000/api/docs`
- [ ] Frontend UI: `http://localhost:3001`

## Smoke Troubleshooting

- Run full health check:

```powershell
.\scripts\health_check.ps1
```

- Confirm ports are listening:

```powershell
netstat -ano | findstr ":5000"
netstat -ano | findstr ":3001"
```
