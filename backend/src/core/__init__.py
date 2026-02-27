"""
core — Shared infrastructure layer for MBSEsmrl backend.

Consolidates Neo4j connection pooling, configuration, caching, and
shared Pydantic models so that **every** consumer (web routers, engine
layer, CLI scripts, FaaS functions) imports from one canonical place.

Modules:
    config      Pydantic-settings ``Settings`` class (env-var driven)
    database    Neo4j driver pool & helpers (``get_driver``, ``Neo4jPool``)
    cache       Unified ``CacheManager`` (in-memory + optional Redis)
    models/     Shared Pydantic request/response schemas
    smrl_adapter    ISO 10303-4443 Neo4j → SMRL conversion
    smrl_validator  JSON Schema validation for SMRL payloads
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("mbsesmrl")
except PackageNotFoundError:
    __version__ = "4.0.0-dev"
