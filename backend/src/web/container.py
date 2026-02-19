"""
ServiceContainer – central dependency-injection hub for the MBSE web layer.

Instead of each module managing its own ``_global_singleton`` with an ad-hoc
factory function, **all** long-lived services are registered here and exposed
as FastAPI ``Depends()`` callables.

Usage in a route module::

    from src.web.container import Services

    @router.get("/example")
    async def example(neo4j=Depends(Services.neo4j)):
        return neo4j.execute_query(...)

The container is initialised once during the FastAPI **lifespan** startup and
torn down on shutdown.  Individual services can still be accessed via the
legacy ``get_neo4j_service()`` helpers during the migration period.

Design goals
~~~~~~~~~~~~
* Single source of truth for service lifecycle (startup → shutdown).
* Engine ``GraphStore`` and web ``Neo4jService`` share the **same** Neo4j
  driver so the application opens only one connection pool.
* Thread-safe – guards the singleton with a ``threading.Lock``.
* Supports async services (Redis, QueryCache) alongside sync ones.
"""

from __future__ import annotations

import threading
from typing import Any, Optional

from loguru import logger


class ServiceContainer:
    """
    Holds references to every long-lived service in the backend.

    Attributes
    ----------
    neo4j_service : Neo4jService
        Web-layer Neo4j service (connection pooling, caching).
    graph_store : GraphStore
        Engine-layer graph store that **shares** the same driver.
    redis_service : optional
        Async Redis wrapper (graceful degradation if unavailable).
    query_cache : optional
        Redis-backed query result cache.
    session_manager : optional
        JWT / session manager backed by Redis.
    """

    _instance: Optional["ServiceContainer"] = None
    _lock = threading.Lock()

    # -- singleton -----------------------------------------------------------

    @classmethod
    def instance(cls) -> "ServiceContainer":
        """Return the global container (creating it lazily if needed)."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Tear down the container and release all resources."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance._shutdown()
                cls._instance = None

    # -- init ----------------------------------------------------------------

    def __init__(self) -> None:
        # All slots start as None – populated by ``startup()``.
        self.neo4j_service: Any = None
        self.graph_store: Any = None
        self.redis_service: Any = None
        self.query_cache: Any = None
        self.session_manager: Any = None
        self._started = False

    # -- lifecycle -----------------------------------------------------------

    def startup(self) -> None:
        """
        Create / verify all mandatory services.

        Called once from the FastAPI lifespan ``startup`` phase.
        """
        if self._started:
            return

        # 1. Neo4j service (web layer) -----------------------------------
        from src.web.services.neo4j_service import Neo4jService

        self.neo4j_service = Neo4jService()
        self.neo4j_service.verify_connectivity()
        logger.info("✓ ServiceContainer: Neo4j service ready")

        # 2. Engine GraphStore wrapping the same driver -------------------
        #    This avoids opening a second connection pool.
        from src.engine.stores.neo4j_store import Neo4jGraphStore
        from src.graph.connection import Neo4jConnection

        # Build a thin Neo4jConnection that re-uses the existing driver.
        conn = Neo4jConnection.__new__(Neo4jConnection)
        conn.uri = self.neo4j_service.uri
        conn.user = self.neo4j_service.user
        conn.password = self.neo4j_service.password
        conn.database = self.neo4j_service.database
        conn._driver = self.neo4j_service.driver  # share the pool

        self.graph_store = Neo4jGraphStore.from_connection(
            conn, owns_connection=False
        )
        logger.info("✓ ServiceContainer: Engine GraphStore bridged (shared driver)")

        # 3. Patch the legacy singleton so existing code keeps working ----
        import src.web.services.neo4j_service as _ns

        _ns._neo4j_service = self.neo4j_service

        self._started = True

    async def startup_async(self) -> None:
        """
        Initialise async services (Redis, QueryCache, sessions).

        Called from the FastAPI lifespan after ``startup()`` completes.
        """
        from src.web.services.redis_service import (
            get_redis_service,
            is_redis_enabled,
        )

        if not is_redis_enabled():
            logger.info("ServiceContainer: Redis disabled – skipping async services")
            return

        try:
            self.redis_service = await get_redis_service()

            if self.redis_service and await self.redis_service.is_connected():
                # Session manager
                from src.web.middleware.session_manager import SessionManager
                from src.web.routes.auth_fastapi import set_session_manager

                self.session_manager = SessionManager(self.redis_service.client)
                set_session_manager(self.session_manager)
                logger.info("✓ ServiceContainer: Session manager ready")

                # Query cache
                from src.web.services.query_cache import get_query_cache

                self.query_cache = await get_query_cache()
                if self.query_cache and getattr(self.query_cache, "enabled", False):
                    self.neo4j_service.set_cache(self.query_cache)
                    logger.info("✓ ServiceContainer: Query cache attached")
        except Exception as exc:
            logger.warning(f"ServiceContainer: async services unavailable – {exc}")

    def _shutdown(self) -> None:
        """Release resources (called by ``reset()``)."""
        if self.graph_store is not None:
            # We set owns_connection=False, so close() is a no-op, but be safe.
            try:
                self.graph_store.close()
            except Exception:
                pass
            self.graph_store = None

        if self.neo4j_service is not None:
            try:
                self.neo4j_service.close()
            except Exception:
                pass
            self.neo4j_service = None

        # Reset legacy singleton too
        try:
            import src.web.services.neo4j_service as _ns

            _ns._neo4j_service = None
        except Exception:
            pass

        self._started = False
        logger.info("ServiceContainer: shut down")


# ---------------------------------------------------------------------------
# FastAPI Depends() callables
# ---------------------------------------------------------------------------

class Services:
    """
    Namespace of FastAPI dependency functions.

    Usage::

        @router.get("/nodes")
        async def list_nodes(neo4j=Depends(Services.neo4j)):
            ...
    """

    @staticmethod
    def neo4j():
        """Provide the Neo4jService singleton."""
        return ServiceContainer.instance().neo4j_service

    @staticmethod
    def graph_store():
        """Provide the engine-layer GraphStore (shared driver)."""
        return ServiceContainer.instance().graph_store

    @staticmethod
    def redis():
        """Provide the Redis service (may be None)."""
        return ServiceContainer.instance().redis_service

    @staticmethod
    def query_cache():
        """Provide the QueryCache (may be None)."""
        return ServiceContainer.instance().query_cache

    @staticmethod
    def session_manager():
        """Provide the SessionManager (may be None)."""
        return ServiceContainer.instance().session_manager
