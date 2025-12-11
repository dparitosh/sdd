"""
Security utilities for production deployment
Includes password hashing, token management, and rate limiting
"""

import bcrypt
import secrets
from typing import Optional
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify
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
        except Exception as e:
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

    def is_allowed(self, key: str, max_requests: int = 100, window_seconds: int = 60) -> bool:
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


def rate_limit(max_requests: int = 100, window_seconds: int = 60):
    """
    Decorator for Flask routes to add rate limiting

    Usage:
        @app.route('/api/endpoint')
        @rate_limit(max_requests=10, window_seconds=60)
        def endpoint():
            return {'status': 'ok'}
    """

    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Get client identifier (IP address)
            client_ip = request.remote_addr

            # Check rate limit
            if not _rate_limiter.is_allowed(client_ip, max_requests, window_seconds):
                return (
                    jsonify(
                        {
                            "error": "Rate limit exceeded",
                            "message": f"Maximum {max_requests} requests per {window_seconds} seconds",
                        }
                    ),
                    429,
                )

            return f(*args, **kwargs)

        return wrapped

    return decorator


def require_api_key(f):
    """
    Decorator to require API key authentication

    Usage:
        @app.route('/api/protected')
        @require_api_key
        def protected():
            return {'data': 'secret'}
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get("X-API-Key")

        if not api_key:
            return (
                jsonify({"error": "Missing API key", "message": "Please provide X-API-Key header"}),
                401,
            )

        # TODO: Validate API key against database
        # For now, this is a placeholder
        if not api_key.startswith("mbse_"):
            return (
                jsonify({"error": "Invalid API key", "message": "API key format is invalid"}),
                401,
            )

        return f(*args, **kwargs)

    return decorated


class SecurityHeaders:
    """Add security headers to Flask responses"""

    @staticmethod
    def add_security_headers(response):
        """
        Add security headers to response
        Should be called in Flask after_request handler
        """
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "no-referrer-when-downgrade"

        # Remove Flask version header
        response.headers.pop("Server", None)

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


# Example usage in Flask app:
"""
from flask import Flask
from security_utils import (
    PasswordHasher,
    TokenManager,
    rate_limit,
    require_api_key,
    SecurityHeaders
)

app = Flask(__name__)

# Add security headers to all responses
@app.after_request
def add_security_headers(response):
    return SecurityHeaders.add_security_headers(response)

# Public endpoint with rate limiting
@app.route('/api/public')
@rate_limit(max_requests=10, window_seconds=60)
def public_endpoint():
    return {'data': 'public'}

# Protected endpoint requiring API key
@app.route('/api/protected')
@require_api_key
@rate_limit(max_requests=100, window_seconds=60)
def protected_endpoint():
    return {'data': 'protected'}

# User registration with password hashing
@app.route('/api/register', methods=['POST'])
def register():
    password = request.json.get('password')
    hashed = PasswordHasher.hash_password(password)
    # Save hashed password to database
    return {'status': 'registered'}

# User login with password verification
@app.route('/api/login', methods=['POST'])
def login():
    password = request.json.get('password')
    stored_hash = get_user_password_hash()  # From database
    
    if PasswordHasher.verify_password(password, stored_hash):
        token = TokenManager.generate_token()
        return {'token': token}
    
    return {'error': 'Invalid credentials'}, 401
"""
