"""
Redis-based Session Management for JWT Authentication
Handles token blacklisting, session tracking, and user activity monitoring
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Optional

from loguru import logger


class SessionManager:
    """
    Manage user sessions and token blacklist using Redis

    Features:
    - Token blacklist for logout/revocation
    - Active session tracking
    - Session expiry management
    - User activity monitoring
    - Concurrent session limits
    """

    def __init__(self, redis_client, prefix: str = "mbse"):
        """
        Initialize session manager

        Args:
            redis_client: Redis client instance
            prefix: Key prefix for Redis storage
        """
        self.redis = redis_client
        self.prefix = prefix
        self.blacklist_key = f"{prefix}:token:blacklist"
        self.sessions_key = f"{prefix}:sessions"
        self.user_sessions_key = f"{prefix}:user:sessions"

        logger.info("Session manager initialized with Redis backend")

    # =========================================================================
    # TOKEN BLACKLIST
    # =========================================================================

    async def blacklist_token(self, token: str, expires_in: int = 3600):
        """
        Add token to blacklist (for logout/revocation)

        Args:
            token: JWT token string
            expires_in: Token expiration time in seconds
        """
        try:
            # Add to Redis set with expiration
            await self.redis.setex(f"{self.blacklist_key}:{token}", expires_in, "1")
            logger.info("Token added to blacklist")
        except Exception as e:
            logger.error(f"Failed to blacklist token: {e}")

    async def is_token_blacklisted(self, token: str) -> bool:
        """
        Check if token is blacklisted

        Args:
            token: JWT token string

        Returns:
            True if token is blacklisted, False otherwise
        """
        try:
            result = await self.redis.exists(f"{self.blacklist_key}:{token}")
            return result == 1
        except Exception as e:
            logger.error(f"Failed to check token blacklist: {e}")
            return False

    async def clear_blacklist(self):
        """Clear all blacklisted tokens (admin only)"""
        try:
            pattern = f"{self.blacklist_key}:*"
            cursor = 0
            deleted = 0

            while True:
                cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
                if keys:
                    await self.redis.delete(*keys)
                    deleted += len(keys)
                if cursor == 0:
                    break

            logger.info(f"Cleared {deleted} blacklisted tokens")
        except Exception as e:
            logger.error(f"Failed to clear blacklist: {e}")

    # =========================================================================
    # SESSION MANAGEMENT
    # =========================================================================

    async def create_session(
        self,
        username: str,
        role: str,
        ip_address: str,
        user_agent: str,
        expires_in: int = 86400,  # 24 hours
    ) -> str:
        """
        Create new user session

        Args:
            username: Username
            role: User role
            ip_address: Client IP address
            user_agent: Client user agent
            expires_in: Session expiration in seconds

        Returns:
            Session ID
        """
        try:
            session_id = str(uuid.uuid4())

            session_data = {
                "session_id": session_id,
                "username": username,
                "role": role,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "created_at": datetime.utcnow().isoformat(),
                "last_activity": datetime.utcnow().isoformat(),
                "expires_at": (
                    datetime.utcnow() + timedelta(seconds=expires_in)
                ).isoformat(),
            }

            # Store session data
            session_key = f"{self.sessions_key}:{session_id}"
            await self.redis.setex(session_key, expires_in, json.dumps(session_data))

            # Track user sessions (for concurrent session management)
            user_session_key = f"{self.user_sessions_key}:{username}"
            await self.redis.sadd(user_session_key, session_id)
            await self.redis.expire(user_session_key, expires_in)

            logger.info(f"Created session for user: {username} ({session_id})")
            return session_id

        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            return str(uuid.uuid4())  # Fallback to UUID without Redis

    async def get_session(self, session_id: str) -> Optional[dict]:
        """
        Get session data

        Args:
            session_id: Session ID

        Returns:
            Session data dict or None
        """
        try:
            session_key = f"{self.sessions_key}:{session_id}"
            data = await self.redis.get(session_key)

            if data:
                return json.loads(data)

            return None

        except Exception as e:
            logger.error(f"Failed to get session: {e}")
            return None

    async def update_session_activity(self, session_id: str):
        """
        Update last activity timestamp for session

        Args:
            session_id: Session ID
        """
        try:
            session = await self.get_session(session_id)

            if session:
                session["last_activity"] = datetime.utcnow().isoformat()

                session_key = f"{self.sessions_key}:{session_id}"
                ttl = await self.redis.ttl(session_key)

                if ttl > 0:
                    await self.redis.setex(session_key, ttl, json.dumps(session))

        except Exception as e:
            logger.error(f"Failed to update session activity: {e}")

    async def revoke_session(self, session_id: str):
        """
        Revoke/delete session

        Args:
            session_id: Session ID
        """
        try:
            session = await self.get_session(session_id)

            if session:
                username = session.get("username")

                # Remove session data
                session_key = f"{self.sessions_key}:{session_id}"
                await self.redis.delete(session_key)

                # Remove from user sessions set
                if username:
                    user_session_key = f"{self.user_sessions_key}:{username}"
                    await self.redis.srem(user_session_key, session_id)

                logger.info(f"Revoked session: {session_id}")

        except Exception as e:
            logger.error(f"Failed to revoke session: {e}")

    async def revoke_all_user_sessions(self, username: str):
        """
        Revoke all sessions for a user

        Args:
            username: Username
        """
        try:
            user_session_key = f"{self.user_sessions_key}:{username}"
            session_ids = await self.redis.smembers(user_session_key)

            for session_id in session_ids:
                await self.revoke_session(session_id.decode("utf-8"))

            # Clear user sessions set
            await self.redis.delete(user_session_key)

            logger.info(f"Revoked all sessions for user: {username}")

        except Exception as e:
            logger.error(f"Failed to revoke user sessions: {e}")

    async def get_user_sessions(self, username: str) -> list:
        """
        Get all active sessions for a user

        Args:
            username: Username

        Returns:
            List of session data dicts
        """
        try:
            user_session_key = f"{self.user_sessions_key}:{username}"
            session_ids = await self.redis.smembers(user_session_key)

            sessions = []
            for session_id in session_ids:
                session_id_str = session_id.decode("utf-8")
                session = await self.get_session(session_id_str)
                if session:
                    sessions.append(session)

            return sessions

        except Exception as e:
            logger.error(f"Failed to get user sessions: {e}")
            return []

    async def enforce_session_limit(self, username: str, max_sessions: int = 5):
        """
        Enforce maximum concurrent sessions per user

        Args:
            username: Username
            max_sessions: Maximum allowed concurrent sessions
        """
        try:
            sessions = await self.get_user_sessions(username)

            if len(sessions) > max_sessions:
                # Sort by last activity (oldest first)
                sessions.sort(key=lambda x: x.get("last_activity", ""))

                # Revoke oldest sessions
                sessions_to_revoke = sessions[: len(sessions) - max_sessions]

                for session in sessions_to_revoke:
                    await self.revoke_session(session["session_id"])

                logger.info(
                    f"Enforced session limit for {username}: revoked {len(sessions_to_revoke)} sessions"
                )

        except Exception as e:
            logger.error(f"Failed to enforce session limit: {e}")

    # =========================================================================
    # STATISTICS & MONITORING
    # =========================================================================

    async def get_active_sessions_count(self) -> int:
        """Get count of all active sessions"""
        try:
            pattern = f"{self.sessions_key}:*"
            cursor = 0
            count = 0

            while True:
                cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
                count += len(keys)
                if cursor == 0:
                    break

            return count

        except Exception as e:
            logger.error(f"Failed to get session count: {e}")
            return 0

    async def get_session_statistics(self) -> dict:
        """Get session statistics"""
        try:
            active_sessions = await self.get_active_sessions_count()

            # Get blacklisted tokens count
            pattern = f"{self.blacklist_key}:*"
            cursor = 0
            blacklisted_count = 0

            while True:
                cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
                blacklisted_count += len(keys)
                if cursor == 0:
                    break

            return {
                "active_sessions": active_sessions,
                "blacklisted_tokens": blacklisted_count,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get session statistics: {e}")
            return {"active_sessions": 0, "blacklisted_tokens": 0, "error": str(e)}

    async def cleanup_expired_sessions(self):
        """
        Cleanup expired sessions (Redis handles this automatically, but this provides manual cleanup)
        """
        try:
            pattern = f"{self.sessions_key}:*"
            cursor = 0
            cleaned = 0

            while True:
                cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)

                for key in keys:
                    session_id = key.decode("utf-8").split(":")[-1]
                    session = await self.get_session(session_id)

                    if session:
                        expires_at = datetime.fromisoformat(
                            session.get("expires_at", "")
                        )
                        if datetime.utcnow() > expires_at:
                            await self.revoke_session(session_id)
                            cleaned += 1

                if cursor == 0:
                    break

            logger.info(f"Cleaned up {cleaned} expired sessions")
            return cleaned

        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return 0


# ============================================================================
# SYNCHRONOUS FALLBACK (for non-async contexts)
# ============================================================================


class InMemorySessionManager:
    """
    In-memory session manager fallback (when Redis is not available)
    WARNING: This is not suitable for production use in distributed systems
    """

    def __init__(self):
        self.blacklist = set()
        self.sessions = {}
        self.user_sessions = {}
        logger.warning("Using in-memory session manager - not suitable for production!")

    async def blacklist_token(self, token: str, expires_in: int = 3600):
        self.blacklist.add(token)

    async def is_token_blacklisted(self, token: str) -> bool:
        return token in self.blacklist

    async def create_session(
        self,
        username: str,
        role: str,
        ip_address: str,
        user_agent: str,
        expires_in: int = 86400,
    ) -> str:
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "session_id": session_id,
            "username": username,
            "role": role,
            "created_at": datetime.utcnow().isoformat(),
        }

        if username not in self.user_sessions:
            self.user_sessions[username] = set()
        self.user_sessions[username].add(session_id)

        return session_id

    async def get_session(self, session_id: str) -> Optional[dict]:
        return self.sessions.get(session_id)

    async def update_session_activity(self, session_id: str):
        if session_id in self.sessions:
            self.sessions[session_id]["last_activity"] = datetime.utcnow().isoformat()

    async def revoke_session(self, session_id: str):
        if session_id in self.sessions:
            username = self.sessions[session_id].get("username")
            del self.sessions[session_id]

            if username and username in self.user_sessions:
                self.user_sessions[username].discard(session_id)

    async def revoke_all_user_sessions(self, username: str):
        if username in self.user_sessions:
            for session_id in list(self.user_sessions[username]):
                await self.revoke_session(session_id)

    async def get_user_sessions(self, username: str) -> list:
        if username not in self.user_sessions:
            return []

        return [
            self.sessions[sid]
            for sid in self.user_sessions[username]
            if sid in self.sessions
        ]
