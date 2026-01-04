"""
JWT-based Authentication Middleware
Provides token generation, validation, and decorators for protected routes
"""

import os
from datetime import datetime, timedelta
from functools import wraps

import jwt
from flask import jsonify, request
from loguru import logger

# ============================================================================
# CONFIGURATION
# ============================================================================


class AuthConfig:
    """Authentication configuration"""

    SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60
    REFRESH_TOKEN_EXPIRE_DAYS = 30

    # Admin credentials (in production, use database with hashed passwords)
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")


# ============================================================================
# TOKEN GENERATION
# ============================================================================


def create_access_token(username: str, role: str = "user") -> str:
    """Create JWT access token"""
    expires_at = datetime.utcnow() + timedelta(
        minutes=AuthConfig.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": username,
        "role": role,
        "type": "access",
        "exp": expires_at,
        "iat": datetime.utcnow(),
    }

    token = jwt.encode(payload, AuthConfig.SECRET_KEY, algorithm=AuthConfig.ALGORITHM)

    logger.info(f"Created access token for user: {username}")
    return token


def create_refresh_token(username: str) -> str:
    """Create JWT refresh token"""
    expires_at = datetime.utcnow() + timedelta(
        days=AuthConfig.REFRESH_TOKEN_EXPIRE_DAYS
    )

    payload = {
        "sub": username,
        "type": "refresh",
        "exp": expires_at,
        "iat": datetime.utcnow(),
    }

    token = jwt.encode(payload, AuthConfig.SECRET_KEY, algorithm=AuthConfig.ALGORITHM)

    logger.info(f"Created refresh token for user: {username}")
    return token


# ============================================================================
# TOKEN VALIDATION
# ============================================================================


def verify_token(token: str, token_type: str = "access") -> dict:
    """
    Verify JWT token and return payload

    Args:
        token: JWT token string
        token_type: Expected token type ('access' or 'refresh')

    Returns:
        dict: Token payload if valid

    Raises:
        jwt.ExpiredSignatureError: Token has expired
        jwt.InvalidTokenError: Token is invalid
    """
    try:
        payload = jwt.decode(
            token, AuthConfig.SECRET_KEY, algorithms=[AuthConfig.ALGORITHM]
        )

        # Verify token type
        if payload.get("type") != token_type:
            raise jwt.InvalidTokenError(f"Invalid token type. Expected {token_type}")

        logger.debug(f"Token verified for user: {payload.get('sub')}")
        return payload

    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        raise
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        raise


def get_token_from_header() -> str:
    """Extract JWT token from Authorization header"""
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        raise ValueError("Authorization header missing")

    parts = auth_header.split()

    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise ValueError("Invalid Authorization header format. Use: Bearer <token>")

    return parts[1]


# ============================================================================
# AUTHENTICATION DECORATORS
# ============================================================================


def require_auth(f):
    """
    Decorator to protect routes with JWT authentication

    Usage:
        @app.route('/protected')
        @require_auth
        def protected_route():
            return jsonify({"message": "You are authenticated"})
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Extract token from header
            token = get_token_from_header()

            # Verify token
            payload = verify_token(token, token_type="access")

            # Add user info to request context
            request.user = {"username": payload.get("sub"), "role": payload.get("role")}

            logger.info(f"Authenticated request from user: {request.user['username']}")

            return f(*args, **kwargs)

        except ValueError as e:
            logger.warning(f"Authentication failed: {e}")
            return jsonify({"error": "Authentication required", "message": str(e)}), 401

        except jwt.ExpiredSignatureError:
            return (
                jsonify(
                    {
                        "error": "Token expired",
                        "message": "Your session has expired. Please login again.",
                    }
                ),
                401,
            )

        except jwt.InvalidTokenError as e:
            return jsonify({"error": "Invalid token", "message": str(e)}), 401

        except Exception as e:
            logger.error(f"Unexpected authentication error: {e}")
            return (
                jsonify(
                    {
                        "error": "Authentication failed",
                        "message": "An unexpected error occurred",
                    }
                ),
                500,
            )

    return decorated_function


def require_role(required_role: str):
    """
    Decorator to restrict access based on user role

    Usage:
        @app.route('/admin')
        @require_auth
        @require_role('admin')
        def admin_route():
            return jsonify({"message": "Admin access granted"})
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = getattr(request, "user", None)

            if not user:
                return (
                    jsonify(
                        {
                            "error": "Authentication required",
                            "message": "You must be logged in to access this resource",
                        }
                    ),
                    401,
                )

            if user.get("role") != required_role:
                logger.warning(
                    f"Access denied for user {user['username']} (role: {user.get('role')}, required: {required_role})"
                )
                return (
                    jsonify(
                        {
                            "error": "Insufficient permissions",
                            "message": f"This resource requires '{required_role}' role",
                        }
                    ),
                    403,
                )

            return f(*args, **kwargs)

        return decorated_function

    return decorator


# ============================================================================
# USER AUTHENTICATION
# ============================================================================


def authenticate_user(username: str, password: str) -> dict | None:
    """
    Authenticate user credentials

    Args:
        username: Username
        password: Password

    Returns:
        dict: User info if authenticated, None otherwise
    """
    # Simple validation (in production, use database with hashed passwords)
    if username == AuthConfig.ADMIN_USERNAME and password == AuthConfig.ADMIN_PASSWORD:
        logger.info(f"User authenticated: {username}")
        return {"username": username, "role": "admin"}

    logger.warning(f"Authentication failed for user: {username}")
    return None


# ============================================================================
# TOKEN REFRESH
# ============================================================================


def refresh_access_token(refresh_token: str) -> dict:
    """
    Generate new access token from refresh token

    Args:
        refresh_token: Valid refresh token

    Returns:
        dict: New access token and metadata

    Raises:
        jwt.ExpiredSignatureError: Refresh token has expired
        jwt.InvalidTokenError: Refresh token is invalid
    """
    payload = verify_token(refresh_token, token_type="refresh")

    username = payload.get("sub")

    # In production, verify user still exists and is active

    new_access_token = create_access_token(username, role="admin")

    logger.info(f"Refreshed access token for user: {username}")

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "expires_in": AuthConfig.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


# ============================================================================
# OPTIONAL: TOKEN BLACKLIST (for logout)
# ============================================================================

# In-memory blacklist (use Redis in production)
_token_blacklist = set()


def revoke_token(token: str):
    """Add token to blacklist"""
    _token_blacklist.add(token)
    logger.info("Token revoked")


def is_token_revoked(token: str) -> bool:
    """Check if token is blacklisted"""
    return token in _token_blacklist


def require_active_token(f):
    """Decorator to check if token is not revoked"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            token = get_token_from_header()

            if is_token_revoked(token):
                return (
                    jsonify(
                        {
                            "error": "Token revoked",
                            "message": "This token has been revoked. Please login again.",
                        }
                    ),
                    401,
                )

            return f(*args, **kwargs)

        except ValueError as e:
            return jsonify({"error": "Authentication required", "message": str(e)}), 401

    return decorated_function
