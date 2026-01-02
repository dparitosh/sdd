"""
Error Handler Middleware - Standardized error responses for Flask API
Provides consistent error handling, logging, and user-friendly error messages
"""

import sys
import traceback
from typing import Any, Dict, Tuple

from flask import jsonify, request
from loguru import logger
from werkzeug.exceptions import HTTPException

# Custom Exception Classes


class APIError(Exception):
    """Base class for API errors"""

    def __init__(self, message: str, status_code: int = 500, payload: Dict[str, Any] = None):
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

    def __init__(self, message: str, field: str = None, payload: Dict[str, Any] = None):
        payload = payload or {}
        if field:
            payload["field"] = field
        super().__init__(message, status_code=400, payload=payload)


class NotFoundError(APIError):
    """Raised when requested resource not found"""

    def __init__(self, resource_type: str = None, resource_id: str = None, message: str = None):
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
        self, message: str = "Database operation failed", original_error: Exception = None
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

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = None):
        payload = {}
        if retry_after:
            payload["retry_after"] = retry_after

        super().__init__(message, status_code=429, payload=payload)


# Error Handler Registration


def register_error_handlers(app):
    """
    Register error handlers with Flask application.

    Args:
        app: Flask application instance

    Usage:
        from web.middleware import register_error_handlers
        register_error_handlers(app)
    """

    @app.errorhandler(APIError)
    def handle_api_error(error: APIError) -> Tuple[Dict[str, Any], int]:
        """Handle custom API errors"""
        response = error.to_dict()

        # Log error with context
        log_error(error, request, error.status_code)

        return jsonify(response), error.status_code

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException) -> Tuple[Dict[str, Any], int]:
        """Handle Werkzeug HTTP exceptions"""
        response = {
            "error": {
                "type": "HTTPException",
                "message": error.description or str(error),
                "status_code": error.code,
            }
        }

        # Log error with context
        log_error(error, request, error.code)

        return jsonify(response), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception) -> Tuple[Dict[str, Any], int]:
        """Handle unexpected errors"""
        # Log full traceback for debugging
        logger.error(f"Unexpected error: {str(error)}")
        logger.error(traceback.format_exc())

        # Don't expose internal error details in production
        if app.config.get("DEBUG", False):
            message = str(error)
            error_type = error.__class__.__name__
        else:
            message = "An internal server error occurred"
            error_type = "InternalServerError"

        response = {"error": {"type": error_type, "message": message, "status_code": 500}}

        # Log error with context
        log_error(error, request, 500)

        return jsonify(response), 500

    @app.errorhandler(404)
    def handle_404(error) -> Tuple[Dict[str, Any], int]:
        """Handle 404 Not Found errors"""
        response = {
            "error": {
                "type": "NotFound",
                "message": f"Endpoint '{request.path}' not found",
                "status_code": 404,
                "path": request.path,
                "method": request.method,
            }
        }

        logger.warning(f"404 Not Found: {request.method} {request.path}")

        return jsonify(response), 404

    @app.errorhandler(405)
    def handle_405(error) -> Tuple[Dict[str, Any], int]:
        """Handle 405 Method Not Allowed errors"""
        response = {
            "error": {
                "type": "MethodNotAllowed",
                "message": f"Method '{request.method}' not allowed for endpoint '{request.path}'",
                "status_code": 405,
                "path": request.path,
                "method": request.method,
            }
        }

        logger.warning(f"405 Method Not Allowed: {request.method} {request.path}")

        return jsonify(response), 405

    logger.info("Error handlers registered successfully")


# Utility Functions


def log_error(error: Exception, request_obj, status_code: int):
    """
    Log error with request context.

    Args:
        error: Exception instance
        request_obj: Flask request object
        status_code: HTTP status code
    """
    error_data = {
        "error_type": error.__class__.__name__,
        "error_message": str(error),
        "status_code": status_code,
        "method": request_obj.method,
        "path": request_obj.path,
        "query_params": dict(request_obj.args),
        "remote_addr": request_obj.remote_addr,
        "user_agent": request_obj.user_agent.string,
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


# Request Logging Middleware


def log_request_info(app):
    """
    Add request/response logging middleware.

    Args:
        app: Flask application instance

    Usage:
        from web.middleware.error_handler import log_request_info
        log_request_info(app)
    """

    @app.before_request
    def before_request():
        """Log incoming request details"""
        logger.debug(f"→ {request.method} {request.path} | IP: {request.remote_addr}")

        # Log query parameters (if any)
        if request.args:
            logger.debug(f"  Query params: {dict(request.args)}")

        # Log request body (for POST/PUT/PATCH, excluding large payloads)
        if request.method in ["POST", "PUT", "PATCH"]:
            if request.content_length and request.content_length < 10000:  # 10KB limit
                try:
                    logger.debug(f"  Request body: {request.get_json()}")
                except Exception:
                    pass  # Ignore JSON parsing errors

    @app.after_request
    def after_request(response):
        """Log outgoing response details"""
        logger.debug(f"← {request.method} {request.path} | Status: {response.status_code}")
        return response

    logger.info("Request logging middleware registered")


# Health Check Utilities


def create_health_check_endpoint(app, neo4j_service=None):
    """
    Create /health endpoint for monitoring.

    Args:
        app: Flask application instance
        neo4j_service: Optional Neo4jService instance for database health check

    Usage:
        from web.middleware.error_handler import create_health_check_endpoint
        from web.services import get_neo4j_service
        create_health_check_endpoint(app, get_neo4j_service())
    """

    @app.route("/health", methods=["GET"])
    def health_check():
        """Health check endpoint for load balancers/monitoring"""
        health = {"status": "healthy", "service": "mbse-knowledge-graph", "checks": {}}

        # Check database connection (if service provided)
        if neo4j_service:
            try:
                # Simple query to verify connectivity
                result = neo4j_service.execute_query("RETURN 1 as test")
                health["checks"]["database"] = "healthy" if result else "unhealthy"
            except Exception as e:
                health["checks"]["database"] = "unhealthy"
                health["status"] = "degraded"
                logger.error(f"Database health check failed: {str(e)}")

        # Determine overall status
        if health["status"] == "degraded":
            status_code = 503  # Service Unavailable
        else:
            status_code = 200

        return jsonify(health), status_code

    logger.info("Health check endpoint created at /health")
