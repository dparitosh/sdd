"""src.web.middleware.security_utils

Security utilities for production deployment.

This module is FastAPI-safe (no Flask imports). It contains framework-agnostic
helpers (password hashing, token generation, basic in-memory rate limiting).

NOTE: For API key auth and rate limiting in FastAPI, prefer `slowapi` (already
used by the app) or dependency-based checks.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta

import bcrypt
from fastapi import HTTPException, Request, status
from loguru import logger


class PasswordHasher:
    """Secure password hashing using bcrypt"""

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt

        Args:
            password: Plain text password

        Returns:
            Hashed password as string
        """
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """
        Verify a password against its hash

        Args:
            password: Plain text password
            hashed: Hashed password

        Returns:
            True if password matches
        """
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except (ValueError, TypeError) as e:
            logger.error(f"Password verification failed: {e}")
            return False


class TokenManager:
    """Secure token generation and validation"""

    @staticmethod
    def generate_token(length: int = 32) -> str:
        """
        Generate a secure random token

        Args:
            length: Token length in bytes

        Returns:
            Hex-encoded token
        """
        return secrets.token_hex(length)

    @staticmethod
    def generate_api_key() -> str:
        """Generate a secure API key"""
        return f"mbse_{secrets.token_urlsafe(32)}"


class RateLimiter:
    """
    Simple in-memory rate limiter
    For production, use Redis-backed rate limiting
    """

    def __init__(self):
        self._requests = {}  # {ip: [(timestamp, count), ...]}
        self._cleanup_interval = timedelta(minutes=5)
        self._last_cleanup = datetime.now()

    def is_allowed(
        self, key: str, max_requests: int = 100, window_seconds: int = 60
    ) -> bool:
        """
        Check if request is allowed under rate limit

        Args:
            key: Identifier (usually IP address)
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds

        Returns:
            True if request is allowed
        """
        now = datetime.now()
        window_start = now - timedelta(seconds=window_seconds)

        # Cleanup old entries periodically
        if now - self._last_cleanup > self._cleanup_interval:
            self._cleanup_old_entries(window_start)

        # Get recent requests for this key
        if key not in self._requests:
            self._requests[key] = []

        # Filter requests within time window
        recent_requests = [ts for ts in self._requests[key] if ts > window_start]

        # Check if limit exceeded
        if len(recent_requests) >= max_requests:
            logger.warning(f"Rate limit exceeded for {key}")
            return False

        # Add current request
        recent_requests.append(now)
        self._requests[key] = recent_requests

        return True

    def _cleanup_old_entries(self, cutoff: datetime):
        """Remove old entries to prevent memory bloat"""
        for key in list(self._requests.keys()):
            self._requests[key] = [ts for ts in self._requests[key] if ts > cutoff]
            if not self._requests[key]:
                del self._requests[key]

        self._last_cleanup = datetime.now()


# Global rate limiter instance
_rate_limiter = RateLimiter()


def enforce_rate_limit(request: Request, *, max_requests: int = 100, window_seconds: int = 60) -> None:
    """Enforce a simple in-memory rate limit.

    In production, prefer Redis-backed rate limiting (e.g., `slowapi`).
    """

    client_ip = request.client.host if request.client else "unknown"
    if not _rate_limiter.is_allowed(client_ip, max_requests, window_seconds):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: max {max_requests} per {window_seconds}s",
        )


def require_api_key(request: Request) -> str:
    """Extract and validate an API key from request headers.

    This is designed to be used as a FastAPI dependency.

    Note: This currently validates format only (prefix). Hook into a proper
    datastore if you need real API keys.
    """

    api_key = request.headers.get("X-API-Key")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key (X-API-Key header)",
        )

    if not api_key.startswith("mbse_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format",
        )

    return api_key


class SecurityHeaders:
    """Add security headers to a response-like object.

    Works with Starlette/FastAPI responses (and most WSGI responses that expose
    a `headers` mapping).
    """

    @staticmethod
    def add_security_headers(response):
        """
        Add security headers to response
        Should be called in a FastAPI/Starlette middleware after the response is created.
        """
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Referrer-Policy"] = "no-referrer-when-downgrade"

        # Remove server version header when possible
        try:
            response.headers.pop("Server", None)
        except (AttributeError, TypeError):
            pass

        return response


def sanitize_input(data: str, max_length: int = 1000) -> str:
    """
    Sanitize user input to prevent injection attacks

    Args:
        data: Input string
        max_length: Maximum allowed length

    Returns:
        Sanitized string
    """
    if not data:
        return ""

    # Truncate to max length
    data = data[:max_length]

    # Remove potentially dangerous characters
    dangerous_chars = ["<", ">", '"', "'", "&", "\x00"]
    for char in dangerous_chars:
        data = data.replace(char, "")

    return data.strip()


__all__ = [
    "PasswordHasher",
    "TokenManager",
    "RateLimiter",
    "enforce_rate_limit",
    "require_api_key",
    "SecurityHeaders",
    "sanitize_input",
]
