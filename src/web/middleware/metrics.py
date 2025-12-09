"""
Prometheus metrics for monitoring application performance
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from flask import Response
from functools import wraps
import time
from loguru import logger


# Define metrics
REQUEST_COUNT = Counter(
    'mbse_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'mbse_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

NEO4J_QUERY_COUNT = Counter(
    'mbse_neo4j_queries_total',
    'Total Neo4j queries executed',
    ['query_type', 'status']
)

NEO4J_QUERY_DURATION = Histogram(
    'mbse_neo4j_query_duration_seconds',
    'Neo4j query duration in seconds',
    ['query_type']
)

ACTIVE_CONNECTIONS = Gauge(
    'mbse_active_connections',
    'Number of active database connections'
)

CACHE_HITS = Counter(
    'mbse_cache_hits_total',
    'Total cache hits',
    ['cache_type']
)

CACHE_MISSES = Counter(
    'mbse_cache_misses_total',
    'Total cache misses',
    ['cache_type']
)

AGENT_QUERIES = Counter(
    'mbse_agent_queries_total',
    'Total AI agent queries',
    ['status']
)

AGENT_QUERY_DURATION = Histogram(
    'mbse_agent_query_duration_seconds',
    'AI agent query duration in seconds'
)

PLM_SYNC_COUNT = Counter(
    'mbse_plm_sync_total',
    'Total PLM synchronizations',
    ['plm_system', 'direction', 'status']
)

PLM_SYNC_DURATION = Histogram(
    'mbse_plm_sync_duration_seconds',
    'PLM sync duration in seconds',
    ['plm_system']
)


def track_request_metrics(f):
    """
    Decorator to track HTTP request metrics
    
    Usage:
        @app.route('/api/endpoint')
        @track_request_metrics
        def endpoint():
            return {'status': 'ok'}
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        start_time = time.time()
        
        # Get endpoint name
        endpoint = f.__name__
        method = 'GET'  # Default, will be overridden by Flask context if available
        
        try:
            # Execute the function
            result = f(*args, **kwargs)
            
            # Determine status code
            if isinstance(result, tuple):
                status = result[1] if len(result) > 1 else 200
            else:
                status = 200
            
            # Record metrics
            duration = time.time() - start_time
            REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
            REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
            
            return result
            
        except Exception as e:
            # Record error
            duration = time.time() - start_time
            REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=500).inc()
            REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
            raise
    
    return decorated


def track_neo4j_query(query_type: str = 'read'):
    """
    Decorator to track Neo4j query metrics
    
    Usage:
        @track_neo4j_query('read')
        def get_nodes():
            # Execute query
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = f(*args, **kwargs)
                
                # Record successful query
                duration = time.time() - start_time
                NEO4J_QUERY_COUNT.labels(query_type=query_type, status='success').inc()
                NEO4J_QUERY_DURATION.labels(query_type=query_type).observe(duration)
                
                return result
                
            except Exception as e:
                # Record failed query
                duration = time.time() - start_time
                NEO4J_QUERY_COUNT.labels(query_type=query_type, status='error').inc()
                NEO4J_QUERY_DURATION.labels(query_type=query_type).observe(duration)
                raise
        
        return decorated
    return decorator


def track_agent_query(f):
    """Decorator to track AI agent query metrics"""
    @wraps(f)
    def decorated(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = f(*args, **kwargs)
            
            duration = time.time() - start_time
            AGENT_QUERIES.labels(status='success').inc()
            AGENT_QUERY_DURATION.observe(duration)
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            AGENT_QUERIES.labels(status='error').inc()
            AGENT_QUERY_DURATION.observe(duration)
            raise
    
    return decorated


def metrics_endpoint():
    """
    Flask endpoint to expose Prometheus metrics
    
    Usage:
        @app.route('/metrics')
        def metrics():
            return metrics_endpoint()
    """
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


class MetricsCollector:
    """Helper class for manual metrics collection"""
    
    @staticmethod
    def record_cache_hit(cache_type: str = 'default'):
        """Record a cache hit"""
        CACHE_HITS.labels(cache_type=cache_type).inc()
    
    @staticmethod
    def record_cache_miss(cache_type: str = 'default'):
        """Record a cache miss"""
        CACHE_MISSES.labels(cache_type=cache_type).inc()
    
    @staticmethod
    def set_active_connections(count: int):
        """Set the number of active database connections"""
        ACTIVE_CONNECTIONS.set(count)
    
    @staticmethod
    def record_plm_sync(plm_system: str, direction: str, success: bool, duration: float):
        """Record PLM synchronization metrics"""
        status = 'success' if success else 'error'
        PLM_SYNC_COUNT.labels(
            plm_system=plm_system,
            direction=direction,
            status=status
        ).inc()
        PLM_SYNC_DURATION.labels(plm_system=plm_system).observe(duration)


# Example integration with Flask:
"""
from flask import Flask
from metrics import (
    metrics_endpoint,
    track_request_metrics,
    track_neo4j_query,
    MetricsCollector
)

app = Flask(__name__)

# Expose metrics endpoint
@app.route('/metrics')
def metrics():
    return metrics_endpoint()

# Track HTTP requests
@app.route('/api/classes')
@track_request_metrics
def get_classes():
    return {'classes': [...]}

# Track Neo4j queries
@track_neo4j_query('read')
def query_database():
    # Execute Neo4j query
    pass

# Manual metrics collection
def some_function():
    # Check cache
    if value_in_cache:
        MetricsCollector.record_cache_hit('query_cache')
        return cached_value
    else:
        MetricsCollector.record_cache_miss('query_cache')
        return fetch_from_db()
"""
