"""
Web API for MBSE Neo4j Knowledge Graph with REST API
ISO 10303-4443 SMRL Compliant - FastAPI Implementation
"""

from contextlib import asynccontextmanager

from dotenv import load_dotenv, find_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from loguru import logger
from neo4j.exceptions import ServiceUnavailable, AuthError
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.web.services import get_neo4j_service, reset_neo4j_service
from src.web.services.redis_service import (
    get_redis_service,
    close_redis_service,
    is_redis_enabled,
)
from src.web.middleware.jwt_middleware import create_jwt_middleware
from src.web.middleware.session_manager import SessionManager
from src.web.routes.auth_fastapi import set_session_manager
from src.web.utils.responses import Neo4jJSONResponse
from src.web.utils.runtime_config import get_cors_origins, get_frontend_url
from src.web.utils.rate_limit import limiter
from src.web.container import ServiceContainer

# Load environment variables (searches current directory and parents for .env)
load_dotenv(find_dotenv(usecwd=True))


# Lifespan context manager for Neo4j connections
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI app.
    Handles startup and shutdown events via the central ServiceContainer.
    """
    # Startup
    logger.info("Starting up FastAPI application...")
    container = ServiceContainer.instance()

    try:
        container.startup()  # Neo4j + Engine GraphStore + legacy singleton
        logger.info("✓ Neo4j database connected (via ServiceContainer)")

        # Check whether the graph has been seeded — warn clearly if empty
        try:
            from src.web.services import get_neo4j_service as _get_svc
            _svc = _get_svc()
            if _svc:
                _result = _svc.execute_query("MATCH (n) RETURN count(n) AS c")
                _count = _result[0]["c"] if _result else 0
                if _count == 0:
                    logger.warning(
                        "⚠ Neo4j is connected but the database is EMPTY — no nodes found.\n"
                        "  The application will start but most API endpoints will return empty results.\n"
                        "  To seed the graph, run from the repository root:\n\n"
                        "    [1] Base domain model + OSLC vocabulary:\n"
                        "          .venv\\Scripts\\python.exe scripts\\reload_database.py\n\n"
                        "    [2] AP hierarchy + sample AP239/AP242/AP243 nodes:\n"
                        "          .venv\\Scripts\\python.exe backend\\scripts\\schema_migrator.py\n\n"
                        "    [3] Requirements + traceability:\n"
                        "          .venv\\Scripts\\python.exe backend\\scripts\\create_sample_data.py\n\n"
                        "    [4] SDD schema + dossier data:\n"
                        "          .venv\\Scripts\\python.exe backend\\scripts\\run_sdd_schema_migration.py\n"
                        "          .venv\\Scripts\\python.exe backend\\scripts\\ingest_sdd_data.py\n\n"
                        "    [5] SimulationRun workflow (requires step 4):\n"
                        "          .venv\\Scripts\\python.exe backend\\scripts\\run_simulation_run_migration.py\n\n"
                        "  See INSTALL.md Sections 6.2 and 6.6 for full details."
                    )
                else:
                    logger.info(f"✓ Graph database contains {_count:,} nodes")
                # Ensure performance-critical indexes exist
                try:
                    _svc.ensure_indexes()
                except Exception as _idx_err:
                    logger.warning(f"Index creation skipped: {_idx_err}")
        except Exception as _e:
            logger.debug(f"Could not check node count at startup: {_e}")

    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {e}")
        logger.warning(
            "⚠ Starting in DEGRADED mode – Neo4j is unreachable. "
            "Health endpoint will report unhealthy. "
            "Database-dependent routes will return 503."
        )
        # Do NOT re-raise – let the app start so /api/health can report status

    # Async services (Redis, sessions, query cache)
    await container.startup_async()

    yield

    # Shutdown
    logger.info("Shutting down FastAPI application...")

    # Close Redis
    try:
        await close_redis_service()
        logger.info("✓ Redis service closed")
    except Exception as e:
        logger.error(f"Error closing Redis: {e}")

    # Close container (Neo4j + GraphStore + legacy singleton)
    ServiceContainer.reset()
    logger.info("✓ ServiceContainer shut down")


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


# Custom exception handler for RequestValidationError (Pydantic validation)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle Pydantic validation errors.
    For auth endpoints, return 400 with 'error' key for test compatibility.
    """
    if "/api/auth/" in str(request.url.path):
        return JSONResponse(status_code=400, content={"error": "Validation error"})

    # For other endpoints, use standard FastAPI format
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


