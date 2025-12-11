"""
Web API for MBSE Neo4j Knowledge Graph with REST API
ISO 10303-4443 SMRL Compliant - FastAPI Implementation
"""

import json
from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from loguru import logger
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.web.services import get_neo4j_service, reset_neo4j_service

# Load environment variables
load_dotenv()

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


# Custom JSON encoder for Neo4j types
class Neo4jJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, "iso_format"):
            return obj.iso_format()
        if hasattr(obj, "isoformat") and not isinstance(obj, str):
            return obj.isoformat()
        return super().default(obj)


# Custom JSON response class for Neo4j types
class Neo4jJSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            cls=Neo4jJSONEncoder,
        ).encode("utf-8")


# Lifespan context manager for Neo4j connections
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI app.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting up FastAPI application...")
    logger.info("Verifying Neo4j database connection...")
    
    try:
        neo4j_service = get_neo4j_service()
        neo4j_service.verify_connectivity()
        logger.info("✓ Neo4j database connected")
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down FastAPI application...")
    try:
        reset_neo4j_service()
        logger.info("✓ Neo4j connections closed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI app
app = FastAPI(
    title="MBSE Knowledge Graph REST API",
    description="ISO 10303-4443 SMRL Compliant API for Model-Based Systems Engineering",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# Root endpoint
@app.get("/", include_in_schema=False)
async def root():
    """Redirect to React frontend dashboard"""
    import os
    frontend_url = os.getenv('FRONTEND_URL', 'https://vigilant-space-goldfish-5x6rp4rvpxg244wj-3001.app.github.dev')
    return RedirectResponse(url=f"{frontend_url}/dashboard")


# Info endpoint
@app.get("/info", response_class=Neo4jJSONResponse)
async def info():
    """API information and architecture overview"""
    import os
    frontend_url = os.getenv('FRONTEND_URL', 'https://vigilant-space-goldfish-5x6rp4rvpxg244wj-3001.app.github.dev')
    
    return {
        "name": "MBSE Knowledge Graph REST API",
        "version": "2.0.0",
        "framework": "FastAPI",
        "architecture": {
            "ui": f"{frontend_url} (React + TypeScript + Vite)",
            "api": "FastAPI REST API (this server)",
            "database": "Neo4j Graph Database",
            "standards": ["ISO 10303-242 (AP242)", "ISO 10303-239 (AP239)", "ISO 10303-4443 (SMRL)"]
        },
        "endpoints": {
            "docs": "/api/docs",
            "redoc": "/api/redoc",
            "openapi": "/api/openapi.json",
            "health": "/api/health",
            "metrics": "/api/metrics/summary",
        }
    }


# Health check endpoint
@app.get("/api/health", response_class=Neo4jJSONResponse)
async def health_check():
    """
    Health check endpoint with database connectivity test.
    
    Returns:
        JSON with status, database connection state, and metrics
    """
    from neo4j.exceptions import ServiceUnavailable, AuthError
    import time
    
    health = {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "2.0.0",
        "framework": "FastAPI",
        "database": {
            "connected": False,
            "latency_ms": None,
            "node_count": None,
            "error": None
        },
        "connection_pool": {
            "max_size": 50,
            "status": "active"
        }
    }
    
    try:
        neo4j_service = get_neo4j_service()
        
        # Measure connection latency
        start = time.time()
        result = neo4j_service.execute_query("MATCH (n) RETURN count(n) as count LIMIT 1")
        latency = (time.time() - start) * 1000
        
        health["database"]["connected"] = True
        health["database"]["latency_ms"] = round(latency, 2)
        health["database"]["node_count"] = result[0]["count"] if result else 0
        
        return health
        
    except AuthError as e:
        health["status"] = "unhealthy"
        health["database"]["error"] = f"Authentication failed: {str(e)}"
        return Neo4jJSONResponse(content=health, status_code=503)
        
    except ServiceUnavailable as e:
        health["status"] = "unhealthy"
        health["database"]["error"] = f"Database unavailable: {str(e)}"
        return Neo4jJSONResponse(content=health, status_code=503)
        
    except Exception as e:
        health["status"] = "unhealthy"
        health["database"]["error"] = str(e)
        return Neo4jJSONResponse(content=health, status_code=500)


# Register route modules (converted from Flask blueprints)
logger.info("=" * 60)
logger.info("🚀 MBSE Knowledge Graph REST API (FastAPI)")
logger.info("=" * 60)

# Import and include routers
try:
    from src.web.routes.metrics_fastapi import router as metrics_router
    app.include_router(metrics_router, prefix="/api/metrics", tags=["Metrics"])
    logger.info("✓ Registered Metrics routes (FastAPI)")
except ImportError as e:
    logger.warning(f"Metrics routes not yet migrated: {e}")

try:
    from src.web.routes.plm_connectors_fastapi import router as plm_router
    app.include_router(plm_router, prefix="/api/v1/plm", tags=["PLM"])
    logger.info("✓ Registered PLM routes (FastAPI)")
except ImportError as e:
    logger.warning(f"PLM routes not yet migrated: {e}")

try:
    from src.web.routes.core_fastapi import router as core_router
    app.include_router(core_router, prefix="/api", tags=["Core"])
    logger.info("✓ Registered Core API routes (FastAPI)")
except ImportError as e:
    logger.warning(f"Core routes not yet migrated: {e}")

try:
    from src.web.routes.graph_fastapi import router as graph_router
    app.include_router(graph_router, prefix="/api/graph", tags=["Graph"])
    logger.info("✓ Registered Graph API routes (FastAPI)")
except ImportError as e:
    logger.warning(f"Graph routes not yet migrated: {e}")

try:
    from src.web.routes.hierarchy_fastapi import router as hierarchy_router
    app.include_router(hierarchy_router, prefix="/api/hierarchy", tags=["Hierarchy & Traceability"])
    logger.info("✓ Registered Hierarchy API routes (FastAPI)")
except ImportError as e:
    logger.warning(f"Hierarchy routes not yet migrated: {e}")

try:
    from src.web.routes.ap239_fastapi import router as ap239_router
    app.include_router(ap239_router, prefix="/api/ap239", tags=["AP239 - Requirements Management"])
    logger.info("✓ Registered AP239 routes (FastAPI)")
except ImportError as e:
    logger.warning(f"AP239 routes not yet migrated: {e}")

# Remaining routes to be converted:
# - AP242 (CAD Integration)
# - AP243 (Product Structure)
# - SMRL v1
# - PLM (additional endpoints)
# - Export
# - Simulation
# - Version Control
# - Authentication

logger.info("=" * 60)

# Entry point for uvicorn
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.web.app_fastapi:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        log_level="info",
    )
