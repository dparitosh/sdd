"""
FastAPI dependencies for authentication, rate limiting, and shared resources.
"""

import hmac
import os
from typing import Optional

from fastapi import Header, HTTPException, status
from loguru import logger


def get_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """
    Dependency for API key authentication.

    Args:
        x_api_key: API key from X-API-Key header

    Returns:
        The validated API key

    Raises:
        HTTPException: If API key is missing or invalid
    """
    expected_key = os.getenv("API_KEY")

    # If no API key configured, only allow in explicit development mode
    if not expected_key:
        if os.getenv("ENVIRONMENT", "production").lower() in ("development", "dev", "local"):
            logger.warning("No API_KEY configured - authentication bypassed (dev mode)")
            return "development"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server misconfiguration: API_KEY not set. Set API_KEY env var or ENVIRONMENT=development.",
        )

    if not x_api_key:
        logger.warning("Missing X-API-Key header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Please provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if not hmac.compare_digest(x_api_key, expected_key):
        logger.warning(f"Invalid API key attempt: {x_api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return x_api_key


def get_optional_api_key(x_api_key: Optional[str] = Header(None)) -> Optional[str]:
    """
    Optional API key dependency for endpoints that don't require auth.

    Args:
        x_api_key: API key from X-API-Key header

    Returns:
        The API key if provided, None otherwise
    """
    return x_api_key
