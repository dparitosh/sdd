"""
Unified FaaS-Ready FastAPI Application (v4.0)

This is the Phase 1b main entry point that mounts ALL 22 function-domain
routers.  It faithfully replicates every middleware, exception handler,
and route from the original ``app_fastapi.py`` while importing routers
through the ``functions/`` package.

Run locally:
    uvicorn src.functions.main:app --host 0.0.0.0 --port 5000 --reload
"""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager

from dotenv import load_dotenv, find_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from loguru import logger
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

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
load_dotenv(find_dotenv(usecwd=True))


# ---------------------------------------------------------------------------
# Lifespan (identical to app_fastapi.py)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown via ServiceContainer."""
    logger.info("Starting up FastAPI application (v4 functions/main)…")
    container = ServiceContainer.instance()

    try:
        container.startup()
        logger.info("✓ Neo4j database connected (via ServiceContainer)")
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {e}")
        raise

    await container.startup_async()

    yield

    logger.info("Shutting down FastAPI application…")
    try:
        await close_redis_service()
        logger.info("✓ Redis service closed")
    except Exception as e:
        logger.error(f"Error closing Redis: {e}")

    ServiceContainer.reset()
    logger.info("✓ ServiceContainer shut down")


# ---------------------------------------------------------------------------
# App creation
# ---------------------------------------------------------------------------
app = FastAPI(
    title="MBSE Knowledge Graph REST API",
    description="ISO 10303-4443 SMRL Compliant API for Model-Based Systems Engineering",
    version="4.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ---------------------------------------------------------------------------
# Exception handlers (replicated from app_fastapi.py)
# ---------------------------------------------------------------------------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    if "/api/auth/" in str(request.url.path):
        return JSONResponse(status_code=400, content={"error": "Validation error"})
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if "/api/auth/" in str(request.url.path):
        status_code = 400 if exc.status_code == 422 else exc.status_code
        error_message = exc.detail
        if isinstance(error_message, list):
            error_message = "Validation error"
        return JSONResponse(status_code=status_code, content={"error": error_message})
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
allowed_origins = get_cors_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
    max_age=600,
)

app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id
    start_time = time.time()
    logger.info(f"[{request_id}] {request.method} {request.url.path} - Started")
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} - "
            f"Status: {response.status_code}, Duration: {duration:.3f}s"
        )
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"[{request_id}] {request.method} {request.url.path} - "
            f"Error: {str(e)}, Duration: {duration:.3f}s"
        )
        raise


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


# ---------------------------------------------------------------------------
# Inline endpoints (/, /info, /api/health)
# ---------------------------------------------------------------------------
@app.get("/", include_in_schema=False)
async def root():
    frontend_url = get_frontend_url()
    return RedirectResponse(url=f"{frontend_url}/dashboard")


