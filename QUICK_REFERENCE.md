# Phase 2 Quick Reference
## Essential Commands & Endpoints

---

## 🚀 Starting Services

### Development Mode
```bash
# Backend (FastAPI)
./start_backend.sh
# or (manual)
python -m uvicorn src.web.app_fastapi:app --host 0.0.0.0 --port 5000

# Frontend (Vite)
npm run dev

# Check status
curl http://localhost:5000/api/health
curl http://localhost:3001
```

### Production Mode (Docker)
```bash
# Build & start all services
docker compose -f docker-compose.prod.yml up -d

# Check logs
docker compose -f docker-compose.prod.yml logs -f

# Stop
docker compose -f docker-compose.prod.yml down
```

---

## 🤖 AI Agent Usage

### Interactive Mode
```bash
# Set API key
export OPENAI_API_KEY=your-key-here

# Run agent
python -m src.agents.langgraph_agent

# Or in Python
from src.agents.langgraph_agent import MBSEAgent
agent = MBSEAgent()
response = agent.run("How many classes are in the system?")
print(response)
```

### Example Queries
```python
# Database statistics
agent.run("How many classes are in the system?")

# Traceability analysis
agent.run("Show me the traceability from requirements to design elements")

# Impact analysis
agent.run("What would be impacted if I change the Sensor class?")

# Parameter extraction
agent.run("Extract all parameters from the Control System class")

# Custom analysis
agent.run("Find all classes that have more than 10 properties")
```

---

## 🌐 API Endpoints

### Core APIs
```bash
# Health check
GET http://localhost:5000/api/health

# Statistics
GET http://localhost:5000/api/stats

# List classes
GET http://localhost:5000/api/v1/Class?limit=10

# Get specific class
GET http://localhost:5000/api/v1/Class/{id}

# Search
GET http://localhost:5000/api/v1/Class?search=Person

# Custom Cypher
POST http://localhost:5000/api/v1/query
{
  "query": "MATCH (n:Class) RETURN n.name LIMIT 5"
}

# Traceability
GET http://localhost:5000/api/v1/traceability?depth=2

# Parameters
GET http://localhost:5000/api/v1/parameters?limit=20

# OpenAPI docs
GET http://localhost:5000/api/openapi.json
```

---

## 🧪 Testing Commands

### Run All Tests
```bash
# All tests
pytest

# Specific suite
pytest tests/unit/ -v
pytest tests/integration/ -v

# With coverage
pytest --cov=src --cov-report=html

# Specific test file
pytest tests/unit/test_neo4j_service.py -v

# Single test
pytest tests/unit/test_neo4j_service.py::TestNeo4jService::test_initialization -v
```

### Service Tests
```bash
# Neo4j connection
python test_neo4j_connection.py

# Service layer
python test_service_layer.py

# REST API
python scripts/test_rest_api.py
```

---

## 🐳 Docker Commands

### Build
```bash
# Build backend
docker build -t mbse-backend .

# Build frontend
docker build -f Dockerfile.frontend -t mbse-frontend .

# Build all (compose)
docker compose -f docker-compose.prod.yml build
```

### Run
```bash
# Start all services
docker compose -f docker-compose.prod.yml up -d

# Start specific service
docker compose -f docker-compose.prod.yml up -d backend

# View logs
docker compose -f docker-compose.prod.yml logs -f backend

# Shell access
docker exec -it mbse-backend /bin/bash
```

### Monitor
```bash
# List containers
docker ps

# Container stats
docker stats

# Health status
docker inspect --format='{{.State.Health.Status}}' mbse-backend
```

### Clean Up
```bash
# Stop all
docker compose -f docker-compose.prod.yml down

# Remove volumes
docker compose -f docker-compose.prod.yml down -v

# Clean system
docker system prune -a
```

---

## 📊 Neo4j Commands

### Cypher Browser (http://localhost:7474)
```cypher
// Count all nodes
MATCH (n) RETURN count(n) as total

// Count by type
MATCH (n) RETURN labels(n)[0] as type, count(*) as count
ORDER BY count DESC

// Get all classes
MATCH (n:Class) 
RETURN n.name, n.uid 
LIMIT 10

// Find relationships
MATCH (a)-[r]->(b)
RETURN type(r) as rel_type, count(*) as count
ORDER BY count DESC

// Traceability query
MATCH path = (req:Requirement)-[*1..3]-(design)
WHERE design:Class OR design:Component
RETURN path
LIMIT 100

// Impact analysis
MATCH (n:Class {name: 'Sensor'})-[*1..3]-(impacted)
RETURN DISTINCT labels(impacted)[0] as type, 
       count(impacted) as count
```

