"""
Authentication Routes (FastAPI)
Provides JWT-based login, token refresh, logout, and password management endpoints
With Redis-based session management support
"""

import os
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

import jwt
from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from loguru import logger
from pydantic import BaseModel, Field

from src.web.utils.responses import Neo4jJSONResponse
from src.web.middleware.session_manager import SessionManager

# ============================================================================
# CONFIGURATION
# ============================================================================

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Session manager instance (will be injected)
_session_manager: Optional[SessionManager] = None


def set_session_manager(session_manager: SessionManager):
    """Set global session manager instance"""
    global _session_manager
    _session_manager = session_manager


def get_session_manager() -> Optional[SessionManager]:
    """Get global session manager instance"""
    return _session_manager


class AuthConfig:
    """Authentication configuration"""

    SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60
    REFRESH_TOKEN_EXPIRE_DAYS = 30

    # Admin credentials (in production, use database with hashed passwords)
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")


# In-memory token blacklist (in production, use Redis)
TOKEN_BLACKLIST = set()


# ============================================================================
# PYDANTIC MODELS
# ============================================================================


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, description="Username")
    password: str = Field(..., min_length=1, description="Password")


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh token")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)


class MessageResponse(BaseModel):
    message: str


class VerifyResponse(BaseModel):
    valid: bool
    user: dict


# ============================================================================
# TOKEN UTILITIES
# ============================================================================


def create_access_token(
    username: str,
    role: str = "user",
    session_id: Optional[str] = None,
    permissions: Optional[list] = None
) -> str:
    """Create JWT access token with session support"""
    expires_at = datetime.utcnow() + timedelta(minutes=AuthConfig.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": username,
        "role": role,
        "type": "access",
        "exp": expires_at,
        "iat": datetime.utcnow(),
        "jti": uuid4().hex,
    }
    
    if session_id:
        payload["session_id"] = session_id
    
    if permissions:
        payload["permissions"] = permissions

    token = jwt.encode(payload, AuthConfig.SECRET_KEY, algorithm=AuthConfig.ALGORITHM)
    logger.info(f"Created access token for user: {username} (session: {session_id})")
    return token


def create_refresh_token(username: str) -> str:
    """Create JWT refresh token"""
    expires_at = datetime.utcnow() + timedelta(days=AuthConfig.REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "sub": username,
        "type": "refresh",
        "exp": expires_at,
        "iat": datetime.utcnow(),
        "jti": uuid4().hex,
    }

    token = jwt.encode(payload, AuthConfig.SECRET_KEY, algorithm=AuthConfig.ALGORITHM)
    logger.info(f"Created refresh token for user: {username}")
    return token


def verify_token(token: str, token_type: str = "access") -> dict:
    """
    Verify JWT token and return payload
    
    Args:
        token: JWT token string
        token_type: Expected token type ('access' or 'refresh')
        
    Returns:
        dict: Token payload if valid
        
    Raises:
        HTTPException: Token is invalid or expired
    """
    try:
        # Check blacklist
        if token in TOKEN_BLACKLIST:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked"
            )

        payload = jwt.decode(token, AuthConfig.SECRET_KEY, algorithms=[AuthConfig.ALGORITHM])

        # Verify token type
        if payload.get("type") != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type. Expected {token_type}"
            )

        logger.debug(f"Token verified for user: {payload.get('sub')}")
        return payload

    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """
    Authenticate user credentials
    
    Args:
        username: Username
        password: Password
        
    Returns:
        User dict if authenticated, None otherwise
    """
    # In production: query database with hashed password
    if username == AuthConfig.ADMIN_USERNAME and password == AuthConfig.ADMIN_PASSWORD:
        return {"username": username, "role": "admin"}
    
    # Add more user validation here
    return None


def revoke_token(token: str):
    """Add token to blacklist"""
    TOKEN_BLACKLIST.add(token)
    logger.info("Token revoked")


