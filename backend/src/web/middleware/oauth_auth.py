"""src.web.middleware.oauth_auth

DEPRECATED (legacy OAuth/OIDC).

The backend uses FastAPI. The prior implementation used a different web stack
and is intentionally removed.

If OAuth/OIDC is required, implement it using:
- Authlib's Starlette integration (authlib.integrations.starlette_client)
- FastAPI security utilities (fastapi.security)
- Starlette session middleware

This placeholder is kept to avoid import errors from stale references.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class OIDCAuthenticator:
    """Placeholder class (not implemented for FastAPI)."""

    def __init__(self, app=None):  # noqa: ANN001
        self.app = app

    def login(self, provider: str = "azure"):  # noqa: ANN001
        raise NotImplementedError("OIDCAuthenticator is not implemented for FastAPI")


def require_auth(*args, **kwargs):  # noqa: ANN001
    raise NotImplementedError("Legacy Flask OAuth decorators are not supported")


def require_role(*args, **kwargs):  # noqa: ANN001
    raise NotImplementedError("Legacy Flask OAuth decorators are not supported")


__all__ = ["OIDCAuthenticator", "require_auth", "require_role"]

