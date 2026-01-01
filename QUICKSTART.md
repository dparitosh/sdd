# Quick Start Guide - FastAPI Backend with Authentication

This guide gets you started with the **FastAPI backend** featuring JWT Authentication and comprehensive REST APIs.

---

## 🚀 Setup (5 minutes)

### 1. Update Environment Variables

Add to your `.env` file:

```bash
# JWT Authentication
JWT_SECRET_KEY=your-secret-key-change-in-production
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123

# Neo4j Connection (already configured for Aura)
NEO4J_URI=neo4j+s://your-neo4j-uri.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
```

**Generate secure JWT_SECRET_KEY** (recommended for production):
```python
import secrets
print(secrets.token_urlsafe(32))
```

### 2. Install Dependencies

All dependencies already installed:
- ✅ FastAPI 0.124.2
- ✅ Uvicorn 0.30.6
- ✅ Pydantic 2.10.6
- ✅ PyJWT 2.10.1

To verify:
```bash
pip list | grep -E "(fastapi|uvicorn|pydantic|PyJWT)"
```

### 3. Start FastAPI Server

```bash
# Using uvicorn directly (recommended for development)
python -m uvicorn src.web.app_fastapi:app --host 0.0.0.0 --port 5000 --reload

# Or using the startup script
./start_backend.sh
```

Look for:
```
✓ Registered Authentication routes (FastAPI)
✓ Registered PLM Integration routes (FastAPI)
🎉 100% FastAPI Migration Complete - All 15 Routes Converted!
```

---

## 🔐 Using Authentication

### Access Interactive API Docs

**Best way to test:** Visit http://localhost:5000/api/docs

The OpenAPI/Swagger UI provides:
- Interactive API testing
- Automatic request/response validation
- Built-in authentication handling
- Real-time API exploration

### Test Login (curl)

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

### Use Access Token

```bash
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Access protected endpoint
curl -X GET http://localhost:5000/api/auth/verify \
  -H "Authorization: Bearer $TOKEN"
```

### Python Client Example

```python
import requests

BASE_URL = "http://localhost:5000"

# Login
response = requests.post(f"{BASE_URL}/api/auth/login", json={
    "username": "admin",
    "password": "admin123"
})
tokens = response.json()
access_token = tokens['access_token']

# Use token
headers = {"Authorization": f"Bearer {access_token}"}
response = requests.get(f"{BASE_URL}/api/classes", headers=headers)
print(response.json())

# Refresh token
response = requests.post(f"{BASE_URL}/api/auth/refresh", json={
    "refresh_token": tokens['refresh_token']
})
new_token = response.json()['access_token']
```

---

## 🤖 Using AI Agent

### Basic Agent Usage

```python
from agents.langgraph_agent import MBSEAgent
import os

# Initialize agent (requires OPENAI_API_KEY in .env)
agent = MBSEAgent(api_key=os.getenv("OPENAI_API_KEY"))

# Ask questions
response = agent.run("How many classes are in the system?")
print(response)
```

### Example Queries

```python
# Statistics query
agent.run("How many classes are in the system?")

# Traceability analysis
agent.run("Show me traceability from requirements to design elements")

# Impact analysis
agent.run("What would be affected if I change the Sensor class?")

# Parameter extraction
agent.run("Extract all parameters from the Control System class")

# Complex multi-step query
agent.run(
    "Find all parameters in classes related to temperature control, "
    "check if they have valid constraints, and export to JSON"
)
```

### Agent Workflow

For each query, the agent:

1. **Understands** the task type (search, traceability, impact, etc.)
2. **Plans** which tools to use (out of 7 available)
3. **Executes** the selected tool(s)
4. **Reasons** about the results
5. **Responds** with a comprehensive answer

### Available Tools

The agent has 7 tools:

| Tool | Purpose | Example |
|------|---------|---------|
| `search_artifacts` | Find by name | "Find all sensor classes" |
| `get_artifact_details` | Get full info | "Show details of Class_123" |
| `get_traceability` | Req→Design traces | "Trace REQ_001 to design" |
| `get_impact_analysis` | Change impact | "Impact of Sensor change?" |
| `get_parameters` | Design parameters | "Get parameters from Control System" |
| `execute_cypher` | Custom queries | "Find circular dependencies" |
| `get_statistics` | Database overview | "How many nodes?" |

---

## 📝 Running Tests

### Authentication Tests

```bash
# Run all authentication tests
pytest tests/integration/test_authentication.py -v

# Run specific test class
pytest tests/integration/test_authentication.py::TestLogin -v

# Run with output
pytest tests/integration/test_authentication.py -v -s
```

**Expected output**: 47+ tests covering login, refresh, logout, verification

### API Workflow Tests

```bash
# Run all integration tests
pytest tests/integration/ -v

# Run specific workflow
pytest tests/integration/test_api_workflows.py::TestPLMWorkflows -v
```

**Expected output**: 87+ tests covering all API workflows

---

## 🔒 Protecting Your Routes

### Method 1: Using @require_auth Decorator

```python
from flask import Blueprint, jsonify
from web.middleware.auth import require_auth

bp = Blueprint('protected', __name__)

@bp.route('/api/v1/protected-resource')
@require_auth
def protected_resource():
    # request.user is automatically populated
    return jsonify({
        "message": f"Hello {request.user['username']}!",
        "role": request.user['role']
    })
```

