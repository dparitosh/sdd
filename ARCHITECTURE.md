# System Architecture

## Overview

The MBSE Knowledge Graph system uses a **modern decoupled architecture** with separate frontend and backend services.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     User Browser                             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ HTTPS
                         ▼
┌─────────────────────────────────────────────────────────────┐
│           React Frontend (Port 3001)                         │
│  • Modern TypeScript/React Dashboard                         │
│  • ISO AP239/AP242/AP243 Dashboards                         │
│  • Requirements Manager & Parts Explorer                     │
│  • Vite dev server with HMR                                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Proxy: /api/* → localhost:5000
                         ▼
┌─────────────────────────────────────────────────────────────┐
│          Flask REST API (Port 5000)                          │
│  • REST API endpoints (/api/*)                               │
│  • Neo4j database integration                                │
│  • Authentication & Authorization                            │
│  • Root (/) redirects to frontend                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ neo4j+s://
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Neo4j Aura Database                             │
│  • 3,275+ nodes (AP239/AP242/AP243)                         │
│  • 10+ cross-level relationship types                        │
│  • ISO 10303 SMRL compliant schema                           │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Frontend (Port 3001)
**Location:** `/workspaces/mbse-neo4j-graph-rep/frontend/`

**Technology Stack:**
- React 18 + TypeScript
- Vite (build tool with HMR)
- TanStack Query (data fetching)
- Tailwind CSS + shadcn/ui
- React Router (navigation)

**Key Routes:**
- `/dashboard` - Main system overview with periodic table visualization
- `/ap239/requirements` - AP239 Requirements Dashboard
- `/ap242/parts` - AP242 Parts & Materials Explorer
- `/search` - Advanced search interface
- `/query-editor` - Cypher query editor
- `/traceability` - Cross-schema traceability matrix

**How to Start:**
```bash
cd frontend
npm install
npm run dev
```

**Environment:**
- `VITE_PORT=3001` - Frontend port
- `API_BASE_URL=http://127.0.0.1:5000` - Backend API URL

### 2. Backend (Port 5000)
**Location:** `/workspaces/mbse-neo4j-graph-rep/src/web/`

**Technology Stack:**
- Flask 3.x (Python web framework)
- Neo4j Python Driver
- Flask-CORS (cross-origin support)
- Flask-SocketIO (real-time updates)

**Key Endpoints:**
- `GET /` - **Redirects to frontend dashboard**
- `GET /info` - API information and architecture overview
- `GET /api/health` - Health check with database connectivity
- `GET /api/stats` - Graph statistics
- `GET /api/ap239/*` - ISO 10303-239 PLCS endpoints
- `GET /api/ap242/*` - ISO 10303-242 CAD endpoints
- `GET /api/ap243/*` - ISO 10303-243 Reference data endpoints
- `GET /api/hierarchy/*` - Cross-schema navigation & traceability

**How to Start:**
```bash
cd /workspaces/mbse-neo4j-graph-rep
export PYTHONPATH=/workspaces/mbse-neo4j-graph-rep
python3 src/web/app.py
```

**Environment:**
- `NEO4J_URI=neo4j+s://...` - Neo4j Aura connection string
- `NEO4J_USER=neo4j` - Database username
- `NEO4J_PASSWORD=...` - Database password
- `FRONTEND_URL=https://...` - Frontend URL for redirects

### 3. Database (Neo4j Aura)
**Connection:** `neo4j+s://2cccd05b.databases.neo4j.io`

**Schema:**
- **AP239 Nodes:** Requirements, Specifications, Approvals, Changes, Versions
- **AP242 Nodes:** Parts, Materials, Properties, Geometries, Assemblies
- **AP243 Nodes:** Units, ValueTypes, OntologyClasses, Classifications
- **Cross-Level:** Traceability links connecting AP239 ↔ AP242 ↔ AP243

## Unified Access

### Production Setup

**User Access:**
1. Visit frontend URL: `https://vigilant-space-goldfish-5x6rp4rvpxg244wj-3001.app.github.dev/dashboard`
2. All UI interactions happen in React frontend
3. API calls are automatically proxied to backend (port 5000)

**Developer Access:**
- Frontend Dev: Port 3001
- Backend API: Port 5000
- Database: Neo4j Aura (cloud)

### Why This Architecture?

**Benefits:**
1. **Separation of Concerns:** UI logic separate from business logic
2. **Modern Development:** HMR for instant frontend updates
3. **Scalability:** Frontend and backend can scale independently
4. **API-First:** Backend serves as reusable REST API
5. **Better UX:** React provides responsive, interactive dashboards

**Previous Setup (Deprecated):**
- Flask served HTML template at `/` (3000+ lines of embedded JS)
- Mixing backend rendering with frontend logic
- Difficult to maintain and extend

**Current Setup:**
- Flask redirects `/` to React frontend
- Clean REST API under `/api/*`
- Modern React dashboards with TypeScript
- Easy to extend and maintain

## Key Features

### ISO 10303 Application Protocol Support

**AP239 - Product Life Cycle Support**
- Requirements management with versions
- Change control and approval workflows
- Specifications and analysis
- Full traceability chains

**AP242 - 3D Managed Product Data**
- Parts catalog with BOMs
- Materials library with properties
- CAD geometry references
- Assembly structures

**AP243 - Reference Data**
- Units and measurements
- Classification ontologies
- Cross-schema linking
- Standardized value types

### Cross-Schema Navigation

The system provides **traceability matrix** functionality:
- Requirement → Part mapping
- Part → Material → Unit relationships
- Change → Approval → Version history
- Full graph traversal capabilities

## Development Workflow

### Starting Both Services

```bash
# Terminal 1: Start Backend
cd /workspaces/mbse-neo4j-graph-rep
export PYTHONPATH=$(pwd)
python3 src/web/app.py

# Terminal 2: Start Frontend
cd frontend
npm run dev
```

### Testing the Integration

```bash
# Test backend health
curl http://localhost:5000/api/health

# Test redirect
curl -I http://localhost:5000/

# Test AP239 endpoint
curl http://localhost:5000/api/ap239/requirements

# Test info endpoint
curl http://localhost:5000/info | jq
```

### Making Changes

**Frontend Changes:**
1. Edit files in `frontend/src/`
2. Vite HMR instantly reflects changes
3. No restart needed

**Backend Changes:**
1. Edit files in `src/web/routes/`
2. Restart Flask server
3. Changes reflected immediately

## URLs Reference

| Service | Development URL | Production URL |
|---------|----------------|----------------|
| Frontend | http://localhost:3001 | https://vigilant-space-goldfish-5x6rp4rvpxg244wj-3001.app.github.dev |
| Backend | http://localhost:5000 | https://vigilant-space-goldfish-5x6rp4rvpxg244wj-5000.app.github.dev |
| Database | neo4j+s://2cccd05b.databases.neo4j.io | (same) |

## Next Steps

1. ✅ **Backend redirects to frontend** - Eliminates duplicate UI
2. ✅ **REST APIs working** - 8/8 AP endpoints functional
3. ✅ **React dashboards implemented** - AP239/AP242/AP243 views ready
4. 🔄 **Frontend testing needed** - Verify dashboards load real data
5. 📋 **Documentation** - Update user guides with new URLs

## Support

For issues or questions:
- Backend issues: Check `/api/health` and server logs
- Frontend issues: Check browser console and network tab
- Database issues: Verify Neo4j Aura connectivity
- Architecture questions: See `/info` endpoint
