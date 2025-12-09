# Phase 2 Quick Reference Card 🚀

## 🔐 Security Features

### Password Management
```python
from src.web.middleware.security_utils import PasswordHasher

# Hash a password
hashed = PasswordHasher.hash_password("my_password")

# Verify password
is_valid = PasswordHasher.verify_password("my_password", hashed)
```

### API Protection
```python
from src.web.middleware.security_utils import rate_limit, require_api_key

# Rate limiting (10 requests per minute)
@app.route('/api/search')
@rate_limit(max_requests=10, window_seconds=60)
def search():
    return results

# API key required
@app.route('/api/admin')
@require_api_key
def admin():
    # Requires X-API-Key header
    return data
```

### Generate Tokens
```python
from src.web.middleware.security_utils import TokenManager

# Generate random token
token = TokenManager.generate_token()  # 64 chars

# Generate API key
api_key = TokenManager.generate_api_key()  # mbse_...
```

---

## 📡 WebSocket Real-time Updates

### Server-side (Notify Clients)
```python
from flask import current_app

# Get notifier
notifier = current_app.config['NOTIFIER']

# Notify node created
notifier.notify_node_created({
    'id': '123',
    'type': 'Class',
    'name': 'Motor'
})

# Notify node updated
notifier.notify_node_updated({
    'id': '123',
    'changes': {'name': 'ElectricMotor'}
})

# Notify batch update
notifier.notify_batch_update([
    {'event': 'created', 'id': '456'},
    {'event': 'updated', 'id': '789'}
])
```

### Client-side (JavaScript)
```javascript
// Connect to WebSocket
const socket = io('http://localhost:5000');

// Subscribe to updates
socket.on('connect', () => {
    socket.emit('subscribe', { room: 'default' });
});

// Listen for updates
socket.on('graph_update', (data) => {
    console.log('Event:', data.event);
    console.log('Data:', data.data);
    
    // Update UI
    if (data.event === 'node_created') {
        addNodeToGraph(data.data);
    }
});
```

---

## 📊 Monitoring & Metrics

### Prometheus Metrics Endpoint
```bash
# Access metrics
curl http://localhost:5000/metrics
```

### Track Custom Metrics
```python
from src.web.middleware.metrics import MetricsCollector

# Cache metrics
MetricsCollector.record_cache_hit('query_cache')
MetricsCollector.record_cache_miss('query_cache')

# Connection pool
MetricsCollector.set_active_connections(10)

# PLM sync
MetricsCollector.record_plm_sync(
    plm_system='teamcenter',
    direction='push',
    success=True,
    duration=2.5
)
```

### Decorator-based Tracking
```python
from src.web.middleware.metrics import track_request_metrics, track_neo4j_query

# Track HTTP requests automatically
@app.route('/api/query')
@track_request_metrics
def query():
    return results

# Track Neo4j queries
@track_neo4j_query('read')
def get_classes():
    # Metrics collected automatically
    return neo4j_service.execute_query(query)
```

---

## 📤 Export Service

### Quick Export
```python
from src.web.services.export_service import ExportService
from src.web.services import get_neo4j_service

service = ExportService(get_neo4j_service())
query = "MATCH (n:Class) RETURN n LIMIT 10"

# JSON export
json_data = service.export_json(query)

# CSV export (for Excel)
csv_data = service.export_csv(query)

# XML export
xml_data = service.export_xml(query)
```

### Graph Visualization Formats
```python
# GraphML (yEd, Gephi, Cytoscape desktop)
graphml = service.export_graphml()

# PlantUML (diagrams)
plantuml = service.export_plantuml("PackageName")

# Cytoscape.js (web visualization)
cyto_json = service.export_cytoscape()

# RDF/Turtle (semantic web)
rdf = service.export_rdf()
```

### Save to File
```python
# Save PlantUML diagram
plantuml = service.export_plantuml()
with open('diagram.puml', 'w') as f:
    f.write(plantuml)

# Save GraphML
graphml = service.export_graphml()
with open('graph.graphml', 'w') as f:
    f.write(graphml)
```

