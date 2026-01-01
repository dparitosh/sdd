# Root Cause Analysis: Neo4j Connection Timeout

**Date:** December 8, 2025  
**Severity:** CRITICAL  
**Status:** IDENTIFIED - FIX IN PROGRESS

---

## 🔍 Executive Summary

The application experiences **indefinite hanging** when accessing API endpoints due to **repeated Neo4j driver initialization** on every request. Each route blueprint creates a new `Neo4jService()` instance instead of using the singleton pattern, causing connection exhaustion and Aura cloud timeouts.

**Impact:**
- All API endpoints unresponsive (timeout after 60s+)
- Frontend shows infinite loading states
- Integration tests cannot execute
- Application unusable despite production-ready code

---

## 📊 Causal Chain Analysis

### Layer 1: Symptom (What Users See)
```
User Action: Access http://localhost:3001/dashboard
↓
Frontend: Sends GET /api/stats
↓
Result: Infinite loading spinner (no response)
```

### Layer 2: API Layer (What Happens in Flask)
```
Flask receives: GET /api/stats
↓
Routes to: core_bp.get_stats() in routes/core.py
↓
Calls: neo4j = get_neo4j_service()
↓
Problem: Uses WRONG get_neo4j_service() from web.services import
↓
But routes have LOCAL get_neo4j_service() that creates NEW instance!
```

### Layer 3: Service Layer (The Bug)
```python
# ❌ WRONG: In routes/plm.py, simulation.py, version.py, export.py
def get_neo4j_service():
    """Get Neo4j service instance"""
    return Neo4jService()  # Creates NEW connection every time!
```

**vs**

```python
# ✅ CORRECT: In services/neo4j_service.py  
_neo4j_service = None

def get_neo4j_service() -> Neo4jService:
    """Get singleton Neo4j service instance"""
    global _neo4j_service
    
    if _neo4j_service is None:
        _neo4j_service = Neo4jService()
    
    return _neo4j_service  # Reuses same instance
```

### Layer 4: Connection Layer (Why It Hangs)
```python
# In Neo4jService.__init__()
self.driver = GraphDatabase.driver(
    self.uri,  # neo4j+s://your-neo4j-uri.databases.neo4j.io
    auth=(self.user, self.password),
    max_connection_pool_size=50,
    connection_acquisition_timeout=60,  # ← Hangs here!
    max_transaction_retry_time=30,
)
```

**What Happens:**
1. Request 1: Creates driver, connects to Aura ✅
2. Request 2: Creates ANOTHER driver, tries to connect ⏳
3. Request 3: Creates ANOTHER driver, tries to connect ⏳
4. ...Aura cloud instance overwhelmed, starts rejecting connections
5. Driver waits 60s for connection_acquisition_timeout
6. Request times out, user sees "Loading..."

---

## 🔬 Evidence

### 1. Code Analysis

**Problem Code Locations:**
```bash
src/web/routes/simulation.py:18  - def get_neo4j_service(): return Neo4jService()
src/web/routes/plm.py:20         - def get_neo4j_service(): return Neo4jService()
src/web/routes/version.py:21     - def get_neo4j_service(): return Neo4jService()
src/web/routes/export.py:26      - def get_neo4j_service(): return Neo4jService()
```

**Correct Implementation:**
```bash
src/web/services/neo4j_service.py:362  - Singleton pattern implemented
src/web/routes/core.py:8               - from web.services import get_neo4j_service ✅
```

### 2. Import Analysis

**Routes Using WRONG Implementation:**
- `routes/plm.py` - Defines own `get_neo4j_service()` (4 occurrences)
- `routes/simulation.py` - Defines own `get_neo4j_service()` (4 occurrences)
- `routes/version.py` - Defines own `get_neo4j_service()` (5 occurrences)
- `routes/export.py` - Defines own `get_neo4j_service()` (1 occurrence)

**Routes Using CORRECT Implementation:**
- `routes/core.py` - Imports from `web.services` ✅
- `routes/smrl_v1.py` - Need to verify

### 3. Connection Behavior

```python
# Expected: 1 connection pool shared across all requests
GraphDatabase.driver() called 1 time → Pool of 50 connections

# Actual: New pool for EVERY request
Request 1: GraphDatabase.driver() → Pool of 50 connections
Request 2: GraphDatabase.driver() → Pool of 50 connections  
Request 3: GraphDatabase.driver() → Pool of 50 connections
... → 150 connections to Aura (exceeds limits!)
```

### 4. Timeout Configuration

```python
# Neo4jService.__init__()
connection_acquisition_timeout=60  # Waits 60s for connection
```

