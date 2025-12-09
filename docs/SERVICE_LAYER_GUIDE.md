# Service Layer Guide

## Overview

The MBSE Knowledge Graph uses a service-oriented architecture with dedicated service modules for database operations, caching, and data transformation. This guide explains how to use and extend the service layer.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Flask Application                      │
│                    (Web Routes & Views)                     │
└────────────┬────────────────────────────┬───────────────────┘
             │                            │
    ┌────────▼─────────┐       ┌─────────▼──────────┐
    │  Service Layer   │       │   Service Layer    │
    │  neo4j_service   │       │  cache_service     │
    │                  │       │                    │
    │  • Connection    │       │  • TTL Cache       │
    │    pooling       │       │  • Decorators      │
    │  • CRUD ops      │       │  • Invalidation    │
    │  • Query         │       │                    │
    │    patterns      │       │                    │
    └────────┬─────────┘       └─────────┬──────────┘
             │                            │
             │                            │
    ┌────────▼────────────────────────────▼──────────┐
    │           Neo4j Aura Database                  │
    │        (3,257 nodes, 10,027 relationships)     │
    └────────────────────────────────────────────────┘
```

## Neo4j Service (`neo4j_service.py`)

### Purpose
Centralized Neo4j database access with connection pooling, common query patterns, and error handling.

### Key Features
- **Connection Pooling**: Max 50 connections, automatic lifecycle management
- **Singleton Pattern**: Single instance shared across application
- **Common Patterns**: Pre-built methods for CRUD, search, relationships
- **Error Handling**: Comprehensive logging and exception handling

### Basic Usage

```python
from web.services import get_neo4j_service

# Get singleton instance
neo4j = get_neo4j_service()

# Execute raw query
results = neo4j.execute_query(
    "MATCH (c:Class) WHERE c.name = $name RETURN c",
    {'name': 'Person'}
)

# Get node by ID
class_node = neo4j.get_node_by_id('Class', '_18_4_1_...')

# Get node by SMRL UID
requirement = neo4j.get_node_by_uid('Requirement', 'REQ-123')

# List nodes with pagination
classes = neo4j.list_nodes('Class', limit=50, skip=0)

# Count nodes
count = neo4j.count_nodes('Class', filters={'name': 'Person'})

# Search nodes
results = neo4j.search_nodes(
    'Class', 
    'Manager',
    fields=['name', 'comment'],
    limit=20
)

# Get relationships
rels = neo4j.get_relationships(
    'Class',
    'uid-123',
    rel_type='HAS_ATTRIBUTE',
    direction='outgoing'
)

# Get statistics
stats = neo4j.get_statistics()
# Returns: {
#   'total_nodes': 3257,
#   'total_relationships': 10027,
#   'node_types': {...},
#   'relationship_types': {...}
# }
```

### CRUD Operations

```python
# Create node
new_class = neo4j.create_node('Class', {
    'id': 'CLASS-001',
    'name': 'MyClass',
    'uid': 'UID-001',
    'smrl_type': 'AccessibleModelTypeConstituent'
})

# Update node
updated = neo4j.update_node('Class', 'UID-001', {
    'name': 'UpdatedClassName',
    'comment': 'New comment'
})
# Note: last_modified is automatically updated

# Delete node
success = neo4j.delete_node('Class', 'UID-001')
```

### Write Transactions

```python
# For operations that modify data
result = neo4j.execute_write("""
    CREATE (c:Class {name: $name})
    RETURN c
""", {'name': 'NewClass'})
```

### Configuration

The service reads from environment variables:
- `NEO4J_URI`: Connection URI (default: `neo4j+s://2cccd05b.databases.neo4j.io`)
- `NEO4J_USER`: Username (default: `neo4j`)
- `NEO4J_PASSWORD`: Password

Connection pool settings:
- Max connections: 50
- Acquisition timeout: 60 seconds
- Max retry time: 30 seconds

## Cache Service (`cache_service.py`)

