"""src.web.middleware

FastAPI middleware and related helpers.

IMPORTANT:
This package must remain safe to import in environments where Flask is not
installed. Keep imports in this file minimal and avoid importing optional or
legacy components at module import time.
"""

# Intentionally do not eagerly import submodules here.
# Import what you need directly, e.g.:
#   from src.web.middleware.jwt_middleware import create_jwt_middleware

__all__: list[str] = []