**Why 60 seconds?**
- Aura free tier has connection limits
- Multiple driver instances compete for connections
- Driver waits for available connection slot
- Eventually times out after 60s

---

## 🎯 Root Cause Statement

**Primary Cause:**  
Four route blueprints (`plm`, `simulation`, `version`, `export`) define local `get_neo4j_service()` functions that create new `Neo4jService()` instances on every API call, **bypassing the singleton pattern** defined in `services/neo4j_service.py`.

**Contributing Factors:**
1. **Name collision** - Local function shadows imported function
2. **No linting enforcement** - No check for duplicate function definitions
3. **Missing connection pooling validation** - No test to verify singleton behavior
4. **Inconsistent imports** - Some routes import from `web.services`, others define locally

**Technical Details:**
- Each `Neo4jService()` initialization calls `GraphDatabase.driver()`
- Neo4j driver creates connection pool (50 connections configured)
- Aura free tier limits concurrent connections
- Multiple pools exhaust connection limit
- New requests wait for `connection_acquisition_timeout=60s`
- Frontend/tests timeout before receiving response

---

## ✅ Solution

### Immediate Fix (5 minutes)

Replace local `get_neo4j_service()` with centralized import:

```python
# ❌ DELETE these lines from plm.py, simulation.py, version.py, export.py
def get_neo4j_service():
    """Get Neo4j service instance"""
    return Neo4jService()

# ✅ ADD this import instead
from web.services import get_neo4j_service
```

### Files to Modify

1. `src/web/routes/plm.py` - Remove lines 20-22, add import
2. `src/web/routes/simulation.py` - Remove lines 18-20, add import
3. `src/web/routes/version.py` - Remove lines 21-23, add import  
4. `src/web/routes/export.py` - Remove lines 26-28, add import

### Verification Steps

1. **Code Check:**
   ```bash
   # Should return 0 results
   grep -r "def get_neo4j_service" src/web/routes/
   ```

2. **Service Test:**
   ```python
   # Verify singleton behavior
   service1 = get_neo4j_service()
   service2 = get_neo4j_service()
   assert service1 is service2  # Same instance!
   ```

3. **API Test:**
   ```bash
   curl http://localhost:5000/api/stats
   # Should return JSON within 2 seconds
   ```

---

## 📈 Expected Improvements

### Before Fix:
- API response time: **60s+ (timeout)**
- Concurrent connections: **N × 50** (N = number of requests)
- Success rate: **0%**
- Memory usage: **High** (multiple driver instances)

### After Fix:
- API response time: **< 1s**
- Concurrent connections: **1-5** (from single pool of 50)
- Success rate: **100%**
- Memory usage: **Normal** (single driver instance)

---

## 🔮 Prevention

### 1. Code Review Checklist
- [ ] No duplicate function definitions across modules
- [ ] All routes import from `web.services`
- [ ] No local `Neo4jService()` instantiation in routes
- [ ] Verify singleton pattern usage

### 2. Linting Rules
```python
# Add to .pylintrc or ruff.toml
# Detect duplicate function definitions
# Flag direct Neo4jService() instantiation in routes/
```

### 3. Unit Test
```python
def test_neo4j_service_singleton():
    """Verify Neo4j service uses singleton pattern"""
    from web.services import get_neo4j_service
    
    service1 = get_neo4j_service()
    service2 = get_neo4j_service()
    
    assert service1 is service2
    assert id(service1) == id(service2)
```

### 4. Integration Test
```python
def test_concurrent_requests_share_connection():
    """Verify multiple API calls use same connection pool"""
    import concurrent.futures
    
    def call_api():
        return requests.get("http://localhost:5000/api/stats")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(call_api) for _ in range(10)]
        results = [f.result() for f in futures]
    
    # All should succeed quickly
    assert all(r.status_code == 200 for r in results)
    assert all(r.elapsed.total_seconds() < 2 for r in results)
```

---

## 📝 Lessons Learned

1. **Singleton Pattern Critical** - For expensive resources (DB connections), singleton is not optional
2. **Name Collisions Dangerous** - Local functions can shadow imports silently
3. **Test Connection Behavior** - Should have tested concurrent request handling
4. **Centralize Imports** - All modules should import from single source
5. **Early Integration Testing** - Should have run API tests before full implementation

---

## 🚀 Next Steps

1. ✅ Root cause identified
2. ⏳ Apply fix to 4 route files
3. ⏳ Verify singleton behavior
4. ⏳ Test API endpoints
5. ⏳ Run integration tests
6. ⏳ Update MCP_ARCHITECTURE_REVIEW.md

**Estimated Time to Resolution:** 10 minutes  
**Risk Level:** LOW (simple import fix)  
**Testing Required:** API health check + integration tests