### Purpose
High-performance in-memory caching with TTL (Time-To-Live) support to reduce database load.

### Key Features
- **TTL-based expiration**: Automatic cache invalidation
- **Decorator pattern**: Easy integration with existing functions
- **Cache invalidation**: Targeted or full cache clearing
- **Background cleanup**: Optional automatic cleanup task

### Basic Usage

```python
from web.services import cached, cache_stats, get_cache

# Cache function results
@cached(ttl=300, key_prefix="my_data")
def get_expensive_data(param):
    # Expensive computation or database query
    return result

# Use specialized decorators
@cache_stats(ttl=60)  # 1 minute cache for stats
def get_statistics():
    return neo4j.get_statistics()

@cache_node(ttl=300)  # 5 minute cache for nodes
def get_class_by_id(class_id):
    return neo4j.get_node_by_id('Class', class_id)

@cache_search(ttl=120)  # 2 minute cache for searches
def search_classes(query):
    return neo4j.search_nodes('Class', query)
```

### Cache Invalidation

```python
from web.services import (
    invalidate_cache,
    invalidate_node_cache,
    invalidate_stats_cache
)

# Invalidate all cache
invalidate_cache()

# Invalidate by pattern
invalidate_cache("stats:*")  # All stats
invalidate_cache("node:Class:*")  # All Class nodes

# Invalidate specific node type
invalidate_node_cache(label='Class')

# Invalidate specific node
invalidate_node_cache(label='Class', uid='UID-001')

# Invalidate statistics cache
invalidate_stats_cache()
```

### Direct Cache Access

```python
# Get cache instance
cache = get_cache()

# Manual cache operations
cache.set('my_key', {'data': 'value'}, ttl=600)
value = cache.get('my_key')
cache.delete('my_key')
cache.clear()

# Get cache statistics
from web.services import get_cache_stats
stats = get_cache_stats()
# Returns: {
#   'size': 42,
#   'default_ttl': 300,
#   'entries': 42,
#   'oldest_entry': 1701945600.0,
#   'newest_entry': 1701949200.0
# }
```

### Cache Performance

**Without Cache:**
```bash
$ time curl http://localhost:5000/api/stats
real    0m0.750s
```

**With Cache:**
```bash
$ time curl http://localhost:5000/api/stats
real    0m0.007s  # 99% faster!
```

### Background Cleanup

```python
from web.services.cache_service import start_cache_cleanup_task

# Start background cleanup (runs every 60 seconds)
start_cache_cleanup_task(interval=60)
```

## SMRL Adapter (`smrl_adapter.py`)

### Purpose
Convert Neo4j graph data to ISO 10303-4443 SMRL compliant format.

### Key Features
- **Type Mapping**: UML/SysML → SMRL resource types
- **Format Conversion**: Neo4j → SMRL JSON
- **Validation**: Ensure required SMRL fields present

### Usage

```python
from web.services import SMRLAdapter

# Convert single node
node_data = {'id': '123', 'name': 'Person', ...}
node_labels = ['Class']

smrl_resource = SMRLAdapter.to_smrl_resource(node_data, node_labels)
# Returns: {
#   'uid': '...',
#   'href': '/api/v1/AccessibleModelTypeConstituent/...',
#   'smrl_type': 'AccessibleModelTypeConstituent',
#   'name': 'Person',
#   'created_on': '2025-12-07T...',
#   ...
# }

# Convert collection
nodes = [...]
collection = SMRLAdapter.to_smrl_collection(nodes, 'Class', limit=10, skip=0)
# Returns: {
#   'count': 10,
#   'total': 143,
#   'resources': [...]
# }

# Validate SMRL resource
is_valid = SMRLAdapter.validate_smrl_resource(smrl_resource)
```

## Integration Examples

### Flask Route with Service Layer

