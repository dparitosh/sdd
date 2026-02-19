"""
Rate limiter instance – shared across routes and the main app.

Extracted from ``app_fastapi.py`` so that route modules can import
it without triggering a circular import.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