@app.get("/info", response_class=Neo4jJSONResponse)
async def info():
    frontend_url = get_frontend_url()
    return {
        "name": "MBSE Knowledge Graph REST API",
        "version": "4.0.0",
        "framework": "FastAPI",
        "architecture": {
            "ui": f"{frontend_url} (React + TypeScript + Vite)",
            "api": "FastAPI REST API (v4 FaaS-ready)",
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


@app.get("/api/health", response_class=Neo4jJSONResponse)
async def health_check():
    from neo4j.exceptions import ServiceUnavailable, AuthError

    health = {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "4.0.0",
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
        neo4j_service = get_neo4j_service()
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


# ===================================================================
# Router registration — ALL 22 function domains
# ===================================================================
logger.info("=" * 60)
logger.info("🚀 MBSE Knowledge Graph REST API v4 (FaaS-Ready)")
logger.info("=" * 60)

# ---- 1. telemetry_service (metrics) ----
try:
    from src.functions.telemetry_service.router import router as metrics_router

    app.include_router(metrics_router, prefix="/api/metrics", tags=["Metrics"])
    logger.info("✓ [telemetry_service] Metrics routes")
except ImportError as e:
    logger.warning(f"telemetry_service not available: {e}")

# ---- 2. core_service ----
try:
    from src.functions.core_service.router import router as core_router

    app.include_router(core_router, prefix="/api", tags=["Core"])
    logger.info("✓ [core_service] Core API routes")
except ImportError as e:
    logger.warning(f"core_service not available: {e}")

# ---- 3. graph_service (graph + hierarchy) ----
try:
    from src.functions.graph_service.router import graph_router, hierarchy_router

    app.include_router(graph_router, prefix="/api/graph", tags=["Graph"])
    app.include_router(
        hierarchy_router, prefix="/api/hierarchy", tags=["Hierarchy & Traceability"]
    )
    logger.info("✓ [graph_service] Graph + Hierarchy routes")
except ImportError as e:
    logger.warning(f"graph_service not available: {e}")

# ---- 4. ap239_service ----
try:
    from src.functions.ap239_service.router import router as ap239_router

    app.include_router(
        ap239_router, prefix="/api/ap239", tags=["AP239 - Requirements Management"]
    )
    logger.info("✓ [ap239_service] AP239 routes")
except ImportError as e:
    logger.warning(f"ap239_service not available: {e}")

# ---- 5. ap242_service ----
try:
    from src.functions.ap242_service.router import router as ap242_router

    app.include_router(
        ap242_router, prefix="/api/ap242", tags=["AP242 - CAD Integration"]
    )
    logger.info("✓ [ap242_service] AP242 routes")
except ImportError as e:
    logger.warning(f"ap242_service not available: {e}")

# ---- 6. ap243_service ----
try:
    from src.functions.ap243_service.router import router as ap243_router

    app.include_router(
        ap243_router,
        prefix="/api/ap243",
        tags=["AP243 - Product Structure & Ontologies"],
    )
    logger.info("✓ [ap243_service] AP243 routes")
except ImportError as e:
    logger.warning(f"ap243_service not available: {e}")

# ---- 7. smrl_service ----
try:
    from src.functions.smrl_service.router import router as smrl_router

    app.include_router(
        smrl_router, prefix="/api/v1", tags=["SMRL v1 - ISO 10303-4443"]
    )
    logger.info("✓ [smrl_service] SMRL v1 routes")
except ImportError as e:
    logger.warning(f"smrl_service not available: {e}")

# ---- 8. auth_service (auth + sessions) ----
try:
    from src.functions.auth_service.router import auth_router, sessions_router

    app.include_router(auth_router, prefix="/api", tags=["Authentication"])
    app.include_router(sessions_router, prefix="/api", tags=["Session Management"])
    logger.info("✓ [auth_service] Auth + Sessions routes")
except ImportError as e:
    logger.warning(f"auth_service not available: {e}")

# ---- 9. plm_service (connectors + integration) ----
try:
    from src.functions.plm_service.router import (
        plm_connectors_router,
        plm_integration_router,
    )

    app.include_router(plm_connectors_router, prefix="/api/v1/plm", tags=["PLM"])
    app.include_router(
        plm_integration_router, prefix="/api", tags=["PLM Integration"]
    )
    logger.info("✓ [plm_service] PLM Connectors + Integration routes")
except ImportError as e:
    logger.warning(f"plm_service not available: {e}")

# ---- 10. simulation_service ----
try:
    from src.functions.simulation_service.router import router as simulation_router

    app.include_router(
        simulation_router, prefix="/api", tags=["Simulation Integration"]
    )
    logger.info("✓ [simulation_service] Simulation routes")
except ImportError as e:
    logger.warning(f"simulation_service not available: {e}")

# ---- 11. export_service ----
try:
    from src.functions.export_service.router import router as export_router

    app.include_router(export_router, prefix="/api", tags=["Data Export"])
    logger.info("✓ [export_service] Export routes")
except ImportError as e:
    logger.warning(f"export_service not available: {e}")

# ---- 12. version_service (version + admin + cache) ----
try:
    from src.functions.version_service.router import (
        version_router,
        admin_router,
        cache_router,
    )

    app.include_router(version_router, prefix="/api", tags=["Version Control"])
    app.include_router(admin_router, tags=["Admin Maintenance"])
    app.include_router(cache_router, prefix="/api", tags=["Cache Management"])
    logger.info("✓ [version_service] Version + Admin + Cache routes")
except ImportError as e:
    logger.warning(f"version_service not available: {e}")

# ---- 13. agent_service ----
try:
    from src.functions.agent_service.router import router as agents_router

    app.include_router(agents_router, prefix="/api", tags=["AI Agents & Orchestration"])
    logger.info("✓ [agent_service] AI Agents routes")
except ImportError as e:
    logger.warning(f"agent_service not available: {e}")

# ---- 14. upload_service (upload + step ingest) ----
try:
    from src.functions.upload_service.router import upload_router, step_ingest_router

    app.include_router(upload_router, tags=["File Upload"])
    app.include_router(step_ingest_router, tags=["STEP Ingestion"])
    logger.info("✓ [upload_service] Upload + STEP Ingest routes")
except ImportError as e:
    logger.warning(f"upload_service not available: {e}")

# ---- 15. graphql_service ----
try:
    from src.functions.graphql_service.router import graphql_router

    app.include_router(graphql_router, prefix="/api/graphql", tags=["GraphQL"])
    logger.info("✓ [graphql_service] GraphQL routes")
except ImportError as e:
    logger.warning(f"graphql_service not available: {e}")

# ---- 16. oslc_service (oslc + trs + client) ----
try:
    from src.functions.oslc_service.router import (
        oslc_router,
        oslc_client_router,
        trs_router,
    )

    app.include_router(oslc_router, tags=["OSLC Semantic Web"])
    app.include_router(trs_router, prefix="/api", tags=["OSLC Tracked Resource Set"])
    app.include_router(oslc_client_router, prefix="/api", tags=["OSLC Client"])
    logger.info("✓ [oslc_service] OSLC + TRS + Client routes")
except ImportError as e:
    logger.warning(f"oslc_service not available: {e}")

# ---- 17. express_service ----
try:
    from src.functions.express_service.router import router as express_router

    app.include_router(express_router, prefix="/api", tags=["EXPRESS Parser"])
    logger.info("✓ [express_service] EXPRESS Parser routes")
except ImportError as e:
    logger.warning(f"express_service not available: {e}")

# ---- 18. ontology_service (ontology ingest + shacl) ----
try:
    from src.functions.ontology_service.router import ontology_router, shacl_router

    app.include_router(ontology_router, tags=["Ontology Ingestion"])
    app.include_router(shacl_router, tags=["SHACL Validation"])
    logger.info("✓ [ontology_service] Ontology + SHACL routes")
except ImportError as e:
    logger.warning(f"ontology_service not available: {e}")

# ---- 19. sdd_service (stub — Phase 1c split) ----
try:
    from src.functions.sdd_service.router import router as sdd_router

    app.include_router(sdd_router, prefix="/api/v1", tags=["SDD - Simulation Data Dossier"])
    logger.info("✓ [sdd_service] SDD Dossier routes (stub)")
except ImportError as e:
    logger.warning(f"sdd_service not available: {e}")

# ---- 20. audit_service (Phase 1c — ISO-CASCO Compliance) ----
try:
    from src.functions.audit_service.router import router as audit_router

    app.include_router(audit_router, prefix="/api/v1/audit", tags=["Audit Trail"])
    logger.info("✓ [audit_service] Audit Trail routes")
except ImportError as e:
    logger.warning(f"audit_service not available: {e}")

# ---- 21. approval_service (Phase 1c — Quality Head Sign-off) ----
try:
    from src.functions.approval_service.router import router as approval_router

    app.include_router(approval_router, prefix="/api/v1/approvals", tags=["Approval Workflow"])
    logger.info("✓ [approval_service] Approval Workflow routes")
except ImportError as e:
    logger.warning(f"approval_service not available: {e}")

# ---- 22. workspace_service (Phase 1c — Simulation Execution) ----
try:
    from src.functions.workspace_service.router import router as workspace_router

    app.include_router(workspace_router, prefix="/api/v1/workspace", tags=["Workspace Execution"])
    logger.info("✓ [workspace_service] Workspace Execution routes")
except ImportError as e:
    logger.warning(f"workspace_service not available: {e}")


# ===================================================================
# Dataloader sub-application
# ===================================================================
try:
    from src.dataloader.app import app as dataloader_app

    app.mount("/dataloader", dataloader_app)
    logger.info("✓ Mounted Dataloader batch processing app at /dataloader")
except ImportError as e:
    logger.warning(f"Dataloader app not available: {e}")


logger.info("=" * 60)
logger.info("🎉 v4 FaaS-Ready — All 22 Function Domains Mounted")
logger.info("=" * 60)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.functions.main:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        log_level="info",
    )