```python
from flask import jsonify, request
from web.services import get_neo4j_service, cache_stats

@app.route('/api/stats')
@cache_stats(ttl=60)  # Cache for 1 minute
def get_stats():
    """Get graph statistics (cached)"""
    try:
        neo4j = get_neo4j_service()
        stats = neo4j.get_statistics()
        
        return jsonify({
            'nodes': {
                'total': stats['total_nodes'],
                'by_type': [
                    {'label': k, 'count': v} 
                    for k, v in stats['node_types'].items()
                ]
            },
            'relationships': {
                'total': stats['total_relationships'],
                'by_type': [
                    {'type': k, 'count': v}
                    for k, v in stats['relationship_types'].items()
                ]
            }
        })
    except Exception as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500
```

### Search Endpoint

```python
@app.route('/api/search')
def search():
    """Search entities"""
    query_text = request.args.get('q', '')
    
    if not query_text or len(query_text) < 2:
        return jsonify([])
    
    try:
        neo4j = get_neo4j_service()
        
        # Use indexed search
        query = """
        MATCH (n)
        WHERE n.name =~ ('(?i).*' + $query + '.*')
        RETURN n.id AS id, n.name AS name,
               labels(n)[0] AS type, n.comment AS comment
        ORDER BY n.name
        LIMIT 50
        """
        result = neo4j.execute_query(query, {'query': query_text})
        
        return jsonify([{
            'id': r['id'],
            'name': r['name'],
            'type': r['type'],
            'comment': r['comment']
        } for r in result])
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

### CRUD with Cache Invalidation

```python
from web.services import get_neo4j_service, invalidate_node_cache

@app.route('/api/class/<class_id>', methods=['PUT'])
def update_class(class_id):
    """Update class and invalidate cache"""
    try:
        neo4j = get_neo4j_service()
        
        # Update node
        data = request.json
        updated = neo4j.update_node('Class', class_id, data)
        
        # Invalidate cache
        invalidate_node_cache(label='Class', uid=class_id)
        invalidate_stats_cache()  # Stats changed
        
        return jsonify(updated)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

## Performance Best Practices

### 1. Use Caching Wisely

```python
# ✅ Good: Cache expensive operations
@cache_stats(ttl=60)
def get_statistics():
    return neo4j.get_statistics()

# ❌ Bad: Don't cache frequently changing data
@cached(ttl=3600)  # Too long!
def get_real_time_data():
    return neo4j.execute_query("...")
```

### 2. Use Appropriate TTL

- **Statistics**: 60 seconds (changes infrequently)
- **Node data**: 300 seconds (5 minutes)
- **Search results**: 120 seconds (2 minutes)
- **Real-time data**: No cache or 10-30 seconds

### 3. Invalidate Cache on Writes

```python
# Always invalidate after modifications
neo4j.create_node('Class', {...})
invalidate_node_cache(label='Class')
invalidate_stats_cache()
```

### 4. Use Connection Pooling

```python
# ✅ Good: Use service singleton
neo4j = get_neo4j_service()  # Reuses connection pool

# ❌ Bad: Create new connections
conn = Neo4jConnection(...)  # Creates new connection
```

### 5. Batch Operations

```python
# ✅ Good: Single query with UNWIND
neo4j.execute_write("""
    UNWIND $items AS item
    CREATE (n:Node {name: item.name})
""", {'items': items})

# ❌ Bad: Multiple queries
for item in items:
    neo4j.create_node('Node', {'name': item['name']})
```

## Testing

### Mock Service Layer

```python
import unittest
from unittest.mock import MagicMock, patch

class TestMyRoute(unittest.TestCase):
    
    @patch('web.services.get_neo4j_service')
    def test_get_stats(self, mock_service):
        # Mock the service
        mock_neo4j = MagicMock()
        mock_neo4j.get_statistics.return_value = {
            'total_nodes': 100,
            'total_relationships': 200,
            'node_types': {'Class': 50},
            'relationship_types': {'HAS_ATTRIBUTE': 100}
        }
        mock_service.return_value = mock_neo4j
        
        # Test endpoint
        response = client.get('/api/stats')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['nodes']['total'], 100)
```