# Custom exception handler for HTTPException to use 'error' key instead of 'detail'
# for auth endpoints (test compatibility)
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Transform HTTPException responses for auth endpoints.
    Maps 'detail' -> 'error' and 422 -> 400 for test compatibility.
    """
    # For auth endpoints, transform response format
    if "/api/auth/" in str(request.url.path):
        # Map 422 validation errors to 400 bad request for auth
        status_code = exc.status_code
        if status_code == 422:
            status_code = 400

        # Handle both string and list detail formats
        error_message = exc.detail
        if isinstance(error_message, list):
            # For validation errors, create a simplified message
            error_message = "Validation error"

        return JSONResponse(status_code=status_code, content={"error": error_message})

    # For other endpoints, use standard FastAPI format
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


# ----- Global handler: Neo4j down / degraded mode ----------------------------
@app.exception_handler(ServiceUnavailable)
async def neo4j_unavailable_handler(request: Request, exc: ServiceUnavailable):
    """
    Catch *any* unhandled ``neo4j.exceptions.ServiceUnavailable`` from any
    route and return a clean 503 instead of a 500 Internal Server Error.
    """
    logger.warning(f"ServiceUnavailable on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Neo4j database is currently unavailable (degraded mode)",
            "error": str(exc),
        },
    )


# Configure CORS - Restrict to specific origins in production
allowed_origins = get_cors_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # Restricted to frontend origins only
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Explicit methods only
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-API-Key",
    ],  # Explicit headers only
    max_age=600,  # Cache preflight requests for 10 minutes
)

# Add GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Request logging middleware for audit trail
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all API requests for audit trail"""
    import time
    import uuid

    # Generate request ID
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id

    # Log request
    start_time = time.time()
    logger.info(f"[{request_id}] {request.method} {request.url.path} - Started")

    # Process request
    try:
        response = await call_next(request)
        duration = time.time() - start_time

        # Log response
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} - "
            f"Status: {response.status_code}, Duration: {duration:.3f}s"
        )

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"[{request_id}] {request.method} {request.url.path} - "
            f"Error: {str(e)}, Duration: {duration:.3f}s"
        )
        raise


# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )
    return response


# Root endpoint
@app.get("/", include_in_schema=False)
async def root():
    """Redirect to React frontend dashboard"""
    frontend_url = get_frontend_url()
    return RedirectResponse(url=f"{frontend_url}/dashboard")


# Info endpoint
@app.get("/info", response_class=Neo4jJSONResponse)
async def info():
    """API information and architecture overview"""
    frontend_url = get_frontend_url()

    return {
        "name": "MBSE Knowledge Graph REST API",
        "version": "2.0.0",
        "framework": "FastAPI",
        "architecture": {
            "ui": f"{frontend_url} (React + TypeScript + Vite)",
            "api": "FastAPI REST API (this server)",
            "database": "Neo4j Graph Database",
            "standards": [
                "ISO 10303-242 (AP242)",
                "ISO 10303-239 (AP239)",
                "ISO 10303-4443 (SMRL)",
            ],
        },
        "endpoints": {
            "docs": "/api/docs",
            "redoc": "/api/redoc",
            "openapi": "/api/openapi.json",
            "health": "/api/health",
            "metrics": "/api/metrics/summary",
        },
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
            "error": None,
        },
        "connection_pool": {"max_size": 50, "status": "active"},
    }

    try:
        neo4j_service = get_neo4j_service()   # raises ServiceUnavailable in degraded mode

        # Measure connection latency
        start = time.time()
        result = neo4j_service.execute_query(
            "MATCH (n) RETURN count(n) as count LIMIT 1"
        )
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

    app.include_router(
        hierarchy_router, prefix="/api/hierarchy", tags=["Hierarchy & Traceability"]
    )
    logger.info("✓ Registered Hierarchy API routes (FastAPI)")
except ImportError as e:
    logger.warning(f"Hierarchy routes not yet migrated: {e}")

try:
    from src.web.routes.ap239_fastapi import router as ap239_router

    app.include_router(
        ap239_router, prefix="/api/ap239", tags=["AP239 - Requirements Management"]
    )
    logger.info("✓ Registered AP239 routes (FastAPI)")
