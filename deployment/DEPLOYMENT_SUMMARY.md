# 📦 MBSE Knowledge Graph - Windows Deployment Summary

This repository is deployed in a **Windows** environment.

## Included Automation

### Installation
- `scripts/install.ps1` — automated installation (no admin required)
- `scripts/reinstall.ps1` — clean reinstall with optional backup/restore
- `scripts/install_oslc.ps1` — OSLC ontology dependencies and seeding

Installs dependencies, builds the frontend, and configures the project in-place.

### Service Management
- `scripts/service_manager.ps1` — start/stop/restart/status/logs
- `scripts/start_all_interactive.ps1` — interactive startup with prerequisite checks
- `scripts/start_opensearch.ps1` — OpenSearch lifecycle management

Supports:
- `start`, `stop`, `restart`, `status`, `logs`
- `backend start|stop|restart`
- `frontend start|stop|restart`

### Diagnostics
- `scripts/health_check.ps1` — 5-step deployment health validation
- `scripts/verify_connectivity.py` — Neo4j connection and graph inspection

## Runtime Ports

| Service | URL | Notes |
|---------|-----|-------|
| Frontend | `http://localhost:3001` | React + Vite dev server |
| Backend API | `http://localhost:5000` | FastAPI (uvicorn) |
| Backend health | `http://localhost:5000/api/health` | |
| API docs | `http://localhost:5000/api/docs` | Interactive Swagger UI |
| Neo4j Bolt | `neo4j://127.0.0.1:7687` | Graph database |
| OpenSearch | `http://localhost:9200` | Vector search |
| Ollama | `http://localhost:11434` | Local LLM / embeddings |
