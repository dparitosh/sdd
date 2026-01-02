"""
Web middleware components for Flask application.
"""

from .error_handler import (
    APIError,
    DatabaseError,
    NotFoundError,
    ValidationError,
    register_error_handlers,
)

__all__ = [
    "register_error_handlers",
    "APIError",
    "ValidationError",
    "NotFoundError",
    "DatabaseError",
]