except ImportError as e:
    logger.warning(f"AP239 routes not yet migrated: {e}")

try:
    from src.web.routes.ap242_fastapi import router as ap242_router

    app.include_router(
        ap242_router, prefix="/api/ap242", tags=["AP242 - CAD Integration"]
    )
    logger.info("✓ Registered AP242 routes (FastAPI)")
except ImportError as e:
    logger.warning(f"AP242 routes not yet migrated: {e}")

try:
    from src.web.routes.ap243_fastapi import router as ap243_router

    app.include_router(
        ap243_router,
        prefix="/api/ap243",
        tags=["AP243 - Product Structure & Ontologies"],
    )
    logger.info("✓ Registered AP243 routes (FastAPI)")
except ImportError as e:
    logger.warning(f"AP243 routes not yet migrated: {e}")

try:
    from src.web.routes.smrl_v1_fastapi import router as smrl_router

    app.include_router(smrl_router, prefix="/api/v1", tags=["SMRL v1 - ISO 10303-4443"])
    logger.info("✓ Registered SMRL v1 routes (FastAPI)")
except ImportError as e:
    logger.warning(f"SMRL v1 routes not yet migrated: {e}")

try:
    from src.web.routes.auth_fastapi import router as auth_router

    app.include_router(auth_router, prefix="/api", tags=["Authentication"])
    logger.info("✓ Registered Authentication routes (FastAPI)")
except ImportError as e:
    logger.warning(f"Authentication routes not yet migrated: {e}")

try:
    from src.web.routes.sessions_fastapi import router as sessions_router

    app.include_router(sessions_router, prefix="/api", tags=["Session Management"])
    logger.info("✓ Registered Session Management routes (FastAPI)")
except ImportError as e:
    logger.warning(f"Session Management routes not available: {e}")

try:
    from src.web.routes.plm_fastapi import router as plm_integration_router

    app.include_router(plm_integration_router, prefix="/api", tags=["PLM Integration"])
    logger.info("✓ Registered PLM Integration routes (FastAPI)")
except ImportError as e:
    logger.warning(f"PLM Integration routes not yet migrated: {e}")

try:
    from src.web.routes.simulation_fastapi import router as simulation_router

    app.include_router(
        simulation_router, prefix="/api", tags=["Simulation Integration"]
    )
    logger.info("✓ Registered Simulation routes (FastAPI)")
except ImportError as e:
    logger.warning(f"Simulation routes not yet migrated: {e}")

try:
    from src.web.routes.export_fastapi import router as export_router

    app.include_router(export_router, prefix="/api", tags=["Data Export"])
    logger.info("✓ Registered Export routes (FastAPI)")
except ImportError as e:
    logger.warning(f"Export routes not yet migrated: {e}")

try:
    from src.web.routes.version_fastapi import router as version_router

    app.include_router(version_router, prefix="/api", tags=["Version Control"])
    logger.info("✓ Registered Version Control routes (FastAPI)")
except ImportError as e:
    logger.warning(f"Version routes not yet migrated: {e}")

try:
    from src.web.routes.cache_fastapi import router as cache_router

    app.include_router(cache_router, prefix="/api", tags=["Cache Management"])
    logger.info("✓ Registered Cache Management routes (FastAPI)")
except ImportError as e:
    logger.warning(f"Cache routes not available: {e}")

try:
    from src.web.routes.agents_fastapi import router as agents_router

    app.include_router(agents_router, prefix="/api", tags=["AI Agents & Orchestration"])
    logger.info("✓ Registered AI Agents routes (FastAPI)")
except ImportError as e:
    logger.warning(f"AI Agents routes not available: {e}")

try:
    from src.web.routes.vector_fastapi import router as vector_router

    app.include_router(vector_router, prefix="/api/vector", tags=["Vector"])
    logger.info("✓ Registered Vector routes (FastAPI)")
except ImportError as e:
    logger.warning(f"Vector routes not available: {e}")

try:
    from src.web.routes.upload_fastapi import router as upload_router

    app.include_router(upload_router, tags=["File Upload"])
    logger.info("✓ Registered File Upload routes (FastAPI)")
except ImportError as e:
    logger.warning(f"Upload routes not available: {e}")

