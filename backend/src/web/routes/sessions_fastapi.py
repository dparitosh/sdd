"""
Session Management Routes (FastAPI)
Provides endpoints for managing user sessions
"""

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field

from src.web.utils.responses import Neo4jJSONResponse
from src.web.middleware.jwt_middleware import (
    get_current_user_from_request,
    require_role,
)
from src.web.routes.auth_fastapi import get_session_manager

router = APIRouter(prefix="/sessions", tags=["Session Management"])


# ============================================================================
# PYDANTIC MODELS
# ============================================================================


class SessionInfo(BaseModel):
    """Single session information"""

    session_id: str
    username: str
    role: str
    ip_address: str
    user_agent: str
    created_at: str
    last_activity: str
    expires_at: str


class SessionListResponse(BaseModel):
    """List of user sessions"""

    sessions: list[SessionInfo]
    total: int


class SessionStatsResponse(BaseModel):
    """Session statistics"""

    active_sessions: int
    blacklisted_tokens: int
    timestamp: str


class MessageResponse(BaseModel):
    """Generic message response"""

    message: str


# ============================================================================
# SESSION ENDPOINTS
# ============================================================================


@router.get("/me", response_model=SessionListResponse, response_class=Neo4jJSONResponse)
async def get_my_sessions(current_user: dict = Depends(get_current_user_from_request)):
    """
    Get all active sessions for current user

    Returns list of all active sessions including current session.

    Args:
        current_user: Current authenticated user

    Returns:
        List of active sessions
    """
    try:
        session_manager = get_session_manager()

        if not session_manager:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Session management not available",
            )

        username = current_user["username"]
        sessions = await session_manager.get_user_sessions(username)

        logger.info(f"Retrieved {len(sessions)} sessions for user: {username}")

        return {"sessions": sessions, "total": len(sessions)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sessions",
        )


@router.delete(
    "/me/{session_id}", response_model=MessageResponse, response_class=Neo4jJSONResponse
)
async def revoke_my_session(
    session_id: str, current_user: dict = Depends(get_current_user_from_request)
):
    """
    Revoke a specific session (except current session)

    Args:
        session_id: Session ID to revoke
        current_user: Current authenticated user

    Returns:
        Success message
    """
    try:
        session_manager = get_session_manager()

        if not session_manager:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Session management not available",
            )

        username = current_user["username"]

        # Get session to verify ownership
        session = await session_manager.get_session(session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
            )

        if session["username"] != username:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot revoke another user's session",
            )

        # Prevent revoking current session (use logout endpoint instead)
        if session_id == current_user.get("session_id"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot revoke current session. Use /auth/logout instead",
            )

        # Revoke session
        await session_manager.revoke_session(session_id)

        logger.info(f"User {username} revoked session: {session_id}")

        return {"message": f"Session {session_id} revoked successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke session",
        )


@router.delete(
    "/me/all", response_model=MessageResponse, response_class=Neo4jJSONResponse
)
async def revoke_all_my_sessions(
    current_user: dict = Depends(get_current_user_from_request),
):
    """
    Revoke all sessions except current one

    Useful for "logout from all devices" functionality.

    Args:
        current_user: Current authenticated user

    Returns:
        Success message
    """
    try:
        session_manager = get_session_manager()

        if not session_manager:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Session management not available",
            )

        username = current_user["username"]
        current_session_id = current_user.get("session_id")

        # Get all user sessions
        sessions = await session_manager.get_user_sessions(username)

        # Revoke all except current
        revoked_count = 0
        for session in sessions:
            if session["session_id"] != current_session_id:
                await session_manager.revoke_session(session["session_id"])
                revoked_count += 1

        logger.info(f"User {username} revoked {revoked_count} sessions (kept current)")

        return {"message": f"Revoked {revoked_count} sessions successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking all sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke sessions",
        )


# ============================================================================
# ADMIN SESSION ENDPOINTS
# ============================================================================


@router.get(
    "/stats",
    response_model=SessionStatsResponse,
    response_class=Neo4jJSONResponse,
    dependencies=[Depends(require_role("admin"))],
)
async def get_session_statistics(
    current_user: dict = Depends(get_current_user_from_request),
):
    """
    Get global session statistics (admin only)

    Returns statistics about active sessions and blacklisted tokens.

    Args:
        current_user: Current authenticated user (must be admin)

    Returns:
        Session statistics
    """
    try:
        session_manager = get_session_manager()

        if not session_manager:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Session management not available",
            )

        stats = await session_manager.get_session_statistics()

        logger.info(f"Admin {current_user['username']} retrieved session statistics")

        return stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics",
        )


@router.get(
    "/user/{username}",
    response_model=SessionListResponse,
    response_class=Neo4jJSONResponse,
    dependencies=[Depends(require_role("admin"))],
)
async def get_user_sessions_admin(
    username: str, current_user: dict = Depends(get_current_user_from_request)
):
    """
    Get all sessions for a specific user (admin only)

    Args:
        username: Target username
        current_user: Current authenticated user (must be admin)

    Returns:
        List of user sessions
    """
    try:
        session_manager = get_session_manager()

        if not session_manager:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Session management not available",
            )

        sessions = await session_manager.get_user_sessions(username)

        logger.info(
            f"Admin {current_user['username']} retrieved sessions for user: {username}"
        )

        return {"sessions": sessions, "total": len(sessions)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user sessions",
        )


@router.delete(
    "/user/{username}",
    response_model=MessageResponse,
    response_class=Neo4jJSONResponse,
    dependencies=[Depends(require_role("admin"))],
)
async def revoke_all_user_sessions_admin(
    username: str, current_user: dict = Depends(get_current_user_from_request)
):
    """
    Revoke all sessions for a specific user (admin only)

    Useful for security incidents or forced logouts.

    Args:
        username: Target username
        current_user: Current authenticated user (must be admin)

    Returns:
        Success message
    """
    try:
        session_manager = get_session_manager()

        if not session_manager:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Session management not available",
            )

        await session_manager.revoke_all_user_sessions(username)

        logger.warning(
            f"Admin {current_user['username']} revoked all sessions for user: {username}"
        )

        return {"message": f"All sessions for user {username} have been revoked"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking user sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke user sessions",
        )


@router.post(
    "/cleanup",
    response_model=MessageResponse,
    response_class=Neo4jJSONResponse,
    dependencies=[Depends(require_role("admin"))],
)
async def cleanup_expired_sessions(
    current_user: dict = Depends(get_current_user_from_request),
):
    """
    Manually cleanup expired sessions (admin only)

    Redis automatically handles expiration, but this provides manual cleanup.

    Args:
        current_user: Current authenticated user (must be admin)

    Returns:
        Success message with cleanup count
    """
    try:
        session_manager = get_session_manager()

        if not session_manager:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Session management not available",
            )

        cleaned = await session_manager.cleanup_expired_sessions()

        logger.info(
            f"Admin {current_user['username']} cleaned up {cleaned} expired sessions"
        )

        return {"message": f"Cleaned up {cleaned} expired sessions"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleaning up sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup sessions",
        )