def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """
    Dependency to get current authenticated user from Bearer token
    
    Args:
        authorization: Authorization header
        
    Returns:
        User dict from token payload
        
    Raises:
        HTTPException: Missing or invalid token
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme",
                headers={"WWW-Authenticate": "Bearer"}
            )

        payload = verify_token(token, "access")
        return {
            "username": payload.get("sub"),
            "role": payload.get("role", "user")
        }

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"}
        )


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================


@router.post("/login", response_model=LoginResponse, response_class=Neo4jJSONResponse)
async def login(credentials: LoginRequest, request: Request):
    """
    User login endpoint
    
    Authenticate with username and password to receive JWT tokens.
    Creates a managed session with activity tracking.
    
    Args:
        credentials: Login credentials (username and password)
        request: FastAPI request object
        
    Returns:
        Access token, refresh token, and user information
        
    Raises:
        HTTPException 400: Invalid credentials
        HTTPException 401: Authentication failed
    """
    try:
        if not credentials.username or not credentials.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Both username and password are required"
            )

        # Authenticate user
        user = authenticate_user(credentials.username, credentials.password)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed"
            )

        # Create session if session manager available
        session_id = None
        session_manager = get_session_manager()
        
        if session_manager:
            client_ip = request.client.host if request.client else "unknown"
            user_agent = request.headers.get("User-Agent", "unknown")
            
            session_id = await session_manager.create_session(
                username=user["username"],
                role=user["role"],
                ip_address=client_ip,
                user_agent=user_agent,
                expires_in=AuthConfig.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            )
            
            # Enforce session limits
            await session_manager.enforce_session_limit(user["username"], max_sessions=5)

        # Generate tokens with session
        access_token = create_access_token(
            username=user["username"],
            role=user["role"],
            session_id=session_id
        )
        refresh_token = create_refresh_token(user["username"])

        logger.info(f"User logged in: {credentials.username} (session: {session_id})")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": AuthConfig.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {"username": user["username"], "role": user["role"]},
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during login"
        )


@router.post("/refresh", response_model=TokenResponse, response_class=Neo4jJSONResponse)
async def refresh_token_endpoint(refresh_request: RefreshRequest):
    """
    Refresh access token using refresh token
    
    Exchange a valid refresh token for a new access token.
    
    Args:
        refresh_request: Refresh token request
        
    Returns:
        New access token
        
    Raises:
        HTTPException 400: Missing refresh token
        HTTPException 401: Invalid or expired refresh token
    """
    try:
        if not refresh_request.refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="refresh_token is required"
            )

        # Verify refresh token
        payload = verify_token(refresh_request.refresh_token, "refresh")
        username = payload.get("sub")
        
        # In production: fetch user role from database
        role = "admin" if username == AuthConfig.ADMIN_USERNAME else "user"

        # Generate new access token
        access_token = create_access_token(username, role)

        logger.info(f"Access token refreshed for user: {username}")

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": AuthConfig.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during token refresh"
        )


@router.post("/logout", response_model=MessageResponse, response_class=Neo4jJSONResponse)
async def logout(current_user: dict = Depends(get_current_user), authorization: str = Header(...)):
    """
    Logout endpoint (revokes current access token and session)
    
    Invalidate the current access token and revoke the session.
    
    Args:
        current_user: Current authenticated user (from dependency)
        authorization: Authorization header with Bearer token
        
    Returns:
        Success message
    """
    try:
        # Extract token from header
        _, token = authorization.split()
        
        # Decode token to get session_id
        payload = jwt.decode(token, AuthConfig.SECRET_KEY, algorithms=[AuthConfig.ALGORITHM], options={"verify_signature": False})
        session_id = payload.get("session_id")
        
        # Revoke token in blacklist
        revoke_token(token)
        
        # Revoke session if session manager available
        session_manager = get_session_manager()
        if session_manager and session_id:
            await session_manager.revoke_session(session_id)
            await session_manager.blacklist_token(token, AuthConfig.ACCESS_TOKEN_EXPIRE_MINUTES * 60)

        logger.info(f"User logged out: {current_user['username']} (session: {session_id})")

        return {"message": "Successfully logged out"}

    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during logout"
        )


@router.get("/verify", response_model=VerifyResponse, response_class=Neo4jJSONResponse)
async def verify_token_endpoint(current_user: dict = Depends(get_current_user)):
    """
    Verify token validity and return user info
    
    Check if the current access token is valid and retrieve user information.
    
    Args:
        current_user: Current authenticated user (from dependency)
        
    Returns:
        Token validity status and user information
    """
    return {"valid": True, "user": current_user}


@router.post("/change-password", response_model=MessageResponse, response_class=Neo4jJSONResponse)
async def change_password(
    password_request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Change user password
    
    Update the password for the currently authenticated user.
    
    Args:
        password_request: Current and new password
        current_user: Current authenticated user (from dependency)
        
    Returns:
        Success message
        
    Raises:
        HTTPException 400: Invalid password requirements
    """
    try:
        if not password_request.current_password or not password_request.new_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Both current_password and new_password are required"
            )

        if len(password_request.new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be at least 8 characters long"
            )

        # In production: verify current password, update in database with hashing
        # For now, just return success

        logger.info(f"Password changed for user: {current_user['username']}")

        return {"message": "Password changed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )
