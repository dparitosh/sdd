"""src.web.middleware.error_handler

FastAPI-native error handling utilities.

This module previously implemented handlers for a different web stack.
The project uses FastAPI, so we provide equivalent exception classes and a
registration helper that works with FastAPI/Starlette.
"""

import traceback
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.exceptions import HTTPException as StarletteHTTPException

# Custom Exception Classes


class APIError(Exception):
    """Base class for API errors"""

    def __init__(
        self, message: str, status_code: int = 500, payload: Dict[str, Any] | None = None
    ):
        super().__init__()
        self.message = message
        self.status_code = status_code
        self.payload = payload or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for JSON response"""
        rv = {
            "error": {
                "type": self.__class__.__name__,
                "message": self.message,
                "status_code": self.status_code,
            }
        }

        # Add any additional payload data
        if self.payload:
            rv["error"].update(self.payload)

        return rv


class ValidationError(APIError):
    """Raised when request validation fails"""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        payload: Dict[str, Any] | None = None,
    ):
        payload = payload or {}
        if field:
            payload["field"] = field
        super().__init__(message, status_code=400, payload=payload)


class NotFoundError(APIError):
    """Raised when requested resource not found"""

    def __init__(
        self,
        resource_type: str | None = None,
        resource_id: str | None = None,
        message: str | None = None,
    ):
        if message is None:
            if resource_type and resource_id:
                message = f"{resource_type} with ID '{resource_id}' not found"
            elif resource_type:
                message = f"{resource_type} not found"
            else:
                message = "Resource not found"

        payload = {}
        if resource_type:
            payload["resource_type"] = resource_type
        if resource_id:
            payload["resource_id"] = resource_id

        super().__init__(message, status_code=404, payload=payload)


class DatabaseError(APIError):
    """Raised when database operation fails"""

    def __init__(
        self,
        message: str = "Database operation failed",
        original_error: Exception | None = None,
    ):
        payload = {}
        if original_error:
            payload["original_error"] = str(original_error)

        super().__init__(message, status_code=500, payload=payload)


class AuthenticationError(APIError):
    """Raised when authentication fails"""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, status_code=401)


class AuthorizationError(APIError):
    """Raised when authorization fails"""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, status_code=403)


class RateLimitError(APIError):
    """Raised when rate limit exceeded"""

    def __init__(
        self, message: str = "Rate limit exceeded", retry_after: int | None = None
    ):
        payload = {}
        if retry_after:
            payload["retry_after"] = retry_after

        super().__init__(message, status_code=429, payload=payload)


def register_error_handlers(app: FastAPI) -> None:
    """Register exception handlers with a FastAPI application.

    Note: `app_fastapi.py` already defines a few custom handlers for auth
    compatibility. Only call this if you want to standardize APIError handling
    across additional apps.
    """

    @app.exception_handler(APIError)
    async def handle_api_error(request: Request, exc: APIError):
        log_error(exc, request, exc.status_code)
        return JSONResponse(status_code=exc.status_code, content=exc.to_dict())

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException):
        # Preserve FastAPI/Starlette's standard "detail" shape by default.
        log_error(exc, request, exc.status_code)
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception):
        logger.error(f"Unexpected error: {exc}")
        logger.error(traceback.format_exc())
        log_error(exc, request, 500)

        # Avoid leaking internals by default.
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "type": "InternalServerError",
                    "message": "An internal server error occurred",
                    "status_code": 500,
                }
            },
        )


# Utility Functions


def log_error(error: Exception, request_obj, status_code: int):
    """
    Log error with request context.

    Args:
        error: Exception instance
        request_obj: Flask request object
        status_code: HTTP status code
    """
    # Starlette/FastAPI request fields differ slightly from Flask.
    client = getattr(request_obj, "client", None)
    error_data = {
        "error_type": error.__class__.__name__,
        "error_message": str(error),
        "status_code": status_code,
        "method": getattr(request_obj, "method", None),
        "path": getattr(getattr(request_obj, "url", None), "path", None),
        "query_params": dict(getattr(request_obj, "query_params", {}) or {}),
        "remote_addr": getattr(client, "host", None) if client else None,
        "user_agent": (request_obj.headers.get("user-agent") if hasattr(request_obj, "headers") else None),
    }

    # Log at appropriate level based on status code
    if status_code >= 500:
        logger.error(f"Server Error: {error_data}")
    elif status_code >= 400:
        logger.warning(f"Client Error: {error_data}")
    else:
        logger.info(f"Request Error: {error_data}")


def format_validation_errors(errors: Dict[str, Any]) -> ValidationError:
    """
    Format validation errors for consistent response.

    Args:
        errors: Dictionary of field-level validation errors

    Returns:
        ValidationError with formatted message

    Usage:
        errors = {'name': 'Field is required', 'age': 'Must be positive'}
        raise format_validation_errors(errors)
    """
    if isinstance(errors, dict):
        messages = [f"{field}: {msg}" for field, msg in errors.items()]
        message = "Validation failed: " + "; ".join(messages)
        return ValidationError(message, payload={"validation_errors": errors})
    else:
        return ValidationError(str(errors))



# NOTE: Request logging and health endpoints are implemented directly in
# `src.web.app_fastapi` and route modules.
