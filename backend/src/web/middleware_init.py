"""src.web.middleware_init

Compatibility shim.

Some older scripts/import paths expect a module named `src.web.middleware_init`
which provided middleware bootstrap helpers.

The project is FastAPI-based; middleware now lives under `src.web.middleware`.
This shim keeps legacy imports working while remaining Flask-free.
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI

from .middleware.error_handler import register_error_handlers
from .middleware.jwt_middleware import JWTAuthMiddleware


def add_jwt_middleware(app: FastAPI, redis_client: Any | None = None) -> None:
    """Add the JWTAuthMiddleware to a FastAPI app.

    Note: `src.web.middleware.jwt_middleware.create_jwt_middleware` currently
    returns an instantiated middleware (legacy pattern). For FastAPI/Starlette,
    the idiomatic way is `app.add_middleware(MiddlewareClass, **kwargs)`.

    This helper provides that wiring for any callers still expecting a
    one-liner setup.
    """

    secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    algorithm = os.getenv("JWT_ALGORITHM", "HS256")

    # Optionally allow disabling global JWT enforcement via env for local dev/tests.
    if os.getenv("JWT_ENABLED", "true").strip().lower() in {"0", "false", "no"}:
        return

    app.add_middleware(
        JWTAuthMiddleware,
        secret_key=secret_key,
        algorithm=algorithm,
        redis_client=redis_client,
    )


def init_middleware(app: FastAPI, redis_client: Any | None = None) -> FastAPI:
    """Initialize common middleware and handlers.

    This function is intentionally lightweight and safe to import in minimal
    environments (no Flask dependency).

    Returns the app for convenience.
    """

    # Register generic APIError handlers (optional; app_fastapi.py defines some
    # endpoint-specific exception mappings already).
    try:
        register_error_handlers(app)
    except (RuntimeError, ValueError):
        # Avoid failing startup due to handler duplication or optional setup.
        pass

    # Add JWT middleware (unless disabled via env)
    add_jwt_middleware(app, redis_client=redis_client)

    return app


__all__ = [
    "add_jwt_middleware",
    "init_middleware",
    "register_error_handlers",
    "JWTAuthMiddleware",
]