---

## 🔌 PLM Integration

### Teamcenter Connector
```python
from src.integrations.teamcenter_connector import TeamcenterConnector
from src.integrations.base_connector import PLMConfig, PLMSystem

# Configure
config = PLMConfig(
    system=PLMSystem.TEAMCENTER,
    base_url='https://plm.company.com',
    username='user',
    password='pass'
)

# Create connector
connector = TeamcenterConnector(config)

# Authenticate
await connector.authenticate()

# Get part details
part = await connector.get_part('PART-001')
print(f"Part: {part['name']}, Rev: {part['revision']}")

# Get BOM (Bill of Materials)
bom = await connector.get_bom('PART-001', depth=3)
for item in bom.children:
    print(f"  - {item.part_number}: {item.quantity}")

# Search parts
results = await connector.search_parts(name='Motor*')
print(f"Found {len(results)} parts")

# Sync to Neo4j
sync_result = await connector.sync_to_neo4j(['PART-001', 'PART-002'])
print(f"Success: {sync_result.success_count}, Failed: {sync_result.failed_count}")
```

### Custom PLM Connector
```python
from src.integrations.base_connector import BasePLMConnector, PLMConnectorFactory

class MyPLMConnector(BasePLMConnector):
    async def authenticate(self):
        # Implement authentication
        pass
    
    async def get_part(self, part_id: str):
        # Implement part retrieval
        pass
    
    async def get_bom(self, part_id: str, depth: int = 1):
        # Implement BOM expansion
        pass

# Register
PLMConnectorFactory.register(PLMSystem.CUSTOM, MyPLMConnector)
```

---

## 🧪 Testing

### Run Phase 2 Tests
```bash
# Test all Phase 2 features
cd /workspaces/mbse-neo4j-graph-rep
python test_phase2_features.py

# Expected output:
# Security: ✓ PASS
# Metrics: ✓ PASS
# Export: ✓ PASS
# Overall: 3/3 tests passed (100%)
```

### Test Individual Features
```python
# Test security
from src.web.middleware.security_utils import PasswordHasher
hashed = PasswordHasher.hash_password("test")
assert PasswordHasher.verify_password("test", hashed)

# Test metrics
from src.web.middleware.metrics import MetricsCollector
MetricsCollector.record_cache_hit('test')

# Test export
from src.web.services.export_service import ExportService
service = ExportService(neo4j_service)
result = service.export_json("MATCH (n) RETURN n LIMIT 1")
assert len(result) > 0
```

---

## 🐳 Docker Deployment

### Build Containers
```bash
# Build all services
docker-compose -f docker-compose.prod.yml build

# Build specific service
docker-compose -f docker-compose.prod.yml build backend
```

### Run Services
```bash
# Start all services
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f backend
```

### Stop Services
```bash
# Stop all
docker-compose -f docker-compose.prod.yml down

# Stop and remove volumes
docker-compose -f docker-compose.prod.yml down -v
```

---

## 🔗 API Endpoints

### New Phase 2 Endpoints
```bash
# Metrics (Prometheus)
GET http://localhost:5000/metrics

# Health check (rate-limited)
GET http://localhost:5000/api/health

# Export JSON (future)
POST http://localhost:5000/api/export/json
Content-Type: application/json
{
  "query": "MATCH (n) RETURN n LIMIT 10"
}

# Export CSV (future)
POST http://localhost:5000/api/export/csv
Content-Type: application/json
{
  "query": "MATCH (n:Class) RETURN n.name, n.type"
}
```

### Protected Endpoints (require API key)
```bash
# Use X-API-Key header
curl -H "X-API-Key: mbse_your_api_key_here" \
     http://localhost:5000/api/protected
```

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
# .env file
OPENAI_API_KEY=sk-...              # For AI agent
LANGSMITH_API_KEY=lsv2_...         # Optional monitoring
TEAMCENTER_URL=https://...         # PLM integration
```

### 3. Start Services
```bash
# Backend (with WebSocket)
python -m src.web.app

