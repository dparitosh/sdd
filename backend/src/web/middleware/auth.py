"""src.web.middleware.auth

JWT helpers for FastAPI.

This project uses FastAPI and provides authentication primarily via
`JWTAuthMiddleware` (see `jwt_middleware.py`) and FastAPI dependencies.

This module keeps a small set of framework-agnostic JWT utilities that are safe
to import without Flask.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
import jwt
from fastapi import HTTPException, Request, status
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
    payload = jwt.decode(token, AuthConfig.SECRET_KEY, algorithms=[AuthConfig.ALGORITHM])

    # Verify token type
    if payload.get("type") != token_type:
        raise jwt.InvalidTokenError(f"Invalid token type. Expected {token_type}")

    logger.debug(f"Token verified for user: {payload.get('sub')}")
    return payload


def get_token_from_header(request: Request) -> str:
    """Extract Bearer token from Authorization header (FastAPI Request)."""
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Use: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return parts[1]


# ============================================================================
# USER AUTHENTICATION
# ============================================================================


def authenticate_user(username: str, password: str) -> dict[str, str] | None:
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
    if not isinstance(username, str) or not username:
        raise jwt.InvalidTokenError("Refresh token missing subject")

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


def revoke_token(token: str) -> None:
    """Add token to blacklist"""
    _token_blacklist.add(token)
    logger.info("Token revoked")


def is_token_revoked(token: str) -> bool:
    """Check if token is blacklisted"""
    return token in _token_blacklist
def require_active_token(request: Request) -> str:
    """Ensure the current Bearer token is not revoked.

    This is intended for use as a FastAPI dependency.
    """

    token = get_token_from_header(request)
    if is_token_revoked(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token revoked. Please login again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token