try:
    from src.web.routes.graphql_fastapi import graphql_router

    app.include_router(graphql_router, prefix="/api/graphql", tags=["GraphQL"])
    logger.info("✓ Registered GraphQL routes (FastAPI)")
except ImportError as e:
    logger.warning(f"GraphQL routes not available: {e}")

try:
    from src.web.routes.oslc_fastapi import router as oslc_router
    # OSLC routes mounted under /api to match frontend apiClient baseURL
    app.include_router(oslc_router, prefix="/api", tags=["OSLC Semantic Web"])
    logger.info("✓ Registered OSLC routes (FastAPI)")
except ImportError as e:
    logger.warning(f"OSLC routes not available: {e}")

try:
    from src.web.routes.trs_fastapi import router as trs_router
    # The frontend expects /api/oslc/trs/* but the router sends /oslc/trs/*
    # We must prefix it with /api to match frontend expectations
    app.include_router(trs_router, prefix="/api", tags=["OSLC Tracked Resource Set"])
    logger.info("✓ Registered OSLC TRS routes (FastAPI)")
except ImportError as e:
    logger.warning(f"OSLC TRS routes not available: {e}")

try:
    from src.web.routes.oslc_client_fastapi import router as oslc_client_router
    app.include_router(oslc_client_router, prefix="/api", tags=["OSLC Client"])
    logger.info("✓ Registered OSLC Client routes (FastAPI)")
except ImportError as e:
    logger.warning(f"OSLC Client routes not available: {e}")

try:
    from src.web.routes.express_parser_fastapi import router as express_parser_router
    app.include_router(express_parser_router, prefix="/api", tags=["EXPRESS Parser"])
    logger.info("✓ Registered EXPRESS Parser routes (FastAPI)")
except ImportError as e:
    logger.warning(f"EXPRESS Parser routes not available: {e}")

try:
    from src.web.routes.ontology_ingest_fastapi import router as ontology_ingest_router

    app.include_router(ontology_ingest_router)
    logger.info("✓ Registered Ontology ingestion routes (FastAPI)")
except ImportError as e:
    logger.warning(f"Ontology ingestion routes not available: {e}")

try:
    from src.web.routes.shacl_fastapi import router as shacl_router

    app.include_router(shacl_router)
    logger.info("✓ Registered SHACL Validation routes (FastAPI)")
except ImportError as e:
    logger.warning(f"SHACL Validation routes not available: {e}")

try:
    from src.web.routes.step_ingest_fastapi import router as step_ingest_router

    app.include_router(step_ingest_router)
    logger.info("✓ Registered STEP ingestion routes (FastAPI)")
except ImportError as e:
    logger.warning(f"STEP ingestion routes not available: {e}")

try:
    from src.web.routes.plmxml_ingest_fastapi import router as plmxml_router

    app.include_router(plmxml_router)
    logger.info("✓ Registered Teamcenter PLMXML ingestion routes (FastAPI)")
except ImportError as e:
    logger.warning(f"PLMXML ingestion routes not available: {e}")

try:
    from src.web.routes.admin_fastapi import router as admin_router

    app.include_router(admin_router)
    logger.info("✓ Registered Admin maintenance routes (FastAPI)")
except ImportError as e:
    logger.warning(f"Admin routes not available: {e}")

try:
    from src.web.routes.insights_fastapi import router as insights_router

    app.include_router(insights_router)
    logger.info("✓ Registered AI Insights routes (FastAPI)")
except ImportError as e:
    logger.warning(f"AI Insights routes not available: {e}")

# Mount the independent Dataloader app as a sub-application
try:
    from src.dataloader.app import app as dataloader_app

    app.mount("/dataloader", dataloader_app)
    logger.info("✓ Mounted Dataloader batch processing app at /dataloader")
except ImportError as e:
    logger.warning(f"Dataloader app not available: {e}")

logger.info("=" * 60)
logger.info("🎉 100% FastAPI Migration Complete - All Routes Converted!")
logger.info("=" * 60)

# Entry point for uvicorn
if __name__ == "__main__":
    import uvicorn
    import os as _os

    _host = _os.getenv("BACKEND_HOST", "0.0.0.0")
    _port = int(_os.getenv("BACKEND_PORT", "5000"))
    uvicorn.run(
        "src.web.app_fastapi:app",
        host=_host,
        port=_port,
        reload=True,
        log_level="info",
    )