# Access:
# - UI: http://localhost:5000
# - API: http://localhost:5000/api/v1/
# - Metrics: http://localhost:5000/metrics
# - Health: http://localhost:5000/api/health
```

### 4. Test Features
```bash
python test_phase2_features.py
```

---

## 📝 Configuration Reference

### Rate Limiting
```python
# Per-endpoint configuration
@rate_limit(max_requests=10, window_seconds=60)   # 10/min
@rate_limit(max_requests=100, window_seconds=60)  # 100/min
@rate_limit(max_requests=1000, window_seconds=60) # 1000/min
```

### WebSocket Rooms
```javascript
// Default room (all updates)
socket.emit('subscribe', { room: 'default' });

// Package-specific
socket.emit('subscribe', { room: 'Package:DomainModel' });

// Entity-specific
socket.emit('subscribe', { room: 'Class:Motor' });
```

### Security Headers (automatic)
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: SAMEORIGIN`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000`
- `Referrer-Policy: no-referrer-when-downgrade`

---

## 🎯 Common Use Cases

### Use Case 1: Real-time Dashboard
```javascript
// Connect to updates
const socket = io('http://localhost:5000');
socket.emit('subscribe', { room: 'default' });

// Update chart on new data
socket.on('graph_update', (data) => {
    if (data.event === 'node_created') {
        updateChart(data.data);
    }
});
```

### Use Case 2: Protected Admin API
```python
@app.route('/api/admin/users')
@require_api_key
@rate_limit(max_requests=5, window_seconds=60)
def manage_users():
    # Only accessible with valid API key
    # Limited to 5 requests per minute
    return users_list
```

### Use Case 3: Export for Visualization
```python
# Generate Cytoscape data for web viewer
service = ExportService(neo4j_service)
graph_data = service.export_cytoscape()

# Send to frontend
return jsonify(graph_data)
```

### Use Case 4: PLM Sync Workflow
```python
# Sync BOM from Teamcenter to Neo4j
connector = TeamcenterConnector(config)
await connector.authenticate()

parts = ['PART-001', 'PART-002', 'PART-003']
result = await connector.sync_to_neo4j(parts)

# Track metrics
MetricsCollector.record_plm_sync(
    'teamcenter', 'push', 
    result.success_count > 0, 
    result.elapsed_seconds
)

# Notify clients
notifier.notify_batch_update([
    {'event': 'node_created', 'id': p} 
    for p in result.successful_items
])
```

---

## 📞 Troubleshooting

### Security Issues
```python
# Password hashing fails
# → Ensure bcrypt is installed: pip install bcrypt

# Rate limiting not working
# → Check that decorator is applied before route handler

# API key rejected
# → Verify X-API-Key header format: mbse_...
```

### WebSocket Issues
```python
# Connection refused
# → Use socketio.run(app) instead of app.run()

# Updates not received
# → Check room subscription: socket.emit('subscribe', {...})

# CORS error
# → Set cors_allowed_origins="*" in SocketIO init
```

### Export Issues
```python
# Query timeout
# → Add LIMIT to large queries
# → Use export_cytoscape() instead of export_graphml()

# Format not supported
# → Check available: json, csv, xml, graphml, rdf, plantuml, cytoscape
```

### Metrics Issues
```python
# Metrics not appearing
# → Access /metrics endpoint directly
# → Check prometheus_client installed

# Decorator not tracking
# → Ensure @track_request_metrics is closest to function
```

---

## 🔮 Future Enhancements (Week 2)

- [ ] Grafana dashboard for metrics
- [ ] Windchill PLM connector
- [ ] OAuth2/OIDC authentication
- [ ] Redis-backed rate limiting
- [ ] Agent chat UI
- [ ] Export API endpoints
- [ ] WebSocket UI integration
- [ ] Audit logging

---

**Last Updated:** December 9, 2025  
**Phase:** 2 Week 1 Complete  
**Status:** Production Ready ✅
