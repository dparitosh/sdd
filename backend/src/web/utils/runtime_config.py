"""Runtime configuration helpers.

Centralizes URL/host/port resolution for the backend web layer.

All values are sourced from environment variables (typically via .env).
The helpers intentionally fail fast with clear messages when required values
are missing, so misconfiguration is obvious.
"""

from __future__ import annotations

import os
from urllib.parse import urlparse


def _strip_trailing_slash(url: str) -> str:
    return url.rstrip("/")


def _build_http_base_url(host: str | None, port: str | None) -> str | None:
    if not host or not port:
        return None
    return f"http://{host}:{port}"


def get_backend_base_url() -> str:
    """Return the backend base URL (scheme + host + port).

    Resolution order:
      1) API_BASE_URL
      2) BACKEND_HOST + BACKEND_PORT
    """
    base = os.getenv("API_BASE_URL") or os.getenv("VITE_API_BASE_URL")
    if base and base.strip():
        return _strip_trailing_slash(base.strip())

    host = os.getenv("BACKEND_HOST")
    port = os.getenv("BACKEND_PORT")
    built = _build_http_base_url(host, port)
    if built:
        return built

    raise ValueError(
        "Missing backend URL configuration. Set API_BASE_URL (recommended) "
        "or set BACKEND_HOST and BACKEND_PORT in your .env."
    )


def get_frontend_url() -> str:
    """Return the frontend base URL (scheme + host + port).

    Resolution order:
      1) FRONTEND_URL
      2) FRONTEND_HOST + FRONTEND_PORT
    """
    base = os.getenv("FRONTEND_URL")
    if base and base.strip():
        return _strip_trailing_slash(base.strip())

    host = os.getenv("FRONTEND_HOST")
    port = os.getenv("FRONTEND_PORT")
    built = _build_http_base_url(host, port)
    if built:
        return built

    raise ValueError(
        "Missing frontend URL configuration. Set FRONTEND_URL (recommended) "
        "or set FRONTEND_HOST and FRONTEND_PORT in your .env."
    )


def get_public_base_url() -> str:
    """Return the public base URL used to construct absolute resource URIs.

    This is used for OSLC/TRS notifications and absolute hrefs.

    Resolution order:
      1) PUBLIC_BASE_URL
      2) API_BASE_URL (or BACKEND_HOST/BACKEND_PORT fallback)
    """
    base = os.getenv("PUBLIC_BASE_URL")
    if base and base.strip():
        return _strip_trailing_slash(base.strip())
    return get_backend_base_url()


def get_cors_origins() -> list[str]:
    """Return the list of allowed CORS origins.

    If CORS_ORIGINS is set, it is treated as a comma-separated list.
    Otherwise, default to the resolved frontend URL.

    For developer convenience, when the configured frontend host is a loopback
    address (127.0.0.1/0.0.0.0), also allow the equivalent localhost origin.
    """
    raw = os.getenv("CORS_ORIGINS")
    if raw and raw.strip():
        raw_origins = [o.strip() for o in raw.split(",") if o.strip()]
        return [_strip_trailing_slash(o) for o in raw_origins]

    frontend_url = get_frontend_url()
    origins: list[str] = [_strip_trailing_slash(frontend_url)]

    # Convenience: allow localhost alias for loopback bindings.
    frontend_host = os.getenv("FRONTEND_HOST")
    frontend_port = os.getenv("FRONTEND_PORT")
    if frontend_host in ("127.0.0.1", "0.0.0.0") and frontend_port:
        origins.append(f"http://localhost:{frontend_port}")

    # Deduplicate while preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for o in origins:
        if o not in seen:
            seen.add(o)
            deduped.append(o)

    # Validate that each origin looks like a URL with scheme.
    for origin in deduped:
        parsed = urlparse(origin)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(
                f"Invalid CORS origin {origin!r}. Use full origins like 'http://localhost:3001'."
            )

    return deduped