---

## 🔧 Development Commands

### Install Dependencies
```bash
# Base dependencies
pip install -r requirements.txt

# Phase 2 dependencies
pip install -r requirements-phase2.txt

# Frontend dependencies
npm install
```

### Code Quality
```bash
# Format code
black src/ tests/

# Lint
flake8 src/ tests/
pylint src/

# Type check
mypy src/

# Security scan
bandit -r src/
```

### Database Operations
```bash
# Load sample data
python scripts/create_sample_data.py

# Reload database
python scripts/reload_database.py

# Validate API alignment
python scripts/validate_api_alignment.py
```

---

## 📝 Configuration Files

### Environment Variables (.env)
```bash
# Neo4j Connection
NEO4J_URI=neo4j+s://your-neo4j-uri.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
NEO4J_DATABASE=neo4j

# Flask
FLASK_ENV=development
SECRET_KEY=your-secret-key

# AI Agent
OPENAI_API_KEY=your-openai-key
LANGSMITH_API_KEY=your-langsmith-key

# Monitoring
LOG_LEVEL=INFO
```

### Docker Environment
```bash
# For docker compose
cp .env.example .env
# Edit values for production
```

---

## 🔍 Monitoring & Logs

### Application Logs
```bash
# Backend logs
tail -f logs/app.log

# Docker logs
docker compose -f docker-compose.prod.yml logs -f backend

# Filter errors
docker compose -f docker-compose.prod.yml logs backend | grep ERROR
```

### Metrics
```bash
# Prometheus metrics
curl http://localhost:5000/metrics

# Health endpoints
curl http://localhost:5000/health
curl http://localhost:3001/health
```

---

## 🐛 Troubleshooting

### Backend Won't Start
```bash
# Check Neo4j connection
python test_neo4j_connection.py

# Check environment
env | grep NEO4J

# Check port
lsof -i :5000

# Kill existing process
pkill -f "python.*web/app.py"
```

### Frontend Issues
```bash
# Clear npm cache
npm cache clean --force
rm -rf node_modules package-lock.json
npm install

# Kill existing process
lsof -i :3001
kill -9 <PID>
```

### Docker Issues
```bash
# Check container logs
docker logs mbse-backend

# Inspect container
docker inspect mbse-backend

# Restart service
docker compose -f docker-compose.prod.yml restart backend

# Check network
docker network inspect mbse-network
```

### Neo4j Connection
```bash
# Test connection
neo4j-driver-test %NEO4J_URI%

# Check Neo4j status
systemctl status neo4j  # if running as service

# Neo4j logs
tail -f /var/log/neo4j/neo4j.log
```

---

## 📚 Useful URLs

### Local Development
- Backend API: http://localhost:5000
- Frontend UI: http://localhost:3001
- Neo4j Browser: http://localhost:7474
- OpenAPI Docs: http://localhost:5000/api/openapi.json
- Health Check: http://localhost:5000/health

### Documentation
- Phase 2 Plan: `PHASE2_PLAN.md`
- Phase 2 Kickoff: `PHASE2_KICKOFF.md`
- Docker Guide: `DOCKER_GUIDE.md`
- API Guide: `REST_API_GUIDE.md`
- Quick Start: `QUICKSTART.md`

---

## 🎯 Common Workflows

### Daily Development
```bash
# 1. Start services
./start_backend.sh &
npm run dev &

# 2. Make changes
# Edit code...

# 3. Test
pytest tests/unit/test_your_changes.py

# 4. Commit
git add .
git commit -m "Your changes"
git push
```

### Testing Agent
```bash
# 1. Set API key
export OPENAI_API_KEY=your-key

# 2. Test interactively
python -c "
from src.agents.langgraph_agent import MBSEAgent
agent = MBSEAgent()
print(agent.run('How many classes?'))
"

# 3. Benchmark
python tests/benchmark_agent.py
```

### Docker Deployment
```bash
# 1. Build
docker compose -f docker-compose.prod.yml build

# 2. Test locally
docker compose -f docker-compose.prod.yml up

# 3. If successful, detach
docker compose -f docker-compose.prod.yml up -d

# 4. Monitor
docker compose -f docker-compose.prod.yml logs -f
```

---

**Last Updated**: December 8, 2025  
**Quick Access**: Keep this file open while developing!
