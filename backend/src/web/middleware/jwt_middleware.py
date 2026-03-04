"""
JWT Authentication Middleware for FastAPI
Global enforcement of JWT authentication with Redis-based session management
"""

import os
from typing import Callable, Optional

import jwt
from fastapi import HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

from src.web.middleware.session_manager import SessionManager


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """
    Global JWT authentication middleware for FastAPI

    This middleware enforces JWT authentication on all routes except public endpoints.
    Uses Redis for session management and token blacklisting.
    """

    def __init__(
        self,
        app,
        secret_key: str,
        algorithm: str = "HS256",
        redis_client=None,
        public_paths: Optional[list] = None,
    ):
        """
        Initialize JWT authentication middleware

        Args:
            app: FastAPI application instance
            secret_key: JWT secret key
            algorithm: JWT algorithm (default: HS256)
            redis_client: Redis client for session management
            public_paths: List of public paths that don't require authentication
        """
        super().__init__(app)
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.session_manager = SessionManager(redis_client) if redis_client else None

        # Default public paths
        self.public_paths = public_paths or [
            "/",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/health",
            "/api/auth/login",
            "/api/auth/refresh",
            "/favicon.ico",
            "/static",
        ]

        logger.info("JWT authentication middleware initialized")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process each request through JWT authentication

        Args:
            request: FastAPI request
            call_next: Next middleware in chain

        Returns:
            Response from next middleware or error response
        """
        # Check if path is public
        if self._is_public_path(request.url.path):
            logger.debug(f"Public path accessed: {request.url.path}")
            return await call_next(request)

        # Extract and verify JWT token
        try:
            token = self._extract_token(request)

            if not token:
                logger.warning(
                    f"No token provided for protected path: {request.url.path}"
                )
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "error": "Authentication required",
                        "message": "Missing authorization token",
                    },
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Check token blacklist — Redis if available, in-memory fallback otherwise
            token_revoked = False
            if self.session_manager:
                token_revoked = await self.session_manager.is_token_blacklisted(token)
            else:
                # Redis is disabled: fall back to the in-memory blacklist in auth_fastapi
                try:
                    from src.web.routes.auth_fastapi import TOKEN_BLACKLIST as _mem_bl  # noqa: PLC0415
                    token_revoked = token in _mem_bl
                except ImportError:
                    pass
            if token_revoked:
                logger.warning("Blacklisted token attempted access")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "error": "Token revoked",
                        "message": "This token has been revoked. Please login again.",
                    },
                )

            # Verify and decode token
            payload = self._verify_token(token)

            # Attach user info to request state
            request.state.user = {
                "username": payload.get("sub"),
                "role": payload.get("role", "user"),
                "permissions": payload.get("permissions", []),
                "session_id": payload.get("session_id"),
            }

            # Update session activity (Redis)
            if self.session_manager:
                session_id = payload.get("session_id")
                if session_id:
                    await self.session_manager.update_session_activity(session_id)

            logger.debug(
                f"Authenticated request: {request.state.user['username']} -> {request.url.path}"
            )

            # Proceed to next middleware
            response = await call_next(request)
            return response

        except jwt.ExpiredSignatureError:
            logger.warning("Expired token attempted access")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "Token expired",
                    "message": "Your session has expired. Please login again.",
                },
                headers={"WWW-Authenticate": "Bearer"},
            )

        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "Invalid token",
                    "message": "Authentication token is invalid",
                },
                headers={"WWW-Authenticate": "Bearer"},
            )

        except HTTPException as e:
            return JSONResponse(status_code=e.status_code, content={"error": e.detail})

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Authentication error",
                    "message": "An error occurred during authentication",
                },
            )

    def _is_public_path(self, path: str) -> bool:
        """
        Check if path is public (doesn't require authentication)

        Args:
            path: Request path

        Returns:
            True if path is public, False otherwise
        """
        # Exact match
        if path in self.public_paths:
            return True

        # Prefix match (for paths like /static/*)
        for public_path in self.public_paths:
            if path.startswith(public_path.rstrip("/")):
                return True

        return False

    def _extract_token(self, request: Request) -> Optional[str]:
        """
        Extract JWT token from Authorization header

        Args:
            request: FastAPI request

        Returns:
            JWT token string or None
        """
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return None

        parts = auth_header.split()

        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format. Use: Bearer <token>",
            )

        return parts[1]

    def _verify_token(self, token: str) -> dict:
        """
        Verify JWT token and return payload

        Args:
            token: JWT token string

        Returns:
            Token payload dictionary

        Raises:
            jwt.ExpiredSignatureError: Token expired
            jwt.InvalidTokenError: Token invalid
        """
        payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

        # Verify token type
        if payload.get("type") != "access":
            raise jwt.InvalidTokenError("Invalid token type. Expected access token")

        return payload


# ============================================================================
# PERMISSION UTILITIES
# ============================================================================


class PermissionChecker:
    """Check user permissions for specific operations"""

    # Role-based permissions matrix
    ROLE_PERMISSIONS = {
        "admin": [
            "read:all",
            "write:all",
            "delete:all",
            "manage:users",
            "manage:system",
            "export:all",
        ],
        "engineer": [
            "read:requirements",
            "read:components",
            "read:analyses",
            "write:requirements",
            "write:components",
            "write:analyses",
            "export:own",
        ],
        "analyst": [
            "read:requirements",
            "read:components",
            "read:analyses",
            "write:analyses",
            "export:own",
        ],
        "viewer": ["read:requirements", "read:components", "read:analyses"],
        "user": ["read:requirements", "read:components"],
    }

    @classmethod
    def get_permissions_for_role(cls, role: str) -> list:
        """Get list of permissions for a role"""
        return cls.ROLE_PERMISSIONS.get(role, cls.ROLE_PERMISSIONS["user"])

    @classmethod
    def has_permission(cls, user_role: str, required_permission: str) -> bool:
        """
        Check if user role has required permission

        Args:
            user_role: User's role
            required_permission: Required permission

        Returns:
            True if user has permission, False otherwise
        """
        permissions = cls.get_permissions_for_role(user_role)

        # Check exact match
        if required_permission in permissions:
            return True

        # Check wildcard permissions
        if "read:all" in permissions and required_permission.startswith("read:"):
            return True
        if "write:all" in permissions and required_permission.startswith("write:"):
            return True
        if "delete:all" in permissions and required_permission.startswith("delete:"):
            return True

        return False


# ============================================================================
# FASTAPI DEPENDENCIES
# ============================================================================


def get_current_user_from_request(request: Request) -> dict:
    """
    FastAPI dependency to get current user from request state

    Usage:
        @router.get("/protected")
        async def protected_route(user: dict = Depends(get_current_user_from_request)):
            return {"username": user["username"]}

    Args:
        request: FastAPI request

    Returns:
        User dict from request state

    Raises:
        HTTPException: User not authenticated
    """
    if not hasattr(request.state, "user"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )

    return request.state.user


def require_permission(permission: str):
    """
    FastAPI dependency to require specific permission

    Usage:
        @router.post("/requirements")
        async def create_requirement(
            user: dict = Depends(get_current_user_from_request),
            _: None = Depends(require_permission("write:requirements"))
        ):
            return {"status": "created"}

    Args:
        permission: Required permission string

    Returns:
        Dependency function
    """

    def check_permission(user: dict = get_current_user_from_request):
        if not PermissionChecker.has_permission(user["role"], permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {permission}",
            )
        return None

    return check_permission


def require_role(required_role: str):
    """
    FastAPI dependency to require specific role

    Usage:
        @router.delete("/system/reset")
        async def reset_system(
            user: dict = Depends(get_current_user_from_request),
            _: None = Depends(require_role("admin"))
        ):
            return {"status": "reset"}

    Args:
        required_role: Required role string

    Returns:
        Dependency function
    """

    def check_role(user: dict = get_current_user_from_request):
        if user["role"] != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient role. Required: {required_role}",
            )
        return None

    return check_role


# ============================================================================
# CONFIGURATION
# ============================================================================


def create_jwt_middleware(app, redis_client=None) -> JWTAuthMiddleware:
    """
    Factory function to create and configure JWT middleware

    Args:
        app: FastAPI application
        redis_client: Redis client for session management

    Returns:
        Configured JWTAuthMiddleware instance
    """
    secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")

    if secret_key == "your-secret-key-change-in-production":
        logger.warning(
            "⚠️  Using default JWT secret key! Change JWT_SECRET_KEY in production!"
        )

    return JWTAuthMiddleware(
        app=app, secret_key=secret_key, algorithm="HS256", redis_client=redis_client
    )