### Method 2: Using @require_role Decorator

```python
from web.middleware.auth import require_auth, require_role

@bp.route('/api/v1/admin-only')
@require_auth
@require_role('admin')
def admin_only():
    return jsonify({"message": "Admin access granted"})
```

### Method 3: Manual Token Verification

```python
from flask import request
from web.middleware.auth import verify_token, get_token_from_header

@bp.route('/api/v1/manual-auth')
def manual_auth():
    try:
        token = get_token_from_header()
        payload = verify_token(token)
        username = payload['sub']
        
        return jsonify({"user": username})
    except Exception as e:
        return jsonify({"error": str(e)}), 401
```

---

## 🎯 Common Tasks

### 1. Change Admin Password

Edit `.env`:
```bash
ADMIN_PASSWORD=new-secure-password
```

Restart server for changes to take effect.

### 2. Extend Token Expiration

Edit `src/web/middleware/auth.py`:
```python
class AuthConfig:
    ACCESS_TOKEN_EXPIRE_MINUTES = 120  # Change from 60 to 120
    REFRESH_TOKEN_EXPIRE_DAYS = 60     # Change from 30 to 60
```

### 3. Add New User Role

Edit `src/web/middleware/auth.py`:
```python
def authenticate_user(username: str, password: str) -> dict | None:
    # Add more users
    if username == "engineer" and password == "engineer123":
        return {"username": username, "role": "engineer"}
    
    # Admin user (existing)
    if username == "admin" and password == AuthConfig.ADMIN_PASSWORD:
        return {"username": username, "role": "admin"}
```

### 4. Create Agent API Endpoint (Optional)

Add to `src/web/routes/auth.py` or create new blueprint:
```python
from flask import Blueprint, request, jsonify
from agents.langgraph_agent import MBSEAgent
import os

agent_bp = Blueprint('agent', __name__)
agent = MBSEAgent(api_key=os.getenv("OPENAI_API_KEY"))

@agent_bp.route('/api/agent/query', methods=['POST'])
def query_agent():
    data = request.get_json()
    query = data.get('query')
    
    if not query:
        return jsonify({"error": "Missing query"}), 400
    
    response = agent.run(query)
    return jsonify({"query": query, "response": response})
```

Register blueprint in `app.py`:
```python
from web.routes.agent import agent_bp
app.register_blueprint(agent_bp)
```

---

## 🛠️ Troubleshooting

### Authentication Issues

**Problem**: `401 Unauthorized` errors

**Solutions**:
1. Check token format: `Authorization: Bearer <token>` (not just `<token>`)
2. Verify token not expired (check `exp` claim with jwt.decode)
3. Ensure JWT_SECRET_KEY matches in .env
4. Check if token was revoked (logout)

**Debug token**:
```python
import jwt

token = "your-token-here"
decoded = jwt.decode(token, options={"verify_signature": False})
print(decoded)  # Check exp, iat, sub, role
```

### Agent Issues

**Problem**: Agent not responding

**Solutions**:
1. Verify OPENAI_API_KEY is set:
   ```bash
   echo $OPENAI_API_KEY
   ```

2. Check Flask server is running:
   ```bash
   curl http://localhost:5000/api/health
   ```

3. Test API tools directly:
   ```bash
   curl http://localhost:5000/api/stats
   ```

4. Review agent logs:
   ```bash
   tail -f logs/app.log
   ```

**Debug agent workflow**:
```python
agent = MBSEAgent(api_key=os.getenv("OPENAI_API_KEY"))

# Check if tools are accessible
for tool in agent.tools:
    print(f"Tool: {tool.name}")
```

---

## 📚 Next Steps

### For Development
1. ✅ Test authentication with curl/Postman
2. ✅ Run integration tests (`pytest tests/integration/ -v`)
3. ✅ Load sample data (`scripts/sample_data.cypher`)
4. ⏳ Test agent with example queries
5. ⏳ Protect sensitive endpoints with @require_auth

### For Production
1. ⏳ Change JWT_SECRET_KEY to secure random string
2. ⏳ Change ADMIN_PASSWORD to strong password
3. ⏳ Replace hardcoded credentials with database
4. ⏳ Use Redis for token blacklist (not in-memory)
5. ⏳ Add rate limiting (Flask-Limiter)
6. ⏳ Enable HTTPS
7. ⏳ Add monitoring (Prometheus, Sentry)

### For Learning
- Read **docs/AGENT_AUTH_GUIDE.md** - Comprehensive guide (900+ lines)
- Read **docs/SERVICE_LAYER_GUIDE.md** - Architecture details
- Read **REFACTORING_TRACKER.md** - Full Phase 1 progress

---

## 🎉 You're Ready!

You now have:
- ✅ JWT authentication (access + refresh tokens)
- ✅ AI agent framework (LangGraph-based)
- ✅ 87 integration tests
- ✅ Comprehensive documentation

**Start experimenting**:
```bash
# Terminal 1: Start server
python src/web/app.py

# Terminal 2: Test authentication
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# Terminal 3: Test agent (Python)
python -c "
from agents.langgraph_agent import MBSEAgent
import os
agent = MBSEAgent(api_key=os.getenv('OPENAI_API_KEY'))
print(agent.run('How many classes are in the system?'))
"
```

**Questions?** See **docs/AGENT_AUTH_GUIDE.md** for detailed examples and troubleshooting.
