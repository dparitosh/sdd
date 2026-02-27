"""
MBSEsmrl Dataloader — Standalone FastAPI Application
=====================================================
Independent batch processing utility for data ingestion into Neo4j.

Run standalone:
    cd backend
    uvicorn src.dataloader.app:app --host 0.0.0.0 --port 5001

Run as FaaS (AWS Lambda / Azure Functions):
    from mangum import Mangum
    from src.dataloader.app import app
    handler = Mangum(app)

Mount into main app:
    from src.dataloader.app import app as dataloader_app
    main_app.mount("/dataloader", dataloader_app)
"""

from contextlib import asynccontextmanager

from dotenv import load_dotenv, find_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from loguru import logger

# Load env
load_dotenv(find_dotenv(usecwd=True))

# Import all routers
from src.dataloader.routes.pipeline import router as pipeline_router
from src.dataloader.routes.xmi import router as xmi_router
from src.dataloader.routes.xsd import router as xsd_router
from src.dataloader.routes.step import router as step_router
from src.dataloader.routes.express import router as express_router
from src.dataloader.routes.ontology import router as ontology_router
from src.dataloader.routes.oslc_seed import router as oslc_router
from src.dataloader.routes.semantic import router as semantic_router
from src.dataloader.routes.sdd import router as sdd_router
from src.dataloader.routes.linking import router as linking_router
from src.dataloader.routes.migrations import router as migrations_router
from src.dataloader.routes.inspect import router as inspect_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown for dataloader app."""
    logger.info("MBSEsmrl Dataloader starting up...")
    yield
    logger.info("MBSEsmrl Dataloader shutting down...")


# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title="MBSEsmrl Dataloader",
    description=(
        "Independent batch processing utility for ingesting MBSE data into Neo4j.\n\n"
        "## Domains\n"
        "- **Pipeline** — Full database reload & orchestration\n"
        "- **XMI** — UML/SysML XMI ingestion (SemanticXMILoader, ~175 node types)\n"
        "- **XSD** — W3C XML Schema ingestion\n"
        "- **STEP** — ISO 10303-21/28 file ingestion\n"
        "- **EXPRESS** — ISO 10303 EXPRESS schema parsing\n"
        "- **Ontology** — OWL/RDF/Turtle ontology ingestion\n"
        "- **OSLC** — OSLC Core/RM vocabulary seeding\n"
        "- **Semantic** — Semantic layer augmentation\n"
        "- **SDD** — Simulation Data Dossier loading\n"
        "- **Linking** — AP239↔AP242↔AP243 cross-schema linking\n"
        "- **Migrations** — Versioned schema migrations\n"
        "- **Inspect** — Read-only graph inspection & audit\n"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


# ---------------------------------------------------------------------------
# Mount routers
# ---------------------------------------------------------------------------

app.include_router(pipeline_router)
app.include_router(xmi_router)
app.include_router(xsd_router)
app.include_router(step_router)
app.include_router(express_router)
app.include_router(ontology_router)
app.include_router(oslc_router)
app.include_router(semantic_router)
app.include_router(sdd_router)
app.include_router(linking_router)
app.include_router(migrations_router)
app.include_router(inspect_router)


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------

@app.get("/", tags=["Root"])
async def root():
    """Dataloader API index — lists all available domains."""
    return {
        "app": "MBSEsmrl Dataloader",
        "version": "1.0.0",
        "docs": "/docs",
        "domains": {
            "pipeline": "/pipeline — Full orchestration (reload, clear, health)",
            "xmi": "/xmi — UML/SysML XMI ingestion",
            "xsd": "/xsd — W3C XML Schema ingestion",
            "step": "/step — STEP ISO 10303 file ingestion",
            "express": "/express — EXPRESS schema parsing",
            "ontology": "/ontology — OWL/RDF ontology ingestion",
            "oslc": "/oslc — OSLC vocabulary seeding",
            "semantic": "/semantic — Semantic layer augmentation",
            "sdd": "/sdd — Simulation Data Dossier loading",
            "linking": "/linking — Cross-schema AP hierarchy linking",
            "migrations": "/migrations — Versioned schema migrations",
            "inspect": "/inspect — Graph inspection & audit",
        },
    }
