"""src.web.error_handler

Compatibility shim.

Historically, some deployments imported error handling utilities from
`src.web.error_handler`. The codebase now keeps FastAPI-native error handling
helpers under `src.web.middleware.error_handler`.

This module re-exports the public symbols so older import paths keep working
without pulling in Flask.
"""

from __future__ import annotations

import importlib

# We intentionally use importlib here to keep this shim resilient in environments
# where static analyzers (or altered PYTHONPATHs) struggle to resolve namespace
# package imports.
_mod = importlib.import_module("src.web.middleware.error_handler")

APIError = getattr(_mod, "APIError")
AuthenticationError = getattr(_mod, "AuthenticationError")
AuthorizationError = getattr(_mod, "AuthorizationError")
DatabaseError = getattr(_mod, "DatabaseError")
NotFoundError = getattr(_mod, "NotFoundError")
RateLimitError = getattr(_mod, "RateLimitError")
ValidationError = getattr(_mod, "ValidationError")
format_validation_errors = getattr(_mod, "format_validation_errors")
log_error = getattr(_mod, "log_error")
register_error_handlers = getattr(_mod, "register_error_handlers")

__all__ = [
    "APIError",
    "AuthenticationError",
    "AuthorizationError",
    "DatabaseError",
    "NotFoundError",
    "RateLimitError",
    "ValidationError",
    "format_validation_errors",
    "log_error",
    "register_error_handlers",
]
