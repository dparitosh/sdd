# MBSE AI Agent Framework - User Guide

## Overview

This guide covers the **LangGraph-based AI Agent** and **JWT Authentication** features added to the MBSE Knowledge Graph system.

---

## Table of Contents

1. [JWT Authentication](#jwt-authentication)
   - [Setup](#authentication-setup)
   - [API Endpoints](#authentication-endpoints)
   - [Usage Examples](#authentication-examples)
   - [Protecting Routes](#protecting-routes)

2. [LangGraph AI Agent](#langgraph-ai-agent)
   - [Setup](#agent-setup)
   - [Architecture](#agent-architecture)
   - [Usage Examples](#agent-examples)
   - [Available Tools](#agent-tools)

3. [Integration Examples](#integration-examples)
4. [Production Deployment](#production-deployment)

---

## JWT Authentication

### Authentication Setup

1. **Configure Environment Variables**

```bash
# Add to .env file
JWT_SECRET_KEY=your-secret-key-change-in-production
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
```

2. **Generate Secure Secret Key** (Production)

```python
import secrets
print(secrets.token_urlsafe(32))
```

### Authentication Endpoints

#### 1. **POST /api/auth/login** - User Login

**Request:**
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "username": "admin",
    "role": "admin"
  }
}
```

#### 2. **POST /api/auth/refresh** - Refresh Access Token

**Request:**
```bash
curl -X POST http://localhost:5000/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

#### 3. **POST /api/auth/logout** - Logout (Revoke Token)

**Request:**
```bash
curl -X POST http://localhost:5000/api/auth/logout \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response:**
```json
{
  "message": "Successfully logged out"
}
```

#### 4. **GET /api/auth/verify** - Verify Token

**Request:**
```bash
curl -X GET http://localhost:5000/api/auth/verify \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response:**
```json
{
  "valid": true,
  "user": {
    "username": "admin",
    "role": "admin"
  }
}
```

### Authentication Examples

#### Python Client Example

```python
import requests

BASE_URL = "http://localhost:5000"

# 1. Login
response = requests.post(f"{BASE_URL}/api/auth/login", json={
    "username": "admin",
    "password": "admin123"
})
tokens = response.json()
access_token = tokens['access_token']

# 2. Make authenticated request
headers = {"Authorization": f"Bearer {access_token}"}
response = requests.get(f"{BASE_URL}/api/classes", headers=headers)
print(response.json())

# 3. Refresh token when expired
response = requests.post(f"{BASE_URL}/api/auth/refresh", json={
    "refresh_token": tokens['refresh_token']
})
new_access_token = response.json()['access_token']
```

#### JavaScript/Node.js Example

```javascript
const axios = require('axios');

const BASE_URL = 'http://localhost:5000';

// 1. Login
const login = async () => {
  const response = await axios.post(`${BASE_URL}/api/auth/login`, {
    username: 'admin',
    password: 'admin123'
  });
  return response.data;
};

// 2. Make authenticated request
const getClasses = async (accessToken) => {
  const response = await axios.get(`${BASE_URL}/api/classes`, {
    headers: { Authorization: `Bearer ${accessToken}` }
  });
  return response.data;
};

// Usage
(async () => {
  const tokens = await login();
  const classes = await getClasses(tokens.access_token);
  console.log(classes);
})();
```

### Protecting Routes

#### Using `@require_auth` Decorator

```python
from flask import Blueprint, jsonify
from web.middleware.auth import require_auth

bp = Blueprint('protected', __name__)

@bp.route('/protected-resource')
@require_auth
def protected_resource():
    # request.user is automatically populated with user info
    return jsonify({
        "message": f"Hello {request.user['username']}!",
        "role": request.user['role']
    })
```

#### Using `@require_role` Decorator

```python
from web.middleware.auth import require_auth, require_role

@bp.route('/admin-only')
@require_auth
@require_role('admin')
def admin_only():
    return jsonify({"message": "Admin access granted"})
```

---

## LangGraph AI Agent

### Agent Setup

1. **Configure OpenAI API Key**

```bash
# Add to .env file
OPENAI_API_KEY=sk-your-openai-api-key
```

2. **Verify Installation**

```bash
pip list | grep langgraph
# Should show: langgraph, langchain, langchain-core, langchain-openai
```

### Agent Architecture

The agent uses a **ReAct-style** (Reasoning + Acting) workflow:

```
┌─────────────┐
│  Understand │  ← Parse user query, categorize task
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    Plan     │  ← Decide which tools to use
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Execute Tool│  ← Call API tools (search, traceability, etc.)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Reason    │  ← Analyze results, decide next step
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Respond   │  ← Generate final answer
└─────────────┘
```

**Key Features:**
- **Chain-of-thought reasoning**: Agent explains its thinking
- **Multi-step planning**: Breaks complex queries into steps
- **Tool orchestration**: Uses 7 API tools automatically
- **Error recovery**: Handles failures gracefully

### Agent Tools

The agent has access to 7 tools:

| Tool | Description | Example Use |
|------|-------------|-------------|
| `search_artifacts` | Search by name/description | "Find all sensor classes" |
| `get_artifact_details` | Get full artifact info | "Show details of Class_123" |
| `get_traceability` | Requirements-to-design traces | "Trace REQ_001 to design" |
| `get_impact_analysis` | Change impact analysis | "What's affected by Sensor change?" |
| `get_parameters` | Extract design parameters | "Get all parameters from Control System" |
| `execute_cypher` | Custom Neo4j queries | "Find all circular dependencies" |
| `get_statistics` | Database overview | "How many nodes in the graph?" |

### Agent Examples

#### Example 1: Basic Query

```python
from agents.langgraph_agent import MBSEAgent
import os

# Initialize agent
agent = MBSEAgent(api_key=os.getenv("OPENAI_API_KEY"))

# Run query
response = agent.run("How many classes are in the system?")
print(response)
```

**Output:**
```
Understanding: Task is statistics query about node counts

Planning: Will use get_statistics tool to retrieve database overview

Executing: get_statistics

Reasoning: Statistics show 3,257 nodes total. Classes are one of the node types.

Response: The system contains 427 classes. The database has a total of 3,257 nodes 
including 427 Classes, 89 Packages, 342 Properties, and other SMRL artifacts.
```

#### Example 2: Traceability Analysis

```python
response = agent.run(
    "Show me how requirement REQ_PERF_002 traces to design elements"
)
print(response)
```

**Agent Workflow:**
1. **Understand**: Recognizes traceability query
2. **Plan**: Will use `get_traceability` with source filter
3. **Execute**: Calls `/api/v1/traceability?source_type=Requirement`
4. **Reason**: Analyzes traceability matrix
5. **Respond**: Provides formatted traceability report

#### Example 3: Impact Analysis

```python
response = agent.run(
    "If I modify the Sensor class, what else will be affected?"
)
```

**Agent Workflow:**
1. **Search**: Find Sensor class ID
2. **Get Details**: Retrieve Sensor class info
3. **Impact Analysis**: Call `/api/v1/impact/{sensor_id}`
4. **Respond**: List upstream/downstream impacts

#### Example 4: Multi-Step Complex Query

```python
response = agent.run(
    "Find all parameters in classes related to temperature control, "
    "check if they have valid constraints, and export to JSON"
)
```

**Agent Workflow:**
1. **Search**: Find temperature-related classes
2. **Get Parameters**: Extract parameters from each class
3. **Check Constraints**: Validate constraint rules
4. **Execute Cypher**: Custom query for additional validation
5. **Format**: Prepare JSON export
6. **Respond**: Provide comprehensive analysis

### Agent API Endpoints (Optional - Future)

You can wrap the agent in a Flask endpoint:

```python
from flask import Blueprint, request, jsonify
from agents.langgraph_agent import MBSEAgent
import os

agent_bp = Blueprint('agent', __name__)
agent = MBSEAgent(api_key=os.getenv("OPENAI_API_KEY"))

@agent_bp.route('/api/agent/query', methods=['POST'])
def query_agent():
    """
    POST /api/agent/query
    Body: {"query": "Your question here"}
    """
    data = request.get_json()
    query = data.get('query')
    
    if not query:
        return jsonify({"error": "Missing query"}), 400
    
    response = agent.run(query)
    
    return jsonify({
        "query": query,
        "response": response
    })
```

**Usage:**
```bash
curl -X POST http://localhost:5000/api/agent/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Show traceability for REQ_PERF_002"}'
```

---

## Integration Examples

### Complete Workflow: Authenticated Agent Query

```python
import requests
import os

BASE_URL = "http://localhost:5000"

# 1. Authenticate
auth_response = requests.post(f"{BASE_URL}/api/auth/login", json={
    "username": "admin",
    "password": "admin123"
})
access_token = auth_response.json()['access_token']

# 2. Use agent via API (if agent endpoint is registered)
headers = {"Authorization": f"Bearer {access_token}"}
agent_response = requests.post(
    f"{BASE_URL}/api/agent/query",
    headers=headers,
    json={"query": "Analyze impact of changing the Sensor class"}
)

print(agent_response.json()['response'])
```

### Programmatic Agent Usage (Direct)

```python
from agents.langgraph_agent import MBSEAgent
import os

# Initialize agent with OpenAI API key
agent = MBSEAgent(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="http://localhost:5000"
)

# Example queries
queries = [
    "How many requirements trace to design elements?",
    "What parameters in the Control System class have constraints?",
    "Analyze the impact of changing the Data Encryption requirement",
    "Export all traceability links to GraphML format",
]

for query in queries:
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print(f"{'='*60}")
    
    response = agent.run(query)
    print(f"\nResponse:\n{response}\n")
```

---

## Production Deployment

### 1. **Environment Configuration**

```bash
# Production .env file
NEO4J_URI=neo4j+s://your-production-instance.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=strong-password

# JWT - Use strong random secret
JWT_SECRET_KEY=<output-of-secrets.token_urlsafe(32)>
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<strong-password>

# OpenAI (optional for agent)
OPENAI_API_KEY=sk-your-production-key

# Flask
FLASK_ENV=production
SECRET_KEY=<flask-secret-key>
```

### 2. **Security Checklist**

- ✅ Change default JWT_SECRET_KEY
- ✅ Change default ADMIN_PASSWORD
- ✅ Use HTTPS in production (not HTTP)
- ✅ Enable rate limiting (use Flask-Limiter)
- ✅ Use Redis for token blacklist (not in-memory)
- ✅ Enable CORS selectively (not wildcard)
- ✅ Use database for user management (not hardcoded)
- ✅ Hash passwords with bcrypt
- ✅ Monitor authentication logs
- ✅ Set short token expiration (15-60 minutes)

### 3. **Recommended Improvements**

#### User Database (Instead of Hardcoded Credentials)

```python
# Example: SQLAlchemy User model
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
```

#### Token Blacklist with Redis

```python
import redis
from datetime import timedelta

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def revoke_token(token: str, expires_in: int):
    """Add token to Redis blacklist with expiration"""
    redis_client.setex(f"blacklist:{token}", timedelta(seconds=expires_in), "1")

def is_token_revoked(token: str) -> bool:
    """Check if token is in Redis blacklist"""
    return redis_client.exists(f"blacklist:{token}") > 0
```

### 4. **Docker Deployment**

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set environment variables
ENV FLASK_APP=src/web/app.py
ENV FLASK_ENV=production

EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "src.web.app:app"]
```

```yaml
# deployment/docker-compose.yml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "5000:5000"
    environment:
      - NEO4J_URI=${NEO4J_URI}
      - NEO4J_USER=${NEO4J_USER}
      - NEO4J_PASSWORD=${NEO4J_PASSWORD}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    env_file:
      - .env
    restart: unless-stopped
```

---

## Testing

### Authentication Tests

```python
# tests/integration/test_auth.py
import pytest
import requests

BASE_URL = "http://localhost:5000"

def test_login():
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_invalid_login():
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": "admin",
        "password": "wrong"
    })
    assert response.status_code == 401

def test_protected_route():
    # Login first
    auth_response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    token = auth_response.json()['access_token']
    
    # Access protected route
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/classes", headers=headers)
    assert response.status_code == 200
```

### Agent Tests

```python
# tests/unit/test_agent.py
from agents.langgraph_agent import MBSEAgent
import os

def test_agent_statistics_query():
    agent = MBSEAgent(api_key=os.getenv("OPENAI_API_KEY"))
    response = agent.run("How many classes are there?")
    assert "classes" in response.lower()
    assert response  # Non-empty response

def test_agent_tool_selection():
    agent = MBSEAgent(api_key=os.getenv("OPENAI_API_KEY"))
    # Should use search_artifacts tool
    response = agent.run("Find all sensor classes")
    assert len(response) > 0
```

---

## Troubleshooting

### Authentication Issues

**Problem**: `401 Unauthorized` errors

**Solutions**:
1. Check token format: `Authorization: Bearer <token>` (not just `<token>`)
2. Verify token not expired (check `exp` claim)
3. Ensure JWT_SECRET_KEY matches between token generation and validation
4. Check if token was revoked (logout)

### Agent Issues

**Problem**: Agent not responding or errors

**Solutions**:
1. Verify OPENAI_API_KEY is set: `echo $OPENAI_API_KEY`
2. Check Flask server is running: `curl http://localhost:5000/api/health`
3. Review agent logs: `tail -f logs/app.log`
4. Test API tools directly first before using agent

---

## Summary

**Completed Features:**
- ✅ JWT authentication with login/refresh/logout
- ✅ LangGraph-based AI agent with 7 tools
- ✅ ReAct-style reasoning workflow
- ✅ Protected route decorators
- ✅ Token blacklist for logout
- ✅ Comprehensive examples and documentation

**Next Steps:**
- Implement user database (replace hardcoded credentials)
- Add Redis for token blacklist (production scalability)
- Create Docker/Kubernetes deployment
- Add rate limiting (Flask-Limiter)
- Implement refresh token rotation
- Add audit logging for authentication events

**Resources:**
- JWT Documentation: https://jwt.io/
- LangGraph Documentation: https://python.langchain.com/docs/langgraph
- Flask Security Best Practices: https://flask.palletsprojects.com/security/