### Test Cache

```python
from web.services import get_cache

def test_cache():
    cache = get_cache()
    
    # Test set/get
    cache.set('test_key', {'data': 'value'})
    assert cache.get('test_key') == {'data': 'value'}
    
    # Test TTL expiration
    cache.set('temp_key', 'value', ttl=1)
    time.sleep(2)
    assert cache.get('temp_key') is None
    
    # Test invalidation
    cache.clear()
    assert cache.size() == 0
```

## Monitoring

### Check Service Status

```python
# Neo4j connection
neo4j = get_neo4j_service()
try:
    stats = neo4j.get_statistics()
    print(f"✅ Neo4j connected: {stats['total_nodes']} nodes")
except Exception as e:
    print(f"❌ Neo4j error: {e}")

# Cache status
from web.services import get_cache_stats
cache_stats = get_cache_stats()
print(f"Cache: {cache_stats['entries']} entries, TTL: {cache_stats['default_ttl']}s")
```

### Performance Metrics

```python
import time

# Measure query time
start = time.time()
results = neo4j.execute_query("MATCH (n:Class) RETURN count(n)")
elapsed = time.time() - start
print(f"Query took {elapsed:.3f}s")

# Check cache hit rate
cache = get_cache()
hits = cache.hits  # If tracking implemented
misses = cache.misses
hit_rate = hits / (hits + misses) * 100
print(f"Cache hit rate: {hit_rate:.1f}%")
```

## Troubleshooting

### Connection Pool Exhausted

**Symptom**: `TimeoutError: Could not acquire connection within 60 seconds`

**Solution**:
```python
# Check pool size in neo4j_service.py
self.driver = GraphDatabase.driver(
    self.uri,
    max_connection_pool_size=50,  # Increase if needed
    connection_acquisition_timeout=60
)
```

### Cache Memory Issues

**Symptom**: High memory usage

**Solution**:
```python
# Reduce TTL or clear cache more frequently
cache = get_cache()
cache.cleanup_expired()  # Manual cleanup

# Or reduce default TTL
cache = TTLCache(default_ttl_seconds=60)  # Lower TTL
```

### Slow Queries

**Symptom**: Queries taking >1 second

**Solution**:
```python
# 1. Check if indexes exist
neo4j.execute_query("SHOW INDEXES")

# 2. Use PROFILE to analyze
neo4j.execute_query("PROFILE MATCH (n:Class) RETURN n")

# 3. Add indexes if missing
neo4j.execute_query("CREATE INDEX FOR (n:Class) ON (n.name)")
```

## Migration Guide

### From Direct Neo4j Calls

**Before:**
```python
@app.route('/api/stats')
def get_stats():
    conn = Neo4jConnection(uri, user, password)
    conn.connect()
    try:
        result = conn.execute_query("MATCH (n) RETURN count(n)")
        return jsonify(result)
    finally:
        conn.close()
```

**After:**
```python
@app.route('/api/stats')
@cache_stats(ttl=60)
def get_stats():
    neo4j = get_neo4j_service()
    stats = neo4j.get_statistics()
    return jsonify(stats)
```

**Benefits:**
- ✅ Connection pooling (no conn.close() needed)
- ✅ Caching (99% faster repeated queries)
- ✅ Error handling (automatic logging)
- ✅ Less boilerplate code

## Additional Resources

- [Neo4j Python Driver Documentation](https://neo4j.com/docs/api/python-driver/)
- [Flask Caching Patterns](https://flask.palletsprojects.com/en/latest/patterns/caching/)
- [ISO 10303-4443 SMRL Standard](https://www.iso.org/standard/78579.html)
- [REFACTORING_TRACKER.md](../REFACTORING_TRACKER.md) - Project roadmap
- [INTEGRATION.md](../mcp-server/INTEGRATION.md) - MCP Server integration

---

**Version**: 1.0.0  
**Last Updated**: December 7, 2025  
**Status**: Production Ready ✅
